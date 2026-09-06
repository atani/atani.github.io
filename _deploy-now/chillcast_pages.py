"""ChillCast の地点別・品種別ページ（英語）を組み立てる。

数値は `scripts/build-chillcast-pages.py` が NASA POWER から作った
`chillcast_data.json`、品種は `chillcast_varieties.json` を読む。どちらもコミット
済みなので、`scripts/build-deploy-now.py` はネットワークに触らずに描画できる。

地点表は 150 件だが、ページを作るのは `PUBLISHED_SLUGS` の 30 地点だけにする。
同じ構造のページを一度に大量公開すると検索エンジンの scaled content 判定を
受けやすいため、残りは後から増やす。ページの無い地点は一覧と品種ページに
数値だけ載せ、リンクにはしない。
"""

import json
import math
import pathlib
import re
import unicodedata
import urllib.parse
from html import escape

HERE = pathlib.Path(__file__).resolve().parent
SITE = "https://atani.lolipop-now.app"
STORE = "https://apps.apple.com/us/app/id6785241430"
POWER = "https://power.larc.nasa.gov/"
POWER_REFERENCING = "https://power.larc.nasa.gov/docs/referencing/"
CHILL_ROOT = "/chillcast/chill-hours/"
VARIETY_ROOT = "/chillcast/varieties/"
CALCULATOR_SRC = "/assets/chillcast-calculator.js"

NEARBY_COUNT = 5
TOP_FITS = 3

# 初回に公開する 30 地点。果樹産地を優先し、国ごとの配分は設計レビューの指示による。
# URL は country_slug/slug で組み立てるので、判定も同じ組で行う。裸の slug で
# 判定すると、別の国に同名の地点が増えたときページの無い側にもリンクが出る。
PUBLISHED_SITES = {
    ("united-states", "wenatchee"), ("united-states", "yakima"),
    ("united-states", "hood-river"), ("united-states", "fresno"),
    ("united-states", "modesto"), ("united-states", "watsonville"),
    ("united-states", "traverse-city"), ("united-states", "geneva"),
    ("united-states", "biglerville"), ("united-states", "fort-valley"),
    ("united-states", "fredericksburg"), ("united-states", "edgefield"),
    ("canada", "kelowna"), ("canada", "niagara-on-the-lake"),
    ("australia", "shepparton"), ("australia", "batlow"), ("australia", "orange"),
    ("australia", "stanthorpe"), ("australia", "manjimup"), ("australia", "huonville"),
    ("new-zealand", "hastings"), ("new-zealand", "cromwell"),
    ("south-africa", "ceres"), ("south-africa", "grabouw"),
    ("spain", "lleida"), ("spain", "calatayud"), ("spain", "cieza"),
    ("turkey", "isparta"), ("turkey", "egirdir"), ("turkey", "amasya"),
}

# 「近く」と言える距離の上限。これを超える候補は近隣として出さない。
NEARBY_MAX_KM = 500.0

DISCLAIMER = (
    "Values are NASA POWER regional estimates (about 0.5° grid), not orchard "
    "measurements. Check your local extension service for station data."
)
NON_ENDORSEMENT = "NASA does not endorse ChillCast."
POWER_CREDIT = (
    "The data was obtained from the National Aeronautics and Space Administration (NASA) "
    "Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project "
    "funded through the NASA Earth Science Division."
)

