const test = require('node:test');
const assert = require('node:assert/strict');
const { MessageFlags } = require('discord.js');
const { createEventMessage, createEventPublisher } = require('../src/event-publisher');

function sampleEvent(overrides = {}) {
  return {
    id: 'ctftime:3504', aliases: ['ctftime:3504', 'organizer:holmes-2026'],
    title: 'Holmes CTF 2026: The Reichenbach Directive',
    url: 'https://ctf.hackthebox.com/event/details/holmes-3504', officialUrl: 'https://ctf.hackthebox.com/event/details/holmes-3504',
    startsAt: new Date('2026-09-18T04:00:00Z'), endsAt: new Date('2026-09-22T09:00:00Z'), allDay: false,
    directions: ['red'], kind: 'ctf', level: 'foundational', participation: 'team', teamSizeMax: 5,
    topics: ['web', 'pwn', 'reverse'], attendance: 'online', deadlines: [], audience: [], ...overrides,
  };
}

test('event announcement exposes the fields needed for a quick reading decision', () => {
  const message = createEventMessage(sampleEvent(), 'Asia/Taipei', new Date('2026-09-01T00:00:00Z'));
  assert.equal(message.content, [
    '[Holmes CTF 2026: The Reichenbach Directive](https://ctf.hackthebox.com/event/details/holmes-3504)',
    '🔴 紅隊 · CTF｜具基礎｜最多 5 人', '🧩 Web、Pwn、Reverse',
    '📅 2026/09/18 12:00～09/22 17:00', '🌐 線上',
  ].join('\n'));
  assert.deepEqual(message.allowedMentions, { parse: [] });
  assert.equal(message.flags, MessageFlags.SuppressEmbeds);
});

test('event announcement handles overflow, deadline, hybrid location and eligibility', () => {
  const message = createEventMessage(sampleEvent({
    directions: ['purple'], kind: 'workshop', level: 'advanced', participation: 'individual', teamSizeMax: null,
    topics: ['web', 'pwn', 'reverse', 'crypto', 'forensics', 'malware', 'network'],
    deadlines: [{ at: new Date('2026-09-10T15:59:00Z'), kind: 'registration' }],
    attendance: 'hybrid', location: '新竹', audience: ['high-school'],
  }), 'Asia/Taipei', new Date('2026-09-01T00:00:00Z'));
  assert.match(message.content, /🟣 紫隊 · 工作坊｜進階｜個人報名/u);
  assert.match(message.content, /🧩 Web、Pwn、Reverse、Crypto、Forensics（另有 2 類）/u);
  assert.match(message.content, /⏳ 報名至 2026\/09\/10 23:59/u);
  assert.match(message.content, /📍 新竹 · 同步提供線上參與/u);
  assert.match(message.content, /👤 限高中職學生/u);
});

test('event announcement states unknown fields without inventing details', () => {
  const message = createEventMessage(sampleEvent({
    startsAt: null, endsAt: null, dateText: 'Sep 2026 – Aug 2027', directions: ['unspecified'], kind: 'event',
    level: 'unspecified', participation: 'unspecified', teamSizeMax: null, topics: [], attendance: 'unknown',
  }));
  assert.match(message.content, /⚫ 方向未標示 · 活動｜程度未標示｜人數未公開/u);
  assert.match(message.content, /📅 Sep 2026 – Aug 2027（詳細時間請見官網）/u);
  assert.doesNotMatch(message.content, /🧩/u);
});

test('event announcement presents an unclassified CTF as general instead of blank direction', () => {
  const message = createEventMessage(sampleEvent({ directions: ['unspecified'], topics: [] }));
  assert.match(message.content, /⚪ 綜合 · CTF/u);
});

test('event publisher prioritizes nearest deadline and persists every alias', async () => {
  const sentMessages = [];
  let savedState = { sentIds: [], lastCheckedAt: null };
  const stateStore = {
    kind: 'memory', loadNamedState: async () => ({ ...savedState, sentIds: [...savedState.sentIds] }),
    saveNamedState: async (_key, state) => { savedState = { ...state, sentIds: [...state.sentIds] }; },
  };
  const later = sampleEvent({ id: 'later', aliases: ['later'] });
  const nearer = sampleEvent({ id: 'nearer', aliases: ['nearer', 'organizer:nearer'], title: 'Nearer deadline', deadlines: [{ at: new Date('2026-09-12T00:00:00Z'), kind: 'registration' }] });
  const publisher = createEventPublisher({
    channel: { send: async (message) => sentMessages.push(message) },
    config: { eventChannelId: 'events', eventTimeZone: 'Asia/Taipei', eventScanHour: 9, maxEventsPerRun: 1 }, stateStore,
    now: () => new Date('2026-09-01T04:30:00Z'), fetchEventsImpl: async () => ({ events: [later, nearer], errors: [] }),
  });
  assert.equal((await publisher.run()).published, 1);
  assert.match(sentMessages[0].content, /Nearer deadline/u);
  assert.deepEqual(savedState.sentIds.sort(), ['nearer', 'organizer:nearer']);
  assert.equal((await publisher.run()).skipped, true);
  assert.equal((await publisher.run({ force: true })).published, 1);
});

test('event publisher treats any sent alias as the same event', async () => {
  const sentMessages = [];
  let savedState = { sentIds: ['organizer:holmes-2026'], lastCheckedAt: null };
  const publisher = createEventPublisher({
    channel: { send: async (message) => sentMessages.push(message) },
    config: { eventChannelId: 'events', eventTimeZone: 'Asia/Taipei', eventScanHour: 0, maxEventsPerRun: 5 },
    stateStore: { kind: 'memory', loadNamedState: async () => savedState, saveNamedState: async (_key, state) => { savedState = state; } },
    now: () => new Date('2026-09-01T04:30:00Z'), fetchEventsImpl: async () => ({ events: [sampleEvent()], errors: [] }),
  });
  const result = await publisher.run({ force: true });
  assert.equal(result.discovered, 0);
  assert.equal(result.published, 0);
  assert.equal(sentMessages.length, 0);
});

test('event publisher waits until configured local scan hour', async () => {
  const publisher = createEventPublisher({
    channel: { send: async () => { throw new Error('should not publish'); } },
    config: { eventChannelId: 'events', eventTimeZone: 'Asia/Taipei', eventScanHour: 9, maxEventsPerRun: 5 },
    stateStore: { kind: 'memory', loadNamedState: async () => ({ sentIds: [], lastCheckedAt: null }), saveNamedState: async () => {} },
    now: () => new Date('2026-09-17T23:30:00Z'), fetchEventsImpl: async () => { throw new Error('should not fetch'); },
  });
  const result = await publisher.run();
  assert.equal(result.skipped, true);
  assert.match(result.reason, /09:00/u);
});
