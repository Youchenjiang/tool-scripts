const assert = require('node:assert/strict');
const test = require('node:test');
const { parseChannelIds } = require('../src/config');

test('event channel list trims, deduplicates, and preserves order', () => {
  assert.deepEqual(parseChannelIds('111, 222,111', '333'), ['111', '222']);
});

test('event channel list supports the legacy single-channel fallback', () => {
  assert.deepEqual(parseChannelIds('', '1536696484286824519'), ['1536696484286824519']);
});

test('event channel list rejects malformed IDs', () => {
  assert.throws(() => parseChannelIds('111,not-a-channel', '333'), /EVENT_CHANNEL_IDS/u);
});
