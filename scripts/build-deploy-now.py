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
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = pathlib.Path(tempfile.gettempdir()) / "atani-deploy-now"

sys.path.insert(0, str(ROOT / "_deploy-now"))
from promo_apps import PROMO_APPS, render_promo_page

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

LOCALIZED_PAGES = {
    "en": {
        "lang": "en",
        "store": "https://apps.apple.com/us/app/id6791587493",
            "replacements": {
            "¥500": "$4.99",
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
            "作図は無料。<br><em>広告非表示は一度だけ。</em>": "Design for free.<br><em>Remove ads once.</em>",
            "すべての作図機能を無料で使えます。気に入って使い続けるときだけ、500円の買い切りでバナー広告を非表示にできます。": "Every drawing feature is free. When you want to keep using Peyo, a one-time purchase removes the banner ads.",
            "買い切り / 自動更新なし": "One-time purchase / No subscription",
            "作図・保存・共有は無料": "Draw, save, and share for free",
            "購入後は広告なし": "No ads after purchase",
            "再インストール後も復元可能": "Restore after reinstall",
            "App Storeで見る": "View on the App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Your next project<br><em>can start today.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "No sign-up. Designs stay on your device. Start free with your first pattern.",
            "App Storeからダウンロード": "Download on the App Store",
            "サポート・プライバシー": "Support & privacy",
            "Summer<br>Bracelet": "Summer<br>Bracelet",
            "80 beads": "80 beads",
            "2 colors": "2 colors",
            "Peyoは、ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。作図は無料、広告非表示は500円の買い切りです。": "Peyo is an iPhone and iPad app for drawing peyote stitch bead patterns and counting beads by color. Drawing is free; remove ads with a one-time purchase.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Draw. Count. Share.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Draw peyote stitch patterns with your finger, count beads by color, and save or share your work as project cards.",
        },
    },
    "de": {
        "lang": "de",
        "store": "https://apps.apple.com/de/app/id6791587493",
        "replacements": {
            "¥500": "€5.99",
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
            "作図は無料。<br><em>Werbung einmalig entfernen.</em>": "Kostenlos gestalten.<br><em>Werbung einmalig entfernen.</em>",
            "作図は無料。<br><em>広告非表示は一度だけ。</em>": "Kostenlos gestalten.<br><em>Werbung einmalig entfernen.</em>",
            "すべての作図機能を無料で使えます。気に入って使い続けるときだけ、500円の買い切りでバナー広告を非表示にできます。": "Alle Zeichenfunktionen sind kostenlos. Mit einem einmaligen Kauf blendest du die Bannerwerbung dauerhaft aus.",
            "買い切り / 自動更新なし": "Einmaliger Kauf / Kein Abo",
            "作図・保存・共有は無料": "Zeichnen, speichern und teilen kostenlos",
            "購入後は広告なし": "Keine Werbung nach dem Kauf",
            "再インストール後も復元可能": "Nach Neuinstallation wiederherstellbar",
            "App Storeで見る": "Im App Store ansehen",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Dein nächstes Projekt<br><em>kann heute beginnen.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Keine Anmeldung. Muster bleiben auf deinem Gerät. Starte kostenlos mit deinem ersten Muster.",
            "App Storeからダウンロード": "Im App Store laden",
            "サポート・プライバシー": "Support & Datenschutz",
            "80 beads": "80 Perlen",
            "2 colors": "2 Farben",
            "Peyoは、ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。作図は無料、広告非表示は500円の買い切りです。": "Peyo ist eine iPhone- und iPad-App zum Zeichnen von Peyote-Perlenmustern und Zählen der Perlen nach Farbe. Zeichnen ist kostenlos; Werbung lässt sich einmalig entfernen.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Zeichnen. Zählen. Teilen.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Peyote-Muster mit dem Finger zeichnen, Perlen nach Farbe zählen und als Projektkarten speichern oder teilen.",
        },
    },
    "es": {
        "lang": "es",
        "store": "https://apps.apple.com/es/app/id6791587493",
        "replacements": {
            "¥500": "€5.99",
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
            "作図は無料。<br><em>広告非表示は一度だけ。</em>": "Diseña gratis.<br><em>Quita los anuncios una sola vez.</em>",
            "すべての作図機能を無料で使えます。気に入って使い続けるときだけ、500円の買い切りでバナー広告を非表示にできます。": "Todas las funciones de dibujo son gratis. Una compra única elimina los anuncios para siempre.",
            "買い切り / 自動更新なし": "Compra única / Sin suscripción",
            "作図・保存・共有は無料": "Dibuja, guarda y comparte gratis",
            "購入後は広告なし": "Sin anuncios después de comprar",
            "再インストール後も復元可能": "Restaurable tras reinstalar",
            "App Storeで見る": "Ver en el App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Tu próximo proyecto<br><em>puede empezar hoy.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Sin registro. Tus diseños se quedan en tu dispositivo. Empieza gratis con tu primer patrón.",
            "App Storeからダウンロード": "Descargar en el App Store",
            "サポート・プライバシー": "Soporte y privacidad",
            "80 beads": "80 cuentas",
            "2 colors": "2 colores",
            "Peyoは、ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。作図は無料、広告非表示は500円の買い切りです。": "Peyo es una app para iPhone y iPad que permite dibujar patrones de cuentas para peyote stitch y contarlas por color. Dibujar es gratis; puedes quitar los anuncios con una compra única.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Dibuja. Cuenta. Comparte.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Dibuja patrones de peyote con el dedo, cuenta las cuentas por color y guarda o comparte tu trabajo como tarjetas de proyecto.",
        },
    },
    "fr": {
        "lang": "fr",
        "store": "https://apps.apple.com/fr/app/id6791587493",
        "replacements": {
            "¥500": "€5.99",
            "ページ内ナビゲーション": "Sur cette page",
            "使い方": "Fonctionnement",
            "料金": "Tarif",
            "Peyoの先頭へ": "Retour en haut",
            "言語": "Langues",
            "ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。": "Peyo est une app pour iPhone et iPad qui permet de dessiner des motifs de perles peyote et de les compter par couleur.",
            "ペヨーテ図案を、<br><em>描く。数える。共有する。</em>": "Des motifs peyote,<br><em>dessiner. compter. partager.</em>",
            "紙に線を引いて、ビーズを数え直す時間を、もっと作品を考える時間に。Peyoは、ペヨーテステッチのための半目ずれキャンバスです。": "Passez moins de temps à redessiner sur papier et à recompter les perles, et plus de temps à créer. Peyo est une grille décalée conçue pour le peyote stitch.",
            "無料でApp Storeから始める": "Commencer gratuitement sur l’App Store",
            "3ステップで見る": "Voir comment ça marche",
            "iPhone・iPad対応 / 登録不要 / 作図機能は無料": "Pour iPhone et iPad / Sans inscription / Création gratuite",
            "Peyoの実際の作図画面。ハートのペヨーテ図案と色ごとのビーズ数が表示されている": "L’écran réel de Peyo avec un motif cœur et le compte des perles par couleur",
            "思いついた模様を、<br><em>すぐに試せる。</em>": "Essayez une idée<br><em>dès qu’elle arrive.</em>",
            "ペヨーテステッチの実際の並びに合わせたキャンバスだから、紙の方眼紙を探すところから始めなくていい。指で描いて、数を見て、また直せます。": "La grille respecte la disposition décalée du peyote stitch. Dessinez, vérifiez le compte et ajustez au fil de l’idée.",
            "Peyoの中身を、<br><em>そのまま見る。</em>": "Découvrez Peyo<br><em>tel qu’il est.</em>",
            "Peyoの作図画面": "Écran de création Peyo",
            "Peyoの作品を書き出す画面": "Écran d’export Peyo",
            "Peyoの作品ギャラリー画面": "Galerie Peyo",
            "描く": "Dessiner",
            "書き出す": "Exporter",
            "残す": "Conserver",
            "作品になるまで、<br>3つだけ。": "De l’idée au motif,<br>trois étapes suffisent.",
            "指で描く": "Dessiner au doigt",
            "ペヨーテステッチ専用の半目ずれキャンバスに、思いついた模様をそのまま描きます。": "Dessinez votre idée directement sur une grille décalée conçue pour le peyote stitch.",
            "数を確認する": "Vérifier le compte",
            "使ったビーズを色ごとに自動集計。材料を準備するときの数え直しを減らせます。": "Peyo compte automatiquement les perles par couleur pour simplifier la préparation du matériel.",
            "作品カードにする": "Créer une fiche projet",
            "作品名、図案、ビーズ数、使用色を1枚にまとめて、保存・共有できます。": "Enregistrez et partagez le nom, le motif, le compte et les couleurs sur une seule fiche.",
            "図案だけで終わらせない。<br><em>作品カードに残す。</em>": "Ne vous arrêtez pas au motif.<br><em>Gardez-le comme fiche projet.</em>",
            "作品名をつけて、図案とビーズ数を1枚に。自分用の記録にも、友だちに見せるときにも、そのまま使えます。": "Donnez un nom à votre création et gardez le motif et le compte ensemble, pour vous ou pour le partager.",
            "Peyoを無料で試す": "Essayer Peyo gratuitement",
            "作図は無料。<br><em>広告非表示は一度だけ。</em>": "Créez gratuitement.<br><em>Supprimez les pubs une seule fois.</em>",
            "すべての作図機能を無料で使えます。気に入って使い続けるときだけ、500円の買い切りでバナー広告を非表示にできます。": "Toutes les fonctions de création sont gratuites. Un achat unique supprime définitivement les publicités.",
            "買い切り / 自動更新なし": "Achat unique / Sans abonnement",
            "作図・保存・共有は無料": "Créer, enregistrer et partager gratuitement",
            "購入後は広告なし": "Aucune pub après l’achat",
            "再インストール後も復元可能": "Récupérable après réinstallation",
            "App Storeで見る": "Voir sur l’App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Votre prochain projet<br><em>peut commencer aujourd’hui.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Sans inscription. Vos motifs restent sur votre appareil. Commencez gratuitement avec votre premier motif.",
            "App Storeからダウンロード": "Télécharger sur l’App Store",
            "サポート・プライバシー": "Assistance et confidentialité",
            "80 beads": "80 perles",
            "2 colors": "2 couleurs",
            "Peyoは、ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。作図は無料、広告非表示は500円の買い切りです。": "Peyo est une app pour iPhone et iPad qui permet de dessiner des motifs de perles peyote et de les compter par couleur. La création est gratuite ; un achat unique supprime les publicités.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Dessiner. Compter. Partager.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Dessinez des motifs peyote au doigt, comptez les perles par couleur et enregistrez ou partagez vos créations sous forme de fiches projet.",
        },
    },
    "it": {
        "lang": "it",
        "store": "https://apps.apple.com/it/app/id6791587493",
        "replacements": {
            "¥500": "€5.99",
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
            "作図は無料。<br><em>広告非表示は一度だけ。</em>": "Disegna gratis.<br><em>Rimuovi la pubblicità una volta sola.</em>",
            "すべての作図機能を無料で使えます。気に入って使い続けるときだけ、500円の買い切りでバナー広告を非表示にできます。": "Tutte le funzioni di disegno sono gratuite. Un acquisto una tantum rimuove per sempre i banner pubblicitari.",
            "買い切り / 自動更新なし": "Acquisto una tantum / Nessun abbonamento",
            "作図・保存・共有は無料": "Disegna, salva e condividi gratis",
            "購入後は広告なし": "Niente pubblicità dopo l’acquisto",
            "再インストール後も復元可能": "Ripristinabile dopo la reinstallazione",
            "App Storeで見る": "Vedi sull’App Store",
            "次に作りたいものを、<br><em>今日のうちに描いてみる。</em>": "Il tuo prossimo progetto<br><em>può iniziare oggi.</em>",
            "登録不要。図案は端末内に保存。まずは無料で、最初の1模様から。": "Nessuna registrazione. I motivi restano sul tuo dispositivo. Inizia gratis dal tuo primo motivo.",
            "App Storeからダウンロード": "Scarica dall’App Store",
            "サポート・プライバシー": "Supporto e privacy",
            "80 beads": "80 perline",
            "2 colors": "2 colori",
            "Peyoは、ペヨーテステッチのビーズ図案を指で描き、色ごとのビーズ数を自動で数えられるiPhoneアプリです。作図は無料、広告非表示は500円の買い切りです。": "Peyo è un’app per iPhone e iPad per disegnare motivi di perline peyote e contarle per colore. Disegnare è gratis; puoi rimuovere la pubblicità con un acquisto una tantum.",
            "Peyo — ペヨーテ図案を、描く。数える。共有する。": "Peyo — Disegna. Conta. Condividi.",
            "ペヨーテステッチの図案を指で描いて、ビーズ数を自動集計。作品カードにして保存・共有できます。": "Disegna motivi peyote con il dito, conta le perline per colore e salva o condividi il tuo lavoro come scheda progetto.",
        },
    },
}

