#!/usr/bin/env python3
"""LOLIPOP! Deploy Now 用の配信ディレクトリを組み立てる。

Deploy Now は Next.js の standalone 出力を動かす前提なので、ポートフォリオと支援
ページを public/ に置いた最小の Next.js アプリを生成する。ページ自体は静的 HTML の
ままで、next.config の rewrites で `/` と `/support/` を public/ 配下へ向ける。

支援ページは Deploy Now でのみ公開するため、ソースは GitHub Pages (Jekyll) が
出力しない `_deploy-now/` に置いてある。

GitHub Pages 側にしか存在しないパス (ブログのアーカイブ、アンクラスPortの紹介
ページ) への絶対パスリンクは、GitHub Pages の URL に書き換える。

lolipop CLI は .gitignore を尊重してファイルを除外するため、出力先はリポジトリの
外に置く。

    python3 scripts/build-deploy-now.py
    lolipop deploy --dir "$(python3 scripts/build-deploy-now.py --print-dir)"
"""

import argparse
import datetime
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape as xml_escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = pathlib.Path(tempfile.gettempdir()) / "atani-deploy-now"

sys.path.insert(0, str(ROOT / "_deploy-now"))
from promo_apps import PROMO_APPS, render_promo_page
from chillcast_pages import build_pages as build_chillcast_pages

SITE = "https://atani.lolipop-now.app"
PAGES = "https://atani.github.io"

PAGES_ONLY_LINKS = {
    'href="/archives/"': f'href="{PAGES}/archives/"',
    'href="/anclas-port/#contact"': f'href="{PAGES}/anclas-port/#contact"',
}

# リポジトリ内のソース -> 配信先の (パス, public 配下の出力先)。
# next.config の trailingSlash: true に合わせ、末尾スラッシュ付きを正とする。
PAGES_TO_COPY = {
    "_deploy-now/index.html": ("/", "index.html"),
    "_deploy-now/app-ads.txt": ("/", "app-ads.txt"),
    "_deploy-now/support/index.html": ("/support/", "support/index.html"),
    "_deploy-now/peyo/index.html": ("/peyo/", "peyo/index.html"),
    "_deploy-now/sports-photo/index.html": ("/sports-photo/", "sports-photo/index.html"),
    "_deploy-now/chillcast/privacy/index.html": ("/chillcast/privacy/", "chillcast/privacy/index.html"),
    "_deploy-now/match-notebook/privacy/index.html": ("/match-notebook/privacy/", "match-notebook/privacy/index.html"),
    "_deploy-now/match-notebook/en/privacy/index.html": ("/match-notebook/en/privacy/", "match-notebook/en/privacy/index.html"),
}

# HTML ではないので rewrite()（canonical の差し込み）を通さずそのまま置く。
# sitemap にも載せない。
FILES_TO_COPY = {
    "_deploy-now/robots.txt": "robots.txt",
}