# 地元の普及機関が公開している chill の資料・計算ツール。(国, 地域) で引き、
# 地域が None の項目はその国全体に当てる。URL とラベルはプレーンテキストで持ち、
# 描画側で escape() する。公開する 30 地点はすべてどれかに当たること
# （build_pages が起動時に確かめる）。
#
# 掲載しているのは URL を開いて chill の記述を確認できたものだけ。Michigan と
# Oregon は州の普及機関（canr.msu.edu / extension.oregonstate.edu）が自動取得を
# 遮断しており個別ページを確認できなかったため、全米の Cooperative Extension の
# 窓口を当てている。
EXTENSION_LINKS = {
    ("United States", "California"): (
        "https://fruitsandnuts.ucdavis.edu/about-chilling-hours-units-and-portions",
        "UC Davis Fruit & Nut Research and Information Center: chilling hours, units, and portions",
    ),
    ("United States", "Washington"): (
        "https://s3.wp.wsu.edu/uploads/sites/2073/2014/03/The-Importance-of-Chilling-Temperatures.pdf",
        "Washington State University: the importance of chilling temperatures for fruit trees",
    ),
    ("United States", "Oregon"): (
        "https://ask.extension.org/",
        "Ask Extension: put a chill question to your state's Cooperative Extension service",
    ),
    ("United States", "Michigan"): (
        "https://ask.extension.org/",
        "Ask Extension: put a chill question to your state's Cooperative Extension service",
    ),
    ("United States", "New York"): (
        "https://www.nrcc.cornell.edu/industry/apple/apple.html",
        "Cornell Northeast Regional Climate Center: accumulated chill and apple frost risk maps",
    ),
    ("United States", "Pennsylvania"): (
        "https://extension.psu.edu/small-fruit-cold-hardiness-winter-injury-in-brambles",
        "Penn State Extension: chilling requirements and winter injury in Pennsylvania",
    ),
    ("United States", "Georgia"): (
        "https://site.extension.uga.edu/peaches/tag/chill-hours/",
        "University of Georgia Extension peach blog: chill hours in Georgia",
    ),
    ("United States", "South Carolina"): (
        "https://hgic.clemson.edu/factsheet/understanding-chill-hours-for-fruit-and-nut-trees-in-south-carolina/",
        "Clemson Extension: understanding chill hours for fruit and nut trees",
    ),
    ("United States", "Texas"): (
        "https://travis-tx.tamu.edu/about-2/horticulture/edible-gardens-for-austin/"
        "fruits-and-nuts-for-austin/chill-hour-requirements-for-austin/",
        "Texas A&M AgriLife Extension: chill hour requirements",
    ),
    ("Canada", "British Columbia"): (
        "https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/animals-and-crops/"
        "crop-production/tree-fruits",
        "British Columbia Ministry of Agriculture and Food: tree fruits",
    ),
    ("Canada", "Ontario"): (
        "https://onfruit.ca/2022/04/28/cold-injury-tender-fruit/",
        "OMAFRA ONfruit: chilling units, dormancy, and cold injury in tender fruit",
    ),
    ("Australia", None): (
        "https://grf-smartfarm.dpi.qld.gov.au/shiny/apps/chillcalculator/",
        "Queensland DPI Chill & Thermal Time Calculator, covering around 600 Australian locations",
    ),
    ("New Zealand", None): (
        "https://www.summerfruitnz.co.nz/publications/news/winter-chill-round-up-2019",
        "Summerfruit New Zealand: winter chill round-up, with Richardson chill units by district",
    ),
    ("South Africa", None): (
        "https://www.hortgro.co.za/science-tech-hub/climate-information/",
        "Hortgro: chilling units, temperature, and rainfall per deciduous fruit production region",
    ),
    ("Spain", None): (
        "https://ivia.gva.es/es/-/el-frio-invernal-como-factor-limitante-de-la-produccion-de-frutales",
        "IVIA (Generalitat Valenciana): el frío invernal como factor limitante de la producción de frutales",
    ),
    ("Turkey", None): (
        "https://www.mgm.gov.tr/FILES/Haberler/2016/04.02.2016Bisip.pdf",
        "Meteoroloji Genel Müdürlüğü: Bitki Soğuklama İsteği Hesaplama Programı (BİSİP)",
    ),
}

MODELS = [
    ("forty_five", "45°F Hours", "hours", "Hours between 0 and 7.2°C (32–45°F)."),
    ("utah", "Utah", "units", "Weighted bands; warm hours subtract from the total."),
    ("dynamic", "Dynamic", "portions", "Fishman–Erez model; handles warm spells."),
]

FIT_LABELS = {
    "fits": ("Fits", "Average chill clears the requirement with room to spare."),
    "marginal": ("Marginal", "Average chill is close to the requirement; some winters fall short."),
    "short": ("Short", "Average chill is below the requirement."),
}

ORDINALS = ["", "lowest", "second-lowest", "third-lowest", "fourth-lowest", "fifth-lowest"]

# 国別索引にその国だけの段落を置く。定型の表だけのページにしないため。
COUNTRY_NOTES = {
    "United States": (
        "The locations here run from the irrigated valleys of the Pacific Northwest, where apples and "
        "sweet cherries dominate, through the Great Lakes tart cherry belt and the mid-Atlantic apple "
        "country, down to the peach districts of the Southeast and the Texas Hill Country. That spread "
        "is why a single national chill map is of little use: a variety that fruits reliably in "
        "Wenatchee can sit dormant and blind in Fort Valley, and the other way round."
    ),
    "Canada": (
        "Canadian tree fruit is concentrated in two narrow, lake-moderated corridors: the Okanagan "
        "Valley in British Columbia and the Niagara Peninsula in Ontario. Both bank chill early and "
        "hold it, so the constraint on variety choice is usually winter cold hardiness and spring "
        "frost rather than a shortage of chill."
    ),
    "Australia": (
        "Australian orchards sit in cool pockets a long way apart: the Goulburn Valley and the "
        "Southern Highlands in the southeast, the Granite Belt in Queensland, the far southwest of "
        "Western Australia, and Tasmania. Chill accumulates over the southern winter, so the season "
        "labels here are single years rather than the split years used in the Northern Hemisphere."
    ),
    "New Zealand": (
        "Hawke's Bay on the North Island and Central Otago in the South Island are the two districts "
        "that carry most of New Zealand's pipfruit and summerfruit. Central Otago is continental and "
        "cold for its latitude, Hawke's Bay is maritime and milder, and the gap between them is wide "
        "enough to change which stonefruit varieties are worth planting."
    ),
    "South Africa": (
        "Almost all South African pome and stone fruit grows in the Western Cape, in cold pockets such "
        "as the Ceres basin and the Elgin valley that sit well above the surrounding country. Chill is "
        "the binding constraint here rather than winter cold, which is why the local industry watches "
        "chill units so closely."
    ),
    "Spain": (
        "The Spanish locations are the Ebro basin around Lleida and Calatayud, where continental "
        "winters give ample chill, and the Murcian districts such as Cieza, where mild winters push "
        "growers toward low-chill stonefruit. The two ends of that range are several hundred hours "
        "apart in an average winter."
    ),
    "Turkey": (
        "Türkiye's fruit districts sit on the Anatolian plateau and around the inland lakes, at "
        "altitudes that give cold, dry winters. Isparta and Eğirdir are apple country, Amasya lends "
        "its name to an old apple variety, and chill is rarely the limiting factor at these elevations."
    ),
}


SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def slugify(value: str) -> str:
    text = value.replace("ı", "i").replace("İ", "i").replace("ğ", "g").replace("ş", "s")
    text = text.replace("ö", "o").replace("ü", "u").replace("ç", "c").replace("ñ", "n")
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()


def checked_slug(value: str) -> str:
    """URL の部品にする前に slug を検証する。生の値を href へ流さない。"""
    text = str(value)
    if not SLUG_RE.fullmatch(text):
        raise SystemExit(f"slug が [a-z0-9-] ではありません: {value!r}")
    return text


def load_data() -> dict:
    return json.loads((HERE / "chillcast_data.json").read_text(encoding="utf-8"))


def load_varieties() -> list[dict]:
    varieties = json.loads((HERE / "chillcast_varieties.json").read_text(encoding="utf-8"))
    for variety in varieties:
        variety["species_slug"] = checked_slug(slugify(variety["species"]))
        variety["slug"] = checked_slug(slugify(variety["name"]))
        variety["path"] = f"{VARIETY_ROOT}{variety['species_slug']}/{variety['slug']}/"
    return varieties


def is_published(site: dict) -> bool:
    return (site["country_slug"], site["slug"]) in PUBLISHED_SITES


def site_path(site: dict) -> str:
    return f"{CHILL_ROOT}{checked_slug(site['country_slug'])}/{checked_slug(site['slug'])}/"


def site_link(site: dict) -> str:
    """ページのある地点だけリンクにする。無い地点は名前だけ出す。"""
    if is_published(site):
        return f'<a href="{escape(site_path(site))}">{escape(site["name"])}</a>'
    return escape(site["name"])


def classify(requirement: float, mean_hours: float) -> str:
    """要求量と平年の 45°F 時間から fits / marginal / short を決める。"""
    if requirement <= mean_hours * 0.9:
        return "fits"
    if requirement <= mean_hours * 1.1:
        return "marginal"
    return "short"


def haversine(a: dict, b: dict) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def source_label(url: str) -> str:
    """出典 URL のホスト名を表示用のラベルにする。"""
    host = urllib.parse.urlsplit(url).netloc
    return host[4:] if host.startswith("www.") else host or url


def extension_link(site: dict) -> tuple[str, str] | None:
    return (EXTENSION_LINKS.get((site["country"], site["region"]))
            or EXTENSION_LINKS.get((site["country"], None)))


def _attribution(meta: dict) -> str:
    stamp = meta["generated_on"].replace("-", "/")
    return (
        f'<p class="chill-attribution">{escape(POWER_CREDIT)}</p>'
        f'<p class="chill-attribution">The data was obtained from the POWER Project\'s Hourly '
        f'{escape(meta["power_version"])} version on {escape(stamp)}. '
        f'<a href="{POWER_REFERENCING}">NASA POWER referencing</a></p>'
    )


def _shell(title: str, description: str, canonical: str, body: str, breadcrumb: str,
           meta: dict, head_extra: str = "") -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="{SITE}/assets/chillcast-icon.png">
  <meta name="twitter:card" content="summary">
  <link rel="alternate" hreflang="en" href="{escape(canonical)}">
  <link rel="icon" href="/assets/chillcast-icon.png">
  <link rel="stylesheet" href="/css/apps.css">
{head_extra}</head>
<body class="promo-page promo-sky">
  <header class="promo-header">
    <a class="promo-brand" href="/chillcast/en/">ATANI / <strong>ChillCast</strong></a>
    <nav class="promo-languages" aria-label="Sections"><a href="{CHILL_ROOT}">Locations</a><a href="{VARIETY_ROOT}">Varieties</a></nav>
  </header>
  <main class="privacy-main">
    <div class="privacy-card">
      <nav class="chill-crumbs" aria-label="Breadcrumb">{breadcrumb}</nav>
{body}
      <section>
        <h2>About this data</h2>
        <p>{escape(DISCLAIMER)}</p>
        <p>Source: <a href="{POWER}">NASA POWER</a> hourly 2-metre air temperature (MERRA-2). {escape(NON_ENDORSEMENT)}</p>
      </section>
    </div>
  </main>
  <footer class="promo-footer chill-footer">
    {_attribution(meta)}
    <p class="chill-footer__links"><a href="https://atani.github.io/chillcast-legal/">Support &amp; privacy</a> <span>© Atani</span></p>
  </footer>
