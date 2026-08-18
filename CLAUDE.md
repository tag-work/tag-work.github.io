# tagc.works ポートフォリオ — プロジェクトメモ

https://tagc.works/ のトップページ。GitHub Pages のユーザーサイト用リポジトリ。
ワークスペース共通のルールは親ディレクトリの CLAUDE.md を参照。

## 重要

- **`CNAME` ファイルを削除しない。** 中身は `tagc.works`。消すとカスタムドメインが外れ、
  配下の eigo-quiz / sansu-quiz も含めてドメインでのアクセスができなくなる
- **リポジトリ名 `tag-work.github.io` はGitHubユーザー名と一致している必要がある。** 変更しない
- `sitemap.xml` はドメイン全体の正式版。ページを増やしたらここに追記する
  （eigo-quiz 側にも同名ファイルがあるが、そちらは使われない）

## 構成

- `index.html` — トップページ。フレームワークなし、外部依存は Google Fonts だけ
- `hannya/` — 毎日般若心経（iOS/Android）のLP。旧 hannya.app から移設したもの。
  `index.html` / `privacy.html` / `terms.html` と画像。リンクはすべて相対パス。
  eigo-quiz / sansu-quiz と違い別リポジトリにしていないのは、
  hannya-lp リポジトリを hannya.app からのリダイレクト置き場として残しているため
- `hannya/index.html` — アプリのLP。手で書いているが、「よみもの」一覧と構造化データは生成される
- `hannya/towa/` `zenbun/` `imi/` `yougo/` `tonaekata/` `oboekata/` `shakyo/` `butsuzo/` —
  検索の受け皿になる読みものページ（計38ページ）。**手で編集しない。** すべて生成物
- `hannya/tools/build_pages.py` — 上のページと sitemap.xml を生成する
- `app-ads.txt` — AdMob用。毎日般若心経のストア掲載URLがこのドメインなので、
  ドメイン直下に置く必要がある。**消さない**

## hannya/ の読みものページ

原稿は `../hannya-app/src/data/` が唯一の真実の源。
アプリの本文・現代語訳・解説・仏さまの説明を直したら、必ずこれを流し直す。

```bash
python3 hannya/tools/build_pages.py
./deploy.sh top "..."
```

生成されるもの（38ページ）:

| URL | 中身 | 原資 |
|---|---|---|
| `towa/` | 般若心経とは（成立・歴史・宗派） | スクリプト内の散文 |
| `zenbun/` | 全文（ふりがな・現代語訳） | `sutra.ts` `sutra_ruby_all.ts` |
| `imi/` | 意味（9つの場面） | `sutra.ts` |
| `yougo/` | 用語集15語 | スクリプト内 `GLOSSARY` |
| `tonaekata/` | 唱え方 | スクリプト内 `STEPS` |
| `oboekata/` | 覚え方 | `sutra.ts` ＋ `OBOE_STEPS` |
| `shakyo/` | 写経（印刷用の手本つき） | `sutra.ts` ＋ `SHAKYO_STEPS` |
| `butsuzo/` ＋ 30体 | 仏さま図鑑 | `deities.ts` |

守ること:

- **生成物を手で直さない。** 直すならアプリ側のデータか、スクリプト内の定数
- `hannya/index.html` の「よみもの」セクションと `<!-- LD:START -->` の中身も生成される。
  記事を足すときはスクリプトの `HUBS` に1行足せばLPのリンクも sitemap も揃う
- sitemap.xml の `/hannya/` 行はスクリプトが入れ直す。手で足さない
- 仏さまのURLはスクリプトの `SLUG` で決めている。**公開後は変えない**（リンクが切れる）
- AdSense は `ADS = False` で切ってある。お経の本文の横に広告を並べたくないため
- **効能・ご利益は書かない。** 「唱えると○○に効く」は載せない方針。
  全ページのフッターに「効果を約束するものではありません」と入れてある
- 9段の個別ページ（`imi/shikisokuzeku/` など）は**あえて作っていない**。
  `imi/` と内容が重なって共食いするため

## デザイン

両クイズとは意図的に別の顔にしている。見るのが大人（本人・仕事関係・気になった親）だから。

- テーマは紙の台帳。罫線の背景に、プロジェクトが `001` `002` と番号つきで並ぶ
- 色は3色だけ。紙 `#F6F3EC` / 墨 `#171614` / 朱 `#C8452B`
- 見出しとラベルは IBM Plex Mono、本文は Zen Kaku Gothic New
- 行にホバーすると朱色で `OPEN →` が出る

## プロジェクトを追加するとき

`<!-- ▼ プロジェクトを増やすときは… -->` のコメント下にある `<a class="item">` を複製し、
番号を繰り上げて中身を書き換える。

- ステータスは `LIVE`（公開中）と `WIP`（作りかけ）の2種類
- 作りかけは `<a class="item soon">` にして href を付けない
- `desc` は1〜2行。**何のために作ったか、誰の何が楽になるか**を書く
- 追加したら `sitemap.xml` にもURLを足す

## 書かないこと

- 会社名・本名は出さない。クレジットは `tagc`
- 連絡先は `hey@tagc.works` のみ
