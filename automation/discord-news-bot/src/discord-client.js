const { Client, GatewayIntentBits } = require('discord.js');

function createDiscordClient() {
  return new Client({
    intents: [GatewayIntentBits.Guilds],
    // Reuse a nonce when discord.js retries a timed-out message POST so Discord
    // returns the original message instead of creating a duplicate.
    enforceNonce: true,
  });
}

module.exports = { createDiscordClient };