ASSETS = ["assets/*.png", "assets/*.svg", "assets/peyo-*.jpg", "css/portfolio.css", "css/peyo.css", "css/sports-photo.css", "css/apps.css", "app-ads.txt"]

PACKAGE_JSON = {
    "name": "atani-portfolio",
    "private": True,
    "scripts": {"build": "next build"},
    "dependencies": {
        "next": "16.3.0",
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
        { source: '/match-notebook/privacy/', destination: '/match-notebook/privacy/index.html' },
        { source: '/match-notebook/en/privacy/', destination: '/match-notebook/en/privacy/index.html' },
        { source: '/peyo/en/', destination: '/peyo/en/index.html' },
        { source: '/peyo/de/', destination: '/peyo/de/index.html' },
        { source: '/peyo/es/', destination: '/peyo/es/index.html' },
        { source: '/peyo/fr/', destination: '/peyo/fr/index.html' },
        { source: '/peyo/it/', destination: '/peyo/it/index.html' },
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
    html = html.replace("/assets/peyo-ja-", f"/assets/peyo-{locale}-")
    html = html.replace("https://apps.apple.com/jp/app/id6791587493", page["store"])
    html = html.replace(f'content="{SITE}/peyo/"', f'content="{SITE}/peyo/{locale}/"', 1)
    for original, translated in sorted(page["replacements"].items(), key=lambda item: len(item[0]), reverse=True):
        html = html.replace(original, translated)
    return html


def build(out: pathlib.Path, quiet: bool) -> None:
    if out.exists():
        shutil.rmtree(out)
    public = out / "public"
    public.mkdir(parents=True)

    def log(message: str) -> None:
        if not quiet:
            print(message)

    for src, (path, out_name) in PAGES_TO_COPY.items():
        dest = public / out_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rewrite((ROOT / src).read_text(encoding="utf-8"), path), encoding="utf-8")
        log(f"page  public/{out_name}")

    peyo_source = (ROOT / "_deploy-now/peyo/index.html").read_text(encoding="utf-8")
    for locale, page in LOCALIZED_PAGES.items():
        path = f"/peyo/{locale}/"
        dest = public / "peyo" / locale / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        html = render_localized_page(peyo_source, locale, page)
        dest.write_text(rewrite(html, path), encoding="utf-8")
        log(f"page  public/peyo/{locale}/index.html")

    for slug, app in PROMO_APPS.items():
        for locale in app["locales"]:
            path = f"/{slug}/" if locale == "ja" else f"/{slug}/{locale}/"
            out_name = f"{slug}/index.html" if locale == "ja" else f"{slug}/{locale}/index.html"
            dest = public / out_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            html = render_promo_page(slug, locale)
            dest.write_text(rewrite(html, path), encoding="utf-8")
            log(f"page  public/{out_name}")

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
