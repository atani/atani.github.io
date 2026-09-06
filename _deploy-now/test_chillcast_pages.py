"""生成した ChillCast のページの構造を確かめる。

build_pages() を 1 回だけ呼び、URL の重複・内部リンク切れ・出典表記・
title と description の重複を検査する。数値そのものではなく、同じ構造の
ページを大量に出す設計で壊れやすいところを固定する。

    python3 -m unittest discover -s _deploy-now -p 'test_*.py' -v
"""

import pathlib
import re
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chillcast_pages  # noqa: E402
from promo_apps import PROMO_APPS, render_promo_page  # noqa: E402

# ChillCast のページ群の外で生成される、リンクしてよいパス。
EXTERNAL_PATHS = {"/chillcast/en/"}
# 静的アセットはページではないので内部リンク検査の対象外にする。
ASSET_PREFIXES = ("/css/", "/assets/", "/js/")


class GeneratedPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = chillcast_pages.build_pages()
        cls.paths = [path for path, _, _ in cls.pages]
        cls.outputs = [out for _, out, _ in cls.pages]
        cls.html = {path: html for path, _, html in cls.pages}

    def test_builds_every_expected_page(self):
        data = chillcast_pages.load_data()
        varieties = chillcast_pages.load_varieties()
        countries = {site["country_slug"] for site in data["sites"]}
        expected = 2 + len(countries) + len(chillcast_pages.PUBLISHED_SITES) + len(varieties)
        self.assertEqual(len(self.pages), expected)

    def test_no_duplicate_url_paths(self):
        duplicates = [p for p in set(self.paths) if self.paths.count(p) > 1]
        self.assertEqual(duplicates, [])

    def test_no_duplicate_output_files(self):
        duplicates = [o for o in set(self.outputs) if self.outputs.count(o) > 1]
        self.assertEqual(duplicates, [])

    def test_every_internal_link_resolves_to_a_generated_page(self):
        known = set(self.paths) | EXTERNAL_PATHS
        broken = []
        for path, html in self.html.items():
            for href in re.findall(r'href="([^"]+)"', html):
                if href.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if href.startswith(ASSET_PREFIXES):
                    continue
                target = href.split("#", 1)[0]
                if target and target not in known:
                    broken.append((path, href))
        self.assertEqual(broken, [])

    def test_every_page_carries_nasa_attribution(self):
        for path, html in self.html.items():
            with self.subTest(path=path):
                self.assertIn("National Aeronautics and Space Administration", html)
                self.assertIn("Prediction Of Worldwide Energy Resources", html)
                self.assertIn("NASA does not endorse ChillCast.", html)
                self.assertIn("power.larc.nasa.gov", html)

    def test_every_page_carries_the_regional_estimate_notice(self):
        for path, html in self.html.items():
            with self.subTest(path=path):
                self.assertIn("regional estimates", html)

    def test_titles_are_unique(self):
        titles = [re.search(r"<title>(.*?)</title>", html, re.S).group(1)
                  for html in self.html.values()]
        duplicates = [t for t in set(titles) if titles.count(t) > 1]
        self.assertEqual(duplicates, [])

    def test_descriptions_are_unique(self):
        pattern = re.compile(r'<meta name="description" content="(.*?)">', re.S)
        found = [pattern.search(html).group(1) for html in self.html.values()]
        duplicates = [d for d in set(found) if found.count(d) > 1]
        self.assertEqual(duplicates, [])

    def test_pages_do_not_embed_canonical(self):
        # canonical の差し込みは scripts/build-deploy-now.py の rewrite() の責務。
        for path, html in self.html.items():
            with self.subTest(path=path):
                self.assertNotIn('rel="canonical"', html)

    def test_published_site_pages_link_to_a_local_extension_service(self):
        data = chillcast_pages.load_data()
        published = [s for s in data["sites"] if chillcast_pages.is_published(s)]
        self.assertEqual(len(published), len(chillcast_pages.PUBLISHED_SITES))
        for site in published:
            with self.subTest(slug=site["slug"]):
                html = self.html[chillcast_pages.site_path(site)]
                self.assertIn("Station data for", html)

    def test_site_pages_show_at_most_three_fitting_varieties(self):
        data = chillcast_pages.load_data()
        for site in (s for s in data["sites"] if chillcast_pages.is_published(s)):
            html = self.html[chillcast_pages.site_path(site)]
            section = html.split("Which fruit varieties suit", 1)[1].split("</section>", 1)[0]
            rows = section.count("<tr>") - section.count("<thead>")
            with self.subTest(slug=site["slug"]):
                self.assertLessEqual(rows, chillcast_pages.TOP_FITS)

    def test_variety_pages_show_a_source_link(self):
        varieties = chillcast_pages.load_varieties()
        for variety in varieties:
            with self.subTest(variety=variety["name"]):
                self.assertTrue(variety.get("source"), "出典 URL がありません")
                html = self.html[variety["path"]]
                self.assertIn(variety["source"].replace("&", "&amp;"), html)

    def test_country_index_carries_a_country_specific_paragraph(self):
        data = chillcast_pages.load_data()
        for country_slug, country in {(s["country_slug"], s["country"]) for s in data["sites"]}:
            path = f"{chillcast_pages.CHILL_ROOT}{country_slug}/"
            with self.subTest(country=country):
                self.assertIn(chillcast_pages.COUNTRY_NOTES[country][:60],
                              self.html[path].replace("&#x27;", "'").replace("&amp;", "&"))

    def test_nearby_locations_stay_within_the_distance_limit(self):
        data = chillcast_pages.load_data()
        published = [s for s in data["sites"] if chillcast_pages.is_published(s)]
        by_path = {chillcast_pages.site_path(s): s for s in published}
        for path, site in by_path.items():
            html = self.html[path]
            for km in re.findall(r"— (\d+) km</li>", html):
                with self.subTest(slug=site["slug"]):
                    self.assertLessEqual(float(km), chillcast_pages.NEARBY_MAX_KM)

    def test_variety_json_payload_has_no_closing_script_tag(self):
        index = self.html[chillcast_pages.CHILL_ROOT]
        payload = index.split('id="chill-varieties">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("</", payload)


class SlugifyTests(unittest.TestCase):
    def test_normalises_turkish_letters(self):
        self.assertEqual(chillcast_pages.slugify("Eğirdir"), "egirdir")
        self.assertEqual(chillcast_pages.slugify("İsparta"), "isparta")

    def test_strips_combining_marks(self):
        self.assertEqual(chillcast_pages.slugify("Logroño"), "logrono")
        self.assertEqual(chillcast_pages.slugify("León"), "leon")

    def test_checked_slug_rejects_unsafe_values(self):
        for bad in ("../etc", "a/b", "Fresno", "", 'a"b'):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    chillcast_pages.checked_slug(bad)


class SeasonStoryTests(unittest.TestCase):
    def _site(self, values):
        seasons = [{"label": f"20{10 + i}–{11 + i}", "forty_five": v,
                    "utah": v / 2, "dynamic": v / 10}
                   for i, v in enumerate(values)]
        mean = sum(values) / len(values)
        return {
            "seasons": seasons,
            "stats": {"forty_five": {"mean": mean}, "dynamic": {"mean": mean / 10}},
        }

    def test_ordinal_holds_for_every_rank_in_a_ten_season_site(self):
        base = [1000, 1010, 1020, 1030, 1040, 1050, 1060, 1070, 1080, 1090]
        for rank in range(10):
            values = base[:9]
            values.append(base[rank] + 0.5)
            with self.subTest(rank=rank):
                text = chillcast_pages._season_story(self._site(values))
                self.assertIn("of the ten seasons recorded here", text)

    def test_zero_mean_does_not_divide_by_zero(self):
        text = chillcast_pages._season_story(self._site([0.0] * 10))
        self.assertIn("within a couple of percent", text)


class PromoLinkTests(unittest.TestCase):
    def test_promo_extra_link_points_at_a_generated_page(self):
        paths = {path for path, _, _ in chillcast_pages.build_pages()}
        html = render_promo_page("chillcast", "en")
        for href in re.findall(r'class="promo-text-link" href="([^"]+)"', html):
            if href.startswith("#"):
                continue
            with self.subTest(href=href):
                self.assertIn(href, paths)

    def test_extra_link_is_omitted_for_locales_without_one(self):
        for locale in PROMO_APPS["chillcast"]["locales"]:
            html = render_promo_page("chillcast", locale)
            expected = 2 if locale == "en" else 1
            with self.subTest(locale=locale):
                self.assertEqual(html.count('class="promo-text-link"'), expected)


if __name__ == "__main__":
    unittest.main()
