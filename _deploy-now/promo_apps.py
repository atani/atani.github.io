"""共通テンプレートで作る各アプリのプロモーションページ。"""

from html import escape


def _copy(data, **changes):
    result = dict(data)
    result.update(changes)
    return result


PROMO_APPS = {
    "match-notebook": {
        "name": "Match Notebook",
        "icon": "match-notebook-icon.png",
        "theme": "blue",
        "store": "https://apps.apple.com/jp/app/id6781687173",
        "locales": {
            "ja": {
                "lang": "ja",
                "label": "日本語",
                "support": "/match-notebook/privacy/",
                "kicker": "対戦相手ノート",
                "headline": "前回効いた作戦を、<em>次の試合で忘れない。</em>",
                "lead": "弱点、効いたこと、避けること。再戦前に、前回の気づきを30秒で思い出せます。",
                "meta": "iPhone・iPad対応 / 登録不要 / 端末内に保存",
                "hero_alt": "Match Notebookの次の試合画面",
                "section_kicker": "試合のあとに残す",
                "section_title": "スコアだけでは残らない、<em>次の一手のための記録。</em>",
                "features": [
                    ("対戦相手を記録", "弱点、対戦成績、試合日を相手ごとにまとめる。"),
                    ("効いた作戦を残す", "最初の作戦、前回効いたこと、避けることを一画面に。"),
                    ("再戦前に見返す", "試合前に次の作戦カードを開いて、迷う時間を減らす。"),
                ],
                "gallery_title": "実際の画面で見る、<em>Match Notebook。</em>",
                "gallery_alts": ["次の試合と対戦相手の記録", "試合後の気づき入力", "対戦相手の戦績と作戦カード", "対応スポーツ一覧", "プライバシー設定"],
                "price_kicker": "無料で始める",
                "price_title": "5人・20試合まで無料。<br><em>買い切り ¥1,500。</em>",
                "price_body": "対戦相手5人・試合20件まで無料。続けたくなったら、¥1,500のLifetime買い切りで記録を無制限にできます。自動更新はありません。",
                "price_points": ["アカウント・サーバー不要", "試合後の気づきを端末内に保存", "一度の購入で自動更新なし"],
                "cta": "App Storeで見る",
                "footer": "Match Notebookを無料で試す",
            },
            "en": {
                "lang": "en",
                "label": "English",
                "support": "/match-notebook/en/privacy/",
                "store": "https://apps.apple.com/us/app/id6781687173",
                "kicker": "Opponent notes for rematches",
                "headline": "Remember what worked.<br><em>Win the rematch.</em>",
                "lead": "Keep weaknesses, winning patterns, and what to avoid in one place—then review your next strategy before the match.",
                "meta": "For iPhone & iPad / No account / Stored on device",
                "hero_alt": "Match Notebook next-match screen",
                "section_kicker": "After every match",
                "section_title": "More than a scorecard: <em>a record of your next move.</em>",
                "features": [
                    ("Know every opponent", "Keep weaknesses, head-to-head results, and match dates together."),
                    ("Save the strategy", "Record your opening plan, what worked, and what to avoid."),
                    ("Prepare in seconds", "Open the next-match card before play and start with a clear plan."),
                ],
                "gallery_title": "See Match Notebook, <em>as it really works.</em>",
                "gallery_alts": ["Next match and opponent notes", "Post-match insight entry", "Opponent record and strategy card", "Supported sports", "Privacy settings"],
                "price_kicker": "Start free",
                "price_title": "5 opponents and 20 matches free.<br><em>$14.99 once.</em>",
                "price_body": "Free for up to 5 opponents and 20 matches. A one-time $14.99 Lifetime purchase unlocks unlimited records, with no auto-renewal.",
                "price_points": ["No account or server required", "Your match notes stay on your device", "One purchase with no auto-renewal"],
                "cta": "View on the App Store",
                "footer": "Try Match Notebook free",
            },
        },
        "gallery": {
            "ja": ["match-notebook-ja-rematch.png", "match-notebook-ja-insight.png", "match-notebook-ja-ready.png", "match-notebook-ja-sports.png", "match-notebook-ja-private.png"],
            "en": ["match-notebook-en-rematch.png", "match-notebook-en-insight.png", "match-notebook-en-ready.png", "match-notebook-en-sports.png", "match-notebook-en-private.png"],
        },
    },
    "sports-photographer-helper": {
        "name": "Sports Photographer Helper",
        "icon": "sports-photographer-helper-icon.png",
        "theme": "indigo",
        "store": "https://apps.apple.com/jp/app/id6781572518",
        "locales": {
            "ja": {
                "lang": "ja",
                "label": "日本語",
                "kicker": "スポーツ撮影の事前準備",
                "headline": "試合前に、<em>設定と逆光をまとめてチェック。</em>",
                "lead": "会場・時刻・競技を入力すると、天気、太陽の向き、シャッター速度やISOまで撮影プランにまとまります。",
                "meta": "iPhone対応 / 英語・日本語 / 外部SDKなし",
                "hero_alt": "スポーツ撮影ヘルパーの試合設定とおすすめ撮影プラン",
                "section_kicker": "撮影前の5分を整える",
                "section_title": "光が変わる試合でも、<em>最初の一枚に迷わない。</em>",
                "features": [
                    ("会場と競技を入力", "試合時刻、競技、天候、カメラとレンズを一つのプランに。"),
                    ("光のリスクを先読み", "日の入り、ゴールデンアワー、逆光や終盤の暗さをタイムラインで確認。"),
                    ("設定をすぐ使う", "シャッター速度、絞り、ISO、AFモードを撮影前に見返せる。"),
                ],
                "gallery_title": "撮影前に見る、<em>実際のプラン画面。</em>",
                "gallery_alts": ["試合設定とおすすめ撮影プラン", "試合当日の天気と光のタイムライン", "6競技の撮影プリセット", "保存した撮影プラン"],
                "price_kicker": "無料 + Pro Lifetime",
                "price_title": "まず3プランを無料で。<em>必要な人だけ一度購入。</em>",
                "price_body": "無料版は3件の撮影プランと標準プリセットを利用できます。Pro Lifetime（買い切り）で保存数、機材プリセット、再利用、PDF書き出しを解放します。",
                "price_points": ["無料で計算結果を試せる", "Pro Lifetimeは自動更新なし", "年額プランはライブ機能提供まで表示しない"],
                "cta": "App Storeで見る",
                "footer": "撮影前の準備を始める",
            },
            "en": {
                "lang": "en",
                "label": "English",
                "kicker": "Pre-game planning for sports photographers",
                "headline": "Know your settings<br><em>before kickoff.</em>",
                "lead": "Add the venue, time, sport, and kit. Get the weather, sun position, exposure guidance, and a practical timeline in one plan.",
                "meta": "For iPhone / English & Japanese / No external SDK",
                "hero_alt": "Sports Photographer Helper match setup and camera plan",
                "section_kicker": "Make the first five minutes count",
                "section_title": "When the light changes, <em>your first shot is still ready.</em>",
                "features": [
                    ("Set up the match", "Bring the venue, sport, weather, camera, and lens into one plan."),
                    ("See light risks early", "Review sunset, golden hour, backlight, and late-game darkness on a timeline."),
                    ("Use clear settings", "Check shutter speed, aperture, ISO, and AF guidance before you shoot."),
                ],
                "gallery_title": "A closer look at <em>the real planning screens.</em>",
                "gallery_alts": ["Match setup and camera plan", "Match-day weather and light timeline", "Six sports presets", "Saved match plans"],
                "price_kicker": "Free + Pro Lifetime",
                "price_title": "Try three plans free.<br><em>Upgrade once when you need more.</em>",
                "price_body": "Free includes three saved plans and standard presets. Pro Lifetime unlocks unlimited plans, reusable weekly plans, equipment presets, and clean PDF exports.",
                "price_points": ["Try the core calculations free", "Pro Lifetime has no auto-renewal", "The annual plan stays hidden until live features ship"],
                "cta": "View on the App Store",
                "footer": "Start your pre-game plan",
            },
        },
        "gallery": {
            "ja": ["sports-ja-camera-plan.png", "sports-ja-weather-light.png", "sports-ja-six-sports.png", "sports-ja-saved-plans.png"],
            "en": ["sports-en-camera-plan.png", "sports-en-weather-light.png", "sports-en-six-sports.png", "sports-en-saved-plans.png"],
        },
    },
    "chillcast": {
        "name": "ChillCast",
        "icon": "chillcast-icon.png",
        "theme": "sky",
        "store": "https://apps.apple.com/jp/app/id6785241430",
        "locales": {
            "ja": {
                "lang": "ja",
                "label": "日本語",
                "kicker": "果樹の低温時間トラッカー",
                "headline": "今年、実はなる？<br><em>低温量から確かめる。</em>",
                "lead": "現在地の過去気象データから、今シーズンの低温時間を自動計算。品種ごとの充足状況をひと目で確認できます。",
                "meta": "iPhone対応 / 南北半球対応 / APIキー不要",
                "hero_alt": "ChillCastの低温量と積算モデル比較画面",
                "section_kicker": "果樹の休眠を数字で見る",
                "section_title": "ひとつの数字だけでなく、<em>3つのモデルで季節を読む。</em>",
                "features": [
                    ("低温量を自動計算", "現在地または指定地点の過去気象データから、今季の積算を表示。"),
                    ("モデルを比較", "45°F Hours、Utah、Dynamicを並べて、気候に合った見方を選べる。"),
                    ("品種の充足を確認", "りんご、もも、ぶどうなどの必要量と現在の状況を一覧で確認。"),
                ],
                "gallery_title": "栽培の判断に使える、<em>ChillCastの実画面。</em>",
                "gallery_alts": ["今シーズンの低温量", "積算モデルの比較", "品種ごとの充足状況"],
                "price_kicker": "無料 + Pro 買い切り",
                "price_title": "まず今季の低温量を確認。<em>必要になったらProへ。</em>",
                "price_body": "無料版は45°F Hoursと3品種を確認できます。Proの買い切りで3モデル、全品種、複数地点、履歴、CSV、通知を解放します。",
                "price_points": ["APIキーなしで始められる", "南北半球を自動判定", "Proは一度の購入で使い続けられる"],
                "cta": "App Storeで見る",
                "footer": "今季の低温量を見てみる",
            },
            "en": {
                "lang": "en",
                "label": "English",
                "kicker": "A chill-hours tracker for fruit growers",
                "headline": "Will your trees fruit<br><em>this year?</em>",
                "lead": "ChillCast calculates this season’s accumulated chill from historical weather data and shows whether each variety has had enough.",
                "meta": "For iPhone / Northern & Southern Hemispheres / No API key",
                "hero_alt": "ChillCast accumulated chill and model comparison screen",
                "section_kicker": "See dormancy as a number",
                "section_title": "Read the season with <em>three chill models, not one guess.</em>",
                "features": [
                    ("Calculate chill automatically", "Use historical weather for your current or selected location to track this season."),
                    ("Compare three models", "Put 45°F Hours, Utah, and Dynamic side by side for a better climate fit."),
                    ("Check every variety", "See required chill and fulfillment for apples, peaches, grapes, and more."),
                ],
                "gallery_title": "A closer look at <em>ChillCast in use.</em>",
                "gallery_alts": ["This season's accumulated chill", "Chill model comparison", "Variety fulfillment status", "History chart", "Pro features"],
                "price_kicker": "Free + Pro one-time purchase",
                "price_title": "Check this season first.<br><em>Unlock the full picture when you need it.</em>",
                "price_body": "The free version includes 45°F Hours and three varieties. Pro unlocks all three models, every variety, multiple locations, history, CSV export, and notifications.",
                "price_points": ["Start without an API key", "Northern and Southern Hemispheres", "Pro is a single purchase"],
                "cta": "View on the App Store",
                "footer": "Check your season’s chill",
            },
        },
        "gallery": {
            "ja": ["chillcast-ja-hero.png", "chillcast-ja-models.png", "chillcast-ja-varieties.png"],
            "en": ["chillcast-en-hero.png", "chillcast-en-models.png", "chillcast-en-varieties.png", "chillcast-en-history.png", "chillcast-en-pro.png"],
        },
    },
    "planonce": {
        "name": "PlanOnce",
        "icon": "planonce-icon.png",
        "theme": "coral",
        "store": "https://apps.apple.com/jp/app/id6782772002",
        "locales": {
            "ja": {
                "lang": "ja",
                "label": "日本語",
                "kicker": "買い切りのゼロベース予算",
                "headline": "すべてのお金に、<em>役割を持たせる。</em>",
                "lead": "収入をカテゴリに振り分け、支出を3タップで記録。銀行ログインなし、サブスクなし、データは端末の中に。",
                "meta": "iPhone・iPad対応 / オフライン / アカウント不要",
                "hero_alt": "PlanOnceの予算カテゴリ画面",
                "section_kicker": "お金の管理を自分の手元へ",
                "section_title": "毎月の支払いではなく、<em>一度の計画で続ける。</em>",
                "features": [
                    ("予算をゼロまで振り分ける", "収入のすべてに役割を持たせ、残りのお金を見える化。"),
                    ("3タップで支出記録", "カテゴリを選ぶ、金額を入れる、保存する。銀行同期を待たない。"),
                    ("端末内で完結", "銀行ログイン、クラウドアカウント、追跡なし。データはiPhoneに保存。"),
                ],
                "gallery_title": "お金の流れを、<em>実際の画面で確認。</em>",
                "gallery_alts": ["予算カテゴリと残額", "支出履歴", "口座一覧", "設定画面"],
                "price_kicker": "PlanOnce Pro",
                "price_title": "サブスクなし。<em>買い切り ¥1,500。</em>",
                "price_body": "基本機能は無料。Proの一度の購入で、カテゴリ・口座・目標の上限解除、レポート、YNAB CSVインポートを利用できます。",
                "price_points": ["銀行ログイン不要", "すべてのデータを端末内に保存", "自動更新なしの買い切り"],
                "cta": "App Storeで見る",
                "footer": "PlanOnceで予算を始める",
            },
            "en": {
                "lang": "en",
                "label": "English",
                "kicker": "Zero-based budgeting, bought once",
                "headline": "Give every dollar<br><em>a job.</em>",
                "lead": "Assign income to categories, log spending in three taps, and keep your money data on your device—no bank login, no subscription.",
                "meta": "For iPhone & iPad / Works offline / No account",
                "hero_alt": "PlanOnce budget categories screen",
                "section_kicker": "Keep your money in your hands",
                "section_title": "Make one plan, then <em>keep using it without a monthly fee.</em>",
                "features": [
                    ("Assign every dollar", "Give your income a job until the unassigned balance reaches zero."),
                    ("Log spending in 3 taps", "Choose a category, enter the amount, save. No bank sync to wait for."),
                    ("Keep it on your device", "No bank login, cloud account, or tracking. Your data stays on your iPhone."),
                ],
                "gallery_title": "See your money flow <em>in the real screens.</em>",
                "gallery_alts": ["Budget categories and remaining money", "Transaction history", "Accounts list", "Settings screen"],
                "price_kicker": "PlanOnce Pro",
                "price_title": "No subscription.<br><em>One-time $14.99.</em>",
                "price_body": "Budgeting basics are free. One purchase unlocks unlimited categories, accounts, goals, reports, and YNAB CSV import.",
                "price_points": ["No bank login required", "Everything stays on your device", "One purchase, no auto-renewal"],
                "cta": "View on the App Store",
                "footer": "Start budgeting with PlanOnce",
            },
            "de": {
                "lang": "de",
                "label": "Deutsch",
                "kicker": "Budgetplanung ohne Abo",
                "headline": "Jeder Euro bekommt<br><em>eine Aufgabe.</em>",
                "lead": "Einkommen Kategorien zuweisen, Ausgaben in drei Schritten erfassen und alles auf dem Gerät behalten – ohne Bank-Login und ohne Abo.",
                "meta": "Für iPhone & iPad / Offline / Kein Konto nötig",
                "hero_alt": "PlanOnce Budget-Kategorien",
                "section_kicker": "Dein Geld bleibt bei dir",
                "section_title": "Einmal planen und <em>ohne Monatsgebühr weitermachen.</em>",
                "features": [
                    ("Jeden Euro einplanen", "Verteile dein Einkommen, bis kein ungeplanter Betrag übrig bleibt."),
                    ("Ausgaben in 3 Schritten", "Kategorie wählen, Betrag eingeben, speichern. Keine Banksynchronisation."),
                    ("Alles bleibt auf dem Gerät", "Kein Bank-Login, kein Cloud-Konto, kein Tracking. Deine Daten bleiben auf dem iPhone."),
                ],
                "gallery_title": "Dein Geld im Blick – <em>mit echten Screenshots.</em>",
                "gallery_alts": ["Budget-Kategorien und Restbetrag", "Transaktionsliste", "Kontenübersicht", "Einstellungen"],
                "price_kicker": "PlanOnce Pro",
                "price_title": "Kein Abo.<br><em>Einmalig 14,99 €.</em>",
                "price_body": "Die Grundlagen sind kostenlos. Ein Kauf schaltet unbegrenzte Kategorien, Konten, Ziele, Berichte und den YNAB-CSV-Import frei.",
                "price_points": ["Kein Bank-Login nötig", "Alles bleibt auf deinem Gerät", "Ein Kauf ohne automatische Verlängerung"],
                "cta": "Im App Store ansehen",
                "footer": "Mit PlanOnce starten",
            },
        },
        "gallery": {
            "all": ["planonce-budget.png", "planonce-transactions.png", "planonce-accounts.png", "planonce-settings.png"],
        },
    },
    "leafmark": {
        "name": "Leafmark",
        "icon": "leafmark-icon.png",
        "theme": "leaf",
        "store": "https://apps.apple.com/app/id6781045740",
        "support": "https://atani.github.io/leafmark-app/support.html",
        "og_image": "leafmark-og.png",
        "locales": {
            "ja": {
                "lang": "ja",
                "label": "日本語",
                "kicker": "買い切りのプライベートEPUBリーダー",
                "headline": "ハイライトを、<br><em>自分のMarkdownへ。</em>",
                "lead": "DRMフリーのEPUBを読み、ハイライトとノートをMarkdownへ書き出せます。アカウント、広告、行動追跡はありません。",
                "meta": "iPhone・iPad対応 / オフライン / アカウント不要",
                "hero_alt": "Leafmarkのハイライト一覧とMarkdown書き出し",
                "section_kicker": "Your highlights are yours",
                "section_title": "読む場所はLeafmark。<em>残す場所は自分で選べる。</em>",
                "features": [
                    ("ハイライトを書き出す", "4色のハイライトとノートを、ObsidianやNotionで使えるMarkdownへ。"),
                    ("一度の購入で使い続ける", "Leafmark Proは買い切り。自動更新されるサブスクリプションはありません。"),
                    ("読書データを端末内に", "アカウント、広告、分析SDKなし。本と注釈は自分の端末に残ります。"),
                ],
                "gallery_title": "読書から書き出しまで、<em>実際の画面で確認。</em>",
                "gallery_alts": ["ハイライトとノートの一覧", "端末内のEPUBライブラリ", "読書時間と連続記録", "テーマ・文字・レイアウト設定"],
                "price_kicker": "Leafmark Pro",
                "price_title": "読むのは無料。<br><em>注釈ワークフローは一度の購入。</em>",
                "price_body": "EPUBの読み込みと閲覧は無料です。無料版でもMarkdown書き出しを1回試せます。Leafmark Proの買い切りで、無制限のハイライト、Markdown書き出し、読書統計を解放します。",
                "price_points": ["無料で読み心地を試せる", "Markdown書き出しを購入前に確認", "自動更新なしの買い切り"],
                "cta": "App Storeで見る",
                "footer": "ハイライトを、自分の手元に残す",
            },
            "en": {
                "lang": "en",
                "label": "English",
                "kicker": "A private EPUB reader you buy once",
                "headline": "Your highlights<br><em>are yours.</em>",
                "lead": "Read DRM-free EPUBs, annotate in four colors, and export your highlights and notes to clean Markdown. No account, ads, analytics, or cloud lock-in.",
                "meta": "For iPhone & iPad / Works offline / No account",
                "hero_alt": "Leafmark highlights ready to export to Markdown",
                "section_kicker": "Portable reading notes",
                "section_title": "Read closely. <em>Keep every note portable.</em>",
                "features": [
                    ("Export clean Markdown", "Move highlights and notes into Obsidian, Notion, or any plain-text workflow."),
                    ("Buy once", "Leafmark Pro is a one-time purchase. There is no auto-renewing subscription."),
                    ("Keep reading private", "No account, ads, or analytics. Your books and reading data stay on your device."),
                ],
                "gallery_title": "See the complete workflow, <em>in the real app.</em>",
                "gallery_alts": ["Highlights and notes ready to export", "Your on-device EPUB library", "Reading time and streak statistics", "Themes, typography, and layout controls"],
                "price_kicker": "Leafmark Pro",
                "price_title": "Read for free.<br><em>Unlock the workflow once for $9.99.</em>",
                "price_body": "Import and read EPUBs for free, with one free Markdown export to test the result. A single Leafmark Pro purchase unlocks unlimited highlights, unlimited Markdown export, and reading statistics.",
                "price_points": ["Try the reading experience for free", "Preview Markdown export before buying", "One purchase, no auto-renewal"],
                "cta": "View on the App Store",
                "footer": "Keep your reading notes yours",
            },
        },
        "gallery": {
            "all": ["leafmark-highlights.png", "leafmark-library.png", "leafmark-statistics.png", "leafmark-appearance.png"],
        },
    },
    "dotto": {
        "name": "Dotto",
        "icon": "dotto-icon.png",
        "theme": "orange",
        "store": "https://apps.apple.com/jp/app/id6782310741",
        "locales": {
            "ja": {
                "lang": "ja",
                "label": "日本語",
                "kicker": "1画面の買い切りToDo",
                "headline": "やることを、<em>3秒で書く。</em>",
                "lead": "タスクを一画面に。必要なときだけ通知。サブスクなし、広告なし、買い切りでずっと使えます。",
                "meta": "iPhone対応 / リマインダー / ウィジェット",
                "hero_alt": "Dottoのタスク一覧とリマインダー",
                "section_kicker": "シンプルに、忘れない",
                "section_title": "機能を増やすより、<em>今日やることを終わらせる。</em>",
                "features": [
                    ("一画面で見渡す", "開いた瞬間に、今日のタスクと残り件数が分かる。"),
                    ("通知をつける", "買い物、電話、締切。必要なタスクだけリマインド。"),
                    ("繰り返しとウィジェット", "毎日の用事を繰り返しにして、ホーム画面から確認。"),
                ],
                "gallery_title": "Dottoの使い心地を、<em>実画面で見る。</em>",
                "gallery_alts": ["Dottoのタスク一覧", "空のタスク画面", "リマインダー付きタスク"],
                "price_kicker": "Dotto Pro",
                "price_title": "サブスクなし。広告なし。<em>買い切り ¥800。</em>",
                "price_body": "無料で10タスク・3リマインダー/日まで。Proの一度の購入でタスク、通知、繰り返し、ウィジェット、テーマが無制限になります。",
                "price_points": ["入力は一画面で完結", "必要な通知だけ", "自動更新なしの買い切り"],
                "cta": "App Storeで見る",
                "footer": "Dottoで今日を整える",
            },
            "en": {
                "lang": "en",
                "label": "English",
                "kicker": "A one-screen todo app you buy once",
                "headline": "Write it down<br><em>in three seconds.</em>",
                "lead": "Keep tasks on one calm screen. Add a reminder when it matters. No subscription, no ads, yours after one purchase.",
                "meta": "For iPhone / Reminders / Home screen widget",
                "hero_alt": "Dotto task list with reminders",
                "section_kicker": "Simple, so you remember",
                "section_title": "Less feature hunting. <em>More finished tasks.</em>",
                "features": [
                    ("See today at a glance", "Open Dotto and see today’s tasks and remaining count immediately."),
                    ("Remind only what matters", "Set a reminder for the groceries, the call, or the deadline you cannot miss."),
                    ("Repeat and widget", "Make routine tasks recurring and check your list from the Home Screen."),
                ],
                "gallery_title": "A closer look at <em>Dotto in use.</em>",
                "gallery_alts": ["Dotto task list", "Empty task screen", "Tasks with reminders"],
                "price_kicker": "Dotto Pro",
                "price_title": "No subscription. No ads.<br><em>$4.99, once.</em>",
                "price_body": "Free includes 10 tasks and three reminders per day. One purchase unlocks unlimited tasks, reminders, recurring tasks, widgets, and themes.",
                "price_points": ["One calm screen", "Reminders when you need them", "One purchase, no auto-renewal"],
                "cta": "View on the App Store",
                "footer": "Make today lighter with Dotto",
            },
            "de": {
                "lang": "de",
                "label": "Deutsch",
                "kicker": "Die To-do-Liste zum Einmalkauf",
                "headline": "Aufschreiben,<br><em>in drei Sekunden.</em>",
                "lead": "Alle Aufgaben auf einem ruhigen Bildschirm. Erinnerungen nur, wenn sie wichtig sind. Kein Abo, keine Werbung.",
                "meta": "Für iPhone / Erinnerungen / Widget",
                "hero_alt": "Dotto Aufgabenliste mit Erinnerungen",
                "section_kicker": "Einfach, damit du dranbleibst",
                "section_title": "Weniger suchen. <em>Mehr erledigen.</em>",
                "features": [
                    ("Heute sofort überblicken", "Dotto öffnen und Aufgaben und Restanzahl direkt sehen."),
                    ("Nur Wichtiges erinnern", "Erinnerungen für Einkauf, Anruf oder Frist setzen – genau dann, wenn du sie brauchst."),
                    ("Wiederholen und Widget", "Routineaufgaben wiederholen lassen und die Liste vom Home-Bildschirm öffnen."),
                ],
                "gallery_title": "Dotto im Alltag – <em>mit echten Screenshots.</em>",
                "gallery_alts": ["Dotto Aufgabenliste", "Leere Aufgabenansicht", "Aufgaben mit Erinnerungen"],
                "price_kicker": "Dotto Pro",
                "price_title": "Kein Abo. Keine Werbung.<br><em>Einmalig 5,99 €.</em>",
                "price_body": "Kostenlos sind 10 Aufgaben und drei Erinnerungen pro Tag. Ein Kauf schaltet unbegrenzte Aufgaben, Erinnerungen, Wiederholungen, Widgets und Themes frei.",
                "price_points": ["Ein ruhiger Bildschirm", "Erinnerungen, wenn du sie brauchst", "Ein Kauf ohne Verlängerung"],
                "cta": "Im App Store ansehen",
                "footer": "Mit Dotto leichter durch den Tag",
            },
        },
        "gallery": {
            "all": ["dotto-tasks.png", "dotto-empty.png", "dotto-reminders.png"],
        },
    },
}


