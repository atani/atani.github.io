"""ChillCast の chill モデルと積算期間のテスト。

期待値は ChillCast アプリ（Swift）の `Tests/ChillCastTests/ChillCastTests.swift`
から移植した。Web 側は同じ計算を Python と JavaScript に写しているので、
アプリと数字が食い違わないことをここで固定する。

依存は標準ライブラリだけ。

    python3 -m unittest discover -s scripts -p 'test_*.py' -v
"""

import contextlib
import datetime as dt
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

# ファイル名にハイフンが入るため通常の import ができない。
BUILD_PATH = pathlib.Path(__file__).resolve().parent / "build-chillcast-pages.py"
_spec = importlib.util.spec_from_file_location("build_chillcast_pages", BUILD_PATH)
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def hours(start: dt.date, end: dt.date, celsius: float) -> dict[str, float]:
    """期間内のすべての時刻を同じ気温で埋めた辞書を返す。"""
    values: dict[str, float] = {}
    day = start
    while day <= end:
        prefix = day.strftime("%Y%m%d")
        for hour in range(24):
            values[f"{prefix}{hour:02d}"] = celsius
        day += dt.timedelta(days=1)
    return values


class UtahUnitTests(unittest.TestCase):
    def test_band_weights_match_swift(self):
        # Swift testUtahBandWeights と同じ境界・重み。
        self.assertEqual(build.utah_unit(0.5), 0.0)
        self.assertEqual(build.utah_unit(2.0), 0.5)
        self.assertEqual(build.utah_unit(5.0), 1.0)
        self.assertEqual(build.utah_unit(10.0), 0.5)
        self.assertEqual(build.utah_unit(14.0), 0.0)
        self.assertEqual(build.utah_unit(17.0), -0.5)
        self.assertEqual(build.utah_unit(20.0), -1.0)

    def test_band_edges_are_half_open(self):
        self.assertEqual(build.utah_unit(1.4), 0.5)
        self.assertEqual(build.utah_unit(2.4), 1.0)
        self.assertEqual(build.utah_unit(9.1), 0.5)
        self.assertEqual(build.utah_unit(12.4), 0.0)
        self.assertEqual(build.utah_unit(15.9), -0.5)
        self.assertEqual(build.utah_unit(18.0), -1.0)


class FortyFiveHoursTests(unittest.TestCase):
    def test_counts_inclusive_band(self):
        # Swift testFortyFiveHoursCountsInclusiveBand の移植。
        # 5, 6, 7, 0, 7.2 を数え、8, -1, 7.3 を数えない。
        day = dt.date(2026, 1, 1)
        values = {}
        for index, celsius in enumerate([5, 6, 7, 8, -1, 0, 7.2, 7.3]):
            values[f"20260101{index:02d}"] = float(celsius)
        result = build.accumulate(values, day, day)
        # 24 時間中 8 時間しか無いので採用されない。積算そのものは別途確認する。
        self.assertIsNone(result)

        filled = hours(day, day, 20.0)
        for index, celsius in enumerate([5, 6, 7, 8, -1, 0, 7.2, 7.3]):
            filled[f"20260101{index:02d}"] = float(celsius)
        result = build.accumulate(filled, day, day)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["forty_five"], 5.0, places=6)

    def test_all_warm_is_zero(self):
        day = dt.date(2026, 1, 1)
        result = build.accumulate(hours(day, day, 20.0), day, day)
        self.assertAlmostEqual(result["forty_five"], 0.0, places=6)


