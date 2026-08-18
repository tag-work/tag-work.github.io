#!/usr/bin/env python3
"""
毎日般若心経 — 検索の受け皿になる読みものページを生成する。

  python3 hannya/tools/build_pages.py

原稿はアプリ本体（../hannya-app/src/data/）を唯一の真実の源にしている。
アプリの本文・現代語訳・解説・仏さまの説明を直したら、このスクリプトを
流し直すだけで Web 側も揃う。ここで文言を書き足さない。
（散文しか持ちようがないページ＝唱え方・覚え方・写経・とは・用語集だけ例外で、
　その原稿はこのファイルの下半分に定数として置いてある）

出力:
  hannya/towa/            般若心経とは（成立・歴史・宗派）
  hannya/zenbun/          全文（ふりがな・現代語訳つき）
  hannya/imi/             意味（9つの場面）
  hannya/yougo/           用語集
  hannya/tonaekata/       唱え方
  hannya/oboekata/        覚え方
  hannya/shakyo/          写経
  hannya/butsuzo/         仏さま図鑑（一覧）
  hannya/butsuzo/<slug>/  仏さま30体の個別ページ
  ../sitemap.xml          /hannya/ 配下のURLを入れ直す
"""
import json, os, re, sys

HANNYA  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../hannya
SITE    = os.path.dirname(HANNYA)                                       # .../tag-work.github.io
APPDATA = os.path.normpath(os.path.join(SITE, "..", "hannya-app", "src", "data"))

BASE  = "https://tagc.works/hannya"
GA_ID = "G-SE4GTXSLEW"
APPSTORE = "https://apps.apple.com/app/id6775722614"
PLAY     = "https://play.google.com/store/apps/details?id=work.tagc.hannya"

# 読みものページに AdSense を出すかどうか。お経の本文の横に広告を並べたくないので既定はオフ。
ADS = False
ADS_CLIENT, ADS_SLOT = "ca-pub-7791812422300435", "5102407537"


