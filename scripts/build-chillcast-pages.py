#!/usr/bin/env python3
"""ChillCast の地点別ページ用に NASA POWER の平年値を作る。

150 地点それぞれについて NASA POWER の hourly API から 10 年分の気温を 1 リクエストで
取得し、45°F Hours / Utah / Dynamic の 3 モデルを直近 10 シーズン分計算して
`_deploy-now/chillcast_data.json` に書き出す。ページの HTML は
`scripts/build-deploy-now.py` が `_deploy-now/chillcast_pages.py` を使って組み立てる。

生の JSON は `_deploy-now/chillcast_cache/` に gzip で残す（.gitignore 済み）。
`--refresh` を付けるとキャッシュを無視して取り直す。

    python3 scripts/build-chillcast-pages.py
    python3 scripts/build-chillcast-pages.py --refresh
"""

import argparse
import datetime as dt
import gzip
import json
import math
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITES_PATH = ROOT / "_deploy-now/chillcast_sites.json"
DATA_PATH = ROOT / "_deploy-now/chillcast_data.json"
CACHE_DIR = ROOT / "_deploy-now/chillcast_cache"

POWER_URL = (
    "https://power.larc.nasa.gov/api/temporal/hourly/point"
    "?parameters=T2M&community=AG&longitude={lon}&latitude={lat}"
    "&start={start}&end={end}&format=JSON"
)
FETCH_START = dt.date(2015, 9, 1)
FILL_THRESHOLD = -900.0
SEASON_COUNT = 10
MIN_COVERAGE = 0.95
REQUEST_INTERVAL = 0.3
RETRIES = 3
NEARBY_COUNT = 5

# 積算期間。北半球は UC Davis / Dave Wilson の慣行に合わせて 11/1 開始。
WINDOWS = {
    "north": {
        "chill": ((11, 1), (2, 28), 1),
        "dynamic": ((9, 1), (3, 31), 1),
    },
    "south": {
        "chill": ((5, 1), (8, 31), 0),
        "dynamic": ((3, 1), (9, 30), 0),
    },
}
WINDOW_LABELS = {
    "north": {"chill": "1 November – 28 February", "dynamic": "1 September – 31 March"},
    "south": {"chill": "1 May – 31 August", "dynamic": "1 March – 30 September"},
}


def utah_unit(celsius: float) -> float:
    """Sources/ChillCast/Models/ChillModels.swift の utahUnit と同じ半開区間。"""
    if celsius < 1.4:
        return 0.0
    if celsius < 2.4:
        return 0.5
    if celsius < 9.1:
        return 1.0
    if celsius < 12.4:
        return 0.5
    if celsius < 15.9:
        return 0.0
    if celsius < 18.0:
        return -0.5
    return -1.0


class DynamicState:
    """Fishman & Erez (1987)。Swift 実装の DynamicState と同じ定数・式。"""

    E0 = 4153.5
    E1 = 12888.8
    A0 = 139500.0
    A1 = 2_567_000_000_000_000_000.0
    SLOPE = 1.6
    TETMLT = 277.0
    AA = A0 / A1
    EE = E1 - E0

    def __init__(self) -> None:
        self.inter_s = 0.0
        self.portions = 0.0

    def step(self, celsius: float) -> None:
        tk = celsius + 273.0
        ftmprt = self.SLOPE * self.TETMLT * (tk - self.TETMLT) / tk
        sr = math.exp(ftmprt)
        xi = sr / (1.0 + sr)
        xs = self.AA * math.exp(self.EE / tk)
        ak1 = self.A1 * math.exp(-self.E1 / tk)
        inter_e = xs - (xs - self.inter_s) * math.exp(-ak1)
        if inter_e < 1.0:
            self.inter_s = inter_e
        else:
            self.portions += xi * inter_e
            self.inter_s = inter_e * (1.0 - xi)