class SeasonBoundsTests(unittest.TestCase):
    def test_north_chill_window(self):
        start, end = build.season_bounds("north", "chill", 2023)
        self.assertEqual((start, end), (dt.date(2023, 11, 1), dt.date(2024, 2, 29)))

    def test_north_chill_window_in_non_leap_year(self):
        start, end = build.season_bounds("north", "chill", 2024)
        self.assertEqual((start, end), (dt.date(2024, 11, 1), dt.date(2025, 2, 28)))

    def test_north_dynamic_window(self):
        start, end = build.season_bounds("north", "dynamic", 2023)
        self.assertEqual((start, end), (dt.date(2023, 9, 1), dt.date(2024, 3, 31)))

    def test_south_chill_window(self):
        start, end = build.season_bounds("south", "chill", 2023)
        self.assertEqual((start, end), (dt.date(2023, 5, 1), dt.date(2023, 8, 31)))

    def test_south_dynamic_window(self):
        start, end = build.season_bounds("south", "dynamic", 2023)
        self.assertEqual((start, end), (dt.date(2023, 3, 1), dt.date(2023, 9, 30)))

    def test_season_labels(self):
        self.assertEqual(build.season_label("north", 2023), "2023–24")
        self.assertEqual(build.season_label("south", 2023), "2023")


class AccumulateTests(unittest.TestCase):
    def test_constant_season_counts_every_hour(self):
        start, end = build.season_bounds("north", "chill", 2024)
        result = build.accumulate(hours(start, end, 5.0), start, end)
        expected_hours = (end - start).days * 24 + 24
        self.assertAlmostEqual(result["forty_five"], float(expected_hours), places=6)
        self.assertAlmostEqual(result["utah"], float(expected_hours), places=6)
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_leap_season_counts_one_more_day(self):
        leap_start, leap_end = build.season_bounds("north", "chill", 2023)
        plain_start, plain_end = build.season_bounds("north", "chill", 2024)
        leap = build.accumulate(hours(leap_start, leap_end, 5.0), leap_start, leap_end)
        plain = build.accumulate(hours(plain_start, plain_end, 5.0), plain_start, plain_end)
        self.assertAlmostEqual(leap["forty_five"] - plain["forty_five"], 24.0, places=6)

    def test_returns_none_below_min_coverage(self):
        start, end = build.season_bounds("north", "chill", 2024)
        values = hours(start, end, 5.0)
        # 散らして 6% ほど落とす。連続欠測は作らない。
        keys = sorted(values)
        for index, key in enumerate(keys):
            if index % 16 == 0:
                del values[key]
        self.assertIsNone(build.accumulate(values, start, end))


class CoverageTests(unittest.TestCase):
    """有効率だけでなく、連続した欠測でも落とすことを固定する。"""

    def _season_with_leading_gap(self, gap_hours: int):
        start, end = build.season_bounds("north", "chill", 2024)
        values = hours(start, end, 5.0)
        for key in sorted(values)[:gap_hours]:
            del values[key]
        return values, start, end

    def test_accepts_full_season(self):
        start, end = build.season_bounds("north", "chill", 2024)
        self.assertIsNotNone(build.accumulate(hours(start, end, 5.0), start, end))

    def test_rejects_contiguous_gap_at_season_start(self):
        # 有効率は 95% を超えるが、24 時間続けて欠けているので採用しない。
        values, start, end = self._season_with_leading_gap(build.MAX_GAP_HOURS)
        self.assertIsNone(build.accumulate(values, start, end))

    def test_accepts_gap_just_under_the_limit(self):
        values, start, end = self._season_with_leading_gap(build.MAX_GAP_HOURS - 1)
        result = build.accumulate(values, start, end)
        self.assertIsNotNone(result)
        self.assertEqual(result["longest_gap"], build.MAX_GAP_HOURS - 1)

    def test_rejects_six_day_gap_that_coverage_alone_would_accept(self):
        values, start, end = self._season_with_leading_gap(24 * 6)
        self.assertIsNone(build.accumulate(values, start, end))


