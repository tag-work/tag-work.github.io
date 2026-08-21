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
- `tools/footer.html` — **ドメイン全体の共通フッターの実体。文言を直すのはここだけ**
- `tools/build_footer.py` — そのフッターを対象ページの
  `<!-- FOOTER:START -->` 〜 `<!-- FOOTER:END -->` に差し込む。ワークスペース直下から実行する。
  対象は6ページ（3アプリの `for-parents/` と `hannya/` の index / privacy / terms）。
  **子どもが遊ぶ画面とトップページには入れない**（前者は外部リンクを置かない約束、後者は自分へのリンクになるため）
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
- `hannya/index.html` の共通フッター（`FOOTER:START` 〜 `FOOTER:END`）は `</body>` の直前にあり、
  `build_pages.py` が書き換える `<section class="read">` と `<!-- LD:START -->` の外側なので流し直しても消えない。
  ただし **読みもの38ページには共通フッターを入れていない。**
  入れるなら `build_pages.py` 側のテンプレートに足すこと（生成物を手で直さない）

## デザイン

両クイズとは意図的に別の顔にしている。見るのが大人（本人・仕事関係・気になった親）だから。

- 白いカードを2カラムのグリッドに並べる。720px 以下で1カラムに落ちる
- カードの中身は上から **アイコン＋プラットフォームのチップ / 番号 `001` / タイトル / 説明 / タグ**
- アイコンは各アプリの実物を出す。`https://tagc.works/{app}/icons/icon-192.png`、
  般若心経だけ `https://tagc.works/hannya/icon.png`。
  **絶対パスのままにしてある**（プレビュー環境でも見えるようにするため）。相対にしない
- グリッドの上に **カテゴリー切替タブ**。`ALL` / `子ども向け` / `ライフスタイル`。
  素のJSでカードの `hidden` を出し入れするだけ。依存ライブラリなし
- 色は 紙 `#FAF9F6` / カード白 `#FFFFFF` / 墨 `#171614` / 朱 `#C8452B` / 罫 `#E8E4DB`
- 見出しとラベルは IBM Plex Mono、本文は Zen Kaku Gothic New
- カードはホバーで少し浮く（`translateY(-2px)` ＋ 影）。台帳時代の `OPEN →` は廃止
- 小アイコン（Web / iOS・Android のチップ）はインラインSVG。
  共通ルール3のとおり `<symbol>` + `<use>` は使わない

## プロジェクトを追加するとき

`<!-- ▼ プロジェクトを増やすときは… -->` のコメント下にある `<a class="item">` を複製し、
番号を繰り上げて中身を書き換える。

- **`data-cat` に `kids` か `life` を必ず入れる。**
  入れ忘れるとタブで絞ったときにそのカードだけ消えて、`ALL` でしか見えなくなる
- タブの件数表示（`<i>4</i>` `<i>3</i>` `<i>1</i>`）は手書き。**カードを増やしたら一緒に直す**
- アイコンの `<img>` も足す。`https://tagc.works/{app}/icons/icon-192.png` の形（絶対パスのまま）
- チップはプラットフォーム（`Web` か `iOS / Android`）だけ。
  **`LIVE` バッジは廃止した。** 載っているものは公開済みという前提なので、全部に付く印は情報量がない
- **作りかけはトップに載せない。公開してから追加する。**
  台帳時代の `WIP` チップと `.item.soon`（href なしの淡いグレー行）は、
  カード型に合う見せ方が決まっていないのでCSSごと落としてある。
  「もうすぐ公開」を出したくなったら、まずチップと非リンクカードのスタイルを設計するところから
- `desc` は1〜2行。**何のために作ったか、誰の何が楽になるか**を書く
- 追加したら `sitemap.xml` にもURLを足す

## 書かないこと

- 会社名・本名は出さない。クレジットは `tagc`
- 連絡先は `hey@tagc.works` のみ
