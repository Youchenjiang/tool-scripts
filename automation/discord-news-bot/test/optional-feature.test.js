const assert = require('node:assert/strict');
const test = require('node:test');
const { initializeOptionalFeature } = require('../src/optional-feature');

test('optional feature returns the initialized service', async () => {
  const service = { run: async () => {} };

  const result = await initializeOptionalFeature('Events', async () => service);

  assert.equal(result, service);
});

test('optional feature logs setup errors without rejecting startup', async () => {
  const messages = [];
  const logger = { error: (message) => messages.push(message) };

  const result = await initializeOptionalFeature('Events', async () => {
    throw new Error('channel unavailable');
  }, logger);

  assert.equal(result, undefined);
  assert.equal(messages.length, 1);
  assert.match(messages[0], /^\[Events setup\]/u);
  assert.match(messages[0], /channel unavailable/u);
});
