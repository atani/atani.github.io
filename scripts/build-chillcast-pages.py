#!/usr/bin/env python3
"""ChillCast の地点別ページ用に NASA POWER の平年値を作る。

150 地点それぞれについて NASA POWER の hourly API から 10 年分の気温を 1 リクエストで
取得し、45°F Hours / Utah / Dynamic の 3 モデルを直近 10 シーズン分計算して
`_deploy-now/chillcast_data.json` に書き出す。ページの HTML は
`scripts/build-deploy-now.py` が `_deploy-now/chillcast_pages.py` を使って組み立てる。

生の JSON は `_deploy-now/chillcast_cache/` に gzip で残す（.gitignore 済み）。
`--refresh` を付けるとキャッシュを無視して取り直す。

1 地点でも落ちたら `chillcast_data.json` は書き換えずに非 0 で終了する。部分的な
結果を承知のうえで採用したいときだけ `--allow-partial` を付ける。

    python3 scripts/build-chillcast-pages.py
    python3 scripts/build-chillcast-pages.py --refresh
"""

import argparse
import datetime as dt
import gzip
import json
import math
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITES_PATH = ROOT / "_deploy-now/chillcast_sites.json"
DATA_PATH = ROOT / "_deploy-now/chillcast_data.json"
CACHE_DIR = ROOT / "_deploy-now/chillcast_cache"

POWER_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/hourly/point"
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# 取得開始は今年から数えて決める。固定日にすると年を追うごとに取得量が増え続ける。
# 直近 10 シーズンを揃えるのに必要なのは 11 年前の 9/1 まで（南半球の Dynamic は
# 3/1 開始なので、これで両半球とも 10 シーズンが窓に収まる）。
FETCH_START_YEARS_BACK = 11
FILL_THRESHOLD = -900.0
SEASON_COUNT = 10
MIN_COVERAGE = 0.95
# 有効率が足りていても、これだけ続けて欠測しているシーズンは採用しない。
# 端にまとまった欠測が「満杯のシーズン」として公開されるのを防ぐ。
MAX_GAP_HOURS = 24
# キャッシュは取得日からこの日数を過ぎたら使わない。地点ごとに違う年の窓で
# 10 シーズンを組み立ててしまうと、ページ間で数字の意味が揃わなくなる。
CACHE_MAX_AGE_DAYS = 31
REQUEST_INTERVAL = 0.3
RETRIES = 3
REQUEST_TIMEOUT = 120

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


def check_slugs(site: dict) -> None:
    """slug はキャッシュのファイル名と公開 URL の両方になるので入口で弾く。"""
    for key in ("country_slug", "slug"):
        if not SLUG_RE.fullmatch(str(site.get(key, ""))):
            raise RuntimeError(f"{key} が [a-z0-9-] ではありません: {site.get(key)!r}")


def power_url(lat: float, lon: float, start: dt.date, end: dt.date) -> str:
    """緯度経度は数値へ寄せたうえでクエリとしてエンコードする。"""
    query = urllib.parse.urlencode({
        "parameters": "T2M",
        "community": "AG",
        "longitude": float(lon),
        "latitude": float(lat),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    })
    return f"{POWER_ENDPOINT}?{query}"


def cache_path(site: dict) -> pathlib.Path:
    return CACHE_DIR / f"{site['country_slug']}__{site['slug']}.json.gz"


def usable_celsius(value) -> float | None:
    """有限の数値で埋め値より大きいものだけ返す。

    chillcast-calculator.js の `Number.isFinite(value) && value > FILL_THRESHOLD`
    と同じ規則にする。数値にならない値は片方だけ例外にせず、両方で落とす。
    """
    try:
        celsius = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(celsius) or celsius <= FILL_THRESHOLD:
        return None
    return celsius


def extract_hourly(payload: dict) -> dict[str, float]:
    """NASA POWER の応答から T2M を取り出す。想定外の形は RuntimeError にする。

    POWER は不正な引数やサービス障害でも HTTP 200 のままエラー本文を返すことが
    あるため、ここで正規化しないと呼び出し側の失敗集計をすり抜ける。
    """
    try:
        raw = payload["properties"]["parameter"]["T2M"]
        items = raw.items()
    except (KeyError, TypeError, AttributeError) as error:
        note = payload.get("messages") if isinstance(payload, dict) else None
        raise RuntimeError(f"NASA POWER が想定外の応答を返しました: {note or error}") from error
    values = {}
    for key, value in items:
        celsius = usable_celsius(value)
        if celsius is not None:
            values[str(key)] = celsius
    return values