class CompleteYearsTests(unittest.TestCase):
    """fetch_start() の 9/1 起点で両半球とも 10 シーズンが揃うこと。"""

    def _years(self, hemisphere: str, today: dt.date) -> list[int]:
        return build.complete_years(hemisphere, build.fetch_start(today), today)

    def test_northern_hemisphere_yields_ten_seasons_from_fetch_start(self):
        for today in (dt.date(2026, 9, 6), dt.date(2027, 1, 5), dt.date(2027, 4, 1)):
            with self.subTest(today=today):
                self.assertEqual(len(self._years("north", today)), build.SEASON_COUNT)

    def test_southern_hemisphere_yields_ten_seasons_from_fetch_start(self):
        for today in (dt.date(2026, 9, 6), dt.date(2027, 1, 5), dt.date(2027, 4, 1)):
            with self.subTest(today=today):
                self.assertEqual(len(self._years("south", today)), build.SEASON_COUNT)

    def test_south_has_no_spare_year(self):
        # 南半球は余裕がゼロ。取得開始を 1 年縮めると 10 シーズンを割る。
        today = dt.date(2026, 9, 6)
        start = dt.date(today.year - (build.FETCH_START_YEARS_BACK - 1), 9, 1)
        self.assertLess(len(build.complete_years("south", start, today)), build.SEASON_COUNT)


class SummariseTests(unittest.TestCase):
    def test_mean_is_rounded_once_after_averaging(self):
        # 丸めた値の平均ではなく、生の値の平均を 1 回だけ丸める。
        seasons = [{"dynamic": 1.04}, {"dynamic": 1.04}, {"dynamic": 1.07}]
        self.assertAlmostEqual(build.summarise(seasons, "dynamic")["mean"], 1.1, places=9)


class PowerUrlTests(unittest.TestCase):
    def test_encodes_coordinates(self):
        url = build.power_url(36.75, -119.77, dt.date(2015, 9, 1), dt.date(2026, 9, 6))
        self.assertIn("latitude=36.75", url)
        self.assertIn("longitude=-119.77", url)
        self.assertIn("start=20150901", url)
        self.assertIn("end=20260906", url)

    def test_rejects_non_numeric_coordinates(self):
        with self.assertRaises(ValueError):
            build.power_url("0&parameters=T2MDEW", 0.0, dt.date(2025, 1, 1), dt.date(2025, 1, 2))


class ExtractHourlyTests(unittest.TestCase):
    def test_drops_fill_values(self):
        payload = {"properties": {"parameter": {"T2M": {"2026010100": 2.0, "2026010101": -999.0}}}}
        self.assertEqual(build.extract_hourly(payload), {"2026010100": 2.0})

    def test_error_body_with_http_200_becomes_runtime_error(self):
        with self.assertRaises(RuntimeError):
            build.extract_hourly({"messages": ["Invalid latitude"], "parameters": {}})


class SlugTests(unittest.TestCase):
    def test_accepts_plain_slugs(self):
        build.check_slugs({"country_slug": "united-states", "slug": "hood-river"})

    def test_rejects_path_traversal(self):
        for bad in ("../etc", "a/b", "Wenatchee", "", "-lead"):
            with self.subTest(bad=bad):
                with self.assertRaises(RuntimeError):
                    build.check_slugs({"country_slug": "spain", "slug": bad})


class UsableCacheTests(unittest.TestCase):
    def test_stale_cache_is_not_reused(self):
        import gzip
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "cache.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump({"fetched_at": "2020-01-01", "start": "2015-09-01",
                           "end": "2020-01-01", "values": {}}, handle)
            start = dt.date(2015, 9, 1)
            self.assertIsNone(build.usable_cache(path, start, dt.date(2026, 9, 6)))
            self.assertIsNotNone(build.usable_cache(path, start, dt.date(2020, 1, 20)))

    def test_cache_starting_after_the_window_is_not_reused(self):
        import gzip
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "cache.json.gz"
            today = dt.date.today()
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump({"fetched_at": today.isoformat(), "start": "2020-09-01",
                           "end": today.isoformat(), "values": {}}, handle)
            self.assertIsNone(build.usable_cache(path, dt.date(2015, 9, 1), today))