LOCALIZED_PAGES = {
    "en": {
        "lang": "en",
        "store": "https://apps.apple.com/us/app/id6791587493",
            "replacements": {
            "ページ内ナビゲーション": "On this page",
            "使い方": "How it works",
            "料金": "Pricing",
            "Peyoの先頭へ": "Back to top",
            "言語": "Languages",
            "ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。": "Peyo is an iPhone and iPad app for drawing peyote stitch bead patterns and counting beads by color.",
            "ペヨーテ図案を、<br><em>描く。数える。共有する。</em>": "Peyote patterns,<br><em>drawn. counted. shared.</em>",
            "紙に線を引いて、ビーズを数え直す時間を、もっと作品を考える時間に。Peyoは、ペヨーテステッチのための半目ずれキャンバスです。": "Spend less time redrawing on paper and recounting beads, and more time making. Peyo is a staggered canvas made for peyote stitch.",
            "無料でApp Storeから始める": "Start free on the App Store",
            "3ステップで見る": "See how it works",
            "iPhone・iPad対応 / 登録不要 / 作図機能は無料": "For iPhone & iPad / No sign-up / Drawing is free",
            "Peyoの実際の作図画面。ハートのペヨーテ図案と色ごとのビーズ数が表示されている": "Peyo's real editor screen showing a heart pattern and bead counts by color",
            "思いついた模様を、<br><em>すぐに試せる。</em>": "Try an idea<br><em>the moment it arrives.</em>",
            "ペヨーテステッチの実際の並びに合わせたキャンバスだから、紙の方眼紙を探すところから始めなくていい。指で描いて、数を見て、また直せます。": "The canvas follows the real staggered layout of peyote stitch. Draw with your finger, check the count, and adjust as you go.",
            "Peyoの中身を、<br><em>そのまま見る。</em>": "See Peyo<br><em>as it really is.</em>",
            "Peyoの作図画面": "Peyo editor screen",
            "Peyoの作品を書き出す画面": "Peyo export screen",
            "Peyoの作品ギャラリー画面": "Peyo gallery screen",
            "描く": "Draw",
            "書き出す": "Export",
            "残す": "Keep",
            "作品になるまで、<br>3つだけ。": "From idea to pattern,<br>just three steps.",
            "指で描く": "Draw with your finger",
            "ペヨーテステッチ専用の半目ずれキャンバスに、思いついた模様をそのまま描きます。": "Draw your idea directly on a staggered canvas designed for peyote stitch.",
            "数を確認する": "Check the count",
            "使ったビーズを色ごとに自動集計。材料を準備するときの数え直しを減らせます。": "Peyo counts beads by color automatically, so preparing materials takes less recounting.",
            "作品カードにする": "Make a project card",
            "作品名、図案、ビーズ数、使用色を1枚にまとめて、保存・共有できます。": "Save and share the name, pattern, bead count, and colors together in one card.",
            "図案だけで終わらせない。<br><em>作品カードに残す。</em>": "Don't stop at the pattern.<br><em>Keep it as a project card.</em>",
            "作品名をつけて、図案とビーズ数を1枚に。自分用の記録にも、友だちに見せるときにも、そのまま使えます。": "Give your work a name and keep the pattern and bead count together. It is ready for your own records or for sharing with friends.",
            "Peyoを無料で試す": "Try Peyo for free",
            "下絵に重ねて描く。<br><em>Peyo Proで配色を試す。</em>": "Draw over a reference image.<br><em>Try new colors with Peyo Pro.</em>",
            "作図、ビーズ数の集計、図案の保存は無料です。Peyo Proでは、下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Drawing, bead counts, and saving your patterns are free. Peyo Pro adds drawing over a reference image and bulk color replacement, and removes banner ads.",
            "Peyo Proに含まれるもの": "What's included in Peyo Pro",
            "下絵を使って作図": "Draw over a reference image",
            "色をまとめて置き換え": "Replace a color throughout your pattern",
            "バナー広告なし": "No banner ads",
            "おすすめ": "Recommended",
            "年額プラン": "Annual plan",
            "アプリ内の表示価格": "Price shown in the app",
            "/ 年": "/ year",
            "毎年自動更新": "Renews yearly",
            "対象の方は年額プランを1週間無料体験": "One-week free trial for eligible customers",
            "永久": "Lifetime",
            "買い切りプラン": "Lifetime plan",
            "買い切り": "One-time purchase",
            "一度の購入でずっと利用": "Pay once, use forever",
            "基本": "Basic",
            "月額プラン": "Monthly plan",
            "/ 月": "/ month",
            "毎月自動更新": "Renews monthly",
            "年額プランは、Appleの初回特典の対象者に1週間の無料体験があります。体験終了の24時間前までに解約しない限り、その後はアプリ内に表示された年額で課金され、毎年自動更新されます。価格と対象条件は購入確定前に確認できます。": "Eligible customers can try the annual plan free for one week. Unless you cancel at least 24 hours before the trial ends, you will then be charged the annual price shown in the app and the subscription will renew annually. Price and introductory-offer eligibility are shown before you confirm.",
            "App Storeで見る": "View on the App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Your next project<br><em>can start today.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "No sign-up. Designs stay on your device. Start free with your first pattern.",
            "App Storeからダウンロード": "Download on the App Store",
            "サポート・プライバシー": "Support & privacy",
            "Summer<br>Bracelet": "Summer<br>Bracelet",
            "80 beads": "80 beads",
            "2 colors": "2 colors",
            "iPhone・iPadでペヨーテステッチの図案を描き、ビーズ数を色ごとに集計。Peyo Proでは下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Draw peyote stitch patterns and count beads by color on iPhone and iPad. Peyo Pro adds reference-image drawing and bulk color replacement, without banner ads.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Draw. Count. Share.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Draw peyote stitch patterns with your finger, count beads by color, and save or share your work as project cards.",
        },
    },
    "de": {
        "lang": "de",
        "store": "https://apps.apple.com/de/app/id6791587493",
        "replacements": {
            "ページ内ナビゲーション": "Auf dieser Seite",
            "使い方": "So funktioniert es",
            "料金": "Preise",
            "Peyoの先頭へ": "Zum Seitenanfang",
            "言語": "Sprachen",
            "ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。": "Peyo ist eine iPhone- und iPad-App zum Zeichnen von Peyote-Perlenmustern und Zählen der Perlen nach Farbe.",
            "ペヨーテ図案を、<br><em>描く。数える。共有する。</em>": "Peyote-Muster,<br><em>zeichnen. zählen. teilen.</em>",
            "紙に線を引いて、ビーズを数え直す時間を、もっと作品を考える時間に。Peyoは、ペヨーテステッチのための半目ずれキャンバスです。": "Weniger auf Papier zeichnen und Perlen nachzählen, mehr Zeit fürs Gestalten: Peyo ist eine versetzte Zeichenfläche für Peyote-Stiche.",
            "無料でApp Storeから始める": "Kostenlos im App Store starten",
            "3ステップで見る": "So funktioniert es",
            "iPhone・iPad対応 / 登録不要 / 作図機能は無料": "Für iPhone & iPad / Keine Anmeldung / Zeichnen kostenlos",
            "Peyoの実際の作図画面。ハートのペヨーテ図案と色ごとのビーズ数が表示されている": "Der echte Peyo-Editor mit einem Herzmuster und Perlenzahlen nach Farbe",
            "思いついた模様を、<br><em>すぐに試せる。</em>": "Eine Idee<br><em>sofort ausprobieren.</em>",
            "ペヨーテステッチの実際の並びに合わせたキャンバスだから、紙の方眼紙を探すところから始めなくていい。指で描いて、数を見て、また直せます。": "Die Zeichenfläche folgt der versetzten Anordnung des Peyote-Stichs. Zeichnen, Anzahl prüfen und direkt weiterarbeiten.",
            "Peyoの中身を、<br><em>そのまま見る。</em>": "Peyo<br><em>in echt erleben.</em>",
            "Peyoの作図画面": "Peyo-Editor",
            "Peyoの作品を書き出す画面": "Peyo-Export",
            "Peyoの作品ギャラリー画面": "Peyo-Galerie",
            "描く": "Zeichnen",
            "書き出す": "Exportieren",
            "残す": "Speichern",
            "作品になるまで、<br>3つだけ。": "Vom Gedanken zum Muster,<br>in nur drei Schritten.",
            "指で描く": "Mit dem Finger zeichnen",
            "ペヨーテステッチ専用の半目ずれキャンバスに、思いついた模様をそのまま描きます。": "Deine Idee direkt auf einer versetzten Zeichenfläche für Peyote-Stiche zeichnen.",
            "数を確認する": "Anzahl prüfen",
            "使ったビーズを色ごとに自動集計。材料を準備するときの数え直しを減らせます。": "Peyo zählt Perlen automatisch nach Farbe und erspart dir das Nachzählen beim Vorbereiten.",
            "作品カードにする": "Projektkarte erstellen",
            "作品名、図案、ビーズ数、使用色を1枚にまとめて、保存・共有できます。": "Name, Muster, Perlenzahl und Farben gemeinsam auf einer Karte speichern und teilen.",
            "図案だけで終わらせない。<br><em>作品カードに残す。</em>": "Nicht beim Muster aufhören.<br><em>Als Projektkarte festhalten.</em>",
            "作品名をつけて、図案とビーズ数を1枚に。自分用の記録にも、友だちに見せるときにも、そのまま使えます。": "Gib deinem Werk einen Namen und bewahre Muster und Perlenzahl zusammen auf – für dich selbst oder zum Teilen.",
            "Peyoを無料で試す": "Peyo kostenlos testen",
            "下絵に重ねて描く。<br><em>Peyo Proで配色を試す。</em>": "Zeichne mit einem Bild als Vorlage.<br><em>Probiere neue Farben mit Peyo Pro.</em>",
            "作図、ビーズ数の集計、図案の保存は無料です。Peyo Proでは、下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Das Zeichnen, die Perlenzählung und das Speichern deiner Muster sind kostenlos. Mit Peyo Pro kannst du beim Zeichnen ein Referenzbild als Vorlage hinterlegen und eine Farbe im gesamten Muster ersetzen. Außerdem entfällt die Bannerwerbung.",
            "Peyo Proに含まれるもの": "In Peyo Pro enthalten",
            "下絵を使って作図": "Mit einem Referenzbild als Vorlage zeichnen",
            "色をまとめて置き換え": "Eine Farbe im gesamten Muster ersetzen",
            "バナー広告なし": "Keine Bannerwerbung",
            "おすすめ": "Empfohlen",
            "年額プラン": "Jahresabo",
            "アプリ内の表示価格": "Preis in der App",
            "/ 年": "/ Jahr",
            "毎年自動更新": "Jährliche Verlängerung",
            "対象の方は年額プランを1週間無料体験": "Eine Woche kostenlos testen für berechtigte Kunden",
            "永久": "Dauerhaft",
            "買い切りプラン": "Einmalkauf",
            "買い切り": "Einmalig",
            "一度の購入でずっと利用": "Einmal zahlen, dauerhaft nutzen",
            "基本": "Basis",
            "月額プラン": "Monatsabo",
            "/ 月": "/ Monat",
            "毎月自動更新": "Monatliche Verlängerung",
            "年額プランは、Appleの初回特典の対象者に1週間の無料体験があります。体験終了の24時間前までに解約しない限り、その後はアプリ内に表示された年額で課金され、毎年自動更新されます。価格と対象条件は購入確定前に確認できます。": "Berechtigte Kunden können das Jahresabo eine Woche lang kostenlos testen. Wenn du nicht spätestens 24 Stunden vor Ende der Testphase kündigst, wird dir anschließend der in der App angezeigte Jahrespreis berechnet und das Abonnement verlängert sich jährlich. Den Preis und ob du das Einführungsangebot nutzen kannst, siehst du vor der Bestätigung.",
            "App Storeで見る": "Im App Store ansehen",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Dein nächstes Projekt<br><em>kann heute beginnen.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Keine Anmeldung. Muster bleiben auf deinem Gerät. Starte kostenlos mit deinem ersten Muster.",
            "App Storeからダウンロード": "Im App Store laden",
            "サポート・プライバシー": "Support & Datenschutz",
            "80 beads": "80 Perlen",
            "2 colors": "2 Farben",
            "iPhone・iPadでペヨーテステッチの図案を描き、ビーズ数を色ごとに集計。Peyo Proでは下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Zeichne Peyote-Muster und zähle Perlen nach Farbe auf iPhone und iPad. Mit Peyo Pro zeichnest du mit einem Referenzbild als Vorlage und ersetzt Farben im gesamten Muster, ohne Bannerwerbung.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Zeichnen. Zählen. Teilen.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Peyote-Muster mit dem Finger zeichnen, Perlen nach Farbe zählen und als Projektkarten speichern oder teilen.",
        },
    },
    "es": {
        "lang": "es",
        "store": "https://apps.apple.com/es/app/id6791587493",
        "replacements": {
            "ページ内ナビゲーション": "En esta página",
            "使い方": "Cómo funciona",
            "料金": "Precio",
            "Peyoの先頭へ": "Volver arriba",
            "言語": "Idiomas",
            "ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。": "Peyo es una app para iPhone y iPad que permite dibujar patrones de cuentas para peyote stitch y contarlas por color.",
            "ペヨーテ図案を、<br><em>描く。数える。共有する。</em>": "Patrones de peyote,<br><em>dibuja. cuenta. comparte.</em>",
            "紙に線を引いて、ビーズを数え直す時間を、もっと作品を考える時間に。Peyoは、ペヨーテステッチのための半目ずれキャンバスです。": "Dedica menos tiempo a dibujar en papel y volver a contar cuentas, y más tiempo a crear. Peyo es un lienzo escalonado para peyote stitch.",
            "無料でApp Storeから始める": "Empieza gratis en el App Store",
            "3ステップで見る": "Ver cómo funciona",
            "iPhone・iPad対応 / 登録不要 / 作図機能は無料": "Para iPhone y iPad / Sin registro / Dibujar es gratis",
            "Peyoの実際の作図画面。ハートのペヨーテ図案と色ごとのビーズ数が表示されている": "La pantalla real de Peyo con un patrón de corazón y el recuento por color",
            "思いついた模様を、<br><em>すぐに試せる。</em>": "Prueba una idea<br><em>en cuanto aparezca.</em>",
            "ペヨーテステッチの実際の並びに合わせたキャンバスだから、紙の方眼紙を探すところから始めなくていい。指で描いて、数を見て、また直せます。": "El lienzo respeta la distribución escalonada del peyote stitch. Dibuja con el dedo, comprueba el recuento y ajusta sobre la marcha.",
            "Peyoの中身を、<br><em>そのまま見る。</em>": "Mira Peyo<br><em>tal como es.</em>",
            "Peyoの作図画面": "Editor de Peyo",
            "Peyoの作品を書き出す画面": "Exportación de Peyo",
            "Peyoの作品ギャラリー画面": "Galería de Peyo",
            "描く": "Dibujar",
            "書き出す": "Exportar",
            "残す": "Guardar",
            "作品になるまで、<br>3つだけ。": "De la idea al patrón,<br>solo tres pasos.",
            "指で描く": "Dibuja con el dedo",
            "ペヨーテステッチ専用の半目ずれキャンバスに、思いついた模様をそのまま描きます。": "Dibuja tu idea directamente en un lienzo escalonado diseñado para peyote stitch.",
            "数を確認する": "Comprueba el recuento",
            "使ったビーズを色ごとに自動集計。材料を準備するときの数え直しを減らせます。": "Peyo cuenta las cuentas por color automáticamente para que prepares los materiales sin volver a contar.",
            "作品カードにする": "Crea una tarjeta de proyecto",
            "作品名、図案、ビーズ数、使用色を1枚にまとめて、保存・共有できます。": "Guarda y comparte el nombre, el patrón, el recuento y los colores en una sola tarjeta.",
            "図案だけで終わらせない。<br><em>作品カードに残す。</em>": "No te quedes solo con el patrón.<br><em>Guárdalo como tarjeta.</em>",
            "作品名をつけて、図案とビーズ数を1枚に。自分用の記録にも、友だちに見せるときにも、そのまま使えます。": "Ponle nombre a tu diseño y guarda juntos el patrón y el recuento, listo para ti o para compartir.",
            "Peyoを無料で試す": "Prueba Peyo gratis",
            "下絵に重ねて描く。<br><em>Peyo Proで配色を試す。</em>": "Dibuja sobre una imagen de referencia.<br><em>Prueba nuevos colores con Peyo Pro.</em>",
            "作図、ビーズ数の集計、図案の保存は無料です。Peyo Proでは、下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Dibujar, contar cuentas y guardar tus patrones es gratis. Con Peyo Pro puedes dibujar sobre una imagen de referencia y sustituir un color en todo el patrón. Además, se eliminan los banners publicitarios.",
            "Peyo Proに含まれるもの": "Qué incluye Peyo Pro",
            "下絵を使って作図": "Dibuja sobre una imagen de referencia",
            "色をまとめて置き換え": "Sustituye un color en todo el patrón",
            "バナー広告なし": "Sin banners publicitarios",
            "おすすめ": "Recomendado",
            "年額プラン": "Plan anual",
            "アプリ内の表示価格": "Precio indicado en la app",
            "/ 年": "/ año",
            "毎年自動更新": "Renovación anual",
            "対象の方は年額プランを1週間無料体験": "Una semana de prueba gratis para clientes que cumplan los requisitos",
            "永久": "De por vida",
            "買い切りプラン": "Compra única",
            "買い切り": "Pago único",
            "一度の購入でずっと利用": "Paga una vez y úsalo para siempre",
            "基本": "Básico",
            "月額プラン": "Plan mensual",
            "/ 月": "/ mes",
            "毎月自動更新": "Renovación mensual",
            "年額プランは、Appleの初回特典の対象者に1週間の無料体験があります。体験終了の24時間前までに解約しない限り、その後はアプリ内に表示された年額で課金され、毎年自動更新されます。価格と対象条件は購入確定前に確認できます。": "Los clientes que cumplan los requisitos pueden probar el plan anual gratis durante una semana. Si no cancelas la suscripción al menos 24 horas antes de que termine la prueba, se te cobrará el precio anual indicado en la app y la suscripción se renovará cada año. El precio y si cumples los requisitos para acceder a la oferta introductoria se muestran antes de confirmar.",
            "App Storeで見る": "Ver en el App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Tu próximo proyecto<br><em>puede empezar hoy.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Sin registro. Tus diseños se quedan en tu dispositivo. Empieza gratis con tu primer patrón.",
            "App Storeからダウンロード": "Descargar en el App Store",
            "サポート・プライバシー": "Soporte y privacidad",
            "80 beads": "80 cuentas",
            "2 colors": "2 colores",
            "iPhone・iPadでペヨーテステッチの図案を描き、ビーズ数を色ごとに集計。Peyo Proでは下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Dibuja patrones de punto peyote y consulta el número de cuentas por color en iPhone y iPad. Con Peyo Pro, dibuja sobre una imagen de referencia y sustituye colores en todo el patrón, sin banners publicitarios.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Dibuja. Cuenta. Comparte.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Dibuja patrones de peyote con el dedo, cuenta las cuentas por color y guarda o comparte tu trabajo como tarjetas de proyecto.",
        },
    },
    "fr": {
        "lang": "fr",
        "store": "https://apps.apple.com/fr/app/id6791587493",
        "replacements": {
            "ページ内ナビゲーション": "Sur cette page",
            "使い方": "Fonctionnement",
            "料金": "Tarif",
            "Peyoの先頭へ": "Retour en haut",
            "言語": "Langues",
            "ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。": "Peyo est une app pour iPhone et iPad qui permet de dessiner des motifs de perles peyote et de les compter par couleur.",
            "ペヨーテ図案を、<br><em>描く。数える。共有する。</em>": "Dessinez vos motifs peyote.<br><em>Comptez les perles par couleur.<br>Enregistrez et partagez.</em>",
            "紙に線を引いて、ビーズを数え直す時間を、もっと作品を考える時間に。Peyoは、ペヨーテステッチのための半目ずれキャンバスです。": "Dessinez au lieu de redessiner sur papier. Peyo est une grille décalée pour le point peyote : il compte les perles par couleur et les réunit dans une carte de projet à enregistrer ou à partager.",
            "無料でApp Storeから始める": "Télécharger gratuitement sur l’App Store",
            "3ステップで見る": "Voir comment ça marche",
            "iPhone・iPad対応 / 登録不要 / 作図機能は無料": "Pour iPhone et iPad / Sans inscription / Tous les outils de dessin sont gratuits",
            "Peyoの実際の作図画面。ハートのペヨーテ図案と色ごとのビーズ数が表示されている": "L’écran réel de Peyo avec un motif cœur et le compte des perles par couleur",
            "思いついた模様を、<br><em>すぐに試せる。</em>": "Essayez une idée<br><em>dès qu’elle arrive.</em>",
            "ペヨーテステッチの実際の並びに合わせたキャンバスだから、紙の方眼紙を探すところから始めなくていい。指で描いて、数を見て、また直せます。": "La grille suit la disposition décalée du point peyote. Dessinez, comptez les perles par couleur et ajustez au fil de l’idée.",
            "Peyoの中身を、<br><em>そのまま見る。</em>": "Découvrez Peyo,<br><em>du dessin au partage.</em>",
            "Peyoの作図画面": "Écran de création Peyo",
            "Peyoの作品を書き出す画面": "Écran du décompte des perles par couleur",
            "Peyoの作品ギャラリー画面": "Écran de la carte de projet à enregistrer et partager",
            "描く": "Dessiner",
            "書き出す": "Compter par couleur",
            "残す": "Enregistrer et partager",
            "作品になるまで、<br>3つだけ。": "De l’idée au motif,<br>trois étapes suffisent.",
            "指で描く": "Dessiner au doigt",
            "ペヨーテステッチ専用の半目ずれキャンバスに、思いついた模様をそのまま描きます。": "Dessinez votre idée directement sur une grille décalée pensée pour le point peyote.",
            "数を確認する": "Compter par couleur",
            "使ったビーズを色ごとに自動集計。材料を準備するときの数え直しを減らせます。": "Peyo indique le nombre exact de perles pour chaque couleur, afin de préparer vos matériaux sans recompter.",
            "作品カードにする": "Créer une carte de projet",
            "作品名、図案、ビーズ数、使用色を1枚にまとめて、保存・共有できます。": "Enregistrez le nom, le motif, le compte et les couleurs dans une carte de projet, prête à partager.",
            "図案だけで終わらせない。<br><em>作品カードに残す。</em>": "Ne vous arrêtez pas au motif.<br><em>Enregistrez et partagez votre carte de projet.</em>",
            "作品名をつけて、図案とビーズ数を1枚に。自分用の記録にも、友だちに見せるときにも、そのまま使えます。": "Donnez un nom à votre création et gardez le motif, le compte et les couleurs dans une carte de projet, pour vous ou pour la partager.",
            "Peyoを無料で試す": "Essayer Peyo gratuitement",
            "下絵に重ねて描く。<br><em>Peyo Proで配色を試す。</em>": "Dessinez par-dessus une image de référence.<br><em>Essayez de nouvelles couleurs avec Peyo Pro.</em>",
            "作図、ビーズ数の集計、図案の保存は無料です。Peyo Proでは、下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Le dessin, le comptage des perles et l’enregistrement de vos motifs sont gratuits. Avec Peyo Pro, dessinez par-dessus une image de référence et remplacez une couleur dans tout le motif. Les bannières publicitaires sont également supprimées.",
            "Peyo Proに含まれるもの": "Ce qui est inclus dans Peyo Pro",
            "下絵を使って作図": "Dessinez par-dessus une image de référence",
            "色をまとめて置き換え": "Remplacez une couleur dans tout le motif",
            "バナー広告なし": "Sans bannières publicitaires",
            "おすすめ": "Recommandé",
            "年額プラン": "Formule annuelle",
            "アプリ内の表示価格": "Prix indiqué dans l’app",
            "/ 年": "/ an",
            "毎年自動更新": "Renouvellement annuel",
            "対象の方は年額プランを1週間無料体験": "Une semaine d’essai gratuit pour les clients éligibles",
            "永久": "À vie",
            "買い切りプラン": "Achat définitif",
            "買い切り": "Achat unique",
            "一度の購入でずっと利用": "Un seul paiement, utilisation à vie",
            "基本": "Essentiel",
            "月額プラン": "Formule mensuelle",
            "/ 月": "/ mois",
            "毎月自動更新": "Renouvellement mensuel",
            "年額プランは、Appleの初回特典の対象者に1週間の無料体験があります。体験終了の24時間前までに解約しない限り、その後はアプリ内に表示された年額で課金され、毎年自動更新されます。価格と対象条件は購入確定前に確認できます。": "Les clients éligibles peuvent essayer l’abonnement annuel gratuitement pendant une semaine. Si vous ne résiliez pas l’abonnement au moins 24 heures avant la fin de l’essai, le prix annuel indiqué dans l’app vous sera ensuite facturé et l’abonnement sera renouvelé chaque année. Le prix et votre éligibilité à l’offre de lancement sont indiqués avant confirmation.",
            "App Storeで見る": "Voir sur l’App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Votre prochain projet<br><em>peut commencer aujourd’hui.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Sans inscription. Vos motifs restent sur votre appareil. Dessinez gratuitement votre premier motif.",
            "App Storeからダウンロード": "Télécharger sur l’App Store",
            "サポート・プライバシー": "Assistance et confidentialité",
            "80 beads": "80 perles",
            "2 colors": "2 couleurs",
            "iPhone・iPadでペヨーテステッチの図案を描き、ビーズ数を色ごとに集計。Peyo Proでは下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Dessinez des motifs au point peyote et comptez les perles par couleur sur iPhone et iPad. Avec Peyo Pro, dessinez par-dessus une image de référence et remplacez des couleurs dans tout le motif, sans bannières publicitaires.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Dessinez. Comptez. Enregistrez et partagez.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Dessinez des motifs peyote au doigt, comptez les perles par couleur et enregistrez ou partagez vos créations dans une carte de projet.",
        },
    },
    "it": {
        "lang": "it",
        "store": "https://apps.apple.com/it/app/id6791587493",
        "replacements": {
            "ページ内ナビゲーション": "In questa pagina",
            "使い方": "Come funziona",
            "料金": "Prezzo",
            "Peyoの先頭へ": "Torna in alto",
            "言語": "Lingue",
            "ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。": "Peyo è un’app per iPhone e iPad per disegnare motivi di perline peyote e contarle per colore.",
            "ペヨーテ図案を、<br><em>描く。数える。共有する。</em>": "Disegni peyote,<br><em>disegna. conta. condividi.</em>",
            "紙に線を引いて、ビーズを数え直す時間を、もっと作品を考える時間に。Peyoは、ペヨーテステッチのための半目ずれキャンバスです。": "Meno tempo a ridisegnare su carta e ricontare le perline, più tempo per creare. Peyo è una griglia sfalsata pensata per il peyote stitch.",
            "無料でApp Storeから始める": "Inizia gratis sull’App Store",
            "3ステップで見る": "Scopri come funziona",
            "iPhone・iPad対応 / 登録不要 / 作図機能は無料": "Per iPhone e iPad / Nessuna registrazione / Disegno gratuito",
            "Peyoの実際の作図画面。ハートのペヨーテ図案と色ごとのビーズ数が表示されている": "La schermata reale di Peyo con un motivo a cuore e il conteggio per colore",
            "思いついた模様を、<br><em>すぐに試せる。</em>": "Prova un’idea<br><em>appena arriva.</em>",
            "ペヨーテステッチの実際の並びに合わせたキャンバスだから、紙の方眼紙を探すところから始めなくていい。指で描いて、数を見て、また直せます。": "La griglia segue la disposizione sfalsata del peyote stitch. Disegna, controlla il conteggio e modifica mentre lavori.",
            "Peyoの中身を、<br><em>そのまま見る。</em>": "Guarda Peyo<br><em>proprio com’è.</em>",
            "Peyoの作図画面": "Schermata di disegno Peyo",
            "Peyoの作品を書き出す画面": "Schermata di esportazione Peyo",
            "Peyoの作品ギャラリー画面": "Galleria Peyo",
            "描く": "Disegna",
            "書き出す": "Esporta",
            "残す": "Conserva",
            "作品になるまで、<br>3つだけ。": "Dall’idea al motivo,<br>solo tre passaggi.",
            "指で描く": "Disegna con il dito",
            "ペヨーテステッチ専用の半目ずれキャンバスに、思いついた模様をそのまま描きます。": "Disegna la tua idea direttamente su una griglia sfalsata pensata per il peyote stitch.",
            "数を確認する": "Controlla il conteggio",
            "使ったビーズを色ごとに自動集計。材料を準備するときの数え直しを減らせます。": "Peyo conta automaticamente le perline per colore, così preparare i materiali è più semplice.",
            "作品カードにする": "Crea una scheda progetto",
            "作品名、図案、ビーズ数、使用色を1枚にまとめて、保存・共有できます。": "Salva e condividi nome, motivo, conteggio e colori in un’unica scheda.",
            "図案だけで終わらせない。<br><em>作品カードに残す。</em>": "Non fermarti al motivo.<br><em>Conservalo come scheda progetto.</em>",
            "作品名をつけて、図案とビーズ数を1枚に。自分用の記録にも、友だちに見せるときにも、そのまま使えます。": "Dai un nome al tuo lavoro e conserva insieme motivo e conteggio, per te o da condividere.",
            "Peyoを無料で試す": "Prova Peyo gratis",
            "下絵に重ねて描く。<br><em>Peyo Proで配色を試す。</em>": "Disegna sopra un’immagine di riferimento.<br><em>Prova nuovi colori con Peyo Pro.</em>",
            "作図、ビーズ数の集計、図案の保存は無料です。Peyo Proでは、下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Disegnare, contare le perline e salvare i tuoi schemi è gratis. Con Peyo Pro puoi disegnare sopra un’immagine di riferimento e sostituire un colore in tutto lo schema. Inoltre, vengono rimossi i banner pubblicitari.",
            "Peyo Proに含まれるもの": "Cosa include Peyo Pro",
            "下絵を使って作図": "Disegna sopra un’immagine di riferimento",
            "色をまとめて置き換え": "Sostituisci un colore in tutto lo schema",
            "バナー広告なし": "Nessun banner pubblicitario",
            "おすすめ": "Consigliato",
            "年額プラン": "Piano annuale",
            "アプリ内の表示価格": "Prezzo indicato nell’app",
            "/ 年": "/ anno",
            "毎年自動更新": "Rinnovo annuale",
            "対象の方は年額プランを1週間無料体験": "Una settimana di prova gratuita per i clienti idonei",
            "永久": "A vita",
            "買い切りプラン": "Acquisto una tantum",
            "買い切り": "Pagamento unico",
            "一度の購入でずっと利用": "Paghi una volta, lo usi per sempre",
            "基本": "Base",
            "月額プラン": "Piano mensile",
            "/ 月": "/ mese",
            "毎月自動更新": "Rinnovo mensile",
            "年額プランは、Appleの初回特典の対象者に1週間の無料体験があります。体験終了の24時間前までに解約しない限り、その後はアプリ内に表示された年額で課金され、毎年自動更新されます。価格と対象条件は購入確定前に確認できます。": "I clienti idonei possono provare il piano annuale gratis per una settimana. Se non annulli l’abbonamento almeno 24 ore prima della fine della prova, ti verrà addebitato il prezzo annuale indicato nell’app e l’abbonamento si rinnoverà ogni anno. Il prezzo e l’idoneità all’offerta introduttiva vengono mostrati prima della conferma.",
            "App Storeで見る": "Vedi sull’App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Il tuo prossimo progetto<br><em>può iniziare oggi.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Nessuna registrazione. I motivi restano sul tuo dispositivo. Inizia gratis dal tuo primo motivo.",
            "App Storeからダウンロード": "Scarica dall’App Store",
            "サポート・プライバシー": "Supporto e privacy",
            "80 beads": "80 perline",
            "2 colors": "2 colori",
            "iPhone・iPadでペヨーテステッチの図案を描き、ビーズ数を色ごとに集計。Peyo Proでは下絵を使った作図と色の一括置換が使え、バナー広告も表示されません。": "Disegna schemi a punto peyote e conta le perline per colore su iPhone e iPad. Con Peyo Pro puoi disegnare sopra un’immagine di riferimento e sostituire colori in tutto lo schema, senza banner pubblicitari.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Disegna. Conta. Condividi.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Disegna motivi peyote con il dito, conta le perline per colore e salva o condividi il tuo lavoro come scheda progetto.",
        },
    },
}