def _gallery(app, locale):
    return app["gallery"].get(locale, app["gallery"].get("all", []))


def render_promo_page(slug, locale):
    app = PROMO_APPS[slug]
    copy = app["locales"][locale]
    gallery = _gallery(app, locale)
    links = []
    for code, locale_copy in app["locales"].items():
        target = f"/{slug}/" if code == "ja" else f"/{slug}/{code}/"
        current = " aria-current=\"page\"" if code == locale else ""
        links.append(f'<a href="{target}"{current}>{escape(locale_copy["label"])}</a>')
    feature_cards = "".join(
        f'<article class="promo-feature"><span>0{index}</span><h3>{escape(title)}</h3><p>{escape(body)}</p></article>'
        for index, (title, body) in enumerate(copy["features"], 1)
    )
    screenshots = "".join(
        f'<figure><img src="/assets/{escape(filename)}" alt="{escape(alt)}" loading="lazy"><figcaption>{escape(alt)}</figcaption></figure>'
        for filename, alt in zip(gallery, copy["gallery_alts"])
    )
    points = "".join(f"<li>{escape(point)}</li>" for point in copy["price_points"])
    hero = gallery[0]
    store = copy.get("store", app["store"])
    support = copy.get("support", app.get("support", "/support/"))
    canonical_path = f"/{slug}/" if locale == "ja" else f"/{slug}/{locale}/"
    canonical = f"https://atani.lolipop-now.app{canonical_path}"
    alternates = "".join(
        f'  <link rel="alternate" hreflang="{escape(code)}" href="https://atani.lolipop-now.app/{escape(slug)}/{"" if code == "ja" else escape(code) + "/"}">\n'
        for code in app["locales"]
    )
    alternates += f'  <link rel="alternate" hreflang="x-default" href="https://atani.lolipop-now.app/{escape(slug)}/">\n'
    og_image = f'https://atani.lolipop-now.app/assets/{app.get("og_image", app["icon"])}'
    title = f'{app["name"]} — {copy["headline"].replace("<br>", " ").replace("<em>", "").replace("</em>", "")}'
    description = copy["lead"]
    return f'''<!doctype html>
<html lang="{escape(copy["lang"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="{escape(og_image)}">
  <meta name="twitter:card" content="summary_large_image">
{alternates.rstrip()}
  <link rel="icon" href="/assets/{escape(app["icon"])}">
  <link rel="stylesheet" href="/css/apps.css">
</head>
<body class="promo-page promo-{escape(app["theme"])}">
  <header class="promo-header">
    <a class="promo-brand" href="/">ATANI / <strong>{escape(app["name"])}</strong></a>
    <nav class="promo-languages" aria-label="Language">{"".join(links)}</nav>
  </header>
  <main>
    <section class="promo-hero">
      <div class="promo-hero__copy">
        <p class="promo-kicker">{escape(copy["kicker"])}</p>
        <h1>{copy["headline"]}</h1>
        <p class="promo-lead">{escape(copy["lead"])}</p>
        <div class="promo-actions"><a class="promo-button" href="{escape(store)}">{escape(copy["cta"])}</a><a class="promo-text-link" href="#features">{'機能を見る' if locale == 'ja' else 'See the features'} <span>↓</span></a></div>
        <p class="promo-meta">{escape(copy["meta"])}</p>
      </div>
      <div class="promo-hero__visual"><div class="promo-device"><img src="/assets/{escape(hero)}" alt="{escape(copy["hero_alt"])}"></div></div>
    </section>
    <section class="promo-proof" aria-label="Highlights"><span>{'実際のApp Store用スクリーンショット' if locale == 'ja' else 'Real App Store screenshots'}</span><span>{'買い切り中心の価格設計' if locale == 'ja' else 'A clear one-time value proposition'}</span><span>{'端末内で完結' if locale == 'ja' else 'Designed to stay on your device'}</span></section>
    <section class="promo-section promo-section--light" id="features">
      <p class="promo-kicker">{escape(copy["section_kicker"])}</p>
      <h2>{copy["section_title"]}</h2>
      <div class="promo-features">{feature_cards}</div>
    </section>
    <section class="promo-section promo-screens">
      <p class="promo-kicker">{'画面でわかること' if locale == 'ja' else 'Inside the app'}</p>
      <h2>{copy["gallery_title"]}</h2>
      <div class="promo-gallery">{screenshots}</div>
    </section>
    <section class="promo-section promo-price">
      <div><p class="promo-kicker">{escape(copy["price_kicker"])}</p><h2>{copy["price_title"]}</h2><p>{escape(copy["price_body"])}</p></div>
      <div class="promo-price__card"><ul>{points}</ul><a class="promo-button promo-button--dark" href="{escape(store)}">{escape(copy["cta"])}</a></div>
    </section>
    <section class="promo-final"><p class="promo-kicker">{escape(app["name"])}</p><h2>{escape(copy["footer"])}</h2><a class="promo-button promo-button--light" href="{escape(store)}">{escape(copy["cta"])}</a></section>
  </main>
  <footer class="promo-footer"><a href="{escape(support)}">{'サポート・プライバシー' if locale == 'ja' else 'Support & privacy'}</a><span>© Atani</span></footer>
</body>
</html>
'''
