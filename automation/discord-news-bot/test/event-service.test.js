const test = require('node:test');
const assert = require('node:assert/strict');
const { createEventService } = require('../src/event-service');
const { boardMessage, keyFor } = require('../src/event-board');

const current = new Date('2026-09-21T02:00:00Z');
const event = { id: 'ctf:1', sourceId: 'ctftime', title: 'Example CTF', url: 'https://example.org/ctf',
  startsAt: '2026-09-25T02:00:00Z', endsAt: '2026-09-26T02:00:00Z', kind: 'ctf' };
function harness() {
  let document = null;
  let feed = { events: [event], errors: [] };
  const calls = [];
  const message = { id: '20', pinned: false,
    edit: async (body) => { calls.push(['edit', body]); }, pin: async () => { message.pinned = true; calls.push(['pin']); } };
  const channel = { id: '10', guild: { id: '30' },
    messages: { fetch: async () => message }, send: async (body) => { calls.push(['send', body]); return message; } };
  const config = { eventChannelId: '10', eventTimeZone: 'Asia/Taipei', eventScanHour: 9, eventWeeklyEnabled: false };
  const store = { loadEventDocument: async () => structuredClone(document),
    saveEventDocument: async (_id, value) => { document = JSON.parse(JSON.stringify(value)); } };
  const make = (options = {}) => createEventService({ channel, config, stateStore: store, now: () => current,
    fetchEventsImpl: async () => feed, ...options });
  return { make, calls, channel, store, get document() { return document; }, setFeed: (value) => { feed = value; } };
}

test('activity board survives restart and edits the same pinned message', async () => {
  const h = harness();
  await h.make().run();
  assert.equal(h.document.boardId, '20');
  await h.make().run({ force: true });
  assert.equal(h.calls.filter(([type]) => type === 'send').length, 1);
  assert.equal(h.calls.filter(([type]) => type === 'edit').length, 1);
  assert.equal(h.calls.filter(([type]) => type === 'pin').length, 1);
});

test('partial source failure retains activities as stale; a successful empty scan removes them', async () => {
  const h = harness(); const service = h.make(); await service.run();
  h.setFeed({ events: [], errors: ['CTFtime unavailable'] }); await service.run({ force: true });
  assert.equal(h.document.events[keyFor(event)].stale, true);
  h.setFeed({ events: [], errors: [] }); await service.run({ force: true });
  assert.equal(Object.keys(h.document.events).length, 0);
});

test('permission failures never create a second board; deleted boards can be recreated', async () => {
  const h = harness(); await h.make().run();
  h.channel.messages.fetch = async () => { throw Object.assign(new Error('forbidden'), { code: 50013 }); };
  await assert.rejects(h.make().run({ force: true }), /forbidden/);
  assert.equal(h.calls.filter(([type]) => type === 'send').length, 1);
  h.channel.messages.fetch = async () => { throw Object.assign(new Error('deleted'), { code: 10008 }); };
  await h.make().run({ force: true });
  assert.equal(h.calls.filter(([type]) => type === 'send').length, 2);
});

test('pagination stays within Discord limits without discarding activities', () => {
  const entries = Object.fromEntries(Array.from({ length: 20 }, (_, i) => [`key${i}`, { event: { ...event, id: `ctf:${i}` } }]));
  const state = { events: entries, lastCheckedAt: current.toISOString() };
  const seen = new Set();
  for (let page = 0; page < 5; page += 1) {
    const body = boardMessage(state, { now: current, page });
    assert.ok(body.content.length <= 2000);
    const select = body.components.at(-1).toJSON().components[0];
    for (const option of select.options) seen.add(option.value);
  }
  assert.equal(seen.size, 20);
  assert.match(boardMessage(state, { now: current, filter: 'community' }).content, /沒有符合/);
});

test('view buttons reply privately and never edit the public board', async () => {
  const h = harness(); const service = h.make(); await service.run();
  let deferred; let response;
  await service.handle({ customId: 'events:view:ctf:0', channelId: '10', guildId: '30',
    deferReply: async (options) => { deferred = options; }, editReply: async (body) => { response = body; } });
  assert.equal(deferred.flags, 64);
  assert.match(response.content, /Example CTF/);
  await service.handle({ customId: 'events:page:ctf:1', channelId: '10', guildId: '30',
    deferReply: async () => {}, editReply: async (body) => { response = body; } });
  assert.match(response.content, /Example CTF/);
  assert.equal(h.calls.filter(([type]) => type === 'edit').length, 0);
});

test('personal subscriptions persist and reminders run during scheduled scans', async () => {
  const h = harness();
  h.setFeed({ events: [{ ...event, startsAt: '2026-09-22T01:00:00Z' }], errors: [] });
  const delivered = [];
  const service = h.make({ sendReminderImpl: async (userId) => delivered.push(userId) });
  await service.run();
  const interaction = { channelId: '10', guildId: '30', user: { id: 'alice' },
    customId: `events:sub:${keyFor(event)}`, deferReply: async () => {}, editReply: async () => {} };
  await service.handle(interaction);
  await service.run();
  assert.deepEqual(delivered, ['alice']);
  await service.handle({ ...interaction, guildId: null, channelId: 'dm', customId: `events:unsub:${keyFor(event)}` });
  assert.deepEqual(h.document.subscriptions, {});
});

test('scheduled runs detect activities added later on the same day', async () => {
  const h = harness();
  h.setFeed({ events: [{ ...event, kind: 'workshop', id: 'existing', aliases: ['existing'] }], errors: [] });
  const service = h.make();
  await service.run();
  h.setFeed({ events: [
    { ...event, kind: 'workshop', id: 'existing', aliases: ['existing'] },
    { ...event, kind: 'community', id: 'new', aliases: ['new'], title: 'New community event' },
  ], errors: [] });
  const result = await service.run();
  assert.equal(result.activityDiscovered, 1);
  assert.equal(result.activityPublished, 1);
  assert.match(h.calls.find(([type, body]) => type === 'send' && /New community event/u.test(body.content))?.[1].content,
    /New community event/u);
});
