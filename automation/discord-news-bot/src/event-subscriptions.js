const { ActionRowBuilder, MessageFlags, PermissionFlagsBits } = require('discord.js');
const { normalizeEventRecord, eventEndTime } = require('./event-model');
const { compactEvent, button } = require('./event-board');
const { fullAddressLine } = require('./event-publisher');

const subscriptionId = (userId, eventKey) => `${userId}:${eventKey}`;
function subscribe(state, userId, eventKey, now) {
  const event = normalizeEventRecord(state.events[eventKey]?.event);
  if (!event || eventEndTime(event) < now.getTime()) throw new Error('活動已結束或不再列入總表。');
  state.subscriptions ||= {};
  const id = subscriptionId(userId, eventKey);
  if (state.subscriptions[id]) return;
  if (Object.values(state.subscriptions).filter((item) => item.userId === userId).length >= 20) {
    throw new Error('最多訂閱 20 場活動，請先取消不需要的訂閱。');
  }
  state.subscriptions[id] = { userId, eventKey, createdAt: now.toISOString(), notices: {} };
}
function unsubscribe(state, userId, eventKey) {
  delete (state.subscriptions || {})[subscriptionId(userId, eventKey)];
}
function pruneSubscriptions(state, now) {
  for (const [id, item] of Object.entries(state.subscriptions || {})) {
    const event = normalizeEventRecord(state.events[item.eventKey]?.event);
    if (!event || eventEndTime(event) < now.getTime()) delete state.subscriptions[id];
  }
}
function detailMessage(state, key, userId, config, now) {
  const event = normalizeEventRecord(state.events[key]?.event);
  if (!event || eventEndTime(event) < now.getTime()) return { content: '活動已結束或不再列入總表。', components: [] };
  const item = state.subscriptions?.[subscriptionId(userId, key)];
  const failed = Object.values(item?.notices || {}).some((notice) => notice.status === 'failed' || notice.status === 'sending');
  const status = item ? '已訂閱：報名截止及開賽前 24 小時私訊提醒。' : '訂閱後，報名截止及開賽前 24 小時會收到私訊。';
  return {
    content: `${compactEvent(event, config.eventTimeZone, now)}${fullAddressLine(event) ? `\n${fullAddressLine(event)}` : ''}\n\n${status}${failed ? '\n先前私訊未確認送達；請檢查私訊權限。' : ''}`.slice(0, 2000),
    allowedMentions: { parse: [] }, flags: MessageFlags.SuppressEmbeds,
    components: [new ActionRowBuilder().addComponents(
      button(`events:${item ? 'unsub' : 'sub'}:${key}`, item ? '取消訂閱' : '訂閱私訊提醒'),
      button('events:view:mine:0', '我的訂閱'),
    )],
  };
}
function dueNotices(event, now) {
  const targets = [
    ...(event.startsAt ? [{ kind: 'start', at: event.startsAt, label: '活動將於 24 小時內開始' }] : []),
    ...event.deadlines.filter(({ kind }) => kind === 'registration')
      .map(({ at }) => ({ kind: 'registration', at, label: '報名將於 24 小時內截止' })),
  ];
  return targets.filter(({ at }) => at > now && at.getTime() - now.getTime() <= 86400000);
}

async function sendMemberReminder(channel, userId, payload) {
  const member = await channel.guild.members.fetch(userId);
  if (!channel.permissionsFor(member)?.has(PermissionFlagsBits.ViewChannel)) throw new Error('Member no longer has access to activity channel');
  await member.send(payload);
}

async function deliverReminders({ state, config, now, save, send }) {
  pruneSubscriptions(state, now);
  let sent = 0; let failed = 0;
  for (const item of Object.values(state.subscriptions || {})) {
    const record = state.events[item.eventKey];
    if (record.stale || !record.verifiedAt || now - new Date(record.verifiedAt) > 36 * 3600000) continue;
    const event = normalizeEventRecord(record.event);
    for (const notice of dueNotices(event, now)) {
      const id = `${notice.kind}:${notice.at.toISOString()}`;
      if (item.notices[id]) continue;
      // Persist intent before sending: restart after an uncertain delivery must not resend it.
      item.notices[id] = { status: 'sending', at: now.toISOString() };
      await save(state);
      try {
        await send(item.userId, {
          content: `**${notice.label}**\n${compactEvent(event, config.eventTimeZone, now)}`.slice(0, 2000),
          allowedMentions: { parse: [] }, flags: MessageFlags.SuppressEmbeds,
          components: [new ActionRowBuilder().addComponents(
            button(`events:unsub:${config.eventChannelId}:${item.eventKey}`, '取消此活動提醒'),
          )],
        });
        item.notices[id].status = 'sent'; sent += 1;
      } catch (error) {
        item.notices[id] = { status: 'failed', at: now.toISOString(), error: String(error.message).slice(0, 200) };
        failed += 1;
      }
      await save(state);
    }
  }
  return { sent, failed };
}

module.exports = { subscribe, unsubscribe, pruneSubscriptions, detailMessage, deliverReminders, sendMemberReminder };
