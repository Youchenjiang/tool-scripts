const assert = require('node:assert/strict');
const test = require('node:test');
const { PermissionFlagsBits } = require('discord.js');
const { createEventInteractionHandler } = require('../src/event-interactions');

function command(name, overrides = {}) {
  const replies = [];
  const edits = [];
  return {
    commandName: name,
    guildId: 'guild',
    isChatInputCommand: () => true,
    memberPermissions: { has: () => true },
    reply: async (payload) => { replies.push(payload); },
    deferReply: async () => {},
    editReply: async (payload) => { edits.push(payload); },
    replies,
    edits,
    ...overrides,
  };
}

test('event components are delegated without claiming unrelated interactions', async () => {
  let handled = 0;
  const handler = createEventInteractionHandler({
    config: { eventsEnabled: true },
    getEventService: () => ({ handle: async () => { handled += 1; } }),
    runEventPublisher: async () => ({}),
  });
  const eventInteraction = { customId: 'events:view:all:0' };
  assert.equal(await handler.handle(eventInteraction), true);
  assert.equal(handled, 1);
  assert.equal(await handler.handle({ isChatInputCommand: () => false }), false);
});

test('event status preserves the operational summary', async () => {
  const interaction = command('events_status');
  const handler = createEventInteractionHandler({
    config: { eventsEnabled: true, eventChannelId: 'channel' },
    getEventService: () => ({ getStatus: () => ({ running: false, latestResult: {
      at: '2026-09-24T03:25:32.833Z', checked: 34, discovered: 0, activityPublished: 0,
      activityDiscovered: 0, published: 0, boardId: 'board', reminders: { sent: 0, failed: 0 },
      sourceErrors: [],
    } }) }),
    runEventPublisher: async () => ({}),
  });

  assert.equal(await handler.handle(interaction), true);
  assert.match(interaction.replies[0].content, /讀取 34 場／資料庫新增 0 場/u);
  assert.match(interaction.replies[0].content, /guild\/channel\/board/u);
});

test('event run-now requires management permission and forces one run', async () => {
  let options;
  const interaction = command('events_now');
  const handler = createEventInteractionHandler({
    config: { eventsEnabled: true },
    getEventService: () => ({}),
    runEventPublisher: async (trigger, received) => {
      assert.equal(trigger, 'command');
      options = received;
      return { checked: 2, discovered: 1, activityPublished: 1, activityDiscovered: 1, published: 0 };
    },
  });
  await handler.handle(interaction);
  assert.deepEqual(options, { force: true });
  assert.match(interaction.edits[0], /活動公告 1 則/u);

  const denied = command('events_now', {
    memberPermissions: { has: (permission) => permission === PermissionFlagsBits.ManageGuild && false },
  });
  await handler.handle(denied);
  assert.match(denied.replies[0].content, /管理伺服器/u);
});
