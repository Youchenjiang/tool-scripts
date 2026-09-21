const { MessageFlags } = require('discord.js');
const { fetchSecurityEvents } = require('./event-feed');
const { isEligibleEvent } = require('./event-eligibility');
const { normalizeEventRecord, eventEndTime } = require('./event-model');
const { keyFor, boardMessage } = require('./event-board');
const { publishWeekly } = require('./event-weekly');
const { publishNewActivities } = require('./event-announcements');
const { subscribe, unsubscribe, pruneSubscriptions, detailMessage, deliverReminders, sendMemberReminder } = require('./event-subscriptions');

function createEventService({ channel, config, stateStore, fetchEventsImpl = fetchSecurityEvents, now = () => new Date(),
  sendReminderImpl = (userId, payload) => sendMemberReminder(channel, userId, payload) }) {
  let queue = Promise.resolve();
  let latestResult = null;
  let running = false;
  function exclusive(action) {
    const next = queue.then(action);
    queue = next.catch(() => {});
    return next;
  }
  const load = async () => (await stateStore.loadEventDocument(config.eventChannelId))
    || { events: {}, subscriptions: {}, boardId: null, lastCheckedAt: null };
  const save = (state) => stateStore.saveEventDocument(config.eventChannelId, state);
  async function updateBoard(state) {
    const payload = boardMessage(state, { timeZone: config.eventTimeZone, now: now() });
    let message;
    if (state.boardId) {
      try { message = await channel.messages.fetch(state.boardId); }
      catch (error) { if (error.code !== 10008) throw error; }
    }
    if (message) await message.edit(payload);
    else {
      message = await channel.send({ ...payload, flags: payload.flags | MessageFlags.SuppressNotifications });
      state.boardId = message.id;
      await save(state);
    }
    try { if (!message.pinned) await message.pin(); }
    catch (error) { return `活動總表無法置頂：${error.message}`; }
    return null;
  }
  async function run({ force = false } = {}) {
    if (running) return { skipped: true, reason: '活動檢查正在執行中' };
    running = true;
    try {
      return await exclusive(async () => {
        const current = now();
        const state = await load();
        const { events, errors } = await fetchEventsImpl(config, { now: current });
        const old = state.events || {};
        const updated = {};
        // A partial outage must not erase otherwise valid activities.
        if (errors.length) for (const [key, record] of Object.entries(old)) {
          const event = normalizeEventRecord(record.event);
          if (event && isEligibleEvent(event) && eventEndTime(event) >= current.getTime()) updated[key] = { ...record, stale: true };
        }
        for (const raw of events) {
          const event = normalizeEventRecord(raw);
          if (!event || !isEligibleEvent(event) || eventEndTime(event) < current.getTime()) continue;
          const aliasKey = Object.keys(old).find((key) => old[key].event.aliases?.some((id) => event.aliases.includes(id)));
          updated[aliasKey || keyFor(event)] = { event, verifiedAt: current.toISOString(), stale: false };
        }
        state.events = updated;
        state.sourceErrors = errors;
        pruneSubscriptions(state, current);
        state.lastCheckedAt = current.toISOString();
        await save(state);
        const boardError = await updateBoard(state);
        const activities = await publishNewActivities({ state, channel, config, now: current, save });
        const published = await publishWeekly({ state, channel, config, now: current, save });
        state.lastCompletedAt = current.toISOString();
        await save(state);
        const reminders = await deliverReminders({ state, config, now: current, save, send: sendReminderImpl });
        latestResult = { checked: events.length, discovered: Object.keys(updated).filter((key) => !old[key]).length,
          published, activityDiscovered: activities.discovered, activityPublished: activities.published,
          reminders, boardId: state.boardId, sourceErrors: [...errors, ...(boardError ? [boardError] : [])], at: state.lastCheckedAt };
        return latestResult;
      });
    } finally { running = false; }
  }
  async function handle(interaction) {
    if (!interaction.customId?.startsWith('events:')) return false;
    const dmUnsubscribe = !interaction.guildId && interaction.customId.startsWith('events:unsub:');
    if (!dmUnsubscribe && (interaction.channelId !== config.eventChannelId || interaction.guildId !== channel.guild.id)) {
      await interaction.reply({ content: '請從活動頻道使用此功能。', flags: MessageFlags.Ephemeral });
      return true;
    }
    await interaction.deferReply(interaction.guildId ? { flags: MessageFlags.Ephemeral } : {});
    await exclusive(async () => {
      const state = await load();
      const [, action, filter, page] = interaction.customId.split(':');
      if (action === 'view') {
        const visible = filter === 'mine' ? { ...state, events: Object.fromEntries(Object.entries(state.events)
          .filter(([key]) => state.subscriptions?.[`${interaction.user.id}:${key}`])) } : state;
        await interaction.editReply(boardMessage(visible, { timeZone: config.eventTimeZone, now: now(), filter, page: Number(page) }));
      } else if (action === 'select') {
        await interaction.editReply(detailMessage(state, interaction.values[0], interaction.user.id, config, now()));
      } else if (action === 'sub' || action === 'unsub') {
        if (action === 'sub') {
          try { subscribe(state, interaction.user.id, filter, now()); }
          catch (error) { await interaction.editReply({ content: error.message }); return; }
        } else unsubscribe(state, interaction.user.id, filter);
        await save(state);
        await interaction.editReply(dmUnsubscribe ? { content: '已取消此活動提醒。', components: [] }
          : detailMessage(state, filter, interaction.user.id, config, now()));
      } else {
        await interaction.editReply({ content: '此操作已失效，請重新開啟活動總表。' });
      }
    });
    return true;
  }
  return { run, handle, getStatus: () => ({ running, latestResult, stateStore: stateStore.kind }) };
}

module.exports = { createEventService };