# ============================================================
# TypeScript のデータファイルを読む
# ============================================================
def _js_literal(text, varname):
    """`(export )?const <varname>... = <リテラル>;` の <リテラル> を切り出して JSON に直す。

    tsc も node も使わずに済ませたいので、文字列と // コメントだけを正しく扱う
    小さなスキャナで処理する。本文に " や ' が混ざっても壊れない。
    """
    m = re.search(r"(?:export\s+)?const\s+" + varname + r"\b[^=]*=\s*", text)
    if not m:
        sys.exit(f"[build] {varname} が見つかりません")
    i, n = m.end(), len(text)
    out, depth, started = [], 0, False
    while i < n:
        c = text[i]
        if c in "'\"":                      # 文字列 → JSON文字列として出し直す
            q, j, buf = c, i + 1, []
            while j < n and text[j] != q:
                if text[j] == "\\":
                    buf.append(text[j:j + 2]); j += 2; continue
                buf.append(text[j]); j += 1
            out.append(json.dumps("".join(buf).replace("\\'", "'")))
            i = j + 1
            continue
        if text.startswith("//", i):
            i = text.find("\n", i)
            if i < 0: break
            continue
        if text.startswith("/*", i):
            i = text.find("*/", i) + 2
            continue
        if c in "[{":
            depth += 1; started = True
        elif c in "]}":
            depth -= 1
        out.append(c)
        i += 1
        if started and depth == 0:
            break
    s = "".join(out)
    s = re.sub(r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:", r'\1"\2":', s)   # 裸のキーを引用符でくくる
    s = re.sub(r",(\s*[}\]])", r"\1", s)                             # 末尾カンマを落とす
    return json.loads(s)


def _read(name):
    return open(os.path.join(APPDATA, name), encoding="utf-8").read()


def load_sutra():
    ruby_map = _js_literal(_read("sutra_ruby_all.ts"), "SUTRA_RUBY")
    sutra = _js_literal(_read("sutra.ts"), "SUTRA")
    for seg in sutra:
        for ln in seg["lines"]:
            if ln["k"] in ruby_map:
                ln["r"] = ruby_map[ln["k"]]
    return sutra


def load_deities():
    raw = _js_literal(_read("deities.ts"), "RAW")
    for i, d in enumerate(raw):
        d["slug"] = SLUG.get(d["name"]) or romaji(d["yomi"])
        d["idx"] = i
    return raw


# ------------------------------------------------------------
# かな → ローマ字（SLUG に無い仏さまが増えたときの保険）
# ------------------------------------------------------------
_KANA = {
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo", "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho", "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo", "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo", "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo", "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "o", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
}


def romaji(kana):
    out, i = [], 0
    while i < len(kana):
        two = kana[i:i + 2]
        if two in _KANA:
            out.append(_KANA[two]); i += 2; continue
        c = kana[i]
        if c == "っ":
            nxt = _KANA.get(kana[i + 1:i + 3]) or _KANA.get(kana[i + 1:i + 2], "")
            if nxt: out.append(nxt[0])
            i += 1; continue
        if c == "ー":
            i += 1; continue
        if c == "う" and out and out[-1].endswith(("o", "u")):
            i += 1; continue          # 長音の「う」は落とす（じぞう→jizo）
        out.append(_KANA.get(c, ""))
        i += 1
    return "".join(out)


# 仏さまのURLは手で決める（自動ローマ字より読みやすいので）
SLUG = {
    "釈迦如来": "shaka-nyorai", "薬師如来": "yakushi-nyorai", "阿弥陀如来": "amida-nyorai",
    "大日如来": "dainichi-nyorai", "阿閦如来": "ashuku-nyorai", "毘盧遮那如来": "birushana-nyorai",
    "観音菩薩": "kannon-bosatsu", "地蔵菩薩": "jizo-bosatsu", "弥勒菩薩": "miroku-bosatsu",
    "文殊菩薩": "monju-bosatsu", "普賢菩薩": "fugen-bosatsu", "勢至菩薩": "seishi-bosatsu",
    "虚空蔵菩薩": "kokuzo-bosatsu", "日光菩薩": "nikko-bosatsu",
    "不動明王": "fudo-myoo", "愛染明王": "aizen-myoo", "降三世明王": "gozanze-myoo",
    "軍荼利明王": "gundari-myoo", "大威徳明王": "daiitoku-myoo", "金剛夜叉明王": "kongoyasha-myoo",
    "弁才天": "benzaiten", "吉祥天": "kisshoten", "大黒天": "daikokuten",
    "毘沙門天": "bishamonten", "帝釈天": "taishakuten", "梵天": "bonten",
    "韋駄天": "idaten", "広目天": "komokuten", "持国天": "jikokuten", "歓喜天": "kangiten",
}

# アプリのイラストの持ち物コード → 日本語。ページに「目じるし」として出す。
PART = {
    "halo": "光背", "haloBig": "大きな光背", "yakko": "薬壺（やっこ）", "tsubo": "水瓶（すいびょう）",
    "shaku": "錫杖（しゃくじょう）", "ken": "剣", "hasu": "蓮の花", "houju": "如意宝珠（にょいほうじゅ）",
    "sun": "日輪", "yumi": "弓と矢", "sanko": "三鈷杵（さんこしょ）", "snake": "蛇",
    "gyu": "水牛", "goko": "五鈷杵（ごこしょ）", "biwa": "琵琶", "tsuchi": "打ち出の小槌",
    "tou": "宝塔", "kongo": "金剛杵（こんごうしょ）", "hata": "幢幡（どうばん）", "fukurou": "袋",
    "none": "",
}

CAT_INTRO = {
    "如来": ("如来（にょらい）は、さとりを開いた仏さま。仏の世界でいちばん上の位にあたります。"
             "装飾を身につけず、質素な衣をまとった姿で表されるのが特徴です。"),
    "菩薩": ("菩薩（ぼさつ）は、さとりを求めながら、同時に人々を救おうとしている存在。"
             "如来になる一歩手前とされ、冠や装身具をつけた華やかな姿で表されます。"),
    "明王": ("明王（みょうおう）は、やさしい説き方では耳を貸さない人をも導くとされる仏さま。"
             "怒りの表情と炎を背負った姿は、大日如来が姿を変えたものと説明されます。"),
    "天": ("天（てん）は、もともとインドの神々が仏教に取り入れられたもの。"
           "仏法とそれを信じる人を守る役どころで、七福神や四天王として親しまれています。"),
}
CAT_SLUG = {"如来": "nyorai", "菩薩": "bosatsu", "明王": "myoo", "天": "ten"}


# ============================================================
# 共通の部品
# ============================================================
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ruby(line, wrap=True):
    """漢文にふりがなを振る。r が無い行は素のまま返す。"""
    if not line.get("r"):
        return esc(line["k"])
    out, idx = [], 0
    for ch in line["k"]:
        if ch in " 　":
            out.append('<span class="sp"></span>')
            continue
        if idx < len(line["r"]):
            k, y = line["r"][idx]
            out.append(f"<ruby>{esc(k)}<rt>{esc(y)}</rt></ruby>" if wrap else esc(k))
            idx += 1
        else:
            out.append(esc(ch))
    return "".join(out)


CSS = """
:root{--paper:#fbf3ea;--paper2:#fff9f0;--washi:#f3e6d2;--ink:#5a4636;--ink-soft:#8a7563;
  --navy:#233a5e;--navy-deep:#1b2c47;--gold:#c2902c;--gold-pale:#f3dca0;--shu:#9b3a2d;
  --line:rgba(90,70,54,.14);--maxw:760px}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Zen Maru Gothic',sans-serif;color:var(--ink);background:var(--paper);
  line-height:1.95;-webkit-font-smoothing:antialiased}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 22px}
a{color:var(--shu)}
.top{background:linear-gradient(180deg,#fff4e2,#ffe9c9);padding:16px 0 0}
.bc{font-size:12px;color:var(--ink-soft);padding-bottom:14px}
.bc a{color:var(--ink-soft);text-decoration:none}
.bc a:hover{text-decoration:underline}
header.hd{padding:14px 0 34px;background:linear-gradient(180deg,#ffe9c9,var(--paper))}
h1{font-family:'Shippori Mincho',serif;font-size:clamp(24px,5.2vw,33px);line-height:1.5;
  color:var(--navy);font-weight:600;letter-spacing:.02em}
h1 small{display:block;font-size:14px;color:var(--ink-soft);font-family:'Zen Maru Gothic',sans-serif;
  font-weight:400;letter-spacing:.06em;margin-top:8px}
.lede{margin-top:16px;font-size:15px;color:var(--ink-soft)}
main{padding:34px 0 10px}
h2{font-family:'Shippori Mincho',serif;font-size:21px;color:var(--navy);font-weight:600;
  margin:46px 0 14px;padding-bottom:9px;border-bottom:2px solid var(--gold-pale);
  display:flex;align-items:baseline;gap:11px}
h2 .n{font-size:12px;color:var(--gold);letter-spacing:.14em;flex:none}
h3{font-family:'Shippori Mincho',serif;font-size:17px;color:var(--navy);margin:30px 0 8px}
p{margin:12px 0;font-size:15.5px}
.toc{background:var(--paper2);border:1px solid var(--line);border-radius:16px;padding:20px 24px;margin:26px 0}
.toc b{font-size:13px;letter-spacing:.1em;color:var(--gold)}
.toc ol,.toc ul{margin:10px 0 0 1.2em;font-size:14.5px}
.toc li{margin:5px 0}
.toc a{color:var(--ink);text-decoration:none}
.toc a:hover{color:var(--shu)}
.seg{background:var(--paper2);border:1px solid var(--line);border-radius:18px;padding:22px 24px;margin:16px 0}
.kan{font-family:'Shippori Mincho',serif;font-size:20px;line-height:2.9;color:var(--navy-deep);letter-spacing:.04em}
.kan .sp{display:inline-block;width:.7em}
.kan ruby rt{font-size:.46em;color:var(--ink-soft);font-family:'Zen Maru Gothic',sans-serif;
  font-weight:400;letter-spacing:0}
.yomi{font-size:13.5px;color:var(--ink-soft);margin-top:4px}
.yaku{margin-top:12px;padding-top:12px;border-top:1px dashed var(--line);font-size:15.5px}
.point{margin-top:14px;background:var(--washi);border-radius:12px;padding:12px 16px;font-size:14.5px}
.point b{color:var(--shu)}
.point .lb{display:block;font-size:11px;letter-spacing:.14em;color:var(--gold);margin-bottom:3px}
.through{background:var(--navy);color:#fff8ec;border-radius:20px;padding:26px 26px 28px;margin:26px 0}
.through .lb{font-size:11px;letter-spacing:.16em;color:var(--gold-pale)}
.through .kan{color:#fff8ec;font-size:19px;line-height:3.1;margin-top:12px}
.through .kan ruby rt{color:#d9c9a8}
.note{font-size:13.5px;color:var(--ink-soft);background:var(--paper2);border-left:3px solid var(--gold-pale);
  padding:12px 16px;margin:20px 0;border-radius:0 10px 10px 0}
.steps{counter-reset:s;list-style:none;margin:18px 0}
.steps li{counter-increment:s;position:relative;padding:16px 0 16px 46px;border-bottom:1px solid var(--line)}
.steps li:before{content:counter(s);position:absolute;left:0;top:16px;width:29px;height:29px;
  border-radius:50%;background:var(--navy);color:#fff;font-size:13px;display:grid;place-items:center}
.steps b{display:block;color:var(--navy);font-size:16px;margin-bottom:2px}
.faq{margin:18px 0}
.faq details{border-bottom:1px solid var(--line);padding:14px 0}
.faq summary{cursor:pointer;font-weight:500;color:var(--navy);font-size:15.5px;list-style:none}
.faq summary::-webkit-details-marker{display:none}
.faq summary:before{content:'Q ';color:var(--gold);font-weight:600}
.faq p{font-size:14.5px;margin:8px 0 2px}
table.tb{width:100%;border-collapse:collapse;margin:18px 0;font-size:14.5px}
table.tb th,table.tb td{border-bottom:1px solid var(--line);padding:11px 8px;text-align:left;vertical-align:top}
table.tb th{color:var(--navy);font-weight:500}
table.tb tbody th{white-space:nowrap}
table.tb thead th{color:var(--gold);font-size:12px;letter-spacing:.1em}
dl.gl dt{font-family:'Shippori Mincho',serif;font-size:17px;color:var(--navy);margin:26px 0 4px;
  padding-top:16px;border-top:1px solid var(--line)}
dl.gl dt span{font-size:12px;color:var(--ink-soft);margin-left:9px;font-family:'Zen Maru Gothic',sans-serif}
dl.gl dd{font-size:15px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin:16px 0}
.card{display:block;background:var(--paper2);border:1px solid var(--line);border-radius:14px;
  padding:14px 16px;text-decoration:none;color:var(--ink);transition:.15s}
.card:hover{border-color:var(--gold);transform:translateY(-2px)}
.card b{display:block;color:var(--navy);font-size:15.5px}
.card span{font-size:12px;color:var(--ink-soft)}
.chip{display:inline-block;font-size:11px;letter-spacing:.1em;color:var(--gold);
  border:1px solid var(--gold-pale);border-radius:999px;padding:2px 10px;margin-bottom:8px}
.cta{background:linear-gradient(180deg,var(--navy),var(--navy-deep));color:#fff8ec;
  border-radius:24px;padding:32px 26px;margin:46px 0 10px;text-align:center}
.cta img{width:64px;height:64px;border-radius:16px}
.cta h2{border:0;color:#fff8ec;display:block;margin:14px 0 6px;font-size:19px;padding:0}
.cta p{font-size:13.5px;color:#d9c9a8;margin:0 0 16px}
.badges{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.badge{display:inline-block;background:var(--gold);color:#3a2a10;text-decoration:none;
  font-size:14px;font-weight:700;padding:11px 20px;border-radius:999px}
.badge small{display:block;font-size:10px;font-weight:400;opacity:.75}
.rel{display:grid;gap:10px;margin:20px 0 0}
.rel a{display:block;background:var(--paper2);border:1px solid var(--line);border-radius:14px;
  padding:14px 18px;text-decoration:none;color:var(--ink)}
.rel a:hover{border-color:var(--gold)}
.rel b{display:block;color:var(--navy);font-size:15.5px}
.rel span{font-size:13px;color:var(--ink-soft)}
.pager{display:flex;justify-content:space-between;gap:12px;margin:26px 0 0;font-size:13.5px}
.pager a{flex:1;background:var(--paper2);border:1px solid var(--line);border-radius:14px;
  padding:12px 16px;text-decoration:none;color:var(--ink)}
.pager a:last-child{text-align:right}
.pager span{display:block;font-size:11px;color:var(--ink-soft)}
footer{margin-top:50px;padding:26px 0 40px;border-top:1px solid var(--line);font-size:12.5px;color:var(--ink-soft)}
footer .links{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px}
footer a{color:var(--ink-soft)}
.trace{font-family:'Shippori Mincho',serif;font-size:23px;line-height:2.6;color:#c9bda9;letter-spacing:.22em}
@media print{
  body{background:#fff;color:#000}
  .top,.hd,.cta,.rel,footer,.note,.noprint{display:none!important}
  .trace{color:#c8c8c8;font-size:26px}
  .wrap{max-width:none;padding:0}
}
@media(max-width:600px){.kan{font-size:18px}.seg{padding:18px 16px}.through{padding:22px 18px}}
"""


def head(title, desc, path, ld_tags="", up="../"):
    url = f"{BASE}/{path}" if path else BASE + "/"
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
           f'?client={ADS_CLIENT}" crossorigin="anonymous"></script>') if ADS else ""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/icon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="毎日般若心経">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#233a5e">
