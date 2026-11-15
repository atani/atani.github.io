#!/usr/bin/env python3
"""Build the free chart pages on the existing GitHub Pages site."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "_deploy-now"))
from peyo_patterns import build_pages, build_assets, SITE


def build():
    for _, name, content in build_pages():
        dest = ROOT / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content + "\n", encoding="utf-8")
    paths = [path for path, _, _ in build_pages()]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += ''.join(f"  <url><loc>{SITE}{path}</loc></url>\n" for path in paths)
    (ROOT / "peyo-sitemap.xml").write_text(sitemap + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/peyo-sitemap.xml\n", encoding="utf-8")
    for name, content in build_assets():
        dest = ROOT / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
