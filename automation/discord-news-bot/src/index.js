require('dotenv').config();
const {
  ActivityType,
  Client,
  Events,
  GatewayIntentBits,
  MessageFlags,
} = require('discord.js');
const { loadConfig } = require('./config');
const { createEventInteractionHandler } = require('./event-interactions');
const { createEventService } = require('./event-service');
const { createNewsInteractionHandler } = require('./news-interactions');
const { createPublisher } = require('./publisher');
const { formatRuleConfig } = require('./rule-options');
const { createRuleSetupManager } = require('./rule-setup');
const { createStateStore } = require('./state-store');
const { createSourceObserver } = require('./source-observer');
const { scheduleRecurringTask } = require('./task-scheduler');

async function main() {
  const config = loadConfig();
  const client = new Client({ intents: [GatewayIntentBits.Guilds] });
  const stateStore = createStateStore(config);
  let publisher;
  let eventPublisher;
  let sourceObserver;
  let ruleSetup;
  const eventInteractions = createEventInteractionHandler({
    config,
    getEventService: () => eventPublisher,
    runEventPublisher,
  });
  const newsInteractions = createNewsInteractionHandler({
    config,
    getPublisher: () => publisher,
    getRuleSetup: () => ruleSetup,
    runPublisher,
  });

  client.once(Events.ClientReady, async (readyClient) => {
    try {
      console.log(`[Bot] Logged in as ${readyClient.user.tag}`);
      readyClient.user.setPresence({
        activities: [{ name: '符合規則的資安新聞', type: ActivityType.Watching }],
        status: 'online',
      });

      const channel = await readyClient.channels.fetch(config.channelId);
      if (!channel?.isTextBased() || !('send' in channel)) {
        throw new Error(`DISCORD_CHANNEL_ID ${config.channelId} is not a sendable text channel`);
      }

      publisher = createPublisher({ channel, config, stateStore });
      ruleSetup = createRuleSetupManager({
        channelId: config.channelId,
        saveRule: (ruleConfig, userId) => publisher.setFilterRule(ruleConfig, userId),
        announceRule: (rule, userId) => channel.send({
          content: [
            `📌 **新聞頻道共用規則已更新（版本 ${rule.version}）**`,
            `更新者：<@${userId}>`,
            formatRuleConfig(rule.config),
          ].join('\n'),
          allowedMentions: { users: [userId] },
        }),
      });
      console.log(`[Bot] State store: ${config.databaseUrl ? 'PostgreSQL' : 'local file'}`);
      console.log(`[Bot] AI filtering: ${config.aiFilteringEnabled ? 'enabled' : 'disabled'}`);
      if (config.sourceObservationEnabled) {
        sourceObserver = createSourceObserver({ config, stateStore });
        void runSourceObserver('startup').catch(() => {});
        scheduleRecurringTask(() => runSourceObserver('schedule'), config.sourceObservationIntervalMs);
        console.log(`[Bot] Source observation: enabled, ${config.maxSourcesPerRun} source(s) per run`);
      }
      if (config.eventsEnabled) {
        const eventChannel = await readyClient.channels.fetch(config.eventChannelId);
        if (!eventChannel?.isTextBased() || !('send' in eventChannel)) {
          throw new Error(`EVENT_CHANNEL_ID ${config.eventChannelId} is not a sendable text channel`);
        }
        eventPublisher = createEventService({
          channel: eventChannel,
          config,
          stateStore,
        });
        await runEventPublisher('startup').catch(() => {});
        scheduleRecurringTask(() => runEventPublisher('schedule'), config.eventPollIntervalMs);
        console.log(`[Bot] Security events: polling every ${config.eventPollIntervalMs / 60_000} minute(s)`);
      }
      if (config.pushOnStart) await runPublisher('startup').catch(() => {});
      scheduleRecurringTask(() => runPublisher('schedule'), config.pollIntervalMs);
      console.log(`[Bot] Polling every ${config.pollIntervalMs / 60_000} minute(s)`);
    } catch (error) {
      console.error(`[Bot setup] ${error.stack || error.message}`);
      readyClient.destroy();
      process.exitCode = 1;
    }
  });

  async function runPublisher(trigger) {
    try {
      const result = await publisher.run();
      console.log(`[News:${trigger}]`, result);
      return result;
    } catch (error) {
      console.error(`[News:${trigger}] ${error.stack || error.message}`);
      throw error;
    }
  }

  async function runEventPublisher(trigger, options = {}) {
    try {
      const result = await eventPublisher.run(options);
      console.log(`[Events:${trigger}]`, result);
      return result;
    } catch (error) {
      console.error(`[Events:${trigger}] ${error.stack || error.message}`);
      throw error;
    }
  }

  async function runSourceObserver(trigger) {
    try {
      const result = await sourceObserver.run();
      console.log(`[Sources:${trigger}]`, result);
      return result;
    } catch (error) {
      console.error(`[Sources:${trigger}] ${error.stack || error.message}`);
      throw error;
    }
  }

  client.on(Events.InteractionCreate, async (interaction) => {
    if (await eventInteractions.handle(interaction)) return;
    if (await newsInteractions.handle(interaction)) return;
    if (!interaction.isChatInputCommand()) return;

    if (interaction.commandName === 'ping') {
      await interaction.reply({ content: `Pong! ${client.ws.ping}ms`, flags: MessageFlags.Ephemeral });
      return;
    }

  });

  let shuttingDown = false;
  async function shutdown(signal) {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log(`[Bot] Received ${signal}, shutting down`);
    client.destroy();
    await stateStore.close();
  }

  process.once('SIGINT', () => void shutdown('SIGINT'));
  process.once('SIGTERM', () => void shutdown('SIGTERM'));
  await client.login(config.token);
}

main().catch((error) => {
  console.error(`[Fatal] ${error.stack || error.message}`);
  process.exitCode = 1;
});
