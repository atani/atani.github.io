#!/usr/bin/env python3
"""LOLIPOP! Deploy Now 用の配信ディレクトリを組み立てる。

Deploy Now は Next.js の standalone 出力を動かす前提なので、ポートフォリオと支援
ページを public/ に置いた最小の Next.js アプリを生成する。ページ自体は静的 HTML の
ままで、next.config の rewrites で `/` と `/support/` を public/ 配下へ向ける。

GitHub Pages 側にしか存在しないパス (ブログのアーカイブ、アンクラスPortの紹介
ページ) への絶対パスリンクは、GitHub Pages の URL に書き換える。

lolipop CLI は .gitignore を尊重してファイルを除外するため、出力先はリポジトリの
外に置く。

    python3 scripts/build-deploy-now.py
    lolipop deploy --dir "$(python3 scripts/build-deploy-now.py --print-dir)"
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = pathlib.Path(tempfile.gettempdir()) / "atani-deploy-now"

SITE = "https://atani.lolipop-now.app"
PAGES = "https://atani.github.io"

PAGES_ONLY_LINKS = {
    'href="/archives/"': f'href="{PAGES}/archives/"',
    'href="/anclas-port/#contact"': f'href="{PAGES}/anclas-port/#contact"',
}

# 配信先のパス。next.config の trailingSlash: true に合わせ、末尾スラッシュ付きを正とする。
PAGES_TO_COPY = {
    "index.html": "/",
    "support/index.html": "/support/",
}

ASSETS = ["assets/*.png", "assets/*.svg", "css/portfolio.css"]

PACKAGE_JSON = {
    "name": "atani-portfolio",
    "private": True,
    "scripts": {"build": "next build"},
    "dependencies": {
        "next": "15.5.4",
        "react": "19.1.1",
        "react-dom": "19.1.1",
    },
}

NEXT_CONFIG = """const config = {
  output: 'standalone',
  trailingSlash: true,
  async rewrites() {
    return {
      beforeFiles: [
        { source: '/', destination: '/index.html' },
        { source: '/support/', destination: '/support/index.html' },
      ],
    };
  },
};

export default config;
"""

LAYOUT = """export const metadata = { title: 'Akira Taniwaki' };

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
"""

NOT_FOUND = """export default function NotFound() {
  return <p>Not found</p>;
}
"""


def rewrite(html: str, path: str) -> str:
    for old, new in PAGES_ONLY_LINKS.items():
        html = html.replace(old, new)
    html = html.replace(f'content="{PAGES}/"', f'content="{SITE}/"')
    html = html.replace(f'content="{PAGES}/support/"', f'content="{SITE}/support/"')
    html = html.replace(f'content="{PAGES}/assets/', f'content="{SITE}/assets/')
    canonical = f'  <link rel="canonical" href="{SITE}{path}">\n'
    return html.replace("</head>", canonical + "</head>", 1)


def build(out: pathlib.Path, quiet: bool) -> None:
    if out.exists():
        shutil.rmtree(out)
    public = out / "public"
    public.mkdir(parents=True)

    def log(message: str) -> None:
        if not quiet:
            print(message)

    for src, path in PAGES_TO_COPY.items():
        dest = public / src
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rewrite((ROOT / src).read_text(encoding="utf-8"), path), encoding="utf-8")
        log(f"page  public/{src}")

    for pattern in ASSETS:
        for src in sorted(ROOT.glob(pattern)):
            dest = public / src.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            log(f"asset public/{src.relative_to(ROOT)}")

    (out / "package.json").write_text(json.dumps(PACKAGE_JSON, indent=2) + "\n", encoding="utf-8")
    (out / "next.config.mjs").write_text(NEXT_CONFIG, encoding="utf-8")
    app = out / "app"
    app.mkdir()
    (app / "layout.jsx").write_text(LAYOUT, encoding="utf-8")
    (app / "not-found.jsx").write_text(NOT_FOUND, encoding="utf-8")
    log("wrap  package.json / next.config.mjs / app")

    # Deploy Now 側の install は npm ci なので、lockfile を同梱する
    subprocess.run(
        ["npm", "install", "--package-lock-only", "--no-audit", "--no-fund"],
        cwd=out, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    log("wrap  package-lock.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT, help="出力先ディレクトリ")
    parser.add_argument("--print-dir", action="store_true", help="出力先のパスだけを標準出力に書く")
    args = parser.parse_args()

    build(args.out, quiet=args.print_dir)
    print(args.out if args.print_dir else f"\n出力先: {args.out}", file=sys.stdout)


if __name__ == "__main__":
    main()
