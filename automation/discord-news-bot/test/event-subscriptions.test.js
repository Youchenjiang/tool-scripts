const test = require('node:test');
const assert = require('node:assert/strict');
const { subscribe, unsubscribe, pruneSubscriptions, deliverReminders, sendMemberReminder } = require('../src/event-subscriptions');

const now = new Date('2026-09-21T02:00:00Z');
const config = { eventTimeZone: 'Asia/Taipei', eventChannelId: '222' };
function state() {
  return { events: { one: { verifiedAt: now.toISOString(), event: {
    id: 'one', sourceId: 'ctftime', title: 'CTF', url: 'https://example.org',
    startsAt: '2026-09-22T01:00:00Z', endsAt: '2026-09-23T00:00:00Z',
    deadlines: [{ kind: 'registration', at: '2026-09-21T16:00:00Z' }],
  } } }, subscriptions: {} };
}

test('subscriptions are idempotent and cancellation is scoped to the requesting member', () => {
  const s = state();
  subscribe(s, 'alice', 'one', now); subscribe(s, 'alice', 'one', now); subscribe(s, 'bob', 'one', now);
  assert.equal(Object.keys(s.subscriptions).length, 2);
  unsubscribe(s, 'alice', 'one');
  assert.deepEqual(Object.keys(s.subscriptions), ['bob:one']);
});

test('reminders send once per member and milestone even after restart', async () => {
  let s = state(); subscribe(s, 'alice', 'one', now);
  let stored; const messages = [];
  const save = async (value) => { stored = JSON.parse(JSON.stringify(value)); };
  const send = async (user, payload) => { messages.push([user, payload]); };
  assert.deepEqual(await deliverReminders({ state: s, config, now, save, send }), { sent: 2, failed: 0 });
  s = stored;
  await deliverReminders({ state: s, config, now, save, send });
  assert.equal(messages.length, 2);
  assert.ok(messages.every(([user]) => user === 'alice'));
  assert.match(messages[0][1].content, /24 小時內開始/);
  assert.match(messages[1][1].content, /24 小時內截止/);
  assert.equal(messages[0][1].components[0].components[0].data.custom_id, 'events:unsub:222:one');
});

test('blocked DMs are recorded without retry storms or a public fallback', async () => {
  const s = state(); subscribe(s, 'alice', 'one', now); let attempts = 0;
  const args = { state: s, config, now, save: async () => {}, send: async () => { attempts += 1; throw new Error('DM blocked'); } };
  assert.deepEqual(await deliverReminders(args), { sent: 0, failed: 2 });
  await deliverReminders(args);
  assert.equal(attempts, 2);
  assert.ok(Object.values(s.subscriptions['alice:one'].notices).every(({ status }) => status === 'failed'));
});

test('stale source data does not trigger reminders and expired subscriptions are removed', async () => {
  const s = state(); subscribe(s, 'alice', 'one', now); s.events.one.stale = true;
  const result = await deliverReminders({ state: s, config, now, save: async () => {}, send: async () => { throw new Error('must not send'); } });
  assert.equal(result.sent, 0);
  pruneSubscriptions(s, new Date('2026-09-24T00:00:00Z'));
  assert.deepEqual(s.subscriptions, {});
});

test('unknown deadlines and milestones that already passed are not reminded', async () => {
  const s = state(); subscribe(s, 'alice', 'one', now);
  s.events.one.event.startsAt = '2026-09-21T01:00:00Z';
  s.events.one.event.deadlines[0].kind = 'unknown';
  const result = await deliverReminders({ state: s, config, now, save: async () => {}, send: async () => { throw new Error('must not send'); } });
  assert.equal(result.sent, 0);
});

test('a crash after dispatch intent cannot duplicate an uncertain notification', async () => {
  const s = state(); subscribe(s, 'alice', 'one', now);
  s.subscriptions['alice:one'].notices['start:2026-09-22T01:00:00.000Z'] = { status: 'sending' };
  s.subscriptions['alice:one'].notices['registration:2026-09-21T16:00:00.000Z'] = { status: 'sent' };
  const result = await deliverReminders({ state: s, config, now, save: async () => {}, send: async () => { throw new Error('must not send'); } });
  assert.equal(result.sent, 0);
});

test('members who lost channel access cannot receive activity DMs', async () => {
  const channel = { guild: { members: { fetch: async () => ({ send: async () => { throw new Error('must not send'); } }) } },
    permissionsFor: () => ({ has: () => false }) };
  await assert.rejects(sendMemberReminder(channel, 'alice', {}), /no longer has access/);
});
