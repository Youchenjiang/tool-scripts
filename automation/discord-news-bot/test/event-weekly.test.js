const test = require('node:test');
const assert = require('node:assert/strict');
const { publishWeekly, weeklyData, weekDayIndex, weekKey } = require('../src/event-weekly');
const { currentEvents, fingerprint } = require('../src/event-board');
const config = { eventTimeZone: 'Asia/Taipei' };
const event = { id: 'one', sourceId: 'ctftime', title: 'Example CTF', url: 'https://example.org',
  startsAt: '2026-09-25T00:00:00Z', endsAt: '2026-09-26T00:00:00Z', kind: 'ctf' };
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

test('a format upgrade edits an existing digest even when event data is unchanged', async () => {
  const now = new Date('2026-09-21T02:00:00Z');
  const state = { events: { one: { event } } };
  const entries = currentEvents(state, now);
  state.weekly = { week: '2026-09-21', messageId: '123',
    signature: fingerprint({ entries: entries.map(({ key, event: item }) => ({ key, event: item })), partial: false }) };
  const calls = [];
  const message = { id: '123', edit: async () => calls.push('edit') };
  const channel = { send: async () => { throw new Error('should edit'); }, messages: { fetch: async () => message } };
  await publishWeekly({ state, channel, config, now, save: async () => {} });
  assert.deepEqual(calls, ['edit']);
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
  assert.match(result.payload.content, /本週 CTF｜09\/21～09\/27/u);
  assert.match(text, /Example CTF/u);
  assert.doesNotMatch(text, /Blue Team Workshop|Security Competition/u);
  assert.equal(result.payload.components[0].components[0].data.custom_id, 'events:view:ctf:0');
  assert.equal(result.payload.components[0].components[0].data.label, '完整 CTF 賽程');
});

test('the schedule shows this week by day and keeps known deadlines ahead of it', () => {
  const state = { events: {
    urgent: { event: { ...event, id: 'urgent', title: 'Registration closes soon', startsAt: '2026-10-10T00:00:00Z',
      endsAt: '2026-10-11T00:00:00Z', deadlines: [{ kind: 'registration', at: '2026-09-23T15:59:00Z' }] } },
    current: { event: { ...event, id: 'current', title: 'This week', startsAt: '2026-09-25T04:00:00Z', endsAt: '2026-09-26T04:00:00Z' } },
    next: { event: { ...event, id: 'next', title: 'Next week', startsAt: '2026-09-28T04:00:00Z', endsAt: '2026-09-29T04:00:00Z' } },
  } };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  const text = payloadText(result.payload);
  assert.match(text, /本週報名期限[\s\S]*Registration closes soon/u);
  assert.match(text, /9\/25（五）[\s\S]*This week/u);
  assert.match(text, /9\/26（六）[\s\S]*This week/u);
  assert.doesNotMatch(text, /Next week/u);
});

test('the public schedule omits dates without competitions', () => {
  const state = { events: { one: { event } } };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  assert.deepEqual(result.payload.embeds.map(({ title }) => title), ['9/25（五）', '9/26（六）']);
  assert.doesNotMatch(payloadText(result.payload), /沒有賽事/u);
});

test('the public schedule stays concise and moves detailed facts behind the button', () => {
  const state = { events: { one: { event: { ...event, startsAt: '2026-09-25T04:00:00Z', endsAt: '2026-09-26T08:30:00Z',
    attendance: 'online', teamSizeMax: 4, participation: 'team', level: 'foundational', topics: ['web', 'pwn'] } } } };
  const rich = payloadText(weeklyData(state, config, new Date('2026-09-21T02:00:00Z')).payload);
  assert.match(rich, /9\/25（五）[\s\S]*Example CTF/u);
  assert.match(rich, /9\/26（六）[\s\S]*Example CTF/u);
  assert.doesNotMatch(rich, /線上|每隊最多|需具基礎|題型/u);

  const sparse = payloadText(weeklyData({ events: { one: { event } } }, config, new Date('2026-09-21T02:00:00Z')).payload);
  assert.doesNotMatch(sparse, /未公開|尚未公布|未確認|人數未標示|程度未標示|題型資訊/u);
  assert.equal(weeklyData(state, config, new Date('2026-09-21T02:00:00Z')).payload.flags, 0);
});

