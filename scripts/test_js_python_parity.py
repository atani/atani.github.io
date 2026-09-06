"""ブラウザ計算機（JavaScript）と地点ページ（Python）が同じ数字を出すことを確かめる。

同じ 3 モデルが 2 か所に写してあるので、片方だけ直す変更を検出したい。
気温はテストの中で決まった形に組み立てるため、NASA POWER には触れない。
うるう年の 2 月と南北両半球を同時に踏む。

    python3 -m unittest discover -s scripts -p 'test_*.py' -v

node が無い環境では skip する。
"""

import datetime as dt
import importlib.util
import json
import math
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD_PATH = ROOT / "scripts/build-chillcast-pages.py"
CALCULATOR = ROOT / "_deploy-now/chillcast-calculator.js"

_spec = importlib.util.spec_from_file_location("build_chillcast_pages", BUILD_PATH)
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

NODE = shutil.which("node")


def synthetic_hourly(start: dt.date, end: dt.date, seed: float) -> dict[str, float]:
    """24 時間周期と年周期を重ねた決まった形の気温列。乱数は使わない。"""
    values: dict[str, float] = {}
    day = start
    index = 0
    while day <= end:
        prefix = day.strftime("%Y%m%d")
        yearly = 9.0 * math.sin(2 * math.pi * (day.timetuple().tm_yday / 365.25))
        for hour in range(24):
            daily = 6.0 * math.sin(2 * math.pi * (hour / 24.0))
            values[f"{prefix}{hour:02d}"] = round(6.0 + seed + yearly + daily, 3)
            index += 1
        day += dt.timedelta(days=1)
    return values


def run_node(script: str, payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        data_path = pathlib.Path(folder) / "input.json"
        data_path.write_text(json.dumps(payload), encoding="utf-8")
        script_path = pathlib.Path(folder) / "run.js"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            [NODE, str(script_path), str(CALCULATOR), str(data_path)],
            capture_output=True, text=True, check=True,
        )
    return json.loads(result.stdout)


ANALYSE_SCRIPT = """
const calculator = require(process.argv[2]);
const input = require(process.argv[3]);
const result = calculator.analyse(
  { properties: { parameter: { T2M: input.values } },
    geometry: { coordinates: [input.gridLon, input.gridLat] },
    header: { api: { version: "test" } } },
  input.latitude, input.longitude
);
process.stdout.write(JSON.stringify({
  hemisphere: result.hemisphere,
  seasons: result.seasons,
  stats: result.stats
}));
"""


