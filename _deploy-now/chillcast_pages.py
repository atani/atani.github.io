"""ChillCast の地点別・品種別ページ（英語）を組み立てる。

数値は `scripts/build-chillcast-pages.py` が NASA POWER から作った
`chillcast_data.json`、品種は `chillcast_varieties.json` を読む。どちらもコミット
済みなので、`scripts/build-deploy-now.py` はネットワークに触らずに描画できる。
"""

import json
import pathlib
import re
import unicodedata
from html import escape

HERE = pathlib.Path(__file__).resolve().parent
SITE = "https://atani.lolipop-now.app"
STORE = "https://apps.apple.com/us/app/id6785241430"
POWER = "https://power.larc.nasa.gov/"
CHILL_ROOT = "/chillcast/chill-hours/"
VARIETY_ROOT = "/chillcast/varieties/"

DISCLAIMER = (
    "Values are NASA POWER regional estimates (about 0.5° grid), not orchard "
    "measurements. Check your local extension service for station data."
)
NON_ENDORSEMENT = "NASA does not endorse ChillCast."

MODELS = [
    ("forty_five", "45°F Hours", "hours", "Hours between 0 and 7.2°C (32–45°F)."),
    ("utah", "Utah", "units", "Weighted bands; warm hours subtract from the total."),
    ("dynamic", "Dynamic", "portions", "Fishman–Erez model; handles warm spells."),
]


def slugify(value: str) -> str:
    text = value.replace("ı", "i").replace("İ", "i").replace("ğ", "g").replace("ş", "s")
    text = text.replace("ö", "o").replace("ü", "u").replace("ç", "c").replace("ñ", "n")
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()


def load_data() -> dict:
    return json.loads((HERE / "chillcast_data.json").read_text(encoding="utf-8"))


def load_varieties() -> list[dict]:
    varieties = json.loads((HERE / "chillcast_varieties.json").read_text(encoding="utf-8"))
    for variety in varieties:
        variety["species_slug"] = slugify(variety["species"])
        variety["slug"] = slugify(variety["name"])
        variety["path"] = f"{VARIETY_ROOT}{variety['species_slug']}/{variety['slug']}/"
    return varieties


def site_path(site: dict) -> str:
    return f"{CHILL_ROOT}{site['country_slug']}/{site['slug']}/"


def classify(requirement: float, mean_hours: float) -> str:
    """要求量と平年の 45°F 時間から fits / marginal / short を決める。"""
    if requirement <= mean_hours * 0.9:
        return "fits"
    if requirement <= mean_hours * 1.1:
        return "marginal"
    return "short"


FIT_LABELS = {
    "fits": ("Fits", "Average chill clears the requirement with room to spare."),
    "marginal": ("Marginal", "Average chill is close to the requirement; some winters fall short."),
    "short": ("Short", "Average chill is below the requirement."),
}


def _shell(title: str, description: str, canonical: str, body: str, breadcrumb: str) -> str:
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
</head>
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
  <footer class="promo-footer"><a href="https://atani.github.io/chillcast-legal/">Support &amp; privacy</a><span>© Atani</span></footer>
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


def _fit_table(rows: list[tuple[str, str, str]], empty: str) -> str:
    if not rows:
        return f"<p>{escape(empty)}</p>"
    cells = "".join(
        f"<tr><td>{first}</td><td>{second}</td><td>{third}</td></tr>"
        for first, second, third in rows
    )
    return (
        '<div class="chill-scroll"><table class="chill-table">'
        "<thead><tr><th>Variety</th><th>Species</th><th>Chill requirement</th></tr></thead>"
        f"<tbody>{cells}</tbody></table></div>"
    )


