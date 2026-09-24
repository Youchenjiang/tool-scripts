const assert = require('node:assert/strict');
const test = require('node:test');
const { createNewsInteractionHandler } = require('../src/news-interactions');

function baseInteraction(overrides = {}) {
  const replies = [];
  const edits = [];
  return {
    commandName: '', customId: '', channelId: 'news', guildId: 'guild', user: { id: 'member' },
    options: { getSubcommand: () => 'show' }, memberPermissions: { has: () => true },
    isButton: () => false, isStringSelectMenu: () => false, isModalSubmit: () => false,
    isChatInputCommand: () => true,
    reply: async (payload) => { replies.push(payload); }, deferReply: async () => {},
    editReply: async (payload) => { edits.push(payload); }, replies, edits, ...overrides,
  };
}

function handler(overrides = {}) {
  return createNewsInteractionHandler({
    config: { channelId: 'news' },
    getPublisher: () => ({ getStatus: () => ({ running: false, latestResult: null }) }),
    getRuleSetup: () => ({ handle: async () => {}, start: async () => {} }),
    runPublisher: async () => ({}),
    ...overrides,
  });
}

test('news handler leaves unrelated commands for the shared runtime', async () => {
  assert.equal(await handler().handle(baseInteraction({ commandName: 'ping' })), false);
});

test('news detail button reads the stored card through the publisher', async () => {
  let requestedKey;
  const interaction = baseInteraction({ customId: 'news_detail:detail-key', isButton: () => true, isChatInputCommand: () => false });
  const newsHandler = handler({ getPublisher: () => ({ getNewsDetail: async (key) => {
    requestedKey = key;
    return { headline: 'Example incident', articleUrl: 'https://example.com', technicalOutcome: '影響',
      technicalFocus: ['Web'], difficulty: 'intermediate', researchRelevance: [], evidenceBoundaries: [],
      attackChainGroups: [] };
  } }) });
  assert.equal(await newsHandler.handle(interaction), true);
  assert.equal(requestedKey, 'detail-key');
  assert.equal(interaction.replies[0].embeds[0].toJSON().title, 'Example incident');
});

test('news status preserves the current operational summary', async () => {
  const interaction = baseInteraction({ commandName: 'news_status' });
  const newsHandler = handler({ getPublisher: () => ({ getStatus: () => ({ running: false, latestResult: {
    at: '2026-09-24T03:25:38.674Z', checked: 50, evaluated: 0, matched: 0, published: 0,
  } }) }) });
  assert.equal(await newsHandler.handle(interaction), true);
  assert.match(interaction.replies[0].content, /讀取 50 篇／AI 新判斷 0 篇/u);
});

test('news run-now delegates one command-triggered run', async () => {
  let trigger;
  const interaction = baseInteraction({ commandName: 'news_now' });
  const newsHandler = handler({ getPublisher: () => ({}), runPublisher: async (received) => {
    trigger = received;
    return { checked: 5, matched: 1, published: 1 };
  } });
  await newsHandler.handle(interaction);
  assert.equal(trigger, 'command');
  assert.match(interaction.edits[0], /符合 1 篇，推送 1 篇/u);
});
