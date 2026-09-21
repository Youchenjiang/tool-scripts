const { ActionRowBuilder, EmbedBuilder } = require('discord.js');
const { currentEvents, fingerprint, button } = require('./event-board');
const { eventStartTime } = require('./event-model');

const DAY = 86400000;
const WEEKLY_FORMAT_VERSION = 6;
const EMBED_TEXT_BUDGET = 5800;
const EMBED_DESCRIPTION_LIMIT = 3800;
const TOPIC_LABELS = {
  web: 'Web', pwn: 'Pwn', reverse: 'Reverse', crypto: 'Crypto', forensics: '鑑識', malware: '惡意程式',
  'threat-intelligence': '威脅情資', 'threat-hunting': '威脅獵捕', 'detection-engineering': '偵測工程',
  network: '網路安全', cloud: '雲端安全', ics: 'ICS/OT', mobile: '行動安全', web3: 'Web3', 'ai-security': 'AI 安全',
};
const DEADLINE_LABELS = { registration: '報名截止', submission: '提交截止', selection: '甄選截止', materials: '資料截止' };

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

function shortDateTime(value, timeZone) {
  const parts = localParts(value, timeZone);
  return `${parts.month}/${parts.day} ${parts.hour}:${parts.minute}`;
}

function scheduleText(event, timeZone) {
  const start = new Date(event.startsAt || event.start || '');
  const finish = new Date(event.endsAt || event.finish || event.startsAt || event.start || '');
  if (!Number.isFinite(start.getTime())) return '';
  const startText = shortDateTime(start, timeZone);
  if (!Number.isFinite(finish.getTime()) || finish.getTime() === start.getTime()) return startText;
  const startParts = localParts(start, timeZone);
  const finishParts = localParts(finish, timeZone);
  const sameDay = startParts.year === finishParts.year && startParts.month === finishParts.month && startParts.day === finishParts.day;
  return `${startText}–${sameDay ? `${finishParts.hour}:${finishParts.minute}` : shortDateTime(finish, timeZone)}`;
}

function attendanceText(event) {
  if (event.attendance === 'online') return '線上';
  if (event.attendance === 'onsite') return event.location ? `實體・${event.location}` : '實體';
  if (event.attendance === 'hybrid') return event.location ? `線上／實體・${event.location}` : '線上／實體';
  return '';
}

function teamText(event) {
  if (['不限人數', '人數不限'].includes(event.teamSize)) return '不限人數';
  if (event.teamSizeMin && event.teamSizeMax) {
    return event.teamSizeMin === event.teamSizeMax ? `每隊 ${event.teamSizeMax} 人` : `每隊 ${event.teamSizeMin}–${event.teamSizeMax} 人`;
  }
  if (event.teamSizeMax) return `每隊最多 ${event.teamSizeMax} 人`;
  const range = String(event.teamSize || '').match(/^(\d+)～(\d+)人$/u);
  if (range) return `每隊 ${range[1]}–${range[2]} 人`;
  const maximum = String(event.teamSize || '').match(/^(\d+)人$/u);
  if (maximum) return `每隊最多 ${maximum[1]} 人`;
  if (event.participation === 'individual') return '個人賽';
  if (event.participation === 'team') return '團隊賽';
  return '';
}

function topicText(event) {
  const topics = (event.topics || []).map((topic) => TOPIC_LABELS[topic] || topic).filter(Boolean);
  return topics.length ? `題型 ${topics.slice(0, 5).join('／')}${topics.length > 5 ? `／另 ${topics.length - 5} 類` : ''}` : '';
}

function levelText(event) {
  return { beginner: '入門', foundational: '需具基礎', advanced: '進階' }[event.level] || '';
}

function knownDeadline(event, now) {
  return (event.deadlines || []).map((deadline) => ({ ...deadline, at: new Date(deadline.at) }))
    .filter(({ at, kind }) => DEADLINE_LABELS[kind] && Number.isFinite(at.getTime()) && at >= now)
    .sort((left, right) => left.at - right.at)[0] || null;
}

function safeTitle(value) { return String(value || '').replace(/[\[\]]/gu, '').trim().slice(0, 180); }