def season_bounds(hemisphere: str, kind: str, year: int) -> tuple[dt.date, dt.date]:
    (start_month, start_day), (end_month, end_day), year_offset = WINDOWS[hemisphere][kind]
    start = dt.date(year, start_month, start_day)
    end_year = year + year_offset
    if end_month == 2 and end_day == 28:
        end_day = 29 if _is_leap(end_year) else 28
    return start, dt.date(end_year, end_month, end_day)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def season_label(hemisphere: str, year: int) -> str:
    if hemisphere == "north":
        return f"{year}–{str(year + 1)[2:]}"
    return str(year)


def cache_path(site: dict) -> pathlib.Path:
    return CACHE_DIR / f"{site['country_slug']}__{site['slug']}.json.gz"


def fetch_hourly(site: dict, end: dt.date, refresh: bool) -> dict[str, float]:
    """時刻キー YYYYMMDDHH -> 摂氏。欠測（<= -900）は落とす。"""
    path = cache_path(site)
    if path.exists() and not refresh:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)["values"]

    url = POWER_URL.format(
        lon=site["lon"], lat=site["lat"],
        start=FETCH_START.strftime("%Y%m%d"), end=end.strftime("%Y%m%d"),
    )
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                payload = json.load(response)
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == RETRIES:
                raise RuntimeError(f"NASA POWER の取得に失敗: {error}") from error
            time.sleep(2.0 * attempt)
    else:  # pragma: no cover - break で必ず抜ける
        raise RuntimeError(f"NASA POWER の取得に失敗: {last_error}")

    raw = payload["properties"]["parameter"]["T2M"]
    values = {key: float(value) for key, value in raw.items() if float(value) > FILL_THRESHOLD}
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump({"fetched_at": dt.date.today().isoformat(), "end": end.isoformat(),
                   "lat": site["lat"], "lon": site["lon"], "values": values}, handle)
    return values


def accumulate(values: dict[str, float], start: dt.date, end: dt.date) -> dict | None:
    """期間内の 3 モデルを 1 パスで積算する。欠測が多い季節は None を返す。"""
    expected = (end - start).days * 24 + 24
    forty_five = 0.0
    utah = 0.0
    dynamic = DynamicState()
    good = 0
    day = start
    while day <= end:
        prefix = day.strftime("%Y%m%d")
        for hour in range(24):
            celsius = values.get(f"{prefix}{hour:02d}")
            if celsius is None:
                continue
            good += 1
            if 0.0 <= celsius <= 7.2:
                forty_five += 1.0
            utah += utah_unit(celsius)
            dynamic.step(celsius)
        day += dt.timedelta(days=1)
    if good < expected * MIN_COVERAGE:
        return None
    return {"forty_five": forty_five, "utah": utah, "dynamic": dynamic.portions,
            "coverage": good / expected}


def complete_years(hemisphere: str, data_start: dt.date, data_end: dt.date) -> list[int]:
    """45°F / Utah と Dynamic の両方の窓が data の中に収まる年だけを返す。"""
    years = []
    for year in range(data_start.year, data_end.year + 1):
        windows = [season_bounds(hemisphere, kind, year) for kind in ("chill", "dynamic")]
        if all(start >= data_start and end <= data_end for start, end in windows):
            years.append(year)
    return years[-SEASON_COUNT:]


def summarise(seasons: list[dict], key: str) -> dict:
    values = [season[key] for season in seasons]
    return {
        "mean": round(sum(values) / len(values), 1),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
    }


