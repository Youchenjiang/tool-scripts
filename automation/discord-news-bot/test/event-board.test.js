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
  assert.match(text, /🔵 藍隊 · 工作坊｜具基礎｜個人報名/u);
  assert.match(text, /📅 2026\/10\/01/u);
  assert.doesNotMatch(text, /Forensics/u);
  assert.doesNotMatch(text, /🌐 線上/u);
});

test('activity board paginates up to ten compact rows per page', () => {
  const document = {
    lastCheckedAt: '2026-09-20T00:00:00Z',
    events: Object.fromEntries(Array.from({ length: 21 }, (_, index) => [String(index), { event: event(index) }])),
  };
  const first = boardMessage(document, { timeZone: 'Asia/Taipei', now: new Date('2026-09-20T00:00:00Z') });
  const last = boardMessage(document, { timeZone: 'Asia/Taipei', now: new Date('2026-09-20T00:00:00Z'), page: 2 });
  assert.match(first.content, /第 1\/3 頁/u);
  assert.equal(first.components.at(-1).components[0].options.length, 10);
  assert.equal(first.flags, MessageFlags.SuppressEmbeds);
  assert.match(last.content, /第 3\/3 頁/u);
  assert.equal(last.components.at(-1).components[0].options.length, 1);
});