def render_site_page(site: dict, varieties: list[dict], generated_on: str) -> str:
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

    summary_rows = "".join(
        f"<tr><td><strong>{escape(label)}</strong><br><span class=\"chill-note\">{escape(note)}</span></td>"
        f"<td>{stats[key]['mean']:.1f} {escape(unit)}</td>"
        f"<td>{stats[key]['min']:.1f}</td><td>{stats[key]['max']:.1f}</td></tr>"
        for key, label, unit, note in MODELS
    )
    season_rows = "".join(
        f"<tr><td>{escape(season['label'])}</td><td>{season['forty_five']:.0f}</td>"
        f"<td>{season['utah']:.1f}</td><td>{season['dynamic']:.1f}</td></tr>"
        for season in seasons
    )

    # 11/1 開始は UC Davis の慣行。南半球はそれを半年ずらした窓なので出典を名乗らない。
    convention = (
        ", following the UC Davis convention" if site["hemisphere"] == "north"
        else ", the Southern Hemisphere equivalent of the UC Davis 1 November start"
    )
    mean_hours = stats["forty_five"]["mean"]
    buckets: dict[str, list[tuple[str, str, str]]] = {"fits": [], "marginal": [], "short": []}
    for variety in sorted(varieties, key=lambda v: (v["species"], v["chillHoursRequirement"])):
        bucket = classify(variety["chillHoursRequirement"], mean_hours)
        buckets[bucket].append((
            f'<a href="{escape(variety["path"])}">{escape(variety["name"])}</a>',
            escape(variety["species"]),
            f"{variety['chillHoursRequirement']} hours",
        ))

    fit_sections = "".join(
        f"<h3>{escape(FIT_LABELS[key][0])} ({len(buckets[key])})</h3>"
        f"<p class=\"chill-note\">{escape(FIT_LABELS[key][1])}</p>"
        + _fit_table(buckets[key], "No varieties in this group.")
        for key in ("fits", "marginal", "short")
    )

    nearby = "".join(
        f'<li><a href="{CHILL_ROOT}{escape(item["country_slug"])}/{escape(item["slug"])}/">'
        f'{escape(item["name"])}, {escape(item["region"])}</a> — {item["km"]} km</li>'
        for item in site.get("nearby", [])
    )

    body = f'''      <h1>Chill hours in {escape(place)}: the last 10 winters</h1>
      <p>Ten seasons of winter chill for {escape(place)} ({site['lat']:.4f}, {site['lon']:.4f}),
         calculated from NASA POWER hourly temperatures across {escape(span)}. Instead of comparing
         winters yourself or hunting for the nearest weather station, the three standard models are
         already worked out below.</p>
      <section>
        <h2>Ten-season average, low, and high</h2>
        <div class="chill-scroll"><table class="chill-table">
          <thead><tr><th>Model</th><th>Average</th><th>Lowest season</th><th>Highest season</th></tr></thead>
          <tbody>{summary_rows}</tbody>
        </table></div>
        <p class="chill-note">45°F Hours and Utah are counted over {escape(site['chill_window'])}{escape(convention)}.
           Dynamic is counted over {escape(site['dynamic_window'])}.</p>
      </section>
      <section>
        <h2>Season by season</h2>
        <div class="chill-scroll"><table class="chill-table">
          <thead><tr><th>Season</th><th>45°F Hours</th><th>Utah units</th><th>Chill portions</th></tr></thead>
          <tbody>{season_rows}</tbody>
        </table></div>
      </section>
      <section>
        <h2>Which fruit varieties suit {escape(site['name'])}?</h2>
        <p>Compared against the ten-season average of {mean_hours:.0f} chill hours.
           A variety fits when its requirement is at or below 90% of that average, and is marginal
           up to 110%.</p>
        {fit_sections}
      </section>
      <section>
        <h2>Nearby locations</h2>
        <ul>{nearby}</ul>
        <p><a href="{CHILL_ROOT}">All chill-hour locations</a></p>
      </section>
      {_cta(f"ChillCast tracks this season's chill for {place} on your iPhone and compares it with the ten-season average above.")}
      <section>
        <h2>Generated</h2>
        <p>This page was generated on {escape(generated_on)}.</p>
      </section>'''

    return _shell(
        title, description, f"{SITE}{site_path(site)}", body,
        _crumbs(("/chillcast/en/", "ChillCast"), (CHILL_ROOT, "Chill hours"),
                (f"{CHILL_ROOT}{site['country_slug']}/", site["country"]), ("", place)),
    )