<link rel="icon" href="{up}icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&family=Shippori+Mincho:wght@500;600&display=swap" rel="stylesheet">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
gtag('js',new Date());gtag('config','{GA_ID}');</script>
{ads}
<style>{CSS}</style>
{ld_tags}
</head>
<body>
"""


def ld(obj):
    return f'<script type="application/ld+json">{json.dumps(obj, ensure_ascii=False)}</script>'


def crumbs(trail, up="../"):
    """trail = [(名前, パス)] ／ 先頭に毎日般若心経を足す。"""
    items = [{"@type": "ListItem", "position": 1, "name": "毎日般若心経", "item": BASE + "/"}]
    for i, (name, path) in enumerate(trail):
        items.append({"@type": "ListItem", "position": i + 2, "name": name,
                      "item": f"{BASE}/{path}"})
    ldtag = ld({"@context": "https://schema.org", "@type": "BreadcrumbList",
                "itemListElement": items})
    depth = up.count("../")
    links = [f'<a href="{up}">毎日般若心経</a>']
    for i, (name, _) in enumerate(trail):
        if i == len(trail) - 1:
            links.append(esc(name))
        else:
            links.append(f'<a href="{"../" * (depth - i - 1)}">{esc(name)}</a>')
    html = (f'<div class="top"><div class="wrap"><nav class="bc">'
            f'{" ／ ".join(links)}</nav></div></div>')
    return html, ldtag


def article_ld(title, desc, path):
    return ld({"@context": "https://schema.org", "@type": "Article",
               "headline": title, "description": desc, "inLanguage": "ja",
               "mainEntityOfPage": f"{BASE}/{path}",
               "author": {"@type": "Organization", "name": "毎日般若心経"},
               "publisher": {"@type": "Organization", "name": "tagc", "url": "https://tagc.works/"}})


def faq_ld(pairs):
    return ld({"@context": "https://schema.org", "@type": "FAQPage",
               "mainEntity": [{"@type": "Question", "name": q,
                               "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]})


def faq_html(pairs):
    return ('<div class="faq">'
            + "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>"
                      for q, a in pairs) + "</div>")


def howto_ld(name, desc, steps):
    return ld({"@context": "https://schema.org", "@type": "HowTo",
               "name": name, "description": desc, "inLanguage": "ja",
               "step": [{"@type": "HowToStep", "position": i + 1, "name": n, "text": t}
                        for i, (n, t) in enumerate(steps)]})


def cta(up="../"):
    return f"""<div class="cta">
  <img src="{up}icon.png" alt="毎日般若心経">
  <h2>お手本の声に合わせて、となえる</h2>
  <p>ふりがな付きの縦書きと、読み上げ。続けた日はカレンダーに残ります。ずっと無料です。</p>
  <div class="badges">
    <a class="badge" href="{APPSTORE}">App Store<small>でダウンロード</small></a>
    <a class="badge" href="{PLAY}">Google Play<small>でダウンロード</small></a>
  </div>
</div>"""


HUBS = [
    ("towa/",      "般若心経とは｜成立と歴史",       "だれが、いつ、なぜ書いたのか。宗派による扱いの違いまで。"),
    ("zenbun/",    "全文（ふりがな・現代語訳つき）", "262文字の全文を、漢字一字ずつのふりがなと現代語訳で。"),
    ("imi/",       "意味を9つの場面で読み解く",     "「色即是空」から「羯諦羯諦」まで、流れで意味をつかむ。"),
    ("yougo/",     "用語集",                        "空・五蘊・波羅蜜多・涅槃など、つまずく言葉をまとめて。"),
    ("tonaekata/", "唱え方",                        "姿勢・速さ・息継ぎ・回数。はじめての方向けの基本。"),
    ("oboekata/",  "覚え方",                        "262文字を9つに割って、順番に覚えていく方法。"),
    ("shakyo/",    "写経のやり方",                  "道具と手順、書き終えたあと。印刷用の手本つき。"),
    ("butsuzo/",   "仏さま図鑑（30体）",            "如来・菩薩・明王・天のちがいと、それぞれの見分け方。"),
]


def related(current, up="../"):
    rows = "".join(
        f'<a href="{up}{p}"><b>{esc(t)}</b><span>{esc(d)}</span></a>'
        for p, t, d in HUBS if p != current)
    return f'<h2><span class="n">INDEX</span>ほかの記事</h2><div class="rel">{rows}</div>'


def foot(up="../"):
    return f"""<footer><div class="wrap">
  <div class="links">
    <a href="{up}">毎日般若心経について</a>
    <a href="{up}privacy.html">プライバシーポリシー</a>
    <a href="{up}terms.html">利用規約</a>
    <a href="https://tagc.works/">tagc.works</a>
  </div>
  意味や解説は、分かりやすさを優先したひとつの解釈です。宗派によって読み方や作法が異なる場合があります。
  般若心経を唱えることに、健康や運勢への効果を約束するものではありません。<br>
  © 2026 毎日般若心経
</div></footer>
</body>
</html>
"""


# ============================================================
# 全文
# ============================================================
def page_zenbun(sutra):
    title = "般若心経の全文｜ふりがな・現代語訳つきで読む"
    desc = ("般若心経（摩訶般若波羅蜜多心経）の全文を、漢字一字ずつのふりがなと現代語訳つきで掲載。"
            "9つの場面に分けているので、意味をたどりながら通して読めます。")
    bc, bcld = crumbs([("全文（ふりがな・現代語訳）", "zenbun/")])
    toc = "".join(f'<li><a href="#s{i+1}">{esc(s["seg"])}</a></li>' for i, s in enumerate(sutra))

    segs = []
    for i, s in enumerate(sutra):
        body = []
        for ln in s["lines"]:
            body.append(f'<div class="kan">{ruby(ln)}</div>')
            body.append(f'<div class="yomi">{esc(ln["y"])}</div>')
        yaku = "".join(l["t"] for l in s["lines"] if l["t"])
        segs.append(f"""<h2 id="s{i+1}"><span class="n">{i+1:02d}</span>{esc(s['seg'])}</h2>
<div class="seg">
{''.join(body)}
  <div class="yaku">{esc(yaku)}</div>
  <div class="point"><span class="lb">ことばの手がかり</span>{s['point']}</div>
</div>""")

    through = "".join(f'{ruby(l)}<span class="sp"></span>' for s in sutra for l in s["lines"])

    return head(title, desc, "zenbun/", article_ld(title, desc, "zenbun/") + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>般若心経の全文<br>ふりがな・現代語訳つき</h1>
  <p class="lede">般若心経は、正式には「摩訶般若波羅蜜多心経（まかはんにゃはらみったしんぎょう）」といいます。
  本文はおよそ262文字。ここでは全文を9つの場面に分け、漢字一字ずつのふりがなと現代語訳を並べました。
  はじめての方は、上から順に読み下していくのがおすすめです。</p>
</div></header>
<main><div class="wrap">

<div class="toc"><b>もくじ</b><ol>{toc}</ol></div>

{''.join(segs)}

<h2><span class="n">通し</span>全文を通して読む</h2>
<p>ふりがなだけを追って、頭から通して読むためのブロックです。声に出すときはここを使ってください。
読む速さや息継ぎの位置は<a href="../tonaekata/">唱え方のページ</a>にまとめています。</p>
<div class="through">
  <span class="lb">摩訶般若波羅蜜多心経</span>
  <div class="kan">{through}</div>
</div>

<div class="note">漢字とふりがなは読誦で一般的な読み方にそろえています。宗派や寺院によって読み方・区切り方が異なることがあります。</div>

{cta()}
{related('zenbun/')}
</div></main>
{foot()}"""


