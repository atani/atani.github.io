"""Free, reproducible peyote-layout charts. No tracking scripts or dependencies."""
from collections import Counter
from html import escape
import json

SITE = "https://atani.github.io"
PRODUCT_SITE = "https://atani.lolipop-now.app"
ART = (
    ".XXX....XXX.", "XXXXX..XXXXX", "XWXXXXXXXXXX", "XWXXXXXXXXXX",
    "XXXXXXXXXXXX", ".XXXXXXXXXX.", "..XXXXXXXX..", "...XXXXXX...",
    "....XXXX....", ".....XX.....",
)
SYMBOLS = {".": "A", "X": "B", "W": "C"}
COUNTS = Counter(SYMBOLS[cell] for row in ART for cell in row)
PALETTES = {
    "coral": {"A": "#fbf4ed", "B": "#f24f3c", "C": "#ffffff"},
    "blue": {"A": "#fbf4ed", "B": "#6170ff", "C": "#ffffff"},
}
ASSET_ROOT = "/peyo/patterns/heart/"


def chart_svg(palette="coral"):
    """Match Peyo's 1.3 bead width/height ratio and odd-column half offset."""
    colors = PALETTES[palette]
    width, height, margin = 39, 30, 24
    cells = []
    for row, line in enumerate(ART):
        for col, cell in enumerate(line):
            symbol = SYMBOLS[cell]
            x, y = margin + col * width, margin + row * height + (col % 2) * height / 2
            text_color = "#101317"
            cells.append(f'<g><title>Column {col + 1}, cell {row + 1}: {symbol}</title>'
                         f'<rect x="{x + 1}" y="{y + 1}" width="{width - 2}" height="{height - 2}" '
                         f'rx="5" fill="{colors[symbol]}" stroke="#101317" stroke-width="1"/>'
                         f'<text x="{x + width / 2}" y="{y + 20}" text-anchor="middle" '
                         f'fill="{text_color}" font-size="15" font-family="system-ui,sans-serif">{symbol}</text></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 516 363" width="1032" height="726" '
            f'role="img" aria-labelledby="title desc"><title id="title">Peyo heart design chart — {palette}</title>'
            '<desc id="desc">12 columns, 10 cells in each column. Odd-numbered zero-based columns are shifted down half a bead. '
            f'A: {COUNTS["A"]}, B: {COUNTS["B"]}, C: {COUNTS["C"]}. Total: 120 beads.</desc>'
            '<rect width="516" height="363" fill="#ffffff"/>' + ''.join(cells) + '</svg>')


def build_assets():
    assets = [(f"peyo/patterns/heart/heart-{palette}.svg", chart_svg(palette)) for palette in PALETTES]
    csv = "symbol,coral_hex,blue_hex,bead_count\n" + ''.join(
        f'{symbol},{PALETTES["coral"][symbol]},{PALETTES["blue"][symbol]},{COUNTS[symbol]}\n'
        for symbol in "ABC")
    assets.append(("peyo/patterns/heart/bead-counts.csv", csv))
    return assets