def render_variety_page(variety: dict, sites: list[dict], varieties: list[dict], generated_on: str) -> str:
    name = variety["name"]
    species = variety["species"]
    requirement = variety["chillHoursRequirement"]
    title = f"{name} {species.lower()} chill hours: {requirement} hours and where it fits"
    description = (
        f"{name} needs about {requirement} chill hours. See which of 150 fruit-growing "
        f"locations reach that in an average winter, based on NASA POWER data."
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
            items = "".join(
                f'<tr><td><a href="{site_path(site)}">{escape(site["name"])}</a></td>'
                f'<td>{escape(site["region"])}</td>'
                f'<td>{site["stats"]["forty_five"]["mean"]:.0f} hours</td></tr>'
                for site in entries
            )
            parts.append(
                f"<h4>{escape(FIT_LABELS[bucket][0])} ({len(entries)})</h4>"
                '<div class="chill-scroll"><table class="chill-table">'
                "<thead><tr><th>Location</th><th>Region</th><th>Average chill</th></tr></thead>"
                f"<tbody>{items}</tbody></table></div>"
            )
        country_blocks.append(f"<h3>{escape(country)}</h3>" + "".join(parts))

    listing = "".join(country_blocks) or "<p>None of the 150 locations reach this requirement on average.</p>"

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
         Of the 150 fruit-growing locations on this site, {fits_total} reach that comfortably in an
         average winter and {marginal_total} are marginal.</p>
      <section>
        <h2>Chill requirement</h2>
        <div class="chill-scroll"><table class="chill-table">
          <thead><tr><th>Variety</th><th>Species</th><th>Requirement</th></tr></thead>
          <tbody><tr><td>{escape(name)}</td><td>{escape(species)}</td><td>{requirement} hours (45°F Hours model)</td></tr></tbody>
        </table></div>
        <p class="chill-note">Requirements are the representative 45°F-hours figures bundled with ChillCast.
           Nurseries publish slightly different numbers for the same variety, so treat this as a mid-range value.</p>
      </section>
      <section>
        <h2>Where {escape(name)} gets enough chill</h2>
        <p>Each location is compared with its ten-season average chill from NASA POWER.
           A location fits when the requirement is at or below 90% of its average, and is marginal up to 110%.</p>
        {listing}
      </section>
      {sibling_block}
      {_cta(f"ChillCast tracks this season's chill against the {requirement} hours {name} needs, wherever you grow it.")}
      <section>
        <h2>Generated</h2>
        <p>This page was generated on {escape(generated_on)}.</p>
      </section>'''

    return _shell(
        title, description, f"{SITE}{variety['path']}", body,
        _crumbs(("/chillcast/en/", "ChillCast"), (VARIETY_ROOT, "Varieties"),
                (f"{VARIETY_ROOT}#{variety['species_slug']}", species), ("", name)),
    )


def render_site_index(sites: list[dict], generated_on: str) -> str:
    title = "Chill hours by location: 150 fruit-growing regions"
    description = (
        "Ten-season chill hour averages for 150 fruit-growing regions and cities across the "
        "United States, Canada, Australia, New Zealand, South Africa, Spain, and Turkey."
    )
    by_country: dict[str, list[dict]] = {}
    for site in sites:
        by_country.setdefault(site["country"], []).append(site)

    blocks = []
    for country in sorted(by_country):
        rows = "".join(
            f'<tr><td><a href="{site_path(site)}">{escape(site["name"])}</a></td>'
            f'<td>{escape(site["region"])}</td>'
            f'<td>{site["stats"]["forty_five"]["mean"]:.0f}</td>'
            f'<td>{site["stats"]["utah"]["mean"]:.0f}</td>'
            f'<td>{site["stats"]["dynamic"]["mean"]:.1f}</td></tr>'
            for site in sorted(by_country[country], key=lambda s: s["name"])
        )
        blocks.append(
            f'<section id="{escape(by_country[country][0]["country_slug"])}">'
            f"<h2>{escape(country)} ({len(by_country[country])})</h2>"
            '<div class="chill-scroll"><table class="chill-table">'
            "<thead><tr><th>Location</th><th>Region</th><th>45°F Hours</th>"
            "<th>Utah units</th><th>Chill portions</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div></section>"
        )

    body = f'''      <h1>Chill hours by location</h1>
      <p>Ten-season averages for {len(sites)} fruit-growing regions and cities, calculated from
         NASA POWER hourly temperatures with the 45°F Hours, Utah, and Dynamic models.
         Every figure below is a ten-season mean; open a location for the season-by-season table
         and the varieties that suit it.</p>
      {"".join(blocks)}
      <section><h2>Varieties</h2><p><a href="{VARIETY_ROOT}">Browse fruit varieties by chill requirement</a></p></section>
      {_cta("ChillCast tracks this season's chill for any location on your iPhone.")}
      <section><h2>Generated</h2><p>This page was generated on {escape(generated_on)}.</p></section>'''

    return _shell(title, description, f"{SITE}{CHILL_ROOT}", body,
                  _crumbs(("/chillcast/en/", "ChillCast"), ("", "Chill hours")))


def render_country_index(country: str, country_slug: str, sites: list[dict], generated_on: str) -> str:
    title = f"Chill hours in {country}: {len(sites)} fruit-growing locations"
    description = (
        f"Ten-season chill hour averages for {len(sites)} fruit-growing regions and cities in "
        f"{country}, calculated from NASA POWER hourly temperatures."
    )
    rows = "".join(
        f'<tr><td><a href="{site_path(site)}">{escape(site["name"])}</a></td>'
        f'<td>{escape(site["region"])}</td>'
        f'<td>{site["stats"]["forty_five"]["mean"]:.0f}</td>'
        f'<td>{site["stats"]["utah"]["mean"]:.0f}</td>'
        f'<td>{site["stats"]["dynamic"]["mean"]:.1f}</td></tr>'
        for site in sorted(sites, key=lambda s: s["name"])
    )
    body = f'''      <h1>Chill hours in {escape(country)}</h1>
      <p>Ten-season averages for {len(sites)} locations in {escape(country)}, from NASA POWER hourly
         temperatures. Open a location for the season-by-season table and the fruit varieties that suit it.</p>
      <section>
        <h2>Locations</h2>
        <div class="chill-scroll"><table class="chill-table">
          <thead><tr><th>Location</th><th>Region</th><th>45°F Hours</th><th>Utah units</th><th>Chill portions</th></tr></thead>
          <tbody>{rows}</tbody>
        </table></div>
      </section>
      <section><h2>Other countries</h2><p><a href="{CHILL_ROOT}">All chill-hour locations</a></p></section>
      {_cta(f"ChillCast tracks this season's chill for any location in {country} on your iPhone.")}
      <section><h2>Generated</h2><p>This page was generated on {escape(generated_on)}.</p></section>'''

    return _shell(title, description, f"{SITE}{CHILL_ROOT}{country_slug}/", body,
                  _crumbs(("/chillcast/en/", "ChillCast"), (CHILL_ROOT, "Chill hours"), ("", country)))


def render_variety_index(varieties: list[dict], sites: list[dict], generated_on: str) -> str:
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
            rows.append(
                f'<tr><td><a href="{escape(variety["path"])}">{escape(variety["name"])}</a></td>'
                f'<td>{variety["chillHoursRequirement"]} hours</td><td>{fits} of {len(sites)}</td></tr>'
            )
        blocks.append(
            f'<section id="{escape(by_species[species][0]["species_slug"])}"><h2>{escape(species)}</h2>'
            '<div class="chill-scroll"><table class="chill-table">'
            "<thead><tr><th>Variety</th><th>Chill requirement</th><th>Locations that fit</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div></section>"
        )

    body = f'''      <h1>Fruit variety chill requirements</h1>
      <p>How many chill hours each variety needs, and how many of the {len(sites)} locations on this
         site reach that in an average winter. Open a variety for the full list by country.</p>
      {"".join(blocks)}
      <section><h2>Locations</h2><p><a href="{CHILL_ROOT}">Browse chill hours by location</a></p></section>
      {_cta("ChillCast tracks this season's chill against the varieties you grow.")}
      <section><h2>Generated</h2><p>This page was generated on {escape(generated_on)}.</p></section>'''

    return _shell(title, description, f"{SITE}{VARIETY_ROOT}", body,
                  _crumbs(("/chillcast/en/", "ChillCast"), ("", "Varieties")))


def build_pages() -> list[tuple[str, str, str]]:
    """(URL パス, public 配下の出力先, HTML) を返す。"""
    data = load_data()
    sites = data["sites"]
    generated_on = data["generated_on"]
    varieties = load_varieties()

    pages: list[tuple[str, str, str]] = [
        (CHILL_ROOT, "chillcast/chill-hours/index.html", render_site_index(sites, generated_on)),
        (VARIETY_ROOT, "chillcast/varieties/index.html", render_variety_index(varieties, sites, generated_on)),
    ]

    by_country: dict[tuple[str, str], list[dict]] = {}
    for site in sites:
        by_country.setdefault((site["country"], site["country_slug"]), []).append(site)
    for (country, country_slug), group in sorted(by_country.items()):
        path = f"{CHILL_ROOT}{country_slug}/"
        pages.append((path, f"chillcast/chill-hours/{country_slug}/index.html",
                      render_country_index(country, country_slug, group, generated_on)))

    for site in sites:
        path = site_path(site)
        pages.append((path, f"chillcast/chill-hours/{site['country_slug']}/{site['slug']}/index.html",
                      render_site_page(site, varieties, generated_on)))

    for variety in varieties:
        pages.append((variety["path"],
                      f"chillcast/varieties/{variety['species_slug']}/{variety['slug']}/index.html",
                      render_variety_page(variety, sites, varieties, generated_on)))

    return pages
