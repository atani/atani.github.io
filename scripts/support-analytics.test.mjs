import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { MEASUREMENT_ID, CONSENT_KEY, readConsent, saveConsent, pageContext, supportEvent, isProductionSupportPage, ownedAnalyticsCookies, createTracker } from '../js/support-analytics.mjs';

const supportUrl = 'https://atani.lolipop-now.app/support/';
const membershipUrl = 'https://ofuse.me/memberships/4761';
const letterUrl = 'https://ofuse.me/akirataniwaki';
const lifetime = 30 * 24 * 60 * 60 * 1000;
function memoryStorage(raw = null) {
  return { getItem: () => raw, setItem: (key, value) => { assert.equal(key, CONSENT_KEY); raw = value; } };
}
function recordingTracker(options = {}) {
  const commands = [];
  let loads = 0;
  let stops = 0;
  const tracker = createTracker({
    enabled: true, context: pageContext(supportUrl, ''),
    send: (...args) => commands.push(args), load: () => loads++, stop: () => stops++, ...options,
  });
  return { tracker, commands, get loads() { return loads; }, get stops() { return stops; } };
}

test('consent is opt-in and storage errors never grant permission', () => {
  for (const raw of [null, '', '{', '{}', '{"choice":"yes","at":100}', '{"choice":"granted"}', '{"choice":"granted","at":"100"}']) {
    assert.equal(readConsent(memoryStorage(raw), 100), null);
  }
  assert.equal(readConsent(undefined), null);
  assert.equal(saveConsent(undefined, 'granted'), false);
  assert.equal(saveConsent(memoryStorage(), 'unexpected'), false);
});
test('both choices round-trip and expire at exactly 30 days, never accepting future timestamps', () => {
  for (const choice of ['granted', 'denied']) {
    const storage = memoryStorage();
    assert.equal(saveConsent(storage, choice, 100), true);
    assert.equal(readConsent(storage, 100), choice);
    assert.equal(readConsent(storage, 100 + lifetime - 1), choice);
    assert.equal(readConsent(storage, 100 + lifetime), null);
    assert.equal(readConsent(storage, 99), null);
  }
});
test('page context preserves only the known experiment tags and removes other URL data', () => {
  const context = pageContext(supportUrl + '?utm_source=x&utm_medium=social&utm_campaign=202609-support&utm_content=experiment-a&email=private@example.test&gclid=secret&analytics_debug=1#private', 'https://note.com/private/path?email=private');
  assert.equal(context.page_location, supportUrl + '?utm_source=x&utm_medium=social&utm_campaign=202609-support&utm_content=experiment-a');
  assert.equal(context.page_referrer, 'https://note.com/');
  assert.equal(pageContext(supportUrl + '?utm_source=private&utm_content=person-name', '').page_location, supportUrl);
});
test('referrers never include unknown domains, credentials, path, query or fragments', () => {
  for (const referrer of ['', 'invalid', 'http://note.com/', 'https://note.com.evil.test/', 'https://private.example.test/']) {
    assert.equal(pageContext(supportUrl, referrer).page_referrer, '');
  }
  assert.equal(pageContext(supportUrl, 'https://username:password@x.com/private?q=secret#private').page_referrer, 'https://x.com/');
});
test('only the production support page is eligible for collection', () => {
  assert.equal(isProductionSupportPage(supportUrl), true);
  assert.equal(isProductionSupportPage(supportUrl + 'index.html?analytics_debug=1'), true);
  for (const url of ['http://127.0.0.1:8765/support/', 'https://atani.github.io/support/', 'https://atani.lolipop-now.app/', 'https://atani.lolipop-now.app.evil.test/support/']) {
    assert.equal(isProductionSupportPage(url), false);
  }
});
test('all three support intentions are distinct, with validated placement and destination', () => {
  assert.equal(supportEvent('membership', 'cards', membershipUrl).name, 'support_membership_click');
  assert.equal(supportEvent('single', 'final', letterUrl).name, 'support_single_click');
  assert.equal(supportEvent('letter', 'hero', letterUrl).name, 'support_letter_click');
  assert.equal(supportEvent('purchase', 'cards', membershipUrl), null);
  assert.equal(supportEvent('membership', 'private-name', membershipUrl), null);
  assert.equal(supportEvent('membership', 'cards', letterUrl), null);
});
test('unknown or denied consent sends nothing and never loads Google', () => {
  const recording = recordingTracker();
  recording.tracker.consent(null);
  recording.tracker.click('membership', 'cards', membershipUrl);
  recording.tracker.consent('denied');
  assert.deepEqual(recording.commands, []);
  assert.equal(recording.loads, 0);
});
test('grant configures privacy before loading and emits only one page view per document', () => {
  const recording = recordingTracker();
  recording.tracker.consent('granted');
  recording.tracker.consent('granted');
  assert.equal(recording.loads, 1);
  assert.equal(recording.commands.filter(command => command[1] === 'page_view').length, 1);
  assert.deepEqual(recording.commands[0].slice(0, 2), ['consent', 'default']);
  assert.equal(recording.commands[0][2].analytics_storage, 'denied');
  assert.equal(recording.commands[1][2].analytics_storage, 'granted');
  assert.equal(recording.commands[1][2].ad_storage, 'denied');
  const config = recording.commands.find(command => command[0] === 'config');
  assert.equal(config[1], MEASUREMENT_ID);
  assert.equal(config[2].send_page_view, false);
  assert.equal(config[2].allow_google_signals, false);
  assert.equal(config[2].allow_ad_personalization_signals, false);
  assert.equal(config[2].cookie_domain, 'none');
  assert.equal(config[2].cookie_expires, lifetime / 1000);
  assert.equal(config[2].debug_mode, undefined);
});
test('clicks are not confused with completed joins; revocation stops even a pending tag', () => {
  const recording = recordingTracker();
  recording.tracker.consent('granted');
  recording.tracker.click('membership', 'cards', membershipUrl);
  assert.equal(recording.commands.at(-1)[1], 'support_membership_click');
  const count = recording.commands.length;
  recording.tracker.consent('denied');
  recording.tracker.consent('denied');
  recording.tracker.click('membership', 'cards', membershipUrl);
  recording.tracker.consent('granted'); // A real browser reloads after revocation.
  recording.tracker.click('membership', 'cards', membershipUrl);
  assert.equal(recording.stops, 1);
  assert.equal(recording.commands.length, count);
});
test('development pages send nothing; QA explicitly enables DebugView', () => {
  const local = recordingTracker({ enabled: false });
  local.tracker.consent('granted');
  local.tracker.click('membership', 'cards', membershipUrl);
  assert.deepEqual(local.commands, []);
  const debug = recordingTracker({ debug: true });
  debug.tracker.consent('granted');
  assert.equal(debug.commands.find(command => command[0] === 'config')[2].debug_mode, true);
});
test('revocation only deletes cookies owned by this integration', () => {
  assert.deepEqual(ownedAnalyticsCookies('_ga=other; support_ga=one; support_ga_P79WP49S4Z=two; support__ga=three; login=keep'), ['support_ga', 'support_ga_P79WP49S4Z', 'support__ga']);
});
test('all six existing OFUSE links retain their destinations and have explicit intention tags', () => {
  const html = readFileSync(new URL('../_deploy-now/support/index.html', import.meta.url), 'utf8');
  const links = [...html.matchAll(/<a\b[^>]*href="(https:\/\/ofuse\.me\/[^\"]+)"[^>]*>/g)].map(match => match[0]);
  assert.equal(links.length, 6);
  for (const link of links) {
    const kind = link.match(/data-support-kind="([^"]+)"/)[1];
    const position = link.match(/data-support-position="([^"]+)"/)[1];
    const href = link.match(/href="([^"]+)"/)[1];
    assert.ok(supportEvent(kind, position, href));
    assert.match(link, /target="_blank" rel="noopener"/);
  }
  assert.equal(links.filter(link => link.includes('data-support-kind="membership"')).length, 2);
  assert.ok(!html.includes('googletagmanager.com'));
  const builder = readFileSync(new URL('build-deploy-now.py', import.meta.url), 'utf8');
  assert.ok(builder.includes('"js/support-analytics.mjs"'));
  assert.ok(builder.includes('"css/support-analytics.css"'));
});