# ============================================================
# 意味
# ============================================================
IMI_FAQ = [
    ("般若心経は何文字ありますか？",
     "本文はおよそ262文字です。表題の「仏説摩訶般若波羅蜜多心経」を含めると276文字前後になります。"
     "数え方は底本によって多少ちがいます。"),
    ("「色即是空」はどういう意味ですか？",
     "「形あるものは、そのまま実体のないものである」という意味です。ものごとは互いに関わり合いながら"
     "変わり続けていて、永遠に同じ姿でいるものは一つもない、という見方を表しています。"),
    ("最後の「羯諦羯諦（ぎゃーていぎゃーてい）」は何ですか？",
     "サンスクリット語の音をそのまま漢字に写した真言（マントラ）です。"
     "「行こう、行こう、向こう岸へ行こう。みなともに行き着こう」という意味にあたります。"),
    ("般若心経はどの宗派のお経ですか？",
     "特定の一宗派のものではありません。天台宗・真言宗・禅宗・浄土宗など幅広い宗派で読まれています。"
     "ただし浄土真宗と日蓮宗では通常は読まれません。"),
    ("誰でも唱えていいのですか？",
     "決まりはありません。仏教徒でなくても、作法を知らなくても唱えて構いません。"
     "気になる場合は、菩提寺や近くのお寺の作法にならうと安心です。"),
]


