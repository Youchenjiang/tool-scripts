const { ActionRowBuilder, EmbedBuilder } = require('discord.js');
const { currentEvents, fingerprint, button } = require('./event-board');
const { eventStartTime } = require('./event-model');
const { eventTechnicalLine } = require('./event-publisher');

const DAY = 86400000;
const WEEKLY_FORMAT_VERSION = 8;
const EMBED_TEXT_BUDGET = 5800;
const EMBED_DESCRIPTION_LIMIT = 3800;
const DEADLINE_LABELS = { registration: '報名截止', submission: '提交截止', selection: '甄選截止', materials: '資料截止' };
const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日'];

function weekKey(now, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now).map(({ type, value }) => [type, value]));
  const day = new Date(Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day)));
  day.setUTCDate(day.getUTCDate() - (day.getUTCDay() + 6) % 7);
  return day.toISOString().slice(0, 10);
}

function weekDayIndex(now, timeZone) {
  const week = new Date(`${weekKey(now, timeZone)}T00:00:00Z`);
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now).map(({ type, value }) => [type, value]));
  const localDate = new Date(Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day)));
  return Math.floor((localDate - week) / 86400000);
}

function localParts(value, timeZone) {
  return Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(value).filter(({ type }) => type !== 'literal').map(({ type, value: part }) => [type, part]));
}

