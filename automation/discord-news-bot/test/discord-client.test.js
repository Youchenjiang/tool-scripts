const test = require('node:test');
const assert = require('node:assert/strict');
const { createDiscordClient } = require('../src/discord-client');

test('Discord client enforces message nonces to deduplicate REST retries', () => {
  const client = createDiscordClient();

  assert.equal(client.options.enforceNonce, true);
  assert.deepEqual(client.options.intents.toArray(), ['Guilds']);

  client.destroy();
});
