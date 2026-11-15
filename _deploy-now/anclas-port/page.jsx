import Image from "next/image";

const APP_STORE_URL =
  "https://apps.apple.com/jp/app/%E3%82%A2%E3%83%B3%E3%82%AF%E3%83%A9%E3%82%B9-port/id6786095771";
const OFUSE_URL = process.env.NEXT_PUBLIC_OFUSE_URL ?? "https://ofuse.me/akirataniwaki";

const Arrow = () => <span aria-hidden="true">↗</span>;

function AppStoreButton({ placement }) {
  return (
    <a
      className="button button-primary"
      href={`${APP_STORE_URL}?pt=126806733&ct=landing-${placement}&mt=8`}
      target="_blank"
      rel="noreferrer"
    >
      <span className="apple" aria-hidden="true">●</span>
      <span><small>App Storeから</small>無料でダウンロード</span>
      <Arrow />
    </a>
  );
}

function PhonePreview() {
  return (
    <div className="phone-wrap" aria-label="アンクラスPortのホーム画面イメージ">
      <div className="orbit orbit-one" />
      <div className="orbit orbit-two" />
      <div className="phone">
        <div className="island" />
        <div className="phone-screen">
          <div className="app-head">
            <span className="app-brand"><Image src="/assets/anclas-port-landing/emblem.png" alt="" width={512} height={512} /><b>アンクラス Port</b></span>
            <span>•••</span>
          </div>
          <p className="screen-label">NEXT MATCH</p>
          <div className="match-card">
            <div className="date-chip"><b>08.30</b><span>SUN</span></div>
            <div className="match-info">
              <span>九州女子サッカーリーグ</span>
              <strong>福岡J・アンクラス</strong>
              <em>vs</em>
              <strong>東海大福岡</strong>
              <small>12:00 KICK OFF</small>
            </div>
          </div>
          <div className="quick-row">
            <div><span>⚓</span><small>日程</small></div>
            <div><span>♜</span><small>順位</small></div>
            <div><span>☆</span><small>推し</small></div>
          </div>
          <p className="screen-label latest">LATEST RESULT</p>
          <div className="result-card"><span>WIN</span><strong>4 - 0</strong><small>試合詳細を見る →</small></div>
          <Image className="character" src="/assets/anclas-port-landing/character.png" alt="" width={940} height={940} />
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="アンクラスPort トップへ">
          <Image src="/assets/anclas-port-landing/emblem.png" alt="" width={512} height={512} priority />
          <span className="brand-copy"><strong>アンクラス Port</strong><small>福岡J・アンクラス公認アプリ</small></span>
        </a>
        <nav aria-label="メインナビゲーション">
          <a href="#features">できること</a>
          <a href="#support">応援する</a>
          <a className="nav-download" href={APP_STORE_URL} target="_blank" rel="noreferrer">ダウンロード <Arrow /></a>
        </nav>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span /> 福岡J・アンクラス公認アプリ</p>
          <h1>アンクラスの今が集まる、<br /><em>サポーターの母港。</em></h1>
          <p className="hero-lead">試合も、選手も、ニュースも。応援したい日に迷わないための情報を、ひとつのアプリにまとめました。</p>
          <div className="hero-actions">
            <AppStoreButton placement="hero" />
            <a className="text-link" href="#features">できることを見る <span aria-hidden="true">↓</span></a>
          </div>
          <p className="fine-print">iPhone対応 · 無料 · 広告なし · アカウント登録不要</p>
        </div>
        <PhonePreview />
      </section>

      <section className="manifesto">
        <p>ALL THINGS ANCLAS, IN ONE PORT.</p>
        <h2>応援のそばに、<br />いつでもアンクラスを。</h2>
        <div className="manifesto-copy">
          <p>次の試合はいつ？ 今の順位は？ 推しの選手はどんな人？</p>
          <p>それぞれの場所に散らばっていた情報を、見やすく、すぐ手に取れる形にしました。</p>
        </div>
      </section>

      <section className="features section" id="features">
        <div className="section-heading">
          <p className="eyebrow light"><span /> WHAT YOU CAN DO</p>
          <h2>知るほど、<br />応援がもっと楽しくなる。</h2>
        </div>
        <div className="feature-grid">
          <article className="feature feature-large">
            <span className="feature-no">01</span>
            <div><p>試合を追う</p><h3>日程・結果・順位を<br />ひとつの場所で。</h3><small>次の試合を開いてすぐ確認。会場やキックオフ時刻、今季の結果も迷わず見つかります。</small></div>
            <div className="mini-match"><span>NEXT</span><strong>08.30 <i>SUN</i></strong><p>アンクラス <b>VS</b> 東海大福岡</p></div>
          </article>
          <article className="feature">
            <span className="feature-no">02</span>
            <div className="player-stack">
              <div>3</div><div>14</div><div>21</div>
            </div>
            <p>選手を知る</p><h3>推しの選手を、<br />もっと近くに。</h3><small>プロフィールや出場数、得点、誕生日をチェック。お気に入りの選手はホームに表示できます。</small>
          </article>
          <article className="feature feature-accent">
            <span className="feature-no">03</span>
            <div className="widget-demo"><Image src="/assets/anclas-port-landing/app-icon.png" alt="" width={1024} height={1024} /><span><small>NEXT MATCH</small><b>8/30 12:00</b></span></div>
            <p>見逃さない</p><h3>ウィジェットと通知で、<br />試合の日を忘れない。</h3><small>ホーム画面から次の試合を確認。お知らせのタイミングも選べます。</small>
          </article>
        </div>
      </section>

      <section className="support section" id="support">
        <div className="support-card">
          <div className="support-copy">
            <p className="eyebrow"><span /> KEEP THE PORT OPEN</p>
            <h2>あなたのひとことが、<br />この港を動かす力になる。</h2>
            <p>アンクラスPortは、ひとりのファンがつくり、無料・広告なしで運営しています。「この機能が好き」「次はこんなことができたら」。そんな声をOFUSEのファンレターで届けてもらえるとうれしいです。</p>
            <a className="button button-ofuse" href={OFUSE_URL} target="_blank" rel="noreferrer">
              OFUSEでファンレターを送る <Arrow />
            </a>
            <small>支援付き・メッセージのみ、どちらでも送れます。支援はアプリの開発・運営に活用します。クラブへの寄付ではありません。</small>
          </div>
          <div className="letter" aria-hidden="true">
            <div className="stamp"><Image src="/assets/anclas-port-landing/character.png" alt="" width={940} height={940} /></div>
            <span>TO: ANCLAS PORT</span>
            <p>これからも、<br />応援しています。</p>
            <i>♡</i>
          </div>
        </div>
      </section>

      <section className="closing section">
        <Image src="/assets/anclas-port-landing/emblem.png" alt="福岡J・アンクラス エンブレム" width={512} height={512} />
        <p>試合の日も、そうでない日も。</p>
        <h2>アンクラスPortから、<br />応援をはじめよう。</h2>
        <AppStoreButton placement="footer" />
      </section>

      <footer>
        <div className="footer-brand"><Image src="/assets/anclas-port-landing/emblem.png" alt="" width={512} height={512} /><strong>アンクラス Port</strong></div>
        <div className="footer-links">
          <a href="https://atani.github.io/anclas-port/#contact">サポート</a>
          <a href="https://atani.github.io/anclas-port/privacy/">プライバシーポリシー</a>
          <a href="https://github.com/atani/anclas-port" target="_blank" rel="noreferrer">GitHub <Arrow /></a>
        </div>
        <p>© 2026 Akira Taniwaki</p>
      </footer>
    </main>
  );
}