@unittest.skipUnless(NODE, "node が見つからないので JavaScript 側を実行できません")
class PythonJavaScriptParityTests(unittest.TestCase):
    """同じ気温列を Python と JavaScript に流して突き合わせる。"""

    def _python_seasons(self, hemisphere, values, data_start, data_end):
        years = build.complete_years(hemisphere, data_start, data_end)
        seasons = []
        for year in years:
            chill = build.accumulate(values, *build.season_bounds(hemisphere, "chill", year))
            dynamic = build.accumulate(values, *build.season_bounds(hemisphere, "dynamic", year))
            self.assertIsNotNone(chill)
            self.assertIsNotNone(dynamic)
            seasons.append({
                "label": build.season_label(hemisphere, year),
                "forty_five": chill["forty_five"],
                "utah": chill["utah"],
                "dynamic": dynamic["dynamic"],
            })
        return seasons

    def _both_sides(self, latitude: float, seed: float):
        today = dt.date(2026, 9, 6)
        data_start = build.fetch_start(today)
        # JavaScript 側は最終時刻から data_end を導くので、23 時まで揃った日で終える。
        data_end = dt.date(2026, 8, 31)
        values = synthetic_hourly(data_start, data_end, seed)
        hemisphere = "north" if latitude >= 0 else "south"
        python_seasons = self._python_seasons(hemisphere, values, data_start, data_end)
        js = run_node(ANALYSE_SCRIPT, {
            "values": values, "latitude": latitude, "longitude": 10.0,
            "gridLat": latitude, "gridLon": 10.0,
        })
        return python_seasons, js

    def test_season_totals_match_between_python_and_js(self):
        for latitude, seed in ((41.0, 0.0), (-41.0, 1.5)):
            with self.subTest(latitude=latitude):
                python_seasons, js = self._both_sides(latitude, seed)
                self.assertEqual(len(python_seasons), build.SEASON_COUNT)
                self.assertEqual([s["label"] for s in python_seasons],
                                 [s["label"] for s in js["seasons"]])
                for mine, theirs in zip(python_seasons, js["seasons"]):
                    self.assertAlmostEqual(mine["forty_five"], theirs["fortyFive"], places=9)
                    self.assertAlmostEqual(mine["utah"], theirs["utah"], places=9)
                    self.assertAlmostEqual(mine["dynamic"], theirs["dynamic"], places=9)

    def test_mean_rounding_is_identical_between_python_and_js(self):
        """平均は両方とも「生の値を平均してから 1 桁に丸める」。"""
        for latitude, seed in ((41.0, 0.0), (-41.0, 1.5)):
            with self.subTest(latitude=latitude):
                python_seasons, js = self._both_sides(latitude, seed)
                for key, js_key in (("forty_five", "fortyFive"), ("utah", "utah"),
                                    ("dynamic", "dynamic")):
                    mine = build.summarise(python_seasons, key)
                    theirs = js["stats"][js_key]
                    self.assertAlmostEqual(mine["mean"], round(theirs["mean"], 1), places=9)
                    self.assertAlmostEqual(mine["min"], round(theirs["min"], 1), places=9)
                    self.assertAlmostEqual(mine["max"], round(theirs["max"], 1), places=9)

    def test_hemisphere_comes_from_the_requested_latitude(self):
        """赤道付近で要求緯度と応答格子の符号が食い違っても、要求側で決める。"""
        today = dt.date(2026, 9, 6)
        values = synthetic_hourly(build.fetch_start(today), dt.date(2026, 8, 31), 0.0)
        js = run_node(ANALYSE_SCRIPT, {
            "values": values, "latitude": -0.05, "longitude": 10.0,
            "gridLat": 0.25, "gridLon": 10.0,
        })
        self.assertEqual(js["hemisphere"], "south")

    def test_javascript_drops_the_same_missing_values_as_python(self):
        """数値にならない値と埋め値は、両方とも落とす。"""
        script = """
        const calculator = require(process.argv[2]);
        const input = require(process.argv[3]);
        let thrown = null;
        try {
          calculator.analyse({ properties: { parameter: { T2M: input.values } },
            geometry: { coordinates: [0, 0] } }, 0, 0);
        } catch (error) { thrown = error.message; }
        process.stdout.write(JSON.stringify({ thrown: thrown }));
        """
        js = run_node(script, {"values": {"2026010100": "nonsense", "2026010101": -999.0}})
        self.assertEqual(js["thrown"], "NASA POWER returned no usable temperatures for this point.")
        payload = {"properties": {"parameter": {"T2M": {"2026010100": "nonsense",
                                                        "2026010101": -999.0}}}}
        self.assertEqual(build.extract_hourly(payload), {})

    def test_javascript_rejects_a_contiguous_gap_like_python(self):
        start, end = build.season_bounds("north", "chill", 2024)
        values = synthetic_hourly(start, end, 0.0)
        for key in sorted(values)[:build.MAX_GAP_HOURS]:
            del values[key]
        self.assertIsNone(build.accumulate(values, start, end))
        script = """
        const calculator = require(process.argv[2]);
        const input = require(process.argv[3]);
        const bounds = calculator.seasonBounds("north", "chill", 2024);
        process.stdout.write(JSON.stringify({
          result: calculator.accumulate(input.values, bounds)
        }));
        """
        js = run_node(script, {"values": values})
        self.assertIsNone(js["result"])


if __name__ == "__main__":
    unittest.main()