COPY = {
    "en": {
        "path": "/peyo/en/patterns/heart/", "lang": "en", "home": "/peyo/en/",
        "title": "Free peyote heart pattern & bead counts | Peyo",
        "heading": "A little heart. Your next color idea.",
        "lead": "A free peyote-layout design chart with exact bead counts and two colorways. Download it, use it as a design reference, or redraw it in Peyo on iPhone and iPad.",
        "chart": "Your free heart chart", "alt": "Peyote-layout heart chart, 12 columns with 10 cells per column, labeled A, B and C",
        "dimensions": "12 columns · 10 cells per column · 120 beads", "count": "Beads by color",
        "headers": ("Symbol", "Coral colorway", "Blue colorway", "Beads"),
        "colors": (("Cream", "Cream"), ("Coral", "Blue"), ("White", "White")),
        "total": "Total", "download": "Download coral chart (SVG)", "download_blue": "Download blue chart (SVG)",
        "download_counts": "Download bead counts (CSV)", "variant": "See the blue colorway",
        "note": "Counts include every cell in the rectangular chart, including the cream background. Letters identify the colors, so you can use the chart without relying on color alone. Screen colors are illustrative, not bead brand or product numbers.",
        "how": "Make it your own in Peyo", "steps": (
            "Start a blank design with 12 columns and 10 rows. Redraw the labeled cells, using three colors from your palette.",
            "Check the total and color counts against the table. Changing a color does not change the number of beads.",
            "Export your design as an image or a project card. Drawing, counting and image export are free; no account is required.",
        ),
        "pro": "Optional: Peyo Pro lets you draw over a reference image and replace a color throughout a pattern. You can also redraw this chart by hand with the free drawing tools. Check saving options and prices in the app.",
        "cta": "Draw your own pattern — get Peyo", "cta_note": "For iPhone and iPad · Free drawing tools · Optional in-app purchases",
        "scope_title": "About this chart", "scope": "This is a design chart, not step-by-step bead-stitching instructions. Adjacent columns are shifted by half a bead, matching Peyo’s peyote canvas. Use your preferred flat-peyote stitching instructions for thread paths and finishing.",
        "license": "Original Peyo sample design. You may download, recolor, print and use this chart for personal beadwork. No purchase or email address is required.",
        "back": "About Peyo", "support": "Support & privacy", "skip": "Skip to the chart", "language": "日本語", "other": "/peyo/patterns/heart/",
    },
    "ja": {
        "path": "/peyo/patterns/heart/", "lang": "ja", "home": "/peyo/",
        "title": "無料のハート図案と色別ビーズ数 | Peyo",
        "heading": "小さなハートから、次の配色へ。",
        "lead": "ペヨーテ配列のハート図案を、色別のビーズ数と2つの配色で用意しました。ダウンロードして使うほか、iPhone・iPadのPeyoで描き直して、自分の配色を試せます。",
        "chart": "無料のハート図案", "alt": "A・B・Cの記号付きハート図案。横12列、各列10マスのペヨーテ配列",
        "dimensions": "横12列・各列10マス・合計120粒", "count": "色ごとのビーズ数",
        "headers": ("記号", "コーラル配色", "ブルー配色", "粒数"),
        "colors": (("クリーム", "クリーム"), ("コーラル", "ブルー"), ("ホワイト", "ホワイト")),
        "total": "合計", "download": "コーラル図案を保存（SVG）", "download_blue": "ブルー図案を保存（SVG）",
        "download_counts": "色別の粒数を保存（CSV）", "variant": "ブルーの配色を見る",
        "note": "クリーム色の背景を含む、長方形全体の粒数です。各マスに記号があるため、色だけに頼らず読めます。画面上の色は参考色で、ビーズの商品番号を表すものではありません。",
        "how": "Peyoで自分の配色を作る", "steps": (
            "横12列・縦10行の白紙の図案を用意し、パレットから3色を選んで記号ごとに描き写します。",
            "色別の粒数と合計を表と照合します。色を変えても、図案のマス数は変わりません。",
            "図案を画像や作品カードとして書き出します。手描き、集計、画像の書き出しは無料で、登録も不要です。",
        ),
        "pro": "Peyo Proでは下絵に重ねた作図や色の一括置換も使えます。この図案は無料の描画ツールで手描きすることもできます。図案の保存条件と価格はアプリ内で確認できます。",
        "cta": "Peyoで自分の図案を描く", "cta_note": "iPhone・iPad対応・作図無料・任意のアプリ内課金あり",
        "scope_title": "この図案について", "scope": "図案の配色見本です。糸の通し方や仕上げ方を説明する編み方手順書ではありません。隣り合う列を半粒ずらしたPeyoのペヨーテ配列で表示しています。制作には普段お使いの平面ペヨーテの編み方を参照してください。",
        "license": "Peyoのオリジナル作例です。個人のビーズ制作のためのダウンロード、配色変更、印刷を自由に行えます。購入やメールアドレス登録は不要です。",
        "back": "Peyoの紹介", "support": "サポート・プライバシー", "skip": "図案へ移動", "language": "English", "other": "/peyo/en/patterns/heart/",
    },
}


