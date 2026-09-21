const test = require('node:test');
const assert = require('node:assert/strict');
const { publishWeekly, weeklyData, weekDayIndex, weekKey } = require('../src/event-weekly');
const config = { eventTimeZone: 'Asia/Taipei' };
const event = { id: 'one', sourceId: 'ctftime', title: 'Example CTF', url: 'https://example.org',
  startsAt: '2026-10-01T00:00:00Z', endsAt: '2026-10-02T00:00:00Z', kind: 'ctf' };

test('weekly digest uses Monday in the configured timezone', () => {
  assert.equal(weekKey(new Date('2026-09-20T16:01:00Z'), 'Asia/Taipei'), '2026-09-21');
  assert.equal(weekKey(new Date('2026-09-20T15:59:00Z'), 'Asia/Taipei'), '2026-09-14');
  assert.equal(weekDayIndex(new Date('2026-09-21T02:00:00Z'), 'Asia/Taipei'), 0);
  assert.equal(weekDayIndex(new Date('2026-09-23T02:00:00Z'), 'Asia/Taipei'), 2);
});

test('same-week additions edit the digest; unchanged weeks do not publish', async () => {
  const state = { events: { one: { event } } }; const calls = [];
  const message = { id: '123', edit: async () => calls.push('edit') };
  const channel = { send: async () => { calls.push('send'); return message; }, messages: { fetch: async () => message } };
  const run = (date) => publishWeekly({ state, channel, config, now: new Date(date), save: async () => {} });
  await run('2026-09-21T02:00:00Z');
  await run('2026-09-22T02:00:00Z');
  state.events.one.event = { ...event, title: 'Updated CTF' };
  await run('2026-09-23T02:00:00Z');
  await run('2026-09-28T02:00:00Z');
  assert.deepEqual(calls, ['send', 'edit']);
});

test('large weekly digests publish curated entries and group excess competitions', () => {
  const state = { events: Object.fromEntries(Array.from({ length: 50 }, (_, i) => [String(i), { event: { ...event, id: `id${i}`, title: `CTF ${i}` } }])) };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  assert.equal(result.count, 50);
  assert.ok(result.payload.content.length <= 2000);
  assert.match(result.payload.content, /其他 CTF 行程/);
  assert.match(result.payload.content, /公開整理 3 場/);
  assert.deepEqual(result.payload.files, []);
});

test('stale entries and distant activities are excluded, but upcoming deadlines qualify', () => {
  const distant = { ...event, startsAt: '2027-01-01T00:00:00Z', endsAt: '2027-01-02T00:00:00Z' };
  const state = { events: { stale: { event, stale: true }, distant: { event: distant }, deadline: {
    event: { ...distant, deadlines: [{ kind: 'registration', at: '2026-09-24T00:00:00Z' }] },
  } } };
  assert.equal(weeklyData(state, config, new Date('2026-09-21T02:00:00Z')).count, 1);
});

test('a partial source outage still permits confirmed events in the weekly digest', () => {
  const state = { sourceErrors: ['other source offline'], events: { one: { event } } };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  assert.equal(result.count, 1);
  assert.match(result.payload.content, /部分來源暫時無法更新/);
  assert.match(result.payload.content, /Example CTF/);
});

test('the weekly digest excludes non-CTF activities', () => {
  const state = { events: {
    ctf: { event },
    workshop: { event: { ...event, id: 'workshop', title: 'Blue Team Workshop', kind: 'workshop' } },
    competition: { event: { ...event, id: 'competition', title: 'Security Competition', kind: 'competition' } },
  } };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  assert.equal(result.count, 1);
  assert.match(result.payload.content, /本週 CTF 賽事/u);
  assert.match(result.payload.content, /Example CTF/u);
  assert.doesNotMatch(result.payload.content, /Blue Team Workshop|Security Competition/u);
});

test('a new digest is not backfilled after Tuesday but an existing digest can still be edited', async () => {
  const state = { events: { one: { event } } }; const calls = [];
  const message = { id: '123', edit: async () => calls.push('edit') };
  const channel = { send: async () => { calls.push('send'); return message; }, messages: { fetch: async () => message } };
  const save = async () => {};
  assert.equal(await publishWeekly({ state, channel, config, now: new Date('2026-09-23T02:00:00Z'), save }), 0);
  assert.deepEqual(calls, []);
  state.weekly = { week: '2026-09-21', messageId: '123', signature: 'old' };
  assert.equal(await publishWeekly({ state, channel, config, now: new Date('2026-09-23T02:00:00Z'), save }), 0);
  assert.deepEqual(calls, ['edit']);
});