def haversine(a: dict, b: dict) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def build(limit: int | None, refresh: bool) -> int:
    sites = json.loads(SITES_PATH.read_text(encoding="utf-8"))
    if limit:
        sites = sites[:limit]
    data_end = dt.date.today()
    started = time.monotonic()
    results: list[dict] = []
    failures: list[str] = []
    frontier: dt.date | None = None

    for index, site in enumerate(sites, 1):
        label = f"{site['name']}, {site['region']}"
        try:
            cached = cache_path(site).exists() and not refresh
            values = fetch_hourly(site, data_end, refresh)
        except RuntimeError as error:
            failures.append(f"{label}: {error}")
            print(f"NG   {label}: {error}", file=sys.stderr)
            continue
        if not cached:
            time.sleep(REQUEST_INTERVAL)
        if not values:
            failures.append(f"{label}: 有効な気温が 0 件")
            print(f"NG   {label}: 有効な気温が 0 件", file=sys.stderr)
            continue

        last_key = max(values)
        last_day = dt.datetime.strptime(last_key[:8], "%Y%m%d").date()
        # 最終日は 23 時まで揃っているときだけ「完全な日」として扱う
        available_end = last_day if last_key[8:] == "23" else last_day - dt.timedelta(days=1)
        frontier = min(frontier, available_end) if frontier else available_end
        hemisphere = "north" if site["lat"] >= 0 else "south"
        years = complete_years(hemisphere, FETCH_START, available_end)
        if len(years) < SEASON_COUNT:
            failures.append(f"{label}: 完了シーズンが {len(years)} 件")
            print(f"NG   {label}: 完了シーズンが {len(years)} 件", file=sys.stderr)
            continue

        seasons = []
        broken = None
        for year in years:
            chill = accumulate(values, *season_bounds(hemisphere, "chill", year))
            dynamic = accumulate(values, *season_bounds(hemisphere, "dynamic", year))
            if chill is None or dynamic is None:
                broken = season_label(hemisphere, year)
                break
            seasons.append({
                "label": season_label(hemisphere, year),
                "forty_five": round(chill["forty_five"], 1),
                "utah": round(chill["utah"], 1),
                "dynamic": round(dynamic["dynamic"], 1),
            })
        if broken:
            failures.append(f"{label}: {broken} シーズンの欠測が多い")
            print(f"NG   {label}: {broken} シーズンの欠測が多い", file=sys.stderr)
            continue

        results.append({
            "slug": site["slug"],
            "name": site["name"],
            "region": site["region"],
            "country": site["country"],
            "country_slug": site["country_slug"],
            "lat": site["lat"],
            "lon": site["lon"],
            "hemisphere": hemisphere,
            "chill_window": WINDOW_LABELS[hemisphere]["chill"],
            "dynamic_window": WINDOW_LABELS[hemisphere]["dynamic"],
            "seasons": seasons,
            "stats": {
                "forty_five": summarise(seasons, "forty_five"),
                "utah": summarise(seasons, "utah"),
                "dynamic": summarise(seasons, "dynamic"),
            },
        })
        print(f"OK   {index:3d}/{len(sites)}  {label}")

    for site in results:
        others = sorted((other for other in results if other["slug"] != site["slug"]),
                        key=lambda other: haversine(site, other))
        site["nearby"] = [
            {"slug": other["slug"], "country_slug": other["country_slug"],
             "name": other["name"], "region": other["region"],
             "km": round(haversine(site, other))}
            for other in others[:NEARBY_COUNT]
        ]

    elapsed = time.monotonic() - started
    DATA_PATH.write_text(
        json.dumps({
            "generated_on": dt.date.today().isoformat(),
            "data_through": frontier.isoformat() if frontier else "",
            "source": "NASA POWER hourly T2M (MERRA-2)",
            "sites": results,
        }, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"\n地点 {len(results)} / {len(sites)}、失敗 {len(failures)} 件、所要 {elapsed:.1f} 秒")
    print(f"出力: {DATA_PATH}")
    for failure in failures:
        print(f"  失敗: {failure}")
    return 0 if results else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="キャッシュを無視して取り直す")
    parser.add_argument("--limit", type=int, help="先頭 N 地点だけ処理する（動作確認用）")
    args = parser.parse_args()
    sys.exit(build(args.limit, args.refresh))


if __name__ == "__main__":
    main()
