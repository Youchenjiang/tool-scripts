const test = require('node:test');
const assert = require('node:assert/strict');
const { MessageFlags } = require('discord.js');
const { boardMessage, boardRow } = require('../src/event-board');

function event(index, overrides = {}) {
  return {
    id: `event-${index}`, sourceId: 'test', title: `Security Activity ${index}`, url: `https://example.com/${index}`,
    startsAt: new Date(`2026-10-${String(index + 1).padStart(2, '0')}T00:00:00Z`),
    endsAt: new Date(`2026-10-${String(index + 1).padStart(2, '0')}T02:00:00Z`), kind: 'workshop',
    directions: ['blue'], topics: ['forensics'], level: 'foundational', participation: 'individual',
    attendance: 'online', deadlines: [], audience: [], ...overrides,
  };
}

test('board rows keep decision and timing data while moving details behind selection', () => {
  const text = boardRow(event(0), 'Asia/Taipei', new Date('2026-09-20T00:00:00Z'));
  assert.match(text, /🧩 Forensics · 🔵 藍隊 · 工作坊｜具基礎｜個人報名/u);
  assert.match(text, /📅 2026\/10\/01/u);
  assert.doesNotMatch(text, /🌐 線上/u);
});

test('activity board paginates up to ten compact rows per page', () => {
  const document = {
    lastCheckedAt: '2026-09-20T00:00:00Z',
    events: Object.fromEntries(Array.from({ length: 21 }, (_, index) => [String(index), { event: event(index) }])),
  };
  const first = boardMessage(document, { timeZone: 'Asia/Taipei', now: new Date('2026-09-20T00:00:00Z') });
  const second = boardMessage(document, { timeZone: 'Asia/Taipei', now: new Date('2026-09-20T00:00:00Z'), page: 1 });
  const last = boardMessage(document, { timeZone: 'Asia/Taipei', now: new Date('2026-09-20T00:00:00Z'), page: 2 });
  assert.match(first.content, /第 1\/3 頁/u);
  assert.equal(first.components.at(-1).components[0].options.length, 10);
  assert.equal(first.flags, MessageFlags.SuppressEmbeds);
  assert.match(last.content, /第 3\/3 頁/u);
  assert.equal(last.components.at(-1).components[0].options.length, 1);
  const ids = second.components.flatMap((row) => row.components.map((component) => component.data.custom_id));
  assert.equal(new Set(ids).size, ids.length);
  assert.match(second.components[1].components[0].data.custom_id, /^events:page:/u);
});

test('activity and CTF boards never mix their records', () => {
  const document = { lastCheckedAt: '2026-09-20T00:00:00Z', events: {
    activity: { event: event(0, { title: 'Blue Team Workshop' }) },
    competition: { event: event(1, { title: 'Security Contest', kind: 'competition' }) },
    ctf: { event: event(2, { title: 'Example CTF', kind: 'ctf' }) },
  } };
  const options = { timeZone: 'Asia/Taipei', now: new Date('2026-09-20T00:00:00Z') };
  const activities = boardMessage(document, options);
  assert.match(activities.content, /Blue Team Workshop/u);
  assert.match(activities.content, /Security Contest/u);
  assert.doesNotMatch(activities.content, /Example CTF/u);
  assert.match(activities.components[0].components[1].data.custom_id, /events:view:competition:0/u);

  const competitions = boardMessage(document, { ...options, filter: 'competition' });
  assert.match(competitions.content, /Security Contest/u);
  assert.doesNotMatch(competitions.content, /Blue Team Workshop|Example CTF/u);

  const ctfs = boardMessage(document, { ...options, filter: 'ctf' });
  assert.match(ctfs.content, /完整 CTF 賽程/u);
  assert.match(ctfs.content, /Example CTF/u);
  assert.doesNotMatch(ctfs.content, /Blue Team Workshop|Security Contest/u);
});