ASSETS = ["assets/*.png", "assets/*.svg", "assets/peyo-*.jpg", "css/portfolio.css", "css/peyo.css", "css/sports-photo.css", "css/apps.css", "css/support-analytics.css", "js/support-analytics.mjs", "app-ads.txt"]

PACKAGE_JSON = {
    "name": "atani-portfolio",
    "private": True,
    "scripts": {"build": "next build"},
    "dependencies": {
        "next": "16.3.4",
        "react": "19.2.8",
        "react-dom": "19.2.8",
    },
}

PROMO_REWRITES = []
for promo_slug, promo_app in PROMO_APPS.items():
    for promo_locale in promo_app["locales"]:
        promo_path = f"/{promo_slug}/" if promo_locale == "ja" else f"/{promo_slug}/{promo_locale}/"
        promo_rewrites = f"        {{ source: '{promo_path}', destination: '{promo_path}index.html' }},"
        PROMO_REWRITES.append(promo_rewrites)

NEXT_CONFIG = """const config = {
  output: 'standalone',
  trailingSlash: true,
  async rewrites() {
    return {
      beforeFiles: [
        { source: '/', destination: '/index.html' },
        { source: '/support/', destination: '/support/index.html' },
        { source: '/peyo/', destination: '/peyo/index.html' },
        { source: '/sports-photo/', destination: '/sports-photo/index.html' },
        { source: '/chillcast/privacy/', destination: '/chillcast/privacy/index.html' },
        { source: '/match-notebook/privacy/', destination: '/match-notebook/privacy/index.html' },
        { source: '/match-notebook/en/privacy/', destination: '/match-notebook/en/privacy/index.html' },
        { source: '/peyo/en/', destination: '/peyo/en/index.html' },
        { source: '/peyo/de/', destination: '/peyo/de/index.html' },
        { source: '/peyo/es/', destination: '/peyo/es/index.html' },
        { source: '/peyo/fr/', destination: '/peyo/fr/index.html' },
        { source: '/peyo/it/', destination: '/peyo/it/index.html' },
        { source: '/chillcast/chill-hours/', destination: '/chillcast/chill-hours/index.html' },
        { source: '/chillcast/chill-hours/:country/', destination: '/chillcast/chill-hours/:country/index.html' },
        { source: '/chillcast/chill-hours/:country/:city/', destination: '/chillcast/chill-hours/:country/:city/index.html' },
        { source: '/chillcast/varieties/', destination: '/chillcast/varieties/index.html' },
        { source: '/chillcast/varieties/:species/:variety/', destination: '/chillcast/varieties/:species/:variety/index.html' },
""" + "\n".join(PROMO_REWRITES) + """
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


def render_localized_page(source: str, locale: str, page: dict) -> str:
    html = source.replace('lang="ja"', f'lang="{page["lang"]}"', 1)
    html = html.replace(
        '<a href="/peyo/" lang="ja" aria-current="page">JA</a>',
        '<a href="/peyo/" lang="ja">JA</a>',
    )
    html = html.replace("/assets/peyo-ja-", f"/assets/peyo-{locale}-")
    html = html.replace("https://apps.apple.com/jp/app/id6791587493", page["store"])
    html = html.replace(f'content="{SITE}/peyo/"', f'content="{SITE}/peyo/{locale}/"', 1)
    for original, translated in sorted(page["replacements"].items(), key=lambda item: len(item[0]), reverse=True):
        html = html.replace(original, translated)
    active_locale = f'<a href="/peyo/{locale}/" lang="{page["lang"]}">{locale.upper()}</a>'
    html = html.replace(
        active_locale,
        f'<a href="/peyo/{locale}/" lang="{page["lang"]}" aria-current="page">{locale.upper()}</a>',
    )
    if locale == "fr":
        html = html.replace("/assets/peyo-fr-export.jpg", "/assets/peyo-fr-project-card.jpg")
        html = html.replace("/assets/peyo-fr-gallery.jpg", "/assets/peyo-fr-share.jpg")
    return html


def render_sitemap(paths: list[str]) -> str:
    """Deploy Now が配信するページだけを列挙する。GitHub Pages 側のパスは含めない。"""
    today = datetime.date.today().isoformat()
    entries = "".join(
        f"  <url><loc>{xml_escape(SITE + path)}</loc><lastmod>{today}</lastmod></url>\n"
        for path in sorted(dict.fromkeys(paths))
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n"
    )


def build(out: pathlib.Path, quiet: bool) -> None:
    if out.exists():
        shutil.rmtree(out)
    public = out / "public"
    public.mkdir(parents=True)

    def log(message: str) -> None:
        if not quiet:
            print(message)

    sitemap_paths: list[str] = []

    for src, (path, out_name) in PAGES_TO_COPY.items():
        dest = public / out_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rewrite((ROOT / src).read_text(encoding="utf-8"), path), encoding="utf-8")
        if path.endswith("/"):
            sitemap_paths.append(path)
        log(f"page  public/{out_name}")

    for src, out_name in FILES_TO_COPY.items():
        dest = public / out_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / src, dest)
        log(f"file  public/{out_name}")

    peyo_source = (ROOT / "_deploy-now/peyo/index.html").read_text(encoding="utf-8")
    for locale, page in LOCALIZED_PAGES.items():
        path = f"/peyo/{locale}/"
        dest = public / "peyo" / locale / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        html = render_localized_page(peyo_source, locale, page)
        dest.write_text(rewrite(html, path), encoding="utf-8")
        sitemap_paths.append(path)
        log(f"page  public/peyo/{locale}/index.html")

    for slug, app in PROMO_APPS.items():
        for locale in app["locales"]:
            path = f"/{slug}/" if locale == "ja" else f"/{slug}/{locale}/"
            out_name = f"{slug}/index.html" if locale == "ja" else f"{slug}/{locale}/index.html"
            dest = public / out_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            html = render_promo_page(slug, locale)
            dest.write_text(rewrite(html, path), encoding="utf-8")
            sitemap_paths.append(path)
            log(f"page  public/{out_name}")

    calculator = public / "assets" / "chillcast-calculator.js"
    calculator.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "_deploy-now/chillcast-calculator.js", calculator)
    log("asset public/assets/chillcast-calculator.js")

    chillcast_pages = build_chillcast_pages()
    for path, out_name, html in chillcast_pages:
        dest = public / out_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rewrite(html, path), encoding="utf-8")
        sitemap_paths.append(path)
    log(f"page  public/chillcast/ 配下に {len(chillcast_pages)} ページ")

    (public / "sitemap.xml").write_text(render_sitemap(sitemap_paths), encoding="utf-8")
    log(f"page  public/sitemap.xml（{len(set(sitemap_paths))} URL）")

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