def usable_cache(path: pathlib.Path, start: dt.date, today: dt.date) -> dict | None:
    """必要な範囲を含み、かつ取得から日が経ちすぎていないキャッシュだけ返す。"""
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        cached = json.load(handle)
    if cached.get("start", "9999-12-31") > start.isoformat():
        return None
    try:
        fetched_at = dt.date.fromisoformat(cached.get("fetched_at", ""))
    except ValueError:
        return None
    if (today - fetched_at).days > CACHE_MAX_AGE_DAYS:
        return None
    return cached


def fetch_hourly(site: dict, start: dt.date, end: dt.date,
                 refresh: bool) -> tuple[dict[str, float], bool]:
    """(時刻キー YYYYMMDDHH -> 摂氏, キャッシュから読んだか)。欠測（<= -900）は落とす。"""
    path = cache_path(site)
    if not refresh:
        # 第 3 引数は鮮度の基準日なので、取得範囲の末日ではなく今日を渡す。
        cached = usable_cache(path, start, dt.date.today())
        if cached is not None:
            return cached["values"], True

    url = power_url(site["lat"], site["lon"], start, end)
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as response:
                payload = json.load(response)
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == RETRIES:
                raise RuntimeError(f"NASA POWER の取得に失敗: {error}") from error
            time.sleep(2.0 * attempt)
    else:  # pragma: no cover - break で必ず抜ける
        raise RuntimeError(f"NASA POWER の取得に失敗: {last_error}")

    values = extract_hourly(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump({"fetched_at": dt.date.today().isoformat(), "start": start.isoformat(),
                   "end": end.isoformat(), "lat": site["lat"], "lon": site["lon"],
                   "values": values}, handle)
    return values, False


def fetch_start(today: dt.date) -> dt.date:
    return dt.date(today.year - FETCH_START_YEARS_BACK, 9, 1)


def probe_version() -> str:
    """NASA POWER の referencing 文へ入れる API バージョンを 1 リクエストで読む。"""
    url = power_url(0.0, 0.0, dt.date(2025, 1, 1), dt.date(2025, 1, 2))
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)
        return str(payload["header"]["api"]["version"]).lstrip("v")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as error:
        raise RuntimeError(f"NASA POWER のバージョン取得に失敗: {error}") from error


def accumulate(values: dict[str, float], start: dt.date, end: dt.date) -> dict | None:
    """期間内の 3 モデルを 1 パスで積算する。

    採用の条件は 2 つ。シーズン内の有効率が MIN_COVERAGE 以上であること、
    MAX_GAP_HOURS 以上続く欠測が無いこと。どちらかを満たさないと None を返す。
    有効率だけで判定すると、端に固まった数日の欠測が満杯のシーズンとして
    公開されてしまう。
    """
    expected = (end - start).days * 24 + 24
    forty_five = 0.0
    utah = 0.0
    dynamic = DynamicState()
    good = 0
    gap = 0
    longest_gap = 0
    day = start
    while day <= end:
        prefix = day.strftime("%Y%m%d")
        for hour in range(24):
            celsius = values.get(f"{prefix}{hour:02d}")
            if celsius is None:
                gap += 1
                longest_gap = max(longest_gap, gap)
                continue
            gap = 0
            good += 1
            if 0.0 <= celsius <= 7.2:
                forty_five += 1.0
            utah += utah_unit(celsius)
            dynamic.step(celsius)
        day += dt.timedelta(days=1)
    if good < expected * MIN_COVERAGE or longest_gap >= MAX_GAP_HOURS:
        return None
    return {"forty_five": forty_five, "utah": utah, "dynamic": dynamic.portions,
            "coverage": good / expected, "longest_gap": longest_gap}


def complete_years(hemisphere: str, data_start: dt.date, data_end: dt.date) -> list[int]:
    """45°F / Utah と Dynamic の両方の窓が data の中に収まる年だけを返す。"""
    years = []
    for year in range(data_start.year, data_end.year + 1):
        windows = [season_bounds(hemisphere, kind, year) for kind in ("chill", "dynamic")]
        if all(start >= data_start and end <= data_end for start, end in windows):
            years.append(year)
    return years[-SEASON_COUNT:]


