require('dotenv').config();
const {
  ActivityType,
  Client,
  Events,
  GatewayIntentBits,
  MessageFlags,
  PermissionFlagsBits,
} = require('discord.js');
const { loadConfig } = require('./config');
const { createEventService } = require('./event-service');
const { createPublisher, createTechnicalDetailReply } = require('./publisher');
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
    if (interaction.customId?.startsWith('events:')) {
      try {
        if (eventPublisher) await eventPublisher.handle(interaction);
        else await interaction.reply({ content: '活動功能尚未準備完成。', flags: MessageFlags.Ephemeral });
      } catch (error) {
        console.error(`[Events interaction] ${error.stack || error.message}`);
        if (interaction.deferred) await interaction.editReply({ content: '操作失敗，請稍後再試。' });
        else if (!interaction.replied) await interaction.reply({ content: '操作失敗，請稍後再試。', flags: MessageFlags.Ephemeral });
      }
      return;
    }
    if (interaction.isButton() && interaction.customId.startsWith('news_detail:')) {
      const detailKey = interaction.customId.slice('news_detail:'.length);
      if (!publisher) {
        await interaction.reply({ content: 'Bot 尚未準備完成，請稍後再試。', flags: MessageFlags.Ephemeral });
        return;
      }
      try {
        const detail = await publisher.getNewsDetail(detailKey);
        if (!detail) {
          await interaction.reply({
            content: '這則新聞的技術細節已不存在，請改由原訊息開啟原文。',
            flags: MessageFlags.Ephemeral,
          });
          return;
        }
        await interaction.reply(createTechnicalDetailReply(detail));
      } catch (error) {
        console.error(`[News detail] ${error.stack || error.message}`);
        if (!interaction.replied && !interaction.deferred) {
          await interaction.reply({
            content: `讀取技術細節失敗：${error.message}`,
            flags: MessageFlags.Ephemeral,
          });
        }
      }
      return;
    }
    if (interaction.isButton() || interaction.isStringSelectMenu() || interaction.isModalSubmit()) {
      try {
        await ruleSetup?.handle(interaction);
      } catch (error) {
        console.error(`[Rule setup] ${error.stack || error.message}`);
        if (!interaction.replied && !interaction.deferred) {
          await interaction.reply({ content: `規則設定失敗：${error.message}`, flags: MessageFlags.Ephemeral });
        }
      }
      return;
    }
    if (!interaction.isChatInputCommand()) return;

    if (interaction.commandName === 'ping') {
      await interaction.reply({ content: `Pong! ${client.ws.ping}ms`, flags: MessageFlags.Ephemeral });
      return;
    }

    if (interaction.commandName === 'news_status') {
      const status = publisher?.getStatus();
      const latest = status?.latestResult;
      const text = latest
        ? [
          `執行中：${status.running ? '是' : '否'}`,
          `上次檢查：${latest.at}`,
          `讀取 ${latest.checked} 篇／AI 新判斷 ${latest.evaluated ?? 0} 篇／符合 ${latest.matched ?? 0} 篇／推送 ${latest.published} 篇`,
          latest.reason ? `狀態：${latest.reason}` : null,
        ].filter(Boolean).join('\n')
        : '尚未完成任何一次新聞檢查。';
      await interaction.reply({ content: text, flags: MessageFlags.Ephemeral });
      return;
    }

    if (interaction.commandName === 'events_status') {
      if (!config.eventsEnabled) {
        await interaction.reply({ content: '資安活動推送目前未啟用。', flags: MessageFlags.Ephemeral });
        return;
      }
      const status = eventPublisher?.getStatus();
      const latest = status?.latestResult;
      const text = latest
        ? [
          `執行中：${status.running ? '是' : '否'}`,
          `上次檢查：${latest.at}`,
          latest.skipped
            ? `狀態：${latest.reason}`
            : `讀取 ${latest.checked} 場／資料庫新增 ${latest.discovered} 場／活動公告 ${latest.activityPublished ?? 0} 則（${latest.activityDiscovered ?? 0} 場）／新 CTF 週報 ${latest.published} 則`,
          latest.boardId ? `活動總表：https://discord.com/channels/${interaction.guildId}/${config.eventChannelId}/${latest.boardId}` : null,
          latest.reminders ? `本輪私訊：送出 ${latest.reminders.sent} 則／失敗 ${latest.reminders.failed} 則` : null,
          latest.sourceErrors?.length ? `來源錯誤：${latest.sourceErrors.join('；')}` : null,
        ].filter(Boolean).join('\n')
        : '尚未完成任何一次資安活動檢查。';
      await interaction.reply({ content: text, flags: MessageFlags.Ephemeral });
      return;
    }

    if (interaction.commandName === 'events_now') {
      if (!interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
        await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
        return;
      }
      if (!eventPublisher) {
        await interaction.reply({ content: '活動推送尚未啟用或 Bot 尚未完成啟動。', flags: MessageFlags.Ephemeral });
        return;
      }
      await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      try {
        const result = await runEventPublisher('command', { force: true });
        await interaction.editReply(
          result.skipped ? result.reason
            : `總表已更新：讀取 ${result.checked} 場，資料庫新增 ${result.discovered} 場，活動公告 ${result.activityPublished ?? 0} 則（${result.activityDiscovered ?? 0} 場），新 CTF 週報 ${result.published} 則。`,
        );
      } catch (error) {
        await interaction.editReply(`活動檢查失敗：${error.message}`);
      }
      return;
    }

    if (interaction.commandName === 'news_rule') {
      if (interaction.channelId !== config.channelId) {
        await interaction.reply({
          content: `請在指定的新聞頻道 <#${config.channelId}> 設定規則。`,
          flags: MessageFlags.Ephemeral,
        });
        return;
      }
      if (!publisher) {
        await interaction.reply({ content: 'Bot 尚未完成啟動，請稍後再試。', flags: MessageFlags.Ephemeral });
        return;
      }

      const action = interaction.options.getSubcommand();
      if (action !== 'show'
          && !interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
        await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
        return;
      }
      if (action === 'setup') {
        await ruleSetup.start(interaction);
        return;
      }

      await interaction.deferReply(action === 'show' ? {} : { flags: MessageFlags.Ephemeral });
      try {
        if (action === 'show') {
          const rule = await publisher.getFilterRule();
          await interaction.editReply(rule
            ? `目前規則（版本 ${rule.version}）：\n${formatRuleConfig(rule.config)}`
            : '目前沒有規則；AI 新聞推送會保持停止。');
          return;
        }
        if (action === 'clear') {
          await publisher.setFilterRule(null, interaction.user.id);
          await interaction.editReply('已清除規則；AI 新聞推送會保持停止。');
          return;
        }
      } catch (error) {
        await interaction.editReply(`規則操作失敗：${error.message}`);
      }
      return;
    }

    if (interaction.commandName === 'news_ai_check') {
      if (!interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
        await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
        return;
      }
      if (!publisher) {
        await interaction.reply({ content: 'Bot 尚未準備完成，請稍後再試。', flags: MessageFlags.Ephemeral });
        return;
      }

      await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      try {
        const result = await publisher.checkAiProvider();
        if (!result.ok) {
          await interaction.editReply(`AI 供應商檢查未執行：${result.reason}`);
          return;
        }
        await interaction.editReply({
          content: [
            'AI 供應商連線成功',
            `HTTP：${result.httpStatus}`,
            `端點：${result.endpoint}`,
            `模型：${result.model}`,
            'Structured Output：通過',
            `供應商訊息：${result.providerMessage}`,
            `耗時：${result.latencyMs} ms`,
          ].join('\n'),
          allowedMentions: { parse: [] },
        });
      } catch (error) {
        await interaction.editReply({
          content: `AI 供應商檢查失敗：${error.message}`,
          allowedMentions: { parse: [] },
        });
      }
      return;
    }

    if (interaction.commandName === 'news_now') {
      if (!interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
        await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
        return;
      }
      if (!publisher) {
        await interaction.reply({ content: 'Bot 尚未完成啟動，請稍後再試。', flags: MessageFlags.Ephemeral });
        return;
      }
      await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      try {
        const result = await runPublisher('command');
        await interaction.editReply(result.skipped
          ? `未執行推送：${result.reason}`
          : `檢查完成：讀取 ${result.checked} 篇，符合 ${result.matched ?? result.published} 篇，推送 ${result.published} 篇。`);
      } catch (error) {
        await interaction.editReply(`檢查失敗：${error.message}`);
      }
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
