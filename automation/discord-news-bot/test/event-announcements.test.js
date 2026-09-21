const test = require('node:test');
const assert = require('node:assert/strict');
const { MessageFlags } = require('discord.js');
const { activityBatches, publishNewActivities } = require('../src/event-announcements');

const now = new Date('2026-09-21T02:00:00Z');
const config = { eventTimeZone: 'Asia/Taipei' };
function event(id, overrides = {}) {
  return {
    id, aliases: [id], sourceId: 'community', title: `Activity ${id}`,
    url: `https://example.org/${id}`, officialUrl: `https://example.org/${id}`,
    startsAt: new Date('2026-09-25T02:00:00Z'), endsAt: new Date('2026-09-25T04:00:00Z'),
    deadlines: [], kind: 'workshop', directions: ['blue'], topics: ['forensics'],
    level: 'foundational', participation: 'individual', attendance: 'online', audience: [], ...overrides,
  };
}

test('first run establishes a baseline without publishing existing activities', async () => {
  const state = { events: { one: { event: event('one') }, ctf: { event: event('ctf', { kind: 'ctf' }) } } };
  const sent = [];
  const result = await publishNewActivities({ state, config, now, save: async () => {},
    channel: { send: async (payload) => sent.push(payload) } });
  assert.deepEqual(result, { initialized: true, discovered: 0, published: 0 });
  assert.deepEqual(state.activityDelivery.sentIds, ['one']);
  assert.deepEqual(sent, []);
});

test('later non-CTF activities are batched and persisted by every alias', async () => {
  const state = { activityDelivery: { initializedAt: '2026-09-20T00:00:00Z', sentIds: ['old'] }, events: {
    old: { event: event('old') },
    next: { event: event('next', { aliases: ['next', 'organizer:next'], kind: 'community' }) },
    ctf: { event: event('ctf', { kind: 'ctf' }) },
  } };
  const sent = [];
  const result = await publishNewActivities({ state, config, now, save: async () => {},
    channel: { send: async (payload) => sent.push(payload) } });
  assert.deepEqual(result, { initialized: false, discovered: 1, published: 1 });
  assert.match(sent[0].content, /Activity next/u);
  assert.doesNotMatch(sent[0].content, /Activity ctf/u);
  assert.doesNotMatch(sent[0].content, /適合想/u);
  assert.equal(sent[0].flags, MessageFlags.SuppressEmbeds);
  assert.deepEqual(state.activityDelivery.sentIds, ['old', 'next', 'organizer:next']);
});

test('large discoveries are split only at activity boundaries', () => {
  const entries = Array.from({ length: 20 }, (_, index) => ({
    key: String(index), event: event(String(index), { title: `Activity ${index} ${'detail '.repeat(20)}` }),
  }));
  const batches = activityBatches(entries, config, now);
  assert.ok(batches.length > 1);
  assert.ok(batches.every(({ content }) => content.length <= 1900));
  assert.deepEqual(batches.flatMap(({ entries: values }) => values.map(({ key }) => key)), entries.map(({ key }) => key));
});

test('a failed send does not checkpoint undispatched activities', async () => {
  const state = { activityDelivery: { initializedAt: '2026-09-20T00:00:00Z', sentIds: [] },
    events: { next: { event: event('next') } } };
  await assert.rejects(publishNewActivities({ state, config, now, save: async () => {},
    channel: { send: async () => { throw new Error('offline'); } } }), /offline/u);
  assert.deepEqual(state.activityDelivery.sentIds, []);
});
