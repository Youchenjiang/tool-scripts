const { MessageFlags, PermissionFlagsBits } = require('discord.js');

function createEventInteractionHandler({ config, getEventService, runEventPublisher }) {
  async function handleComponent(interaction) {
    if (!interaction.customId?.startsWith('events:')) return false;
    try {
      const eventService = getEventService();
      if (eventService) await eventService.handle(interaction);
      else await interaction.reply({ content: '活動功能尚未準備完成。', flags: MessageFlags.Ephemeral });
    } catch (error) {
      console.error(`[Events interaction] ${error.stack || error.message}`);
      if (interaction.deferred) await interaction.editReply({ content: '操作失敗，請稍後再試。' });
      else if (!interaction.replied) {
        await interaction.reply({ content: '操作失敗，請稍後再試。', flags: MessageFlags.Ephemeral });
      }
    }
    return true;
  }

  async function handleStatus(interaction) {
    if (!config.eventsEnabled) {
      await interaction.reply({ content: '資安活動推送目前未啟用。', flags: MessageFlags.Ephemeral });
      return;
    }
    const status = getEventService()?.getStatus();
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
  }

  async function handleRunNow(interaction) {
    if (!interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild)) {
      await interaction.reply({ content: '你需要「管理伺服器」權限。', flags: MessageFlags.Ephemeral });
      return;
    }
    if (!getEventService()) {
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
  }

  async function handle(interaction) {
    if (await handleComponent(interaction)) return true;
    if (!interaction.isChatInputCommand()) return false;
    if (interaction.commandName === 'events_status') {
      await handleStatus(interaction);
      return true;
    }
    if (interaction.commandName === 'events_now') {
      await handleRunNow(interaction);
      return true;
    }
    return false;
  }

  return { handle };
}

module.exports = { createEventInteractionHandler };