test('the public schedule exposes evidence-backed CTF directions and balanced topics', () => {
  const state = { events: { one: { event: { ...event,
    directions: ['red', 'blue'], topics: ['web', 'crypto', 'reverse', 'forensics'] } } } };
  const text = payloadText(weeklyData(state, config, new Date('2026-09-21T02:00:00Z')).payload);
  assert.match(text, /Example CTF[^\n]*🔴 紅隊＋🔵 藍隊[^\n]*🧩 Web、Forensics、Crypto/u);

  const unknown = payloadText(weeklyData({ events: { one: { event: { ...event,
    directions: ['unspecified'], topics: [] } } } }, config, new Date('2026-09-21T02:00:00Z')).payload);
  assert.doesNotMatch(unknown, /紅隊|藍隊|紫隊|綜合|🧩/u);
});

test('Sunday block alone answers which competitions remain playable that day', () => {
  const values = [
    ['nile', 'NileCTF', '2026-09-25T12:00:00Z', '2026-09-27T12:00:00Z'],
    ['flight', 'FlightPath2026', '2026-09-25T13:30:00Z', '2026-09-27T21:00:00Z'],
    ['bcs', 'BCS CTF 2026', '2026-09-25T14:00:00Z', '2026-09-27T14:00:00Z'],
    ['h7', 'H7CTF 2026 Quals', '2026-09-26T03:30:00Z', '2026-09-27T15:30:00Z'],
    ['faust', 'FAUST CTF 2026', '2026-09-26T12:00:00Z', '2026-09-26T21:00:00Z'],
    ['sunshine', 'SunshineCTF 2026', '2026-09-26T14:00:00Z', '2026-09-28T14:00:00Z'],
    ['pointer', 'Pointer Overflow CTF', '2026-09-27T14:00:00Z', '2026-12-06T14:00:00Z'],
  ];
  const state = { events: Object.fromEntries(values.map(([id, title, startsAt, endsAt]) => [id, {
    event: { ...event, id, title, startsAt, endsAt, url: `https://example.org/${id}` },
  }])) };
  const result = weeklyData(state, config, new Date('2026-09-21T02:00:00Z'));
  const sunday = result.payload.embeds.find((embed) => embed.title === '9/27（日）');
  assert.ok(sunday);
  for (const title of values.map(([, title]) => title)) assert.match(sunday.description, new RegExp(title, 'u'));
  assert.match(sunday.description, /NileCTF[^\n]*進行至/u);
  assert.match(sunday.description, /NileCTF[^\n]*20:00/u);
  assert.match(sunday.description, /FAUST CTF 2026[^\n]*進行至/u);
  assert.match(sunday.description, /FAUST CTF 2026[^\n]*05:00/u);
  assert.match(sunday.description, /Pointer Overflow CTF[^\n]*開始/u);
  assert.match(sunday.description, /Pointer Overflow CTF[^\n]*22:00/u);
});

test('the first digest is backfilled midweek while later weeks keep the weekly schedule', async () => {
  const state = { events: { one: { event } } }; const calls = [];
  const message = { id: '123', edit: async () => calls.push('edit') };
  const channel = { send: async () => { calls.push('send'); return message; }, messages: { fetch: async () => message } };
  const save = async () => {};
  assert.equal(await publishWeekly({ state, channel, config, now: new Date('2026-09-23T02:00:00Z'), save }), 1);
  assert.deepEqual(calls, ['send']);

  state.events.one.event = { ...event, title: 'Updated CTF' };
  assert.equal(await publishWeekly({ state, channel, config, now: new Date('2026-09-23T02:00:00Z'), save }), 0);
  assert.deepEqual(calls, ['send', 'edit']);

  state.events.one.event = { ...event, startsAt: '2026-10-02T00:00:00Z', endsAt: '2026-10-03T00:00:00Z' };
  calls.length = 0;
  assert.equal(await publishWeekly({ state, channel, config, now: new Date('2026-10-01T02:00:00Z'), save }), 0);
  assert.deepEqual(calls, []);
});