def page_imi(sutra):
    title = "般若心経の意味｜9つの場面でやさしく読み解く"
    desc = ("般若心経が何を言っているのかを、全文を9つの場面に分けて順番に解説します。"
            "「色即是空」「五蘊皆空」「羯諦羯諦」など、つまずきやすい言葉も現代語で。")
    bc, bcld = crumbs([("意味をやさしく読み解く", "imi/")])
    toc = "".join(f'<li><a href="#m{i+1}">{esc(s["seg"])}</a></li>' for i, s in enumerate(sutra))

    segs = []
    for i, s in enumerate(sutra):
        kan = "／".join(l["k"] for l in s["lines"])
        yaku = "".join(l["t"] for l in s["lines"] if l["t"])
        segs.append(f"""<h2 id="m{i+1}"><span class="n">{i+1:02d}</span>{esc(s['seg'])}</h2>
<p class="yomi">{esc(kan)}</p>
<p>{esc(yaku)}</p>
<div class="point"><span class="lb">ここが要</span>{s['point']}</div>""")

    return head(title, desc, "imi/", faq_ld(IMI_FAQ) + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>般若心経の意味<br>9つの場面でやさしく読み解く</h1>
  <p class="lede">般若心経は、観音さま（観自在菩薩）が釈迦の弟子・舎利子に語りかける形で進みます。
  262文字のなかに、大乗仏教の核心である「空（くう）」の考え方がまとめられています。
  ここでは全文を9つの場面に区切り、それぞれが何を言っているのかを順に見ていきます。
  漢文とふりがなを並べて読みたい方は<a href="../zenbun/">全文のページ</a>へ。</p>
</div></header>
<main><div class="wrap">

<div class="toc"><b>9つの場面</b><ol>{toc}</ol></div>

{''.join(segs)}

<h2><span class="n">FAQ</span>よくある質問</h2>
{faq_html(IMI_FAQ)}

<div class="note">ここに書いた意味は、分かりやすさを優先したひとつの解釈です。
般若心経には古来さまざまな注釈があり、宗派や訳者によって受け取り方が異なります。
個々の言葉の意味は<a href="../yougo/">用語集</a>にもまとめています。</div>

{cta()}
{related('imi/')}
</div></main>
{foot()}"""


# ============================================================
# 唱え方
# ============================================================
STEPS = [
    ("姿勢をととのえる",
     "椅子でも正座でも構いません。背すじを軽く伸ばし、肩の力を抜きます。"
     "手は合掌するか、経本を持つなら胸の高さで。目は半分ほど開けて、少し先の床に落とします。"),
    ("ひと呼吸おいて始める",
     "いきなり読み始めず、静かに息を吐いてから入ります。"
     "「これから唱えます」と区切りをつけるだけで、声の調子が安定します。"),
    ("一定の速さで、平らに読む",
     "抑揚をつけず、同じ高さ・同じ速さで淡々と読むのが基本です。"
     "全文はゆっくりで2分半、慣れると1分半ほど。速さより、途中で崩れないことを優先してください。"),
    ("句の切れ目で息を継ぐ",
     "「観自在菩薩／行深般若波羅蜜多時」のように、意味のまとまりで区切って息を継ぎます。"
     "苦しくなったら、途中でも構いません。息が続かないのは失敗ではありません。"),
    ("最後まで読んだら、間をとる",
     "「般若心経」と読み終えたら、すぐに立ち上がらず、数呼吸そのままでいます。"
     "唱えたあとの静けさまでを、ひと続きと考えてください。"),
]

TONAE_FAQ = [
    ("何回唱えればいいですか？",
     "決まりはありません。1回でも構いませんし、3回・7回と重ねる習わしもあります。"
     "毎日続けるなら、無理なく終われる回数にしておくのが長続きします。"),
    ("いつ唱えるのがいいですか？",
     "時間の決まりもありません。朝の支度前、夜寝る前など、生活の中で毎日同じタイミングに置くと習慣になります。"),
    ("声に出さないとだめですか？",
     "黙読でも構いません。声に出すと自分の声で呼吸が整いやすい、という違いがあります。"
     "家族が寝ている時間などは、口の中で小さく読む形でも十分です。"),
    ("正座やお仏壇は必要ですか？",
     "必要ありません。椅子でも、外出先でも唱えられます。"
     "ご自宅にお仏壇があれば、その前で唱えると気持ちの区切りがつけやすくなります。"),
    ("覚えられません。見ながらでもいいですか？",
     "見ながらで構いません。ほとんどの方は経本やふりがなを追って読みます。"
     "覚えたい場合は、9つの場面ごとに区切って、1場面ずつ繰り返すのが近道です。"),
]


def page_tonaekata():
    title = "般若心経の唱え方｜姿勢・速さ・息継ぎの基本"
    desc = ("はじめて般若心経を唱える方向けに、姿勢・読む速さ・息継ぎの位置・回数の考え方をまとめました。"
            "決まりごとは多くありません。今日から始められる形で説明します。")
    bc, bcld = crumbs([("唱え方", "tonaekata/")])
    steps = "".join(f"<li><b>{esc(n)}</b>{esc(t)}</li>" for n, t in STEPS)

    return head(title, desc, "tonaekata/",
                howto_ld("般若心経の唱え方", desc, STEPS) + faq_ld(TONAE_FAQ) + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>般若心経の唱え方<br>姿勢・速さ・息継ぎの基本</h1>
  <p class="lede">般若心経を唱えるのに、資格も許可も要りません。守らなければならない決まりごとも、
  実はそれほど多くありません。ここでは、はじめての方がつまずきやすいところ——
  どんな姿勢で、どれくらいの速さで、どこで息を継ぐのか——を順に説明します。</p>
</div></header>
<main><div class="wrap">

<h2><span class="n">STEP</span>唱えるまでの5つの手順</h2>
<ol class="steps">{steps}</ol>

<h2><span class="n">目安</span>速さと長さ</h2>
<p>全文はおよそ262文字。ゆっくり読んで2分半、慣れてくると1分半ほどで読み終えます。
速く読めることに意味はありません。むしろ、最後まで同じ調子で読み切れる速さを見つけるほうが大切です。
はじめは自分が思うより遅めに入ると、途中で崩れにくくなります。</p>
<p>読む速さに迷ったら、お手本の声に合わせるのがいちばん早い方法です。
アプリでは読み上げの速さを変えられるので、遅い設定から入って少しずつ上げていけます。</p>

<h2><span class="n">区切り</span>どこで息を継ぐか</h2>
<p>息継ぎの位置に絶対の正解はありませんが、意味のまとまりで切ると自然になります。
たとえば冒頭は「観自在菩薩／行深般若波羅蜜多時／照見五蘊皆空／度一切苦厄」のように、
四つに分けて読みます。
<a href="../zenbun/">全文のページ</a>では、この区切りのまま行を分けて掲載しています。</p>

<h2><span class="n">作法</span>気にしなくていいこと</h2>
<p>「服装は」「数珠は」「お仏壇の前でないとだめか」と気になる方が多いのですが、
個人で唱えるぶんには、いずれも決まりはありません。
法要や寺院の行事に参列するときは、その場の作法にならえば十分です。
宗派によって読み方や区切り方、前後に唱えるものが異なる場合があるので、
菩提寺がある方はそちらの形にそろえると迷いがなくなります。</p>

<h2><span class="n">FAQ</span>よくある質問</h2>
{faq_html(TONAE_FAQ)}

<div class="note">般若心経を唱えることに、健康や運勢への効果を約束するものではありません。
このページは読み方と作法の説明にとどめています。</div>

{cta()}
{related('tonaekata/')}
</div></main>
{foot()}"""


# ============================================================
# 覚え方
# ============================================================
OBOE_STEPS = [
    ("先に意味を入れる",
     "音だけで262文字を覚えるのは、意味のない記号列を覚えるのと同じでかなり大変です。"
     "先に何を言っているお経なのかを通して読んでおくと、あとの暗記がずいぶん楽になります。"),
    ("9つの場面に割る",
     "全文をひとかたまりで扱わず、話の切れ目で9つに割ります。"
     "1つあたり2〜5行なので、1日1場面でも9日で一周できます。"),
    ("1場面を、見ないで言えるまで繰り返す",
     "声に出して読む → 半分隠して読む → 何も見ずに言う、の順で進めます。"
     "つまずいたらすぐ見て構いません。思い出せずに固まる時間を短くするほど早く定着します。"),
    ("前の場面とつなげてから、次へ",
     "2場面目を覚えたら、必ず1場面目から続けて言います。"
     "場面の切り替わりがいちばん飛びやすいので、つなぎ目だけを重点的に繰り返します。"),
    ("毎日、同じ時間に通しで唱える",
     "覚えたあとは、思い出す回数がそのまま定着になります。"
     "1日1回でいいので通して唱える時間を決めてしまうのが、結局いちばん近道です。"),
]

OBOE_FAQ = [
    ("どれくらいで覚えられますか？",
     "個人差が大きいですが、1日1場面ずつ進めれば9日で一周し、"
     "その後2〜3週間くり返すと見ないで言えるようになる方が多いようです。急ぐ必要はありません。"),
    ("意味がわからなくても覚えられますか？",
     "覚えられますが、遠回りになりがちです。"
     "「無」が続くところなど、意味を知っていると順番を思い出す手がかりになります。"),
    ("途中で止まってしまいます。",
     "止まる場所はたいてい決まっています。その前後の2行だけを切り出して繰り返すと抜けます。"
     "全文を頭から繰り返すのは効率が悪い、と考えてください。"),
    ("書いて覚えるのと、声に出すのはどちらがいいですか？",
     "唱えるために覚えるなら、声に出すほうが近道です。"
     "書く場合は写経として別の目的で取り組むと、どちらも続けやすくなります。"),
]


def page_oboekata(sutra):
    title = "般若心経の覚え方｜262文字を9つに割って暗記する"
    desc = ("般若心経を暗記したい方向けの手順。262文字を9つの場面に割り、意味を手がかりに"
            "順番に覚えていく方法をまとめました。つまずきやすい場所と、その抜け方も。")
    bc, bcld = crumbs([("覚え方", "oboekata/")])
    steps = "".join(f"<li><b>{esc(n)}</b>{esc(t)}</li>" for n, t in OBOE_STEPS)

    rows = ""
    for i, s in enumerate(sutra):
        chars = sum(len(l["k"].replace(" ", "").replace("　", "")) for l in s["lines"])
        head_k = s["lines"][0]["k"].split(" ")[0]
        rows += (f'<tr><th>{i+1:02d}</th><td>{esc(s["seg"])}</td>'
                 f'<td>{esc(head_k)}〜</td><td>{len(s["lines"])}行 / 約{chars}字</td></tr>')

    return head(title, desc, "oboekata/",
                howto_ld("般若心経の覚え方", desc, OBOE_STEPS)
                + faq_ld(OBOE_FAQ) + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>般若心経の覚え方<br>262文字を9つに割って暗記する</h1>
  <p class="lede">般若心経を覚えたい、という方はとても多いのですが、
  頭から一文字ずつ丸暗記しようとすると、たいてい「無」が続くあたりで挫折します。
  意味の切れ目で9つに割り、1つずつ積み上げていくほうがずっと楽です。その手順をまとめました。</p>
</div></header>
<main><div class="wrap">

<h2><span class="n">STEP</span>覚えるまでの5つの手順</h2>
<ol class="steps">{steps}</ol>

<h2><span class="n">分割</span>9つの場面と、その分量</h2>
<p>割り方の目安です。1日1場面なら9日、2日で1場面なら3週間ほどで一周します。
それぞれの中身は<a href="../imi/">意味のページ</a>で確認してください。</p>
<table class="tb">
<thead><tr><th>#</th><th>場面</th><th>書き出し</th><th>分量</th></tr></thead>
<tbody>{rows}</tbody>
</table>

<h2><span class="n">難所</span>つまずきやすいのはこの2か所</h2>
<h3>「無」が続くところ</h3>
<p>「無眼耳鼻舌身意 無色声香味触法 無眼界 乃至無意識界 無無明…」と、
似た形の否定が延々と続きます。ここは順番を音だけで覚えようとすると必ず崩れます。
<b>感覚器官 → その対象 → 認識の世界 → 迷い → 老いと死 → 苦集滅道 → 智慧</b>と、
否定していく対象が外側から内側へ移っていく、という流れで押さえてください。</p>
<h3>場面と場面のつなぎ目</h3>
<p>1つの場面の中は言えるのに、次の場面の頭が出てこない。これがいちばん多い詰まり方です。
対策は単純で、<b>前の場面の最後の1行＋次の場面の最初の1行</b>だけを取り出して繰り返すことです。
つなぎ目を個別に潰していくと、通しで言えるようになります。</p>

<h2><span class="n">FAQ</span>よくある質問</h2>
{faq_html(OBOE_FAQ)}

<div class="note">アプリには、本文を隠して思い出す「暗記モード」があります。
9つの場面ごとに区切って練習できるので、上の手順をそのまま進められます。</div>

{cta()}
{related('oboekata/')}
</div></main>
{foot()}"""


# ============================================================
# 写経
# ============================================================
SHAKYO_STEPS = [
    ("手を洗い、机の上を片づける",
     "特別な清め方は要りません。手を洗って、机に写経用紙と筆記具だけを置きます。"
     "スマートフォンは伏せるか、別の部屋に置いておくと集中が続きます。"),
    ("道具を用意する",
     "筆ペンでも、鉛筆でも、ボールペンでも構いません。書き慣れた道具がいちばんです。"
     "用紙はお手本が薄く印刷された「なぞり書き用」から始めると、字の形で悩まずにすみます。"),
    ("願文（がんもん）を書くなら先に決めておく",
     "末尾に願いごとを書く形式もありますが、必須ではありません。"
     "書く場合は、始める前に一言だけ決めておくと、途中で手が止まりません。"),
    ("一字ずつ、ゆっくり書く",
     "うまく書こうとしなくて構いません。速く書き終えることにも意味はありません。"
     "一字を書き終えるたびに、次の一字に移る。それだけを繰り返します。"),
    ("書き終えたら、日付と名前を入れる",
     "最後に日付、住所、名前を書いて終わりです。"
     "書き上げたものは、自宅で保管しても、納経を受け付けているお寺に納めても構いません。"),
]

SHAKYO_FAQ = [
    ("どれくらい時間がかかりますか？",
     "はじめてなら1時間前後、慣れると30〜40分ほどです。途中で切り上げて、翌日に続きを書いても構いません。"),
    ("字が下手でも大丈夫ですか？",
     "問題ありません。写経は字の上手さを競うものではなく、一字ずつ書く時間そのものが目的です。"
     "なぞり書きの用紙を使えば、字形で迷うこともありません。"),
    ("筆でないとだめですか？",
     "決まりはありません。筆ペン、鉛筆、ボールペンいずれでも構いません。"
     "書き慣れた道具のほうが、手が止まらず最後まで書けます。"),
    ("書いたものはどうすればいいですか？",
     "自宅で保管しても構いませんし、納経を受け付けているお寺に納めることもできます。"
     "菩提寺がある方は、まずそちらに相談してみてください。"),
    ("間違えたときは？",
     "書き直しても、脇に小さく書き足しても構いません。"
     "訂正の作法は寺院によって異なるので、納める予定があるなら納め先に確認するのが確実です。"),
]


def page_shakyo(sutra):
    title = "般若心経の写経｜道具と手順、書き終えたあと"
    desc = ("はじめて写経をする方向けに、必要な道具、書く手順、かかる時間、書き終えたあとの扱いを"
            "まとめました。印刷してなぞり書きに使える全文の手本つきです。")
    bc, bcld = crumbs([("写経のやり方", "shakyo/")])
    steps = "".join(f"<li><b>{esc(n)}</b>{esc(t)}</li>" for n, t in SHAKYO_STEPS)
    trace = "".join(ruby(l, wrap=False) + "　" for s in sutra for l in s["lines"])

    return head(title, desc, "shakyo/",
                howto_ld("般若心経の写経のやり方", desc, SHAKYO_STEPS)
                + faq_ld(SHAKYO_FAQ) + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>般若心経の写経<br>道具と手順、書き終えたあと</h1>
  <p class="lede">写経は、お経を一字ずつ書き写すことです。仏教徒でなくても、作法を知らなくても始められます。
  必要なものは紙と書くものだけ。ここでは道具の選び方から、書く手順、書き上げたあとの扱いまでを順にまとめました。</p>
</div></header>
<main><div class="wrap">

<h2 class="noprint"><span class="n">STEP</span>写経の5つの手順</h2>
<ol class="steps noprint">{steps}</ol>

<h2 class="noprint"><span class="n">道具</span>そろえるもの</h2>
<table class="tb noprint">
<tbody>
<tr><th>用紙</th><td>写経用紙（なぞり書き用がおすすめ）。無地のコピー用紙でも構いません。</td></tr>
<tr><th>書くもの</th><td>筆ペン・鉛筆・ボールペンのいずれでも。書き慣れたものを選んでください。</td></tr>
<tr><th>下敷き</th><td>あると紙が動かず書きやすくなります。なくても構いません。</td></tr>
<tr><th>時間</th><td>はじめては1時間前後。途中で切り上げて翌日に続けても構いません。</td></tr>
</tbody>
</table>

<h2 class="noprint"><span class="n">手本</span>印刷して使う全文</h2>
<p class="noprint">下のブロックは、ブラウザの印刷機能（<b>Ctrl / ⌘ + P</b>）でそのまま印刷できます。
うすい文字なので、上からなぞって書けます。印刷すると見出しやリンクは消え、本文だけが出ます。</p>
<div class="trace">{trace}</div>

<div class="note noprint">この手本は書き写しの練習用です。寺院に納経する場合は、
納め先が用意している用紙や形式にならってください。
全文をふりがな・現代語訳つきで読みたい方は<a href="../zenbun/">全文のページ</a>へ。</div>

<h2 class="noprint"><span class="n">FAQ</span>よくある質問</h2>
<div class="noprint">{faq_html(SHAKYO_FAQ)}</div>

<div class="noprint">{cta()}
{related('shakyo/')}</div>
</div></main>
{foot()}"""


# ============================================================
# 般若心経とは
# ============================================================
TOWA_FAQ = [
    ("般若心経は誰が書いたお経ですか？",
     "作者は特定されていません。インドで成立した経典を、7世紀の中国で玄奘三蔵が漢訳したものが、"
     "日本で読まれている般若心経として伝わっています。"),
    ("何のためのお経ですか？",
     "「空（くう）」というものの見方を短くまとめた経典です。"
     "膨大な般若経典群の核心だけを取り出したものと位置づけられています。"),
    ("どの宗派で読まれますか？",
     "天台宗・真言宗・禅宗（曹洞宗・臨済宗）・浄土宗など、幅広い宗派で読まれています。"
     "一方、浄土真宗と日蓮宗では通常は読まれません。"),
    ("なぜ日本でこれほど広まったのですか？",
     "短くて覚えやすいこと、特定の宗派に閉じないこと、写経の題材として扱いやすいことが"
     "重なった結果と説明されます。"),
    ("「摩訶般若波羅蜜多心経」とはどういう意味ですか？",
     "摩訶は「偉大な」、般若は「智慧」、波羅蜜多は「向こう岸へ渡ること」。"
     "つまり「偉大な智慧によってさとりに至る、その心髄を説くお経」という題名です。"),
]


def page_towa():
    title = "般若心経とは｜成立・歴史・宗派をやさしく"
    desc = ("般若心経がいつ、どこで生まれ、誰の手で日本に伝わったのか。"
            "262文字に何が書かれているのか、どの宗派で読まれるのかを、はじめての方向けにまとめました。")
    bc, bcld = crumbs([("般若心経とは", "towa/")])

    return head(title, desc, "towa/",
                article_ld(title, desc, "towa/") + faq_ld(TOWA_FAQ) + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>般若心経とは<br>成立・歴史・宗派</h1>
  <p class="lede">日本でいちばん広く読まれているお経が、般若心経です。
  法要で耳にしたことがある、写経で書いたことがある、という方は多いはずですが、
  そもそも何のお経で、いつ生まれたものなのかは意外と知られていません。順に見ていきます。</p>
</div></header>
<main><div class="wrap">

<h2><span class="n">01</span>正式な名前と長さ</h2>
<p>般若心経の正式名称は「摩訶般若波羅蜜多心経（まかはんにゃはらみったしんぎょう）」です。
冒頭に「仏説」を付けて「仏説摩訶般若波羅蜜多心経」と呼ぶこともあります。</p>
<p>本文はおよそ262文字。日本で読まれる仏教経典のなかでは、際立って短い部類に入ります。
この短さが、暗記や写経の題材として広まった大きな理由です。
全文は<a href="../zenbun/">ふりがな・現代語訳つきのページ</a>に掲載しています。</p>

<h2><span class="n">02</span>何が書かれているのか</h2>
<p>中心にあるのは「空（くう）」という考え方です。
あらゆるものは互いに関わり合いながら移り変わっていて、
「これは絶対にこういうものだ」と固定できる実体は無い——という見方を指します。</p>
<p>お経は、観音さま（観自在菩薩）が釈迦の弟子・舎利子に語りかける形で進みます。
前半で「空」とは何かを示し、中盤で「無」を重ねてこだわりを外していき、
終盤で「だからおそれもない」と結んで、最後に真言（マントラ）で締めくくられます。
流れは<a href="../imi/">意味のページ</a>で9つの場面に分けて追えます。</p>

<h2><span class="n">03</span>いつ、どこで生まれたか</h2>
<p>もとになったのは、インドで成立した「般若経」と呼ばれる一群の経典です。
その分量は膨大で、代表的な『大般若波羅蜜多経』は600巻にもなります。
般若心経は、その核心にあたる部分だけを短くまとめたものと位置づけられています。</p>
<p>日本で読まれている漢訳は、7世紀の唐の僧・玄奘三蔵（げんじょうさんぞう）によるものと伝えられます。
玄奘はインドへ旅して大量の経典を持ち帰り、漢訳した人物で、
『西遊記』の三蔵法師のモデルとしても知られています。
作者そのものは特定されていません。</p>

<h2><span class="n">04</span>どの宗派で読まれるか</h2>
<table class="tb">
<thead><tr><th>宗派</th><th>般若心経</th></tr></thead>
<tbody>
<tr><th>真言宗</th><td>読まれる。写経の題材としてもよく用いられます</td></tr>
<tr><th>天台宗</th><td>読まれる</td></tr>
<tr><th>曹洞宗・臨済宗（禅宗）</th><td>読まれる。日々のおつとめで唱えられます</td></tr>
<tr><th>浄土宗</th><td>読まれることがある</td></tr>
<tr><th>浄土真宗</th><td>通常は読まれない</td></tr>
<tr><th>日蓮宗</th><td>通常は読まれない</td></tr>
</tbody>
</table>
<p>特定の一宗派に属さない経典なので、宗派を問わず個人で唱えても差し支えありません。
菩提寺がある方は、そちらの作法にそろえると迷いがなくなります。</p>

<h2><span class="n">05</span>いつ唱えるものか</h2>
<p>法要や葬儀で僧侶が読むほか、日々のおつとめとして自宅の仏壇の前で唱える形、
写経として書き写す形、巡礼で納経する形など、関わり方はさまざまです。
決まった時間や回数はありません。<a href="../tonaekata/">唱え方のページ</a>に基本をまとめています。</p>

<h2><span class="n">FAQ</span>よくある質問</h2>
{faq_html(TOWA_FAQ)}

<div class="note">成立年代や訳者については諸説あります。ここでは一般に知られている説明にそっています。</div>

{cta()}
{related('towa/')}
</div></main>
{foot()}"""


# ============================================================
# 用語集
# ============================================================
GLOSSARY = [
    ("空", "くう",
     "般若心経の中心にある考え方。「何も無い」という意味ではなく、"
     "「これは絶対にこういうものだ、と固定できる実体は無い」という意味です。"
     "ものごとは互いに関わり合いながら移り変わっている、という見方を指します。"),
    ("五蘊", "ごうん",
     "人の心身をつくる五つの要素。色（形あるもの）・受（感じること）・想（思い浮かべること）・"
     "行（意思のはたらき）・識（見分けること）を指します。"
     "「照見五蘊皆空」は、この五つに固定した実体は無いと見抜いた、という意味です。"),
    ("色即是空", "しきそくぜくう",
     "「形あるものは、そのまま実体のないものである」。"
     "続く「空即是色」と対になっていて、形と空は別々のものではない、と繰り返し押さえています。"),
    ("般若", "はんにゃ",
     "サンスクリット語の prajñā（プラジュニャー）の音を写したもので、「智慧」を意味します。"
     "知識の量ではなく、ものごとの本当のすがたを見抜く力を指します。"),
    ("波羅蜜多", "はらみった",
     "pāramitā の音写で、「向こう岸へ渡ること」。"
     "迷いのこちら側から、さとりの向こう岸へ渡り切ることを表します。"),
    ("舎利子", "しゃりし",
     "釈迦の弟子・シャーリプトラのこと。智慧第一と呼ばれた高弟で、"
     "般若心経では観音さまの語りかけを受ける相手として登場します。"),
    ("観自在菩薩", "かんじざいぼさつ",
     "観音さまのこと。般若心経で説法する側の主人公です。"
     "「観音菩薩」「観世音菩薩」も同じ仏さまを指します。"),
    ("無明", "むみょう",
     "ものごとの本当のすがたが見えていない状態、つまり根本的な迷いのこと。"
     "「無無明」は、その迷いさえ固定した実体ではない、という意味になります。"),
    ("苦集滅道", "くしゅうめつどう",
     "四諦（したい）と呼ばれる仏教の基本の教え。苦しみがあること、その原因、"
     "苦しみが消えた状態、そこへ至る道、の四つを指します。"),
    ("罣礙", "けいげ",
     "心のひっかかり、さまたげのこと。「心無罣礙」は、心にひっかかりが無い状態を表します。"),
    ("涅槃", "ねはん",
     "迷いやこだわりが消えた、静かな安らぎの境地。"
     "「究竟涅槃」は、その境地に至り切ることを指します。"),
    ("菩提薩埵", "ぼだいさった",
     "菩薩のこと。さとりを求めながら、同時に人々を救おうとしている存在を指します。"),
    ("阿耨多羅三藐三菩提", "あのくたらさんみゃくさんぼだい",
     "anuttarā samyaksaṃbodhi の音写で、「この上ない正しいさとり」。"
     "般若心経のなかでいちばん長い語です。"),
    ("呪", "しゅ",
     "真言（マントラ）のこと。意味を訳さず、音そのものを唱える言葉を指します。"
     "般若心経では末尾の「羯諦羯諦…」がこれにあたります。"),
    ("羯諦", "ぎゃーてい",
     "gate の音写で、「行った者よ」「行こう」。"
     "「羯諦羯諦 波羅羯諦 波羅僧羯諦 菩提薩婆訶」で、"
     "「行こう、行こう、向こう岸へ。みなともに行き着こう。さとりよ、幸あれ」という意味になります。"),
]


def page_yougo():
    title = "般若心経の用語集｜空・五蘊・波羅蜜多などをやさしく"
    desc = ("般若心経に出てくる言葉を一覧で解説します。空、五蘊、色即是空、波羅蜜多、罣礙、涅槃、"
            "阿耨多羅三藐三菩提など、読んでいてつまずきやすい語をまとめました。")
    bc, bcld = crumbs([("用語集", "yougo/")])
    terms_ld = ld({"@context": "https://schema.org", "@type": "DefinedTermSet",
                   "name": "般若心経の用語集", "inLanguage": "ja", "url": f"{BASE}/yougo/",
                   "hasDefinedTerm": [{"@type": "DefinedTerm", "name": n,
                                       "alternateName": y, "description": d}
                                      for n, y, d in GLOSSARY]})
    toc = "".join(f'<li><a href="#t{i}">{esc(n)}</a></li>' for i, (n, _, _) in enumerate(GLOSSARY))
    items = "".join(
        f'<dt id="t{i}">{esc(n)}<span>{esc(y)}</span></dt><dd>{esc(d)}</dd>'
        for i, (n, y, d) in enumerate(GLOSSARY))

    return head(title, desc, "yougo/", terms_ld + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>般若心経の用語集</h1>
  <p class="lede">般若心経は短いお経ですが、耳慣れない言葉が続けて出てきます。
  ここでは、読んでいてつまずきやすい語をまとめました。
  本文の流れのなかで意味を追いたい方は<a href="../imi/">意味のページ</a>へどうぞ。</p>
</div></header>
<main><div class="wrap">

<div class="toc"><b>ことば</b><ul>{toc}</ul></div>

<dl class="gl">{items}</dl>

<div class="note">語義は、分かりやすさを優先したひとつの説明です。
仏教学上はより厳密な定義があり、宗派や訳者によって説明が異なる場合があります。</div>

{cta()}
{related('yougo/')}
</div></main>
{foot()}"""


# ============================================================
# 仏さま図鑑
# ============================================================
BUTSU_FAQ = [
    ("如来と菩薩は何がちがうのですか？",
     "如来はすでにさとりを開いた仏さま、菩薩はさとりを求めながら人々を救おうとしている存在です。"
     "見た目でも区別でき、如来は装飾のない質素な衣、菩薩は冠や首飾りをつけた華やかな姿で表されます。"),
    ("明王が怒った顔をしているのはなぜですか？",
     "やさしい説き方では聞き入れない相手をも導くため、あえて忿怒の姿をとっているとされます。"
     "大日如来が姿を変えたものという説明が一般的です。"),
    ("「天」はどういう存在ですか？",
     "もとはインドの神々で、仏教に取り入れられて仏法の守り手になったものです。"
     "弁才天や大黒天のように七福神として親しまれているものも、四天王のように寺院を守るものもあります。"),
    ("仏像はどこを見れば見分けられますか？",
     "手に持っているもの（持物）と、頭のかたち、装飾の量が手がかりになります。"
     "薬壺なら薬師如来、錫杖なら地蔵菩薩、というように持ち物で特定できる仏さまが多くいます。"),
]


def page_butsuzo_index(deities):
    title = "仏さま図鑑｜如来・菩薩・明王・天のちがいと見分け方"
    desc = ("如来・菩薩・明王・天の4つの区分のちがいと、代表的な30体の仏さまを一覧でまとめました。"
            "持ち物や姿から見分けるための手がかりつきです。")
    bc, bcld = crumbs([("仏さま図鑑", "butsuzo/")])
    list_ld = ld({"@context": "https://schema.org", "@type": "ItemList",
                  "name": "仏さま図鑑", "numberOfItems": len(deities),
                  "itemListElement": [
                      {"@type": "ListItem", "position": i + 1, "name": d["name"],
                       "url": f"{BASE}/butsuzo/{d['slug']}/"} for i, d in enumerate(deities)]})

    blocks = ""
    for cat in ["如来", "菩薩", "明王", "天"]:
        members = [d for d in deities if d["cat"] == cat]
        cards = "".join(
            f'<a class="card" href="{d["slug"]}/"><b>{esc(d["name"])}</b>'
            f'<span>{esc(d["yomi"])}</span></a>' for d in members)
        blocks += (f'<h2 id="{CAT_SLUG[cat]}"><span class="n">{esc(cat)}</span>'
                   f'{esc(cat)}（{len(members)}体）</h2>'
                   f'<p>{esc(CAT_INTRO[cat])}</p><div class="grid">{cards}</div>')

    return head(title, desc, "butsuzo/",
                article_ld(title, desc, "butsuzo/") + list_ld + faq_ld(BUTSU_FAQ) + bcld) + f"""{bc}
<header class="hd"><div class="wrap">
  <h1>仏さま図鑑<br>如来・菩薩・明王・天のちがい</h1>
  <p class="lede">お寺で仏像を前にしても、どれが誰なのか分からない。
  そう感じたことのある方に向けて、仏さまの4つの区分と、代表的な30体をまとめました。
  区分が分かると、持ち物や姿から名前を推測できるようになります。</p>
</div></header>
<main><div class="wrap">

<h2><span class="n">早見</span>4つの区分</h2>
<table class="tb">
<thead><tr><th>区分</th><th>立場</th><th>見た目の特徴</th></tr></thead>
<tbody>
<tr><th>如来</th><td>さとりを開いた仏</td><td>装飾がなく、質素な衣。頭は螺髪（らほつ）</td></tr>
<tr><th>菩薩</th><td>さとりを求め、人を救う</td><td>冠・首飾りなど装身具をつけた華やかな姿</td></tr>
<tr><th>明王</th><td>力ずくで導く</td><td>怒りの表情、背に炎、武器を持つ</td></tr>
<tr><th>天</th><td>仏法と人を守る</td><td>甲冑や天女の姿。もとはインドの神々</td></tr>
</tbody>
</table>
<p>大まかには如来 → 菩薩 → 明王 → 天という位の順で語られます。
ただし優劣というより役どころのちがいと考えるほうが実態に合います。</p>

{blocks}

<h2><span class="n">FAQ</span>よくある質問</h2>
{faq_html(BUTSU_FAQ)}

<div class="note">解説はアプリ「毎日般若心経」の仏さま図鑑と同じ内容です。
分かりやすさを優先した説明で、像容や由来には地域・時代による差があります。</div>

{cta()}
{related('butsuzo/')}
</div></main>
{foot()}"""


def page_butsuzo_detail(d, deities):
    title = f"{d['name']}（{d['yomi']}）とは｜{d['cat']}の仏さま"
    desc = re.sub(r"\s+", "", d["desc"])[:95]
    bc, bcld = crumbs([("仏さま図鑑", "butsuzo/"), (d["name"], f"butsuzo/{d['slug']}/")],
                      up="../../")
    same = [x for x in deities if x["cat"] == d["cat"] and x["slug"] != d["slug"]]
    cards = "".join(f'<a class="card" href="../{x["slug"]}/"><b>{esc(x["name"])}</b>'
                    f'<span>{esc(x["yomi"])}</span></a>' for x in same)

    part = PART.get(d["part"], "")
    rows = f'<tr><th>よみ</th><td>{esc(d["yomi"])}</td></tr>'
    rows += f'<tr><th>区分</th><td>{esc(d["cat"])}</td></tr>'
    if part:
        rows += f'<tr><th>目じるし</th><td>{esc(part)}</td></tr>'
    if d.get("central"):
        rows += '<tr><th>アプリでの登場</th><td>はじめから中心におられます</td></tr>'
    else:
        rows += f'<tr><th>アプリでの登場</th><td>累計{d["unlock"]}回となえると現れます</td></tr>'

    prev_d = deities[(d["idx"] - 1) % len(deities)]
    next_d = deities[(d["idx"] + 1) % len(deities)]
    pager = (f'<div class="pager">'
             f'<a href="../{prev_d["slug"]}/"><span>まえ</span>{esc(prev_d["name"])}</a>'
             f'<a href="../{next_d["slug"]}/"><span>つぎ</span>{esc(next_d["name"])}</a></div>')

    return head(title, desc, f"butsuzo/{d['slug']}/",
                article_ld(title, desc, f"butsuzo/{d['slug']}/") + bcld,
                up="../../") + f"""{bc}
<header class="hd"><div class="wrap">
  <span class="chip">{esc(d['cat'])}</span>
  <h1>{esc(d['name'])}<small>{esc(d['yomi'])}</small></h1>
  <p class="lede">{esc(d['desc'])}</p>
</div></header>
<main><div class="wrap">

<h2><span class="n">DATA</span>基本の情報</h2>
<table class="tb"><tbody>{rows}</tbody></table>

<h2><span class="n">{esc(d['cat'])}</span>「{esc(d['cat'])}」とはどういう仏さまか</h2>
<p>{esc(CAT_INTRO[d['cat']])}</p>
<p>4つの区分の見分け方は<a href="../">仏さま図鑑のトップ</a>に一覧でまとめています。</p>

<h2><span class="n">同じ区分</span>ほかの{esc(d['cat'])}</h2>
<div class="grid">{cards}</div>

{pager}

<div class="note">解説はアプリ「毎日般若心経」の仏さま図鑑と同じ内容です。
分かりやすさを優先した説明で、像容や由来には地域・時代による差があります。
古くからそう伝えられてきたという紹介であり、効果を保証するものではありません。</div>

{cta(up='../../')}
{related('butsuzo/', up='../../')}
</div></main>
{foot(up='../../')}"""


# ============================================================
# 出力
# ============================================================
def _save(path, text):
    """マウント越しでも壊れないように、unlink せず truncate して書く。"""
    mode = "r+" if os.path.exists(path) else "w"
    with open(path, mode, encoding="utf-8") as f:
        f.write(text)
        f.truncate()
    return path


def write(rel, html):
    path = os.path.join(HANNYA, rel, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _save(path, html)
    return len(html)


def update_lp():
    """LP（hannya/index.html）の「よみもの」一覧と構造化データを入れ直す。

    LP本体は手で書いているが、記事一覧だけは HUBS からの生成に寄せておく。
    記事を足したときに LP のリンクを足し忘れる、という事故を防ぐため。
    """
    p = os.path.join(HANNYA, "index.html")
    s = open(p, encoding="utf-8").read()

    cards = "\n".join(
        f'      <a class="read-item rv d{min(i+1,4)}" href="{path}">\n'
        f'        <b>{esc(t)}</b>\n        <span>{esc(d)}</span>\n'
        f'        <i>読む →</i>\n      </a>'
        for i, (path, t, d) in enumerate(HUBS))
    section = f"""<section class="read">
  <div class="wrap">
    <p class="eyebrow rv">よみもの</p>
    <h2 class="sec-title rv d1">般若心経について、もっと知る</h2>
    <div class="read-list">
{cards}
    </div>
  </div>
</section>

"""
    if '<section class="read">' in s:
        s = re.sub(r'<section class="read">.*?</section>\n*', section, s, count=1, flags=re.S)
    else:
        s = s.replace('<section class="cta">', section + '<section class="cta">', 1)

    app_ld = ld({"@context": "https://schema.org", "@type": "MobileApplication",
                 "name": "毎日般若心経", "inLanguage": "ja",
                 "applicationCategory": "LifestyleApplication",
                 "operatingSystem": "iOS, Android",
                 "url": BASE + "/",
                 "description": "般若心経を、意味からやさしく学んでとなえられるアプリ。"
                                "全文を9つの場面に分け、ふりがなとお手本の声をつけました。",
                 "offers": {"@type": "Offer", "price": "0", "priceCurrency": "JPY"},
                 "installUrl": [APPSTORE, PLAY],
                 "publisher": {"@type": "Organization", "name": "tagc", "url": "https://tagc.works/"}})
    site_ld = ld({"@context": "https://schema.org", "@type": "WebSite",
                  "name": "毎日般若心経", "url": BASE + "/", "inLanguage": "ja"})
    block = f"<!-- LD:START -->{app_ld}{site_ld}<!-- LD:END -->"
    if "<!-- LD:START -->" in s:
        s = re.sub(r"<!-- LD:START -->.*?<!-- LD:END -->", block, s, count=1, flags=re.S)
    else:
        s = s.replace("</head>", block + "\n</head>", 1)
    return _save(p, s)


def update_sitemap(urls):
    p = os.path.join(SITE, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    s = "\n".join(l for l in s.splitlines() if "/hannya/" not in l)
    add = "".join(f"<url><loc>{BASE}/{u}</loc><changefreq>{f}</changefreq></url>\n"
                  for u, f in urls)
    s = s.replace("</urlset>", add + "</urlset>")
    return _save(p, s)


if __name__ == "__main__":
    print("般若心経 読みものページを生成します")
    print(f"  データ: {APPDATA}")
    sutra = load_sutra()
    deities = load_deities()
    print(f"  お経 {len(sutra)}段 / {sum(len(s['lines']) for s in sutra)}行、仏さま {len(deities)}体")

    pages = [
        ("towa/", page_towa()),
        ("zenbun/", page_zenbun(sutra)),
        ("imi/", page_imi(sutra)),
        ("yougo/", page_yougo()),
        ("tonaekata/", page_tonaekata()),
        ("oboekata/", page_oboekata(sutra)),
        ("shakyo/", page_shakyo(sutra)),
        ("butsuzo/", page_butsuzo_index(deities)),
    ]
    for d in deities:
        pages.append((f"butsuzo/{d['slug']}/", page_butsuzo_detail(d, deities)))

    total = sum(write(rel, html) for rel, html in pages)
    print(f"  ✅ {len(pages)}ページ / 計{total:,} bytes")
    print(f"  ✅ {update_lp()}（よみもの一覧と構造化データ）")

    urls = [("", "monthly")] + [(rel, "monthly") for rel, _ in pages] \
        + [("privacy.html", "yearly"), ("terms.html", "yearly")]
    print(f"  ✅ {update_sitemap(urls)}（{len(urls)}URL）")
    print("\n次: cd ~/tagc.works && ./deploy.sh top \"...\"")