def render(locale):
    c = COPY[locale]
    store = ("https://apps.apple.com/us/app/id6791587493" if locale == "en" else "https://apps.apple.com/jp/app/id6791587493")
    store += f"?pt=129044417&ct=free-heart-{locale}-202611&mt=8"
    rows = ''.join(f'<tr><th scope="row">{s}</th><td>{c["colors"][i][0]}</td><td>{c["colors"][i][1]}</td><td>{COUNTS[s]}</td></tr>' for i, s in enumerate("ABC"))
    headers = ''.join(f'<th scope="col">{x}</th>' for x in c['headers'])
    steps = ''.join(f'<li>{escape(x)}</li>' for x in c['steps'])
    data = {"@context": "https://schema.org", "@type": "Article", "headline": c["title"], "description": c["lead"],
            "inLanguage": c["lang"], "url": SITE + c["path"], "author": {"@type": "Organization", "name": "Peyo"},
            "image": SITE + ASSET_ROOT + "heart-coral.svg"}
    return f'''<!doctype html>
<html lang="{c['lang']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(c['title'])}</title><meta name="description" content="{escape(c['lead'], quote=True)}">
<meta property="og:type" content="article"><meta property="og:title" content="{escape(c['title'], quote=True)}">
<meta property="og:description" content="{escape(c['lead'], quote=True)}"><meta property="og:url" content="{SITE}{c['path']}">
<meta property="og:image" content="{SITE}{ASSET_ROOT}heart-coral.svg">
<link rel="canonical" href="{SITE}{c['path']}"><link rel="alternate" hreflang="en" href="{SITE}{COPY['en']['path']}"><link rel="alternate" hreflang="ja" href="{SITE}{COPY['ja']['path']}">
<link rel="icon" href="/assets/peyo-icon.png"><link rel="stylesheet" href="/css/peyo.css"><link rel="stylesheet" href="/css/peyo-patterns.css">
<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script></head>
<body class="peyo-page pattern-page"><a class="pattern-skip" href="#chart">{c['skip']}</a>
<header class="pattern-header"><a href="{PRODUCT_SITE}{c['home']}" class="pattern-brand"><img src="/assets/peyo-icon.png" alt="" width="44" height="44"><strong>Peyo</strong></a><nav aria-label="Languages"><a href="{c['other']}">{c['language']}</a><a href="{PRODUCT_SITE}{c['home']}">{c['back']}</a></nav></header>
<main class="pattern-main"><p class="peyo-kicker">FREE PEYOTE DESIGN CHART</p><h1>{c['heading']}</h1><p class="pattern-lead">{c['lead']}</p>
<section id="chart" aria-labelledby="chart-title"><h2 id="chart-title">{c['chart']}</h2><p>{c['dimensions']}</p>
<figure><img class="pattern-chart" src="{ASSET_ROOT}heart-coral.svg" width="516" height="363" alt="{c['alt']}"></figure>
<div class="pattern-actions"><a class="peyo-button peyo-button--dark" href="{ASSET_ROOT}heart-coral.svg" download="peyo-heart-coral.svg">{c['download']}</a><a class="pattern-link" href="{ASSET_ROOT}bead-counts.csv" download="peyo-heart-bead-counts.csv">{c['download_counts']}</a></div>
<h3>{c['count']}</h3><div class="pattern-table"><table><thead><tr>{headers}</tr></thead><tbody>{rows}<tr><th scope="row" colspan="3">{c['total']}</th><td>120</td></tr></tbody></table></div><p class="pattern-note">{c['note']}</p>
<details><summary>{c['variant']}</summary><img class="pattern-chart" src="{ASSET_ROOT}heart-blue.svg" width="516" height="363" alt="{c['alt']}"><a class="pattern-link" href="{ASSET_ROOT}heart-blue.svg" download="peyo-heart-blue.svg">{c['download_blue']}</a></details></section>
<section aria-labelledby="make-title"><h2 id="make-title">{c['how']}</h2><ol>{steps}</ol><p class="pattern-note">{c['pro']}</p><a class="peyo-button peyo-button--dark" href="{store}">{c['cta']}</a><p class="pattern-note">{c['cta_note']}</p></section>
<section aria-labelledby="about-title"><h2 id="about-title">{c['scope_title']}</h2><p>{c['scope']}</p><p>{c['license']}</p></section></main>
<footer class="pattern-footer"><a href="{PRODUCT_SITE}{c['home']}">{c['back']}</a><a href="https://atani.github.io/peyo-legal/">{c['support']}</a></footer></body></html>'''


def build_pages():
    return [(c["path"], c["path"].lstrip("/") + "index.html", render(locale)) for locale, c in COPY.items()]