def summarise(seasons: list[dict], key: str) -> dict:
    """生のシーズン値を平均してから 1 桁に丸める。

    先に各シーズンを丸めてから平均すると、同じ入力でも計算機（JavaScript）と
    0.1 ずれることがある。丸めは平均を取った後の 1 回だけにする。
    """
    values = [season[key] for season in seasons]
    return {
        "mean": round(sum(values) / len(values), 1),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
    }


def build(limit: int | None, refresh: bool, allow_partial: bool = False) -> int:
    sites = json.loads(SITES_PATH.read_text(encoding="utf-8"))
    total = len(sites)
    if limit:
        sites = sites[:limit]
    data_end = dt.date.today()
    data_start = fetch_start(data_end)
    started = time.monotonic()
    power_version = probe_version()
    print(f"NASA POWER Hourly API バージョン: {power_version}")
    results: list[dict] = []
    failures: list[str] = []
    frontier: dt.date | None = None

    for index, site in enumerate(sites, 1):
        label = f"{site['name']}, {site['region']}"
        try:
            check_slugs(site)
            values, cached = fetch_hourly(site, data_start, data_end, refresh)
        # ValueError は power_url() が非数値の緯度経度で投げる。1 行の壊れた
        # データでビルド全体を落とさず、他の地点と同じ失敗集計へ載せる。
        except (RuntimeError, ValueError) as error:
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
        years = complete_years(hemisphere, data_start, available_end)
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
                "forty_five": chill["forty_five"],
                "utah": chill["utah"],
                "dynamic": dynamic["dynamic"],
                "coverage": min(chill["coverage"], dynamic["coverage"]),
            })
        if broken:
            failures.append(f"{label}: {broken} シーズンの欠測が基準を超えている")
            print(f"NG   {label}: {broken} シーズンの欠測が基準を超えている", file=sys.stderr)
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
            # 表示用は 1 桁に丸め、平均は生の値から取る（summarise の docstring を参照）
            "seasons": [{
                "label": season["label"],
                "forty_five": round(season["forty_five"], 1),
                "utah": round(season["utah"], 1),
                "dynamic": round(season["dynamic"], 1),
                "coverage": round(season["coverage"], 4),
            } for season in seasons],
            "stats": {
                "forty_five": summarise(seasons, "forty_five"),
                "utah": summarise(seasons, "utah"),
                "dynamic": summarise(seasons, "dynamic"),
            },
        })
        print(f"OK   {index:3d}/{len(sites)}  {label}")

    elapsed = time.monotonic() - started
    print(f"\n地点 {len(results)} / {len(sites)}、失敗 {len(failures)} 件、所要 {elapsed:.1f} 秒")
    for failure in failures:
        print(f"  失敗: {failure}")

    # --limit は動作確認用で、処理するのは先頭 N 地点だけ。書き込むと
    # コミット済みの地点が N 件へ切り詰められるので、--allow-partial を
    # 付けたかどうかによらず書き込まない。
    if limit:
        print(f"--limit は先頭 {len(sites)} 地点しか処理しないので {DATA_PATH.name} は"
              "更新しません。", file=sys.stderr)
        return 1
    if not results:
        print("有効な地点が 0 件のため書き込みません。", file=sys.stderr)
        return 1
    # 1 地点でも欠けたまま書き込むと、コミット済みの地点が黙って消える。
    # 部分的な結果を採るのは明示的に指示されたときだけにする。
    if len(results) != total and not allow_partial:
        print(f"{total - len(results)} 地点が揃わなかったので {DATA_PATH.name} は更新しません。"
              "部分的な結果を採用するなら --allow-partial を付けてください。", file=sys.stderr)
        return 1

    DATA_PATH.write_text(
        json.dumps({
            "generated_on": dt.date.today().isoformat(),
            "data_through": frontier.isoformat() if frontier else "",
            "source": "NASA POWER hourly T2M (MERRA-2)",
            "power_version": power_version,
            "sites": results,
        }, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"出力: {DATA_PATH}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="キャッシュを無視して取り直す")
    parser.add_argument("--limit", type=int,
                        help="先頭 N 地点だけ処理する（動作確認用。書き込みは行わない）")
    parser.add_argument("--allow-partial", action="store_true",
                        help="一部の地点が揃わなくても書き込む（既定は書き込まずに失敗）")
    args = parser.parse_args()
    if args.limit and args.allow_partial:
        parser.error("--limit と --allow-partial は同時に使えません。"
                     "--limit は動作確認用で、先頭 N 地点だけのファイルを書き出さないためです。")
    sys.exit(build(args.limit, args.refresh, args.allow_partial))


if __name__ == "__main__":
    main()
