export const MEASUREMENT_ID = 'G-P79WP49S4Z';
export const CONSENT_KEY = 'support-analytics-consent-v1';
const CONSENT_LIFETIME_MS = 30 * 24 * 60 * 60 * 1000;
const SUPPORT_URL = 'https://atani.lolipop-now.app/support/';
const DENIED = { analytics_storage: 'denied', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' };
const CAMPAIGNS = {
  utm_source: ['x', 'note'],
  utm_medium: ['social', 'article', 'profile'],
  utm_campaign: ['202609-support'],
  utm_content: ['experiment-a', 'experiment-b', 'experiment-c', 'profile', 'qa'],
};
const REFERRERS = ['x.com', 't.co', 'note.com', 'atani.github.io', 'atani.lolipop-now.app', 'www.google.com', 'www.google.co.jp'];

export function readConsent(storage, now = Date.now()) {
  try {
    const saved = JSON.parse(storage.getItem(CONSENT_KEY));
    if (!['granted', 'denied'].includes(saved?.choice)) return null;
    if (!Number.isFinite(saved.at) || saved.at > now || now - saved.at >= CONSENT_LIFETIME_MS) return null;
    return saved.choice;
  } catch { return null; }
}

export function saveConsent(storage, choice, now = Date.now()) {
  if (!['granted', 'denied'].includes(choice)) return false;
  try {
    storage.setItem(CONSENT_KEY, JSON.stringify({ choice, at: now }));
    return true;
  } catch { return false; }
}

export function pageContext(href, referrer) {
  const incoming = new URL(href);
  const clean = new URL(SUPPORT_URL);
  for (const [key, allowed] of Object.entries(CAMPAIGNS)) {
    const value = incoming.searchParams.get(key);
    if (allowed.includes(value)) clean.searchParams.set(key, value);
  }
  let safeReferrer = '';
  try {
    const source = new URL(referrer);
    if (source.protocol === 'https:' && REFERRERS.includes(source.hostname)) safeReferrer = source.origin + '/';
  } catch { /* Direct visits have no referrer. */ }
  return { page_location: clean.href, page_referrer: safeReferrer, page_title: 'アンクラスPortの応援方法' };
}

export function supportEvent(kind, position, href) {
  if (!['membership', 'single', 'letter'].includes(kind)) return null;
  if (!['hero', 'cards', 'final'].includes(position)) return null;
  const destination = kind === 'membership' ? 'https://ofuse.me/memberships/4761' : 'https://ofuse.me/akirataniwaki';
  if (href !== destination) return null;
  return { name: `support_${kind}_click`, parameters: { support_position: position } };
}

export function isProductionSupportPage(href) {
  const url = new URL(href);
  return url.origin === new URL(SUPPORT_URL).origin && ['/support/', '/support/index.html'].includes(url.pathname);
}

export function ownedAnalyticsCookies(cookieHeader) {
  return cookieHeader.split(';').map(cookie => cookie.trim().split('=')[0])
    .filter(name => /^support__?ga(?:_|$)/.test(name));
}

// Consent is our boundary: the Google script itself is absent until an explicit grant.
export function createTracker({ send, load, stop, context, enabled, debug = false }) {
  let hasStarted = false;
  let isGranted = false;
  let hasStopped = false;
  return {
    consent(choice) {
      isGranted = choice === 'granted';
      if (!isGranted) {
        if (hasStarted && !hasStopped) { hasStopped = true; stop(); }
        return;
      }
      if (hasStarted || !enabled) return;
      hasStarted = true;
      send('consent', 'default', DENIED);
      send('consent', 'update', { ...DENIED, analytics_storage: 'granted' });
      send('js', new Date());
      send('config', MEASUREMENT_ID, {
        ...context, send_page_view: false,
        allow_google_signals: false, allow_ad_personalization_signals: false,
        cookie_domain: 'none', cookie_prefix: 'support', cookie_path: '/',
        cookie_expires: CONSENT_LIFETIME_MS / 1000, cookie_update: false,
        cookie_flags: 'SameSite=Lax;Secure', ...(debug ? { debug_mode: true } : {}),
      });
      send('event', 'page_view', context);
      load();
    },
    click(kind, position, href) {
      if (!isGranted || !hasStarted || hasStopped) return;
      const event = supportEvent(kind, position, href);
      if (event) send('event', event.name, { ...context, ...event.parameters });
    },
  };
}

function boot() {
  const panel = document.getElementById('analytics-choice');
  const settings = document.getElementById('analytics-settings');
  const status = document.getElementById('analytics-status');
  if (!panel || !settings || !status) return;
  let storage;
  try { storage = window.localStorage; } catch { /* A blocked store must not break the page. */ }
  const tracker = createTracker({
    enabled: isProductionSupportPage(location.href),
    debug: new URL(location.href).searchParams.get('analytics_debug') === '1',
    context: pageContext(location.href, document.referrer),
    send: function () { (window.dataLayer ||= []).push(arguments); },
    load() {
      const script = document.createElement('script');
      script.async = true;
      script.src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`;
      script.referrerPolicy = 'no-referrer';
      document.head.append(script);
    },
    stop() {
      window[`ga-disable-${MEASUREMENT_ID}`] = true;
      for (const name of ownedAnalyticsCookies(document.cookie)) {
        document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax; Secure`;
      }
      // Reload unloads all Google listeners, including queued automatic engagement events.
      location.reload();
    },
  });
  const initial = readConsent(storage);
  panel.hidden = initial !== null;
  settings.hidden = false;
  const describeChoice = choice => choice === 'granted' ? '許可する' : choice === 'denied' ? '許可しない' : '未選択（計測していません）';
  status.textContent = `現在の選択：${describeChoice(initial)}`;
  tracker.consent(initial);
  let returnFocus = null;
  settings.addEventListener('click', () => {
    returnFocus = settings;
    panel.hidden = false;
    panel.scrollIntoView({ behavior: 'instant', block: 'start' });
    panel.querySelector('button').focus({ preventScroll: true });
  });
  panel.addEventListener('click', event => {
    const button = event.target.closest('button[data-analytics-choice]');
    if (!button) return;
    const choice = button.dataset.analyticsChoice;
    const isSaved = saveConsent(storage, choice);
    tracker.consent(choice);
    panel.hidden = true;
    status.textContent = `現在の選択：${describeChoice(choice)}${isSaved ? '' : '（保存できないため、このページを開いている間のみ）'}`;
    if (returnFocus) returnFocus.focus();
    else {
      const heading = document.getElementById('story-title');
      heading.setAttribute('tabindex', '-1');
      heading.focus({ preventScroll: true });
    }
  });
  const clickSupport = event => {
    if (event.defaultPrevented || (event.type === 'auxclick' && event.button !== 1)) return;
    const link = event.target.closest?.('a[data-support-kind]');
    if (link) tracker.click(link.dataset.supportKind, link.dataset.supportPosition, link.href);
  };
  document.addEventListener('click', clickSupport);
  document.addEventListener('auxclick', clickSupport);
  window.addEventListener('storage', event => {
    if ((event.key === CONSENT_KEY || event.key === null) && readConsent(storage) !== 'granted') tracker.consent('denied');
  });
  // A back/forward-cache restoration must honor revocation made in another tab.
  window.addEventListener('pageshow', event => {
    if (event.persisted && readConsent(storage) !== 'granted') tracker.consent('denied');
  });
}

if (typeof document !== 'undefined') boot();