</body>
</html>
'''


def _cta(text: str) -> str:
    return (
        f'<section><h2>Track this season in ChillCast</h2><p>{escape(text)}</p>'
        f'<p><a class="promo-button" href="{STORE}">View ChillCast on the App Store</a></p></section>'
    )


def _crumbs(*parts) -> str:
    links = [f'<a href="{escape(href)}">{escape(label)}</a>' for href, label in parts[:-1]]
    links.append(f"<span>{escape(parts[-1][1])}</span>")
    return " / ".join(links)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """セルは組み立て済みの HTML として扱う。呼び出し側でエスケープしておく。"""
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (
        '<div class="chill-scroll"><table class="chill-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def _season_story(site: dict) -> str:
    """直近シーズンが平年とどう違ったかを地点ごとの文章にする。"""
    seasons = site["seasons"]
    latest = seasons[-1]
    mean = site["stats"]["forty_five"]["mean"]
    delta = latest["forty_five"] - mean
    percent = abs(delta) / mean * 100 if mean else 0.0

    if percent < 2:
        first = (
            f"The {latest['label']} season came in at {latest['forty_five']:.0f} chill hours, "
            f"within a couple of percent of the ten-season average of {mean:.0f}."
        )
    else:
        direction = "above" if delta > 0 else "below"
        first = (
            f"The {latest['label']} season delivered {latest['forty_five']:.0f} chill hours, "
            f"{abs(delta):.0f} {direction} the ten-season average of {mean:.0f}. "
            f"That is a difference of {percent:.0f}%."
        )

    ordered = sorted(seasons, key=lambda season: season["forty_five"])
    rank = [season["label"] for season in ordered].index(latest["label"]) + 1
    if rank <= 5:
        second = f"It was the {ORDINALS[rank]} of the ten seasons recorded here."
    else:
        top = len(seasons) - rank + 1
        second = f"It was the {ORDINALS[top].replace('lowest', 'highest')} of the ten seasons recorded here."

    dynamic_mean = site["stats"]["dynamic"]["mean"]
    third = (
        f"Chill portions, which discount warm spells differently, came to "
        f"{latest['dynamic']:.1f} against a ten-season average of {dynamic_mean:.1f}."
    )
    return " ".join((first, second, third))


def render_site_page(site: dict, varieties: list[dict], published: list[dict], meta: dict) -> str:
    stats = site["stats"]
    place = f"{site['name']}, {site['region']}"
    title = f"Chill hours in {place}: the last 10 winters"
    seasons = site["seasons"]
    span = f"{seasons[0]['label']} to {seasons[-1]['label']}"
    description = (
        f"Ten seasons of chill accumulation for {place} from NASA POWER: "
        f"{stats['forty_five']['mean']:.0f} hours below 45°F, "
        f"{stats['utah']['mean']:.0f} Utah units, and "
        f"{stats['dynamic']['mean']:.0f} chill portions on average."
    )

    # 11/1 開始は UC Davis の慣行。南半球はそれを半年ずらした窓なので出典を名乗らない。
    convention = (
        ", following the UC Davis convention" if site["hemisphere"] == "north"
        else ", the Southern Hemisphere equivalent of the UC Davis 1 November start"
    )

    summary_rows = [
        [f'<strong>{escape(label)}</strong><br><span class="chill-note">{escape(note)}</span>',
         f"{stats[key]['mean']:.1f} {escape(unit)}",
         f"{stats[key]['min']:.1f}", f"{stats[key]['max']:.1f}"]
        for key, label, unit, note in MODELS
    ]
    season_rows = [
        [escape(season["label"]), f"{season['forty_five']:.0f}",
         f"{season['utah']:.1f}", f"{season['dynamic']:.1f}"]
        for season in seasons
    ]

    mean_hours = stats["forty_five"]["mean"]
    fits = sorted(
        (v for v in varieties if classify(v["chillHoursRequirement"], mean_hours) == "fits"),
        key=lambda v: -v["chillHoursRequirement"],
    )[:TOP_FITS]
    if fits:
        fit_block = (
            f'<p>The {len(fits)} most chill-demanding varieties that still fit an average of '
            f"{mean_hours:.0f} chill hours here.</p>"
            + _table(["Variety", "Species", "Chill requirement"], [
                [f'<a href="{escape(v["path"])}">{escape(v["name"])}</a>',
                 escape(v["species"]), f"{v['chillHoursRequirement']} hours"]
                for v in fits
            ])
        )
    else:
        fit_block = (
            f"<p>None of the varieties bundled with ChillCast fit an average of "
            f"{mean_hours:.0f} chill hours here.</p>"
        )

    # 「近く」と呼べる範囲だけを出す。候補が 30 地点しかないので上限を付けないと
    # 地点の少ない国では大陸を跨いだ地点が並ぶ。
    others = [other for other in sorted(published, key=lambda other: haversine(site, other))
              if not (other["country_slug"], other["slug"]) == (site["country_slug"], site["slug"])
              and haversine(site, other) <= NEARBY_MAX_KM][:NEARBY_COUNT]
    nearby_block = ""
    if others:
        nearby = "".join(
            f'<li><a href="{escape(site_path(other))}">{escape(other["name"])}, {escape(other["region"])}</a>'
            f" — {haversine(site, other):.0f} km</li>"
            for other in others
        )
        nearby_block = (
            f"<section><h2>Nearby locations</h2><ul>{nearby}</ul>"
            f'<p><a href="{CHILL_ROOT}">All chill-hour locations</a></p></section>'
        )
    else:
        nearby_block = (
            f"<section><h2>Other locations</h2><p>No other page here sits within "
            f'{NEARBY_MAX_KM:.0f} km of {escape(site["name"])}. '
            f'<a href="{CHILL_ROOT}">All chill-hour locations</a>.</p></section>'
        )

    link = extension_link(site)
    extension_block = (
        f'<section><h2>Station data for {escape(site["region"])}</h2>'
        f"<p>NASA POWER is a grid estimate. For measured station data and local chill guidance, see "
        f'<a href="{escape(link[0])}">{escape(link[1])}</a>.</p></section>'
        if link else ""
    )

    body = f'''      <h1>Chill hours in {escape(place)}: the last 10 winters</h1>
      <p>Ten seasons of winter chill for {escape(place)} ({site['lat']:.4f}, {site['lon']:.4f}),
         calculated from NASA POWER hourly temperatures across {escape(span)}. Instead of comparing
         winters yourself or hunting for the nearest weather station, the three standard models for
         fruit trees and berries are already worked out below.</p>
      <section>
        <h2>How the last season compared</h2>
        <p>{escape(_season_story(site))}</p>
      </section>
      <section>
        <h2>Ten-season average, low, and high</h2>
        {_table(["Model", "Average", "Lowest season", "Highest season"], summary_rows)}
        <p class="chill-note">45°F Hours and Utah are counted over {escape(site['chill_window'])}{escape(convention)}.
           Dynamic is counted over {escape(site['dynamic_window'])}.</p>
      </section>
      <section>
        <h2>Season by season</h2>
        {_table(["Season", "45°F Hours", "Utah units", "Chill portions"], season_rows)}
      </section>
      <section>
        <h2>Which fruit varieties suit {escape(site['name'])}?</h2>
        {fit_block}
        <p><a class="promo-button" href="{STORE}">See all varieties that fit in the ChillCast app</a></p>
      </section>
      {extension_block}
      {nearby_block}
      {_cta(f"ChillCast tracks this season's chill for {place} on your iPhone and compares it with the ten-season average above.")}
      <section>
        <h2>Generated</h2>
        <p>This page was generated on {escape(meta['generated_on'])}.</p>
      </section>'''

    return _shell(
        title, description, f"{SITE}{site_path(site)}", body,
        _crumbs(("/chillcast/en/", "ChillCast"), (CHILL_ROOT, "Chill hours"),
                (f"{CHILL_ROOT}{site['country_slug']}/", site["country"]), ("", place)),
        meta,
    )


def render_variety_page(variety: dict, sites: list[dict], varieties: list[dict], meta: dict) -> str:
    name = variety["name"]
    species = variety["species"]
    requirement = variety["chillHoursRequirement"]
    title = f"{name} {species.lower()} chill hours: {requirement} hours and where it fits"
    description = (
        f"{name} needs about {requirement} chill hours. See which of {len(sites)} fruit-growing "
        f"locations reach that in an average winter, based on NASA POWER data."
    )

    source = variety.get("source", "")
    source_cell = (
        f'<a href="{escape(source)}" rel="nofollow">{escape(source_label(source))}</a>'
        if source else "—"
    )

    grouped: dict[str, dict[str, list[dict]]] = {}
    for site in sites:
        bucket = classify(requirement, site["stats"]["forty_five"]["mean"])
        if bucket == "short":
            continue
        grouped.setdefault(site["country"], {}).setdefault(bucket, []).append(site)

    country_blocks = []
    fits_total = marginal_total = 0
    for country in sorted(grouped):
        parts = []
        for bucket in ("fits", "marginal"):
            entries = sorted(grouped[country].get(bucket, []),
                             key=lambda s: -s["stats"]["forty_five"]["mean"])
            if not entries:
                continue
            if bucket == "fits":
                fits_total += len(entries)
            else:
                marginal_total += len(entries)
            parts.append(
                f"<h4>{escape(FIT_LABELS[bucket][0])} ({len(entries)})</h4>"
                + _table(["Location", "Region", "Average chill"], [
                    [site_link(site), escape(site["region"]),
                     f"{site['stats']['forty_five']['mean']:.0f} hours"]
                    for site in entries
                ])
            )
        country_blocks.append(f"<h3>{escape(country)}</h3>" + "".join(parts))

    listing = "".join(country_blocks) or f"<p>None of the {len(sites)} locations reach this requirement on average.</p>"

    siblings = [other for other in varieties
                if other["species"] == species and other["slug"] != variety["slug"]]
    sibling_links = "".join(
        f'<li><a href="{escape(other["path"])}">{escape(other["name"])}</a> — '
        f'{other["chillHoursRequirement"]} hours</li>'
        for other in sorted(siblings, key=lambda v: v["chillHoursRequirement"])
    )
    sibling_block = (
        f"<section><h2>Other {escape(species.lower())} varieties</h2><ul>{sibling_links}</ul>"
        f'<p><a href="{VARIETY_ROOT}">All varieties</a></p></section>'
        if sibling_links else f'<section><h2>More varieties</h2><p><a href="{VARIETY_ROOT}">All varieties</a></p></section>'
    )

    body = f'''      <h1>{escape(name)} ({escape(species)}): {requirement} chill hours</h1>
      <p>{escape(name)} needs roughly {requirement} chill hours below 45°F to break dormancy properly.
         Of the {len(sites)} fruit-growing locations tracked here, {fits_total} reach that comfortably in an
         average winter and {marginal_total} are marginal.</p>
      <section>
        <h2>Chill requirement</h2>
        {_table(["Variety", "Species", "Requirement", "Source"],
                [[escape(name), escape(species), f"{requirement} hours (45°F Hours model)", source_cell]])}
        <p class="chill-note">Requirements are the representative 45°F-hours figures bundled with ChillCast,
           each taken from the published source linked above.
           Nurseries publish slightly different numbers for the same variety, so treat this as a mid-range value.</p>
      </section>
      <section>
        <h2>Where {escape(name)} gets enough chill</h2>
        <p>Each location is compared with its ten-season average chill from NASA POWER.
           A location fits when the requirement is at or below 90% of its average, and is marginal up to 110%.
           Locations with their own page are linked; the rest are listed for comparison.</p>
        {listing}
      </section>
      {sibling_block}
      {_cta(f"ChillCast tracks this season's chill against the {requirement} hours {name} needs, wherever you grow it.")}
      <section>
        <h2>Generated</h2>
        <p>This page was generated on {escape(meta['generated_on'])}.</p>
      </section>'''

    return _shell(
        title, description, f"{SITE}{variety['path']}", body,
        _crumbs(("/chillcast/en/", "ChillCast"), (VARIETY_ROOT, "Varieties"),
                (f"{VARIETY_ROOT}#{variety['species_slug']}", species), ("", name)),
        meta,
    )


def _calculator(sites: list[dict], varieties: list[dict]) -> str:
    options = "".join(
        f'<option value="{escape(site["slug"])}" data-lat="{site["lat"]}" data-lon="{site["lon"]}">'
        f'{escape(site["name"])}, {escape(site["region"])} ({escape(site["country"])})</option>'
        for site in sorted(sites, key=lambda s: (s["country"], s["name"]))
    )
    # script 要素へ入れるので閉じタグを無害化する。JSON では "<\\/" と "</" が同じ
    # 文字列を表すため、JSON.parse 側は変更しなくてよい。
    payload = json.dumps([
        {"name": v["name"], "species": v["species"], "requirement": v["chillHoursRequirement"]}
        for v in sorted(varieties, key=lambda v: -v["chillHoursRequirement"])
    ], ensure_ascii=False).replace("</", "<\\/")
    return f'''      <section id="calculator">
        <h2>Calculate chill for any point</h2>
        <p>This runs in your browser. It asks NASA POWER for ten years of hourly temperatures at the
           point you choose, then works out the same three models used on every page here. Nothing is
           sent anywhere else, and there is no account.</p>
        <form id="chill-calculator" class="chill-form">
          <div class="chill-field">
            <label for="chill-site">Pick one of the {len(sites)} locations</label>
            <select id="chill-site"><option value="">Choose a location…</option>{options}</select>
            <button type="button" class="promo-button" id="chill-site-go">Calculate</button>
          </div>
          <div class="chill-field">
            <label for="chill-geo-go">Use where you are</label>
            <p class="chill-note">Your browser will ask permission. The coordinates are rounded to
               0.1° before they are sent to NASA POWER.</p>
            <button type="button" class="promo-button" id="chill-geo-go">Use my location</button>
          </div>
          <div class="chill-field">
            <span class="chill-field__label" id="chill-coords-label">Or enter coordinates</span>
            <div class="chill-coords" role="group" aria-labelledby="chill-coords-label">
              <input id="chill-lat" aria-label="Latitude" type="number" step="0.01" min="-90" max="90" placeholder="Latitude, e.g. 36.75" inputmode="decimal">
              <input id="chill-lon" aria-label="Longitude" type="number" step="0.01" min="-180" max="180" placeholder="Longitude, e.g. -119.77" inputmode="decimal">
            </div>
            <button type="button" class="promo-button" id="chill-manual-go">Calculate</button>
          </div>
        </form>
        <p id="chill-status" class="chill-status" role="status" aria-live="polite"></p>
        <div id="chill-output"></div>
        <script type="application/json" id="chill-varieties">{payload}</script>
      </section>'''


def render_site_index(sites: list[dict], varieties: list[dict], meta: dict) -> str:
    title = "Chill hours by location: a calculator and 10-winter averages"
    description = (
        "Work out chill hours for any point from NASA POWER in your browser, or read ten-season "
        "averages for fruit-growing regions in seven countries."
    )
    published = [site for site in sites if is_published(site)]
    by_country: dict[str, list[dict]] = {}
    for site in sites:
        by_country.setdefault(site["country"], []).append(site)

    blocks = []
    for country in sorted(by_country):
        rows = [
            [site_link(site), escape(site["region"]),
             f"{site['stats']['forty_five']['mean']:.0f}",
             f"{site['stats']['utah']['mean']:.0f}",
             f"{site['stats']['dynamic']['mean']:.1f}"]
            for site in sorted(by_country[country], key=lambda s: s["name"])
        ]
        blocks.append(
            f'<section id="{escape(by_country[country][0]["country_slug"])}">'
            f"<h2>{escape(country)} ({len(by_country[country])})</h2>"
            + _table(["Location", "Region", "45°F Hours", "Utah units", "Chill portions"], rows)
            + "</section>"
        )

    body = f'''      <h1>Chill hours by location</h1>
      <p>Ten-season averages for {len(sites)} fruit-growing regions and cities, calculated from
         NASA POWER hourly temperatures with the 45°F Hours, Utah, and Dynamic models. You can also
         calculate any point yourself below. {len(published)} locations have a full page with the
         season-by-season table and the varieties that suit them.</p>
{_calculator(sites, varieties)}
      <section>
        <h2>Chill hours are not USDA hardiness zones</h2>
        <p>The two answer different questions and are easy to confuse. A USDA hardiness zone describes
           the coldest winter night a plant has to survive, so it tells you whether a tree or bush
           lives through the winter. Chill hours describe how long the plant spends in the cold range
           that ends dormancy, so they tell you whether it will flower and set fruit at all.</p>
        <p>Two places can share a hardiness zone and still differ by hundreds of chill hours. That is
           why a low-chill peach can sit dormant and fruitless in a cold garden it survives easily,
           and a high-chill apple can leaf out raggedly in a mild one. Fruit trees and berries need
           both numbers checked, not just the zone on the label.</p>
      </section>
      {"".join(blocks)}
      <section><h2>Varieties</h2><p><a href="{VARIETY_ROOT}">Browse fruit varieties by chill requirement</a></p></section>
      {_cta("ChillCast tracks this season's chill for any location on your iPhone.")}
      <section><h2>Generated</h2><p>This page was generated on {escape(meta['generated_on'])}.</p></section>'''

    head_extra = f'  <script src="{CALCULATOR_SRC}" defer></script>\n'
    return _shell(title, description, f"{SITE}{CHILL_ROOT}", body,
                  _crumbs(("/chillcast/en/", "ChillCast"), ("", "Chill hours")),
                  meta, head_extra)


def render_country_index(country: str, country_slug: str, sites: list[dict], meta: dict) -> str:
    published = [site for site in sites if is_published(site)]
    title = f"Chill hours in {country}: {len(sites)} fruit-growing locations"
    description = (
        f"Ten-season chill hour averages for {len(sites)} fruit-growing regions and cities in "
        f"{country}, calculated from NASA POWER hourly temperatures."
    )
    rows = [
        [site_link(site), escape(site["region"]),
         f"{site['stats']['forty_five']['mean']:.0f}",
         f"{site['stats']['utah']['mean']:.0f}",
         f"{site['stats']['dynamic']['mean']:.1f}"]
        for site in sorted(sites, key=lambda s: s["name"])
    ]
    coldest = max(sites, key=lambda s: s["stats"]["forty_five"]["mean"])
    mildest = min(sites, key=lambda s: s["stats"]["forty_five"]["mean"])
    window = sites[0]["chill_window"]
    spread = (
        f"Across these locations the ten-season average runs from "
        f"{mildest['stats']['forty_five']['mean']:.0f} chill hours at {escape(mildest['name'])}, "
        f"{escape(mildest['region'])}, to {coldest['stats']['forty_five']['mean']:.0f} at "
        f"{escape(coldest['name'])}, {escape(coldest['region'])}. "
        f"45°F Hours and Utah are counted over {escape(window)}."
        if len(sites) > 1 else
        f"45°F Hours and Utah are counted over {escape(window)}."
    )

    body = f'''      <h1>Chill hours in {escape(country)}</h1>
      <p>Ten-season averages for {len(sites)} locations in {escape(country)}, from NASA POWER hourly
         temperatures. {len(published)} of them have a full page with the season-by-season table and
         the fruit trees and berries that suit them.</p>
      <section>
        <h2>Where fruit grows in {escape(country)}</h2>
        <p>{escape(COUNTRY_NOTES[country])}</p>
        <p>{spread}</p>
      </section>
      <section>
        <h2>Locations</h2>
        {_table(["Location", "Region", "45°F Hours", "Utah units", "Chill portions"], rows)}
      </section>
      <section><h2>Other countries</h2><p><a href="{CHILL_ROOT}">All chill-hour locations</a>, including a
         calculator for any point.</p></section>
      {_cta(f"ChillCast tracks this season's chill for any location in {country} on your iPhone.")}
      <section><h2>Generated</h2><p>This page was generated on {escape(meta['generated_on'])}.</p></section>'''

    return _shell(title, description, f"{SITE}{CHILL_ROOT}{country_slug}/", body,
                  _crumbs(("/chillcast/en/", "ChillCast"), (CHILL_ROOT, "Chill hours"), ("", country)),
                  meta)


def render_variety_index(varieties: list[dict], sites: list[dict], meta: dict) -> str:
    title = "Fruit variety chill requirements"
    description = (
        "Chill hour requirements for fruit tree and berry varieties, with the fruit-growing "
        "locations that reach them in an average winter."
    )
    by_species: dict[str, list[dict]] = {}
    for variety in varieties:
        by_species.setdefault(variety["species"], []).append(variety)

    blocks = []
    for species in sorted(by_species):
        rows = []
        for variety in sorted(by_species[species], key=lambda v: v["chillHoursRequirement"]):
            fits = sum(1 for site in sites
                       if classify(variety["chillHoursRequirement"], site["stats"]["forty_five"]["mean"]) == "fits")
            rows.append([
                f'<a href="{escape(variety["path"])}">{escape(variety["name"])}</a>',
                f'{variety["chillHoursRequirement"]} hours',
                f"{fits} of {len(sites)}",
            ])
        blocks.append(
            f'<section id="{escape(by_species[species][0]["species_slug"])}"><h2>{escape(species)}</h2>'
            + _table(["Variety", "Chill requirement", "Locations that fit"], rows)
            + "</section>"
        )

    body = f'''      <h1>Fruit variety chill requirements</h1>
      <p>How many chill hours each fruit tree and berry variety needs, and how many of the {len(sites)}
         locations tracked here reach that in an average winter. Open a variety for the full list by country.</p>
      {"".join(blocks)}
      <section><h2>Locations</h2><p><a href="{CHILL_ROOT}">Browse chill hours by location</a>, or calculate
         any point in your browser.</p></section>
      {_cta("ChillCast tracks this season's chill against the varieties you grow.")}
      <section><h2>Generated</h2><p>This page was generated on {escape(meta['generated_on'])}.</p></section>'''

    return _shell(title, description, f"{SITE}{VARIETY_ROOT}", body,
                  _crumbs(("/chillcast/en/", "ChillCast"), ("", "Varieties")), meta)


def build_pages() -> list[tuple[str, str, str]]:
    """(URL パス, public 配下の出力先, HTML) を返す。"""
    data = load_data()
    sites = data["sites"]
    varieties = load_varieties()
    meta = {"generated_on": data["generated_on"], "power_version": data["power_version"]}
    published = [site for site in sites if is_published(site)]

    missing = PUBLISHED_SITES - {(site["country_slug"], site["slug"]) for site in sites}
    if missing:
        raise SystemExit(f"PUBLISHED_SITES に未知の地点があります: {sorted(missing)}")

    unknown_countries = {site["country"] for site in sites} - set(COUNTRY_NOTES)
    if unknown_countries:
        raise SystemExit(f"COUNTRY_NOTES に無い国があります: {sorted(unknown_countries)}")

    # 普及機関のリンクは設計上「各ページに置く」項目なので、欠けたら落とす。
    # if link else "" の分岐で節が黙って消えるのを防ぐ。
    without_link = [f"{site['country']} / {site['region']}"
                    for site in published if extension_link(site) is None]
    if without_link:
        raise SystemExit(f"EXTENSION_LINKS に無い地域があります: {sorted(set(without_link))}")

    pages: list[tuple[str, str, str]] = [
        (CHILL_ROOT, "chillcast/chill-hours/index.html", render_site_index(sites, varieties, meta)),
        (VARIETY_ROOT, "chillcast/varieties/index.html", render_variety_index(varieties, sites, meta)),
    ]

    by_country: dict[tuple[str, str], list[dict]] = {}
    for site in sites:
        by_country.setdefault((site["country"], site["country_slug"]), []).append(site)
    for (country, country_slug), group in sorted(by_country.items()):
        path = f"{CHILL_ROOT}{country_slug}/"
        pages.append((path, f"chillcast/chill-hours/{country_slug}/index.html",
                      render_country_index(country, country_slug, group, meta)))

    for site in published:
        pages.append((site_path(site),
                      f"chillcast/chill-hours/{site['country_slug']}/{site['slug']}/index.html",
                      render_site_page(site, varieties, published, meta)))

    for variety in varieties:
        pages.append((variety["path"],
                      f"chillcast/varieties/{variety['species_slug']}/{variety['slug']}/index.html",
                      render_variety_page(variety, sites, varieties, meta)))

    return pages
