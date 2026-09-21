const test = require('node:test');
const assert = require('node:assert/strict');
const { publishWeekly, weeklyData, weekDayIndex, weekKey } = require('../src/event-weekly');
const config = { eventTimeZone: 'Asia/Taipei' };
const event = { id: 'one', sourceId: 'ctftime', title: 'Example CTF', url: 'https://example.org',
  startsAt: '2026-10-01T00:00:00Z', endsAt: '2026-10-02T00:00:00Z', kind: 'ctf' };
const payloadText = (payload) => [payload.content, ...(payload.embeds || []).flatMap((embed) => [embed.title, embed.description])]
  .filter(Boolean).join('\n');

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

test('large weekly digests list substantially more than three competitions within Discord limits', () => {
  const state = { events: Object.fromEntries(Array.from({ length: 50 }, (_, i) => [String(i), { event: { ...event, id: `id${i}`, title: `CTF ${i}` } }])) };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  const text = payloadText(result.payload);
  assert.equal(result.count, 50);
  assert.ok(result.payload.content.length <= 2000);
  assert.ok(result.payload.embeds.length <= 10);
  assert.ok(result.payload.embeds.reduce((total, embed) => total + embed.title.length + embed.description.length, 0) <= 6000);
  assert.ok((text.match(/CTF \d+/gu) || []).length > 20);
  assert.doesNotMatch(text, /公開整理|適合想透過競賽/u);
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
  assert.match(payloadText(result.payload), /Example CTF/);
});

test('the weekly digest excludes non-CTF activities', () => {
  const state = { events: {
    ctf: { event },
    workshop: { event: { ...event, id: 'workshop', title: 'Blue Team Workshop', kind: 'workshop' } },
    competition: { event: { ...event, id: 'competition', title: 'Security Competition', kind: 'competition' } },
  } };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  const text = payloadText(result.payload);
  assert.equal(result.count, 1);
  assert.match(result.payload.content, /本週 CTF 賽程/u);
  assert.match(text, /Example CTF/u);
  assert.doesNotMatch(text, /Blue Team Workshop|Security Competition/u);
});

test('the schedule groups starts and known deadlines by calendar week', () => {
  const state = { events: {
    urgent: { event: { ...event, id: 'urgent', title: 'Registration closes soon', startsAt: '2026-10-10T00:00:00Z',
      endsAt: '2026-10-11T00:00:00Z', deadlines: [{ kind: 'registration', at: '2026-09-23T15:59:00Z' }] } },
    current: { event: { ...event, id: 'current', title: 'This week', startsAt: '2026-09-25T04:00:00Z', endsAt: '2026-09-26T04:00:00Z' } },
    next: { event: { ...event, id: 'next', title: 'Next week', startsAt: '2026-09-28T04:00:00Z', endsAt: '2026-09-29T04:00:00Z' } },
  } };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  const text = payloadText(result.payload);
  assert.match(text, /即將截止[\s\S]*Registration closes soon/u);
  assert.match(text, /本週開賽[\s\S]*This week/u);
  assert.match(text, /下週開賽[\s\S]*Next week/u);
});

test('the schedule shows confirmed facts and silently omits unknown fields', () => {
  const state = { events: { one: { event: { ...event, startsAt: '2026-09-25T04:00:00Z', endsAt: '2026-09-26T08:30:00Z',
    attendance: 'online', teamSizeMax: 4, participation: 'team', level: 'foundational', topics: ['web', 'pwn'] } } } };
  const rich = payloadText(weeklyData(state, config, new Date('2026-09-21T02:00:00Z')).payload);
  assert.match(rich, /09\/25 12:00–09\/26 16:30/u);
  assert.match(rich, /28 小時 30 分鐘・線上・每隊最多 4 人・需具基礎・題型 Web／Pwn/u);

  const sparse = payloadText(weeklyData({ events: { one: { event } } }, config, new Date('2026-09-21T02:00:00Z')).payload);
  assert.doesNotMatch(sparse, /未公開|尚未公布|未確認|人數未標示|程度未標示|題型資訊/u);
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