function localDateKey(value, timeZone) {
  const parts = localParts(value, timeZone);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function knownDeadline(event, now) {
  return (event.deadlines || []).map((deadline) => ({ ...deadline, at: new Date(deadline.at) }))
    .filter(({ at, kind }) => DEADLINE_LABELS[kind] && Number.isFinite(at.getTime()) && at >= now)
    .sort((left, right) => left.at - right.at)[0] || null;
}

function safeTitle(value) { return String(value || '').replace(/[\[\]]/gu, '').trim().slice(0, 180); }

function weekDateKeys(week) {
  const start = new Date(`${week}T00:00:00Z`);
  return Array.from({ length: 7 }, (_, index) => new Date(start.getTime() + index * DAY).toISOString().slice(0, 10));
}

function discordTime(value, style) {
  return `<t:${Math.floor(new Date(value).getTime() / 1000)}:${style}>`;
}

function localClock(value, timeZone, includeDate = false) {
  const parts = localParts(value, timeZone);
  return `${includeDate ? `${parts.month}/${parts.day} ` : ''}${parts.hour}:${parts.minute}`;
}

function dailyStatus(event, dateKey, timeZone) {
  const start = new Date(event.startsAt || event.start || '');
  const finish = new Date(event.endsAt || event.finish || event.startsAt || event.start || '');
  const startKey = localDateKey(start, timeZone);
  const finishKey = localDateKey(finish, timeZone);
  if (startKey === dateKey && finishKey === dateKey) {
    return `${localClock(start, timeZone)}–${localClock(finish, timeZone)}（${discordTime(finish, 'R')}結束）`;
  }
  if (startKey === dateKey) return `${localClock(start, timeZone)} 開始・${localClock(finish, timeZone, true)} 結束（${discordTime(finish, 'R')}）`;
  if (finishKey === dateKey) return `進行至 ${localClock(finish, timeZone)}（${discordTime(finish, 'R')}）`;
  return `持續進行・${localClock(finish, timeZone, true)} 結束（${discordTime(finish, 'R')}）`;
}

function dailyGroups(entries, config, week) {
  return weekDateKeys(week).map((dateKey, index) => {
    const values = entries.filter(({ event }) => {
      const start = new Date(event.startsAt || event.start || '');
      const finish = new Date(event.endsAt || event.finish || event.startsAt || event.start || '');
      if (!Number.isFinite(start.getTime()) || !Number.isFinite(finish.getTime())) return false;
      return localDateKey(start, config.eventTimeZone) <= dateKey
        && localDateKey(finish, config.eventTimeZone) >= dateKey;
    }).sort((left, right) => eventStartTime(left.event) - eventStartTime(right.event)
      || left.event.title.localeCompare(right.event.title));
    const [, month, day] = dateKey.split('-');
    return { dateKey, title: `${Number(month)}/${Number(day)}（${WEEKDAYS[index]}）`, values };
  });
}

function deadlineEntries(entries, now, week, timeZone) {
  const dates = weekDateKeys(week);
  return entries.flatMap((entry) => {
    const deadline = knownDeadline(entry.event, now);
    if (!deadline) return [];
    const dateKey = localDateKey(deadline.at, timeZone);
    return dateKey >= dates[0] && dateKey <= dates[6] ? [{ ...entry, deadline }] : [];
  }).sort((left, right) => left.deadline.at - right.deadline.at);
}

function dailyEmbeds(entries, config, now, week) {
  const embeds = [];
  let used = 0;
  let omitted = 0;
  const deadlines = deadlineEntries(entries, now, week, config.eventTimeZone);
  if (deadlines.length) {
    const lines = [];
    for (const { event, deadline } of deadlines) {
      const text = `**${DEADLINE_LABELS[deadline.kind]} ${localClock(deadline.at, config.eventTimeZone, true)}｜[${safeTitle(event.title)}](${event.officialUrl || event.url})**`;
      if (lines.join('\n').length + text.length > EMBED_DESCRIPTION_LIMIT) omitted += 1;
      else lines.push(text);
    }
    const description = lines.join('\n');
    embeds.push(new EmbedBuilder().setColor(0xF0B232).setTitle('本週報名期限').setDescription(description).toJSON());
    used += '本週報名期限'.length + description.length;
  }
  for (const group of dailyGroups(entries, config, week)) {
    const lines = [];
    for (const { event } of group.values) {
      const technical = eventTechnicalLine(event);
      const text = `**[${safeTitle(event.title)}](${event.officialUrl || event.url})**｜${technical ? `${technical}｜` : ''}${dailyStatus(event, group.dateKey, config.eventTimeZone)}`;
      if (used + group.title.length + lines.join('\n').length + text.length > EMBED_TEXT_BUDGET) omitted += 1;
      else lines.push(text);
    }
    const description = lines.join('\n') || '沒有賽事';
    embeds.push(new EmbedBuilder().setColor(0x5865F2).setTitle(group.title).setDescription(description).toJSON());
    used += group.title.length + description.length;
  }
  return { embeds, omitted };
}

function weeklyData(state, config, now) {
  const week = weekKey(now, config.eventTimeZone);
  const dates = weekDateKeys(week);
  const entries = currentEvents(state, now).filter(({ event, stale }) => {
    if (stale || event.kind !== 'ctf') return false;
    const start = new Date(event.startsAt || event.start || '');
    const finish = new Date(event.endsAt || event.finish || event.startsAt || event.start || '');
    const overlapsWeek = Number.isFinite(start.getTime()) && Number.isFinite(finish.getTime())
      && localDateKey(start, config.eventTimeZone) <= dates[6]
      && localDateKey(finish, config.eventTimeZone) >= dates[0];
    const deadlineThisWeek = event.deadlines.some(({ at }) => {
      const key = localDateKey(at, config.eventTimeZone);
      return key >= dates[0] && key <= dates[6];
    });
    return overlapsWeek || deadlineThisWeek;
  });
  const signature = fingerprint({ format: WEEKLY_FORMAT_VERSION,
    entries: entries.map(({ key, event }) => ({ key, event })), partial: Boolean(state.sourceErrors?.length) });
  const { embeds, omitted } = dailyEmbeds(entries, config, now, week);
  let content = `**本週 CTF｜${dates[0].slice(5).replace('-', '/')}～${dates[6].slice(5).replace('-', '/')}**`;
  if (state.sourceErrors?.length) content += '\n部分來源暫時無法更新；本期僅列已確認賽事。';
  if (omitted) content += `\n另有 ${omitted} 個當日項目超出顯示容量，請從完整 CTF 賽程查看。`;
  const payload = {
    content, embeds, flags: 0, allowedMentions: { parse: [] }, attachments: [],
    components: [new ActionRowBuilder().addComponents(button('events:view:ctf:0', '完整 CTF 賽程'))],
    files: [],
  };
  return { week, signature, payload, count: entries.length };
}

async function publishWeekly({ state, channel, config, now, save }) {
  if (config.eventWeeklyEnabled === false) return 0;
  const next = weeklyData(state, config, now);
  const previous = state.weekly;
  if (previous?.signature === next.signature) return 0;
  if (!next.count && previous?.week !== next.week) return 0;
  if (previous && previous.week !== next.week && weekDayIndex(now, config.eventTimeZone) > 1) return 0;
  let message;
  if (previous?.week === next.week && previous.messageId) {
    try { message = await channel.messages.fetch(previous.messageId); }
    catch (error) { if (error.code !== 10008) throw error; }
  }
  if (message) await message.edit(next.payload);
  else message = await channel.send(next.payload);
  state.weekly = { week: next.week, signature: next.signature, messageId: message.id };
  await save(state);
  return previous?.week === next.week ? 0 : 1;
}

module.exports = { dailyGroups, dailyStatus, weekDayIndex, weekKey, weeklyData, publishWeekly };