class WriteGateTests(unittest.TestCase):
    """全地点が揃わない限り chillcast_data.json を書き換えないこと。

    ネットワークにもキャッシュにも触れない。取得は必ず成功する固定値へ
    差し替えるので、「書かなかったのは gate のせい」と「取得に失敗した」を
    切り分けられる。
    """

    def setUp(self):
        today = dt.date.today()
        start = build.fetch_start(today)
        # 11 年分の合成気温。両半球とも 10 シーズンが揃う長さにする。
        values = hours(start, today, 5.0)
        self._patched = {
            "probe_version": build.probe_version,
            "fetch_hourly": build.fetch_hourly,
        }
        build.probe_version = lambda: "test"
        build.fetch_hourly = lambda site, s, e, refresh: (values, True)
        self.addCleanup(self._restore)

    def _restore(self):
        for name, original in self._patched.items():
            setattr(build, name, original)

    def _run(self, **kwargs) -> tuple[int, str]:
        """build() を走らせ、DATA_PATH が 1 バイトも変わらないことを確かめる。"""
        before = build.DATA_PATH.read_bytes()
        stamp = build.DATA_PATH.stat().st_mtime_ns
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = build.build(**kwargs)
        self.assertEqual(stamp, build.DATA_PATH.stat().st_mtime_ns, "書き込みが起きています")
        self.assertEqual(before, build.DATA_PATH.read_bytes())
        return code, stdout.getvalue()

    def test_limit_does_not_rewrite_the_committed_file(self):
        code, out = self._run(limit=3, refresh=False, allow_partial=False)
        self.assertEqual(code, 1)
        # 取得はすべて成功している。書かなかった理由が --limit だと分かる形にする。
        self.assertIn("地点 3 / 3", out)
        self.assertIn("失敗 0 件", out)

    def test_limit_does_not_rewrite_even_with_allow_partial(self):
        # --allow-partial との併用でも先頭 N 地点のファイルを書き出さない。
        code, out = self._run(limit=3, refresh=False, allow_partial=True)
        self.assertEqual(code, 1)
        self.assertIn("失敗 0 件", out)

    def test_partial_results_are_written_only_with_allow_partial(self):
        """--limit を使わず一部の地点が落ちたときの対の挙動を確かめる。"""
        sites = json.loads(build.SITES_PATH.read_text(encoding="utf-8"))
        broken = build.fetch_hourly

        def fail_one(site, start, end, refresh):
            if site["slug"] == sites[0]["slug"]:
                raise RuntimeError("テスト用の取得失敗")
            return broken(site, start, end, refresh)

        build.fetch_hourly = fail_one
        with tempfile.TemporaryDirectory() as folder:
            original_path = build.DATA_PATH
            build.DATA_PATH = pathlib.Path(folder) / "out.json"
            self.addCleanup(setattr, build, "DATA_PATH", original_path)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                code = build.build(None, False, False)
            self.assertEqual(code, 1)
            self.assertFalse(build.DATA_PATH.exists(), "揃っていないのに書き込んでいます")

            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = build.build(None, False, True)
            self.assertEqual(code, 0)
            written = json.loads(build.DATA_PATH.read_text(encoding="utf-8"))
            self.assertEqual(len(written["sites"]), len(sites) - 1)


class ClassifyTests(unittest.TestCase):
    """適合の境界。Swift VarietyFitTests.testFitThresholdsAgainstTypicalChill の移植。"""

    def setUp(self):
        import sys

        root = pathlib.Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root / "_deploy-now"))
        import chillcast_pages

        self.classify = chillcast_pages.classify

    def test_fit_thresholds_match_swift(self):
        self.assertEqual(self.classify(900, 1000), "fits")
        self.assertEqual(self.classify(901, 1000), "marginal")
        self.assertEqual(self.classify(1100, 1000), "marginal")
        self.assertEqual(self.classify(1101, 1000), "short")


if __name__ == "__main__":
    unittest.main()
