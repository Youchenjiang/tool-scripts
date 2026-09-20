const { ActionRowBuilder } = require('discord.js');
const { currentEvents, fingerprint, button } = require('./event-board');
const { curateWeeklyEntries, futureDeadline, participationReason, DAY } = require('./event-curation');
const { eventStartTime } = require('./event-model');
const { eventDecisionLine, eventTimingLine } = require('./event-publisher');

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

function weeklyData(state, config, now) {
  const limit = now.getTime() + 28 * 86400000;
  const entries = currentEvents(state, now).filter(({ event, stale }) => !stale
    && (eventStartTime(event) <= limit
      || event.deadlines.some(({ at }) => at.getTime() >= now.getTime() && at.getTime() <= limit)));
  const signature = fingerprint({ entries: entries.map(({ key, event }) => ({ key, event })), partial: Boolean(state.sourceErrors?.length) });
  const week = weekKey(now, config.eventTimeZone);
  const curated = curateWeeklyEntries(entries, now, 8);
  let content = `**本週資安活動｜${week}**\n未來四週內值得留意的活動與報名期限\n`;
  if (state.sourceErrors?.length) content += '部分來源暫時無法更新；本期僅列已確認活動。\n';

  function summary(event) {
    return [
      `[${String(event.title || '').replace(/[\[\]]/gu, '').slice(0, 180)}](${event.officialUrl || event.url})`,
      eventDecisionLine(event).replace(/｜程度未標示/gu, '').replace(/｜人數未公開/gu, ''),
      eventTimingLine(event, config.eventTimeZone, now), participationReason(event),
    ].filter(Boolean).join('\n');
  }

  const urgent = curated.selected.filter(({ event }) => futureDeadline(event, now) - now.getTime() <= 7 * DAY);
  const upcoming = curated.selected.filter((entry) => !urgent.includes(entry));
  const visible = [];
  const omitted = [];
  for (const [heading, group] of [['即將截止', urgent], ['近期活動', upcoming]]) {
    if (!group.length) continue;
    let sectionStarted = false;
    for (const entry of group) {
      const text = summary(entry.event);
      const addition = `${sectionStarted ? '\n' : `\n**${heading}**\n`}${text}\n`;
      if (content.length + addition.length <= 1600) {
        content += addition; sectionStarted = true; visible.push(entry);
      } else omitted.push(entry);
    }
  }
  const competitionOverflow = [...curated.competitionOverflow, ...omitted.filter(({ event }) => ['ctf', 'competition'].includes(event.kind))];
  const otherOverflow = [...curated.otherOverflow, ...omitted.filter(({ event }) => !['ctf', 'competition'].includes(event.kind))];
  if (competitionOverflow.length) {
    const names = competitionOverflow.slice(0, 3).map(({ event }) => event.title).join('、');
    content += `\n**其他 CTF 行程**\n${names}${competitionOverflow.length > 3 ? `等 ${competitionOverflow.length} 場` : ''}，完整時間與參賽資訊請從活動總表查看。\n`;
  }
  const hidden = competitionOverflow.length + otherOverflow.length;
  content += `\n本期收錄 ${entries.length} 場，公開整理 ${visible.length} 場${hidden ? `，其餘 ${hidden} 場保留在活動總表` : ''}。`;
  const payload = {
    content, allowedMentions: { parse: [] }, attachments: [],
    components: [new ActionRowBuilder().addComponents(button('events:view:all:0', '完整活動總表'))],
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
  if (previous?.week !== next.week && weekDayIndex(now, config.eventTimeZone) > 1) return 0;
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

module.exports = { weekDayIndex, weekKey, weeklyData, publishWeekly };
