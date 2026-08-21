#!/usr/bin/env python3
"""
全ページ共通フッターの差し込み

  tag-work.github.io/tools/footer.html      ← 文言を直すのはここだけ
  tag-work.github.io/tools/build_footer.py

使い方（どこから実行してもよい）:

  python3 tag-work.github.io/tools/build_footer.py            # 差し込む
  python3 tag-work.github.io/tools/build_footer.py --check    # 書き換えずに差分の有無だけ見る

仕組み:

  各ページの <!-- FOOTER:START --> 〜 <!-- FOOTER:END --> の間を footer.html で
  丸ごと置き換える。マーカーがまだ無いページには、初回だけ TARGETS の mode に
  従って設置する。以降は何度実行しても結果が変わらない（冪等）。

  出力は普通の静的HTML。JSに依存しないので、検索エンジンにもJS無効でも見える。

注意:

  - リポジトリが分かれているので push は別々。最後に対象を一覧で出す
  - **eigo-quiz / sansu-quiz / toilet-gacha は sw.js のキャッシュ名を手で上げること。**
    Service Worker が同一オリジンを cache-first で拾うので、上げないと
    一度でも for-parents を開いた端末は古いフッターを見続ける。
    deploy.sh の自動bumpは「リポジトリ直下の index.html に差分があるとき」だけなので、
    今回のように for-parents/index.html しか変わらないケースでは働かない
  - hannya/ 配下の読みものページ38本は build_pages.py の生成物なので対象外。
    そちらにも入れたくなったら build_pages.py 側のテンプレートに足すこと
"""

import re
import sys
from pathlib import Path

FOOTER = Path(__file__).resolve().parent / "footer.html"

START = "<!-- FOOTER:START"
END = "<!-- FOOTER:END -->"

# (ワークスペース直下からの相対パス, 初回設置のしかた)
#   replace-footer … 既存の <footer>…</footer> を置き換える
#   append         … </body> の直前に足す（既存フッターは残す）
TARGETS = [
    ("eigo-quiz/for-parents/index.html",             "replace-footer"),
    ("sansu-quiz/for-parents/index.html",            "replace-footer"),
    ("toilet-gacha/for-parents/index.html",          "replace-footer"),
    ("tag-work.github.io/hannya/index.html",         "append"),
    ("tag-work.github.io/hannya/privacy.html",       "append"),
    ("tag-work.github.io/hannya/terms.html",         "append"),
]

# sw.js の bump が要るリポジトリ（Service Worker が cache-first のため）
SW_REPOS = {"eigo-quiz", "sansu-quiz", "toilet-gacha"}

BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
FOOTER_RE = re.compile(r"[ \t]*<footer\b(?![^>]*tagc-footer).*?</footer>\n?", re.S)


def find_root() -> Path:
    """deploy.sh を持つ祖先ディレクトリ（= ~/tagc.works）を探す。"""
    for d in Path(__file__).resolve().parents:
        if (d / "deploy.sh").exists():
            return d
    raise SystemExit("deploy.sh を持つワークスペースが見つからない。配置場所を確認する")


def build(path: Path, mode: str, block: str) -> str | None:
    """差し込み後の中身を返す。変更なしなら None。"""
    src = path.read_text(encoding="utf-8")

    if START in src:
        if END not in src:
            raise SystemExit(f"{path}: FOOTER:START はあるのに FOOTER:END が無い")
        out = BLOCK_RE.sub(lambda _: block, src, count=1)

    elif mode == "replace-footer":
        if not FOOTER_RE.search(src):
            raise SystemExit(f"{path}: 置き換える <footer> が見つからない")
        out = FOOTER_RE.sub(lambda _: block + "\n", src, count=1)

    elif mode == "append":
        if "</body>" not in src:
            raise SystemExit(f"{path}: </body> が見つからない")
        out = src.replace("</body>", block + "\n</body>", 1)

    else:
        raise SystemExit(f"{path}: 未知の mode {mode!r}")

    return None if out == src else out


def main() -> int:
    check = "--check" in sys.argv
    root = find_root()

    if not FOOTER.exists():
        raise SystemExit(f"{FOOTER} が無い")
    block = FOOTER.read_text(encoding="utf-8").strip()
    if START not in block or END not in block:
        raise SystemExit("footer.html に FOOTER:START / FOOTER:END が入っていない")

    print(f"ワークスペース: {root}\n")

    changed, repos = [], set()
    for rel, mode in TARGETS:
        path = root / rel
        if not path.exists():
            raise SystemExit(f"{path} が無い。リポジトリが揃っているか確認する")
        out = build(path, mode, block)
        if out is None:
            print(f"  そのまま  {rel}")
            continue
        changed.append(rel)
        repos.add(rel.split("/")[0])
        if not check:
            path.write_text(out, encoding="utf-8")
        print(f"  {'差分あり' if check else '書き換え '}  {rel}")

    print()
    if not changed:
        print("すべて最新。やることなし。")
        return 0
    if check:
        print(f"{len(changed)} ファイルに差分。--check を外すと書き換える。")
        return 1

    print(f"{len(changed)} ファイルを書き換えた。push が必要なリポジトリ:")
    for r in sorted(repos):
        print(f"  - {r}")

    need_bump = sorted(repos & SW_REPOS)
    if need_bump:
        print("\n⚠️  次のリポジトリは sw.js の const V=\"...-vN\" を手で +1 すること。")
        print("   Service Worker が cache-first なので、上げないと古いフッターが残る。")
        print("   deploy.sh の自動bumpは直下の index.html を見るので、今回は働かない。")
        for r in need_bump:
            print(f"  - {r}/sw.js")

    print("\n表示を確認してから deploy する。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
