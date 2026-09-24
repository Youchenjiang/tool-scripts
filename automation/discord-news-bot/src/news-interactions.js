const { MessageFlags, PermissionFlagsBits } = require('discord.js');
const { createTechnicalDetailReply } = require('./publisher');
const { formatRuleConfig } = require('./rule-options');

function createNewsInteractionHandler({ config, getPublisher, getRuleSetup, runPublisher }) {
  async function handleDetail(interaction) {
    if (!interaction.isButton() || !interaction.customId.startsWith('news_detail:')) return false;
    const publisher = getPublisher();
    if (!publisher) {
      await interaction.reply({ content: 'Bot 尚未準備完成，請稍後再試。', flags: MessageFlags.Ephemeral });
      return true;
    }
    try {
      const detail = await publisher.getNewsDetail(interaction.customId.slice('news_detail:'.length));
      if (!detail) {
        await interaction.reply({
          content: '這則新聞的技術細節已不存在，請改由原訊息開啟原文。',
          flags: MessageFlags.Ephemeral,
        });
        return true;
      }
      await interaction.reply(createTechnicalDetailReply(detail));
    } catch (error) {
      console.error(`[News detail] ${error.stack || error.message}`);
      if (!interaction.replied && !interaction.deferred) {
        await interaction.reply({ content: `讀取技術細節失敗：${error.message}`, flags: MessageFlags.Ephemeral });
      }
    }
    return true;
  }

  async function handleRuleComponent(interaction) {
    if (!interaction.isButton() && !interaction.isStringSelectMenu() && !interaction.isModalSubmit()) return false;
    try {
      await getRuleSetup()?.handle(interaction);
    } catch (error) {
      console.error(`[Rule setup] ${error.stack || error.message}`);
      if (!interaction.replied && !interaction.deferred) {
        await interaction.reply({ content: `規則設定失敗：${error.message}`, flags: MessageFlags.Ephemeral });
      }
    }
    return true;
  }

  async function handleStatus(interaction) {
    const status = getPublisher()?.getStatus();
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
  }

  async function handleRuleCommand(interaction) {
    if (interaction.channelId !== config.channelId) {
      await interaction.reply({
        content: `請在指定的新聞頻道 <#${config.channelId}> 設定規則。`,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }
    const publisher = getPublisher();
    if (!publisher) {
      await interaction.reply({ content: 'Bot 尚未完成啟動，請稍後再試。', flags: MessageFlags.Ephemeral });
      return;
    }
    const action = interaction.options.getSubcommand();
    if (action !== 'show' && !interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
      await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
      return;
    }
    if (action === 'setup') {
      await getRuleSetup().start(interaction);
      return;
    }
    await interaction.deferReply(action === 'show' ? {} : { flags: MessageFlags.Ephemeral });
    try {
      if (action === 'show') {
        const rule = await publisher.getFilterRule();
        await interaction.editReply(rule
          ? `目前規則（版本 ${rule.version}）：\n${formatRuleConfig(rule.config)}`
          : '目前沒有規則；AI 新聞推送會保持停止。');
      } else if (action === 'clear') {
        await publisher.setFilterRule(null, interaction.user.id);
        await interaction.editReply('已清除規則；AI 新聞推送會保持停止。');
      }
    } catch (error) {
      await interaction.editReply(`規則操作失敗：${error.message}`);
    }
  }

  async function handleAiCheck(interaction) {
    if (!interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
      await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
      return;
    }
    const publisher = getPublisher();
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
  }

  async function handleRunNow(interaction) {
    if (!interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
      await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
      return;
    }
    if (!getPublisher()) {
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

  async function handle(interaction) {
    if (await handleDetail(interaction)) return true;
    if (await handleRuleComponent(interaction)) return true;
    if (!interaction.isChatInputCommand()) return false;
    if (interaction.commandName === 'news_status') await handleStatus(interaction);
    else if (interaction.commandName === 'news_rule') await handleRuleCommand(interaction);
    else if (interaction.commandName === 'news_ai_check') await handleAiCheck(interaction);
    else if (interaction.commandName === 'news_now') await handleRunNow(interaction);
    else return false;
    return true;
  }

  return { handle };
}

module.exports = { createNewsInteractionHandler };
