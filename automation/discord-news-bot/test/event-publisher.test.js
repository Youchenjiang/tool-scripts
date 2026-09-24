const test = require('node:test');
const assert = require('node:assert/strict');
const { MessageFlags } = require('discord.js');
const { createEventMessage } = require('../src/event-publisher');

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
    '🧩 Web、Pwn、Reverse · 🔴 紅隊 · CTF｜具基礎｜最多 5 人',
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
  assert.match(message.content, /🧩 Web、Pwn、Reverse · 🟣 紫隊 · 工作坊/u);
  assert.doesNotMatch(message.content, /Crypto|Forensics|另有/u);
  assert.match(message.content, /⏳ 報名至 2026\/09\/10 23:59/u);
  assert.match(message.content, /🌐 線上／📍 新竹/u);
  assert.match(message.content, /👤 限高中職學生/u);
});

test('event announcement silently omits unknown fields', () => {
  const message = createEventMessage(sampleEvent({
    startsAt: null, endsAt: null, dateText: 'Sep 2026 – Aug 2027', directions: ['unspecified'], kind: 'event',
    level: 'unspecified', participation: 'unspecified', teamSizeMax: null, topics: [], attendance: 'unknown',
  }));
  assert.match(message.content, /\n活動\n/u);
  assert.doesNotMatch(message.content, /綜合/u);
  assert.doesNotMatch(message.content, /未標示|未公開/u);
  assert.match(message.content, /📅 Sep 2026 – Aug 2027（詳細時間請見官網）/u);
  assert.doesNotMatch(message.content, /🧩/u);
});

test('event announcement abbreviates public places without exposing street addresses', () => {
  const overseas = createEventMessage(sampleEvent({
    attendance: 'onsite', venue: 'Fundação António Cupertino de Miranda', city: 'Porto', country: 'Portugal',
    address: 'Avenida da Boavista 4245', location: 'Fundação António Cupertino de Miranda / Avenida da Boavista 4245',
  }));
  assert.match(overseas.content, /📍 Porto, Portugal/u);
  assert.doesNotMatch(overseas.content, /Fundação|Avenida/u);

  const taiwan = createEventMessage(sampleEvent({
    attendance: 'hybrid', venue: 'IEAT 會議中心', city: '台北', country: '台灣', address: '松江路 350 號',
  }));
  assert.match(taiwan.content, /🌐 線上／📍 台北・IEAT 會議中心/u);
  assert.doesNotMatch(taiwan.content, /松江路/u);
});

test('event announcement omits an unclassified CTF direction instead of presenting it as general', () => {
  const message = createEventMessage(sampleEvent({ directions: ['unspecified'], topics: [] }));
  assert.match(message.content, /\nCTF｜具基礎｜最多 5 人\n/u);
  assert.doesNotMatch(message.content, /綜合/u);
});

test('event announcement keeps attack and defense directions visible without calling them purple team', () => {
  const message = createEventMessage(sampleEvent({
    directions: ['red', 'blue'], topics: ['web', 'crypto', 'reverse', 'forensics'],
  }));
  assert.match(message.content, /🧩 Web、Forensics、Crypto/u);
  assert.match(message.content, /🔴 紅隊＋🔵 藍隊/u);
  assert.doesNotMatch(message.content, /紫隊|綜合/u);
});