function entryText(event, config, group, deadline) {
  const schedule = scheduleText(event, config.eventTimeZone);
  const title = `[${safeTitle(event.title)}](${event.officialUrl || event.url})`;
  const lead = group === '即將截止'
    ? `${DEADLINE_LABELS[deadline.kind]} ${shortDateTime(deadline.at, config.eventTimeZone)}`
    : schedule;
  const facts = [
    group === '即將截止' && schedule ? `賽程 ${schedule}` : '', attendanceText(event),
    teamText(event), levelText(event), topicText(event),
  ].filter(Boolean);
  return `**${lead ? `${lead}｜` : ''}${title}**${facts.length ? `\n${facts.join('・')}` : ''}`;
}

function scheduleGroups(entries, config, now, week) {
  const groups = new Map([
    ['即將截止', []], ['進行中', []], ['本週開賽', []], ['下週開賽', []], ['後續賽程', []],
  ]);
  const weekTime = new Date(`${week}T00:00:00Z`).getTime();
  for (const entry of entries) {
    const { event } = entry;
    const deadline = knownDeadline(event, now);
    const start = new Date(event.startsAt || event.start || '');
    const finish = new Date(event.endsAt || event.finish || event.startsAt || event.start || '');
    let group;
    if (deadline && deadline.at.getTime() - now.getTime() <= 7 * DAY) group = '即將截止';
    else if (Number.isFinite(start.getTime()) && start <= now && finish >= now) group = '進行中';
    else {
      const dateKey = Number.isFinite(start.getTime()) ? localDateKey(start, config.eventTimeZone) : week;
      const offset = Math.floor((new Date(`${dateKey}T00:00:00Z`).getTime() - weekTime) / DAY);
      group = offset < 7 ? '本週開賽' : offset < 14 ? '下週開賽' : '後續賽程';
    }
    groups.get(group).push({ ...entry, deadline });
  }
  for (const [name, values] of groups) values.sort((left, right) => {
    const leftTime = name === '即將截止' ? left.deadline.at.getTime() : eventStartTime(left.event);
    const rightTime = name === '即將截止' ? right.deadline.at.getTime() : eventStartTime(right.event);
    return leftTime - rightTime || left.event.title.localeCompare(right.event.title);
  });
  return groups;
}

function scheduleEmbeds(groups, config) {
  const embeds = [];
  let used = 0;
  let omitted = 0;
  for (const [heading, entries] of groups) {
    let title = heading;
    let description = '';
    for (const entry of entries) {
      const text = entryText(entry.event, config, heading, entry.deadline);
      const addition = `${description ? '\n\n' : ''}${text}`;
      if (description && description.length + addition.length > EMBED_DESCRIPTION_LIMIT) {
        embeds.push(new EmbedBuilder().setColor(0x5865F2).setTitle(title).setDescription(description).toJSON());
        used += title.length + description.length;
        title = `${heading}（續）`;
        description = '';
      }
      if (used + title.length + description.length + text.length > EMBED_TEXT_BUDGET || embeds.length >= 9) {
        omitted += 1;
        continue;
      }
      description += `${description ? '\n\n' : ''}${text}`;
    }
    if (description) {
      embeds.push(new EmbedBuilder().setColor(0x5865F2).setTitle(title).setDescription(description).toJSON());
      used += title.length + description.length;
    }
  }
  return { embeds, omitted };
}

function weeklyData(state, config, now) {
  const limit = now.getTime() + 28 * 86400000;
  const entries = currentEvents(state, now).filter(({ event, stale }) => !stale
    && event.kind === 'ctf'
    && (eventStartTime(event) <= limit
      || event.deadlines.some(({ at }) => at.getTime() >= now.getTime() && at.getTime() <= limit)));
  const signature = fingerprint({ format: WEEKLY_FORMAT_VERSION,
    entries: entries.map(({ key, event }) => ({ key, event })), partial: Boolean(state.sourceErrors?.length) });
  const week = weekKey(now, config.eventTimeZone);
  const groups = scheduleGroups(entries, config, now, week);
  const { embeds, omitted } = scheduleEmbeds(groups, config);
  let content = `**本週 CTF 賽程｜${week}**`;
  if (state.sourceErrors?.length) content += '\n部分來源暫時無法更新；本期僅列已確認賽事。';
  if (omitted) content += `\n另有 ${omitted} 場超出 Discord 顯示容量，請從完整 CTF 賽程查看。`;
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

module.exports = { scheduleText, teamText, weekDayIndex, weekKey, weeklyData, publishWeekly };
