const { createHash } = require('node:crypto');
const { ActionRowBuilder, ButtonBuilder, ButtonStyle, MessageFlags, StringSelectMenuBuilder } = require('discord.js');
const { normalizeEventRecord, eventEndTime, eventStartTime } = require('./event-model');
const { createEventMessage } = require('./event-publisher');

const keyFor = (event) => createHash('sha256').update(event.id).digest('hex').slice(0, 24);
const fingerprint = (value) => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const isCtf = (event) => event.kind === 'ctf';
const isCompetition = (event) => event.kind === 'competition';
function button(id, label, disabled = false) {
  return new ButtonBuilder().setCustomId(id).setLabel(label).setStyle(ButtonStyle.Secondary).setDisabled(disabled);
}
function compactEvent(event, timeZone, now) {
  return createEventMessage(event, timeZone, now).content
    .replace(/⚫ 方向未標示 · /gu, '')
    .replace(/｜程度未標示/gu, '')
    .replace(/｜人數未公開/gu, '');
}
function boardRow(event, timeZone, now) {
  const lines = createEventMessage(event, timeZone, now).content.split('\n');
  const decision = (lines[1] || '').replace(/｜程度未標示/gu, '').replace(/｜人數未公開/gu, '');
  const timing = lines.filter((line) => line.startsWith('📅') || line.startsWith('⏳')).join(' · ');
  return [lines[0], decision, timing].filter(Boolean).join('\n');
}
function currentEvents(document, now) {
  return Object.entries(document.events || {}).flatMap(([key, record]) => {
    const event = normalizeEventRecord(record.event);
    return event && eventEndTime(event) >= now.getTime() ? [{ key, event, stale: record.stale }] : [];
  }).sort((a, b) => eventStartTime(a.event) - eventStartTime(b.event));
}
function boardMessage(document, { timeZone = 'Asia/Taipei', now = new Date(), filter = 'all', page = 0 } = {}) {
  if (!['all', 'competition', 'ctf', 'community', 'mine'].includes(filter)) filter = 'all';
  const entries = currentEvents(document, now).filter(({ event }) => {
    if (filter === 'ctf') return isCtf(event);
    if (isCtf(event)) return false;
    if (filter === 'competition') return isCompetition(event);
    if (filter === 'community') return !isCompetition(event);
    return true;
  });
  const pages = [[]];
  let length = 0;
  for (const entry of entries) {
    const text = `${boardRow(entry.event, timeZone, now)}${entry.stale ? '\n來源暫時未確認' : ''}`;
    // Oversized source text is still available through the official link/detail button.
    entry.text = text.length > 1400 ? `${entry.event.title.slice(0, 150)}\n詳情請選擇下方活動。` : text;
    if (pages.at(-1).length && (length + entry.text.length > 1750 || pages.at(-1).length >= 10)) {
      pages.push([]); length = 0;
    }
    pages.at(-1).push(entry); length += entry.text.length + 2;
  }
  const index = Math.max(0, Math.min(Number.isInteger(page) ? page : 0, pages.length - 1));
  const selected = pages[index];
  const components = filter === 'ctf' ? [] : [new ActionRowBuilder().addComponents(
    button('events:view:all:0', '全部活動'), button('events:view:competition:0', '一般競賽'),
    button('events:view:community:0', '社群／課程'), button('events:view:mine:0', '我的訂閱'),
  )];
  if (pages.length > 1) components.push(new ActionRowBuilder().addComponents(
    button(`events:page:${filter}:${index - 1}`, '上一頁', index === 0),
    button(`events:page:${filter}:${index + 1}`, '下一頁', index === pages.length - 1),
  ));
  if (selected.length) components.push(new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder().setCustomId('events:select').setPlaceholder('查看活動／訂閱提醒')
      .addOptions(selected.map(({ key, event }) => ({ label: event.title.slice(0, 100), value: key }))),
  ));
  const date = document.lastCheckedAt ? new Intl.DateTimeFormat('sv-SE', { timeZone, dateStyle: 'short' }).format(new Date(document.lastCheckedAt)) : '尚未更新';
  return {
    content: `**${filter === 'ctf' ? '完整 CTF 賽程' : '資安活動總表'}**\n更新：${date}｜${entries.length} 場｜第 ${index + 1}/${pages.length} 頁\n\n${selected.map(({ text }) => text).join('\n\n') || '目前沒有符合條件的活動。'}`,
    components, allowedMentions: { parse: [] }, flags: MessageFlags.SuppressEmbeds,
  };
}

module.exports = { keyFor, fingerprint, currentEvents, compactEvent, boardMessage, boardRow, button };
