const { MessageFlags } = require('discord.js');

const DIRECTION_LABELS = { red: '🔴 紅隊', blue: '🔵 藍隊', purple: '🟣 紫隊', general: '⚪ 綜合' };
const KIND_LABELS = { ctf: 'CTF', competition: '競賽', training: '培訓', workshop: '工作坊', conference: '研討會', community: '社群小聚', cfp: '徵稿', event: '活動' };
const LEVEL_LABELS = { beginner: '入門', foundational: '具基礎', advanced: '進階' };
const TOPIC_LABELS = {
  appsec: 'AppSec', api: 'API Security', devsecops: 'DevSecOps',
  web: 'Web', pwn: 'Pwn', reverse: 'Reverse', crypto: 'Crypto', forensics: 'Forensics', malware: 'Malware',
  'threat-intelligence': 'Threat Intelligence', 'threat-hunting': 'Threat Hunting', 'detection-engineering': 'Detection Engineering',
  network: 'Network', cloud: 'Cloud Security', ics: 'ICS/OT', mobile: 'Mobile Security', web3: 'Web3', 'ai-security': 'AI Security',
};
const DEADLINE_LABELS = { registration: '報名至', submission: '投稿至', selection: '甄選至', materials: '資料繳交至', unknown: '最近期限' };

function dateParts(date, timeZone, includeTime = false) {
  const options = { timeZone, year: 'numeric', month: '2-digit', day: '2-digit', ...(includeTime ? { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' } : {}) };
  return Object.fromEntries(new Intl.DateTimeFormat('en-CA', options).formatToParts(date)
    .filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]));
}

function formatCompactDate(date, timeZone) {
  const parts = dateParts(date, timeZone);
  return `${parts.year}${parts.month}${parts.day}`;
}

function formatDisplayDate(date, timeZone, includeTime = false, includeYear = true) {
  const parts = dateParts(date, timeZone, includeTime);
  const text = includeYear ? `${parts.year}/${parts.month}/${parts.day}` : `${parts.month}/${parts.day}`;
  return includeTime ? `${text} ${parts.hour}:${parts.minute}` : text;
}

function formatCompactDateTime(date, timeZone) {
  const parts = dateParts(date, timeZone, true);
  return `${parts.year}${parts.month}${parts.day} ${parts.hour}:${parts.minute}`;
}

function markdownLinkTitle(value) { return String(value || '').replace(/[\[\]]/gu, '').trim().slice(0, 200); }

function directionLabel(directions, kind) {
  const values = (directions || []).filter((value, index, all) => value !== 'unspecified' && all.indexOf(value) === index);
  return values.map((value) => DIRECTION_LABELS[value]).filter(Boolean).join('＋');
}

function participationLabel(event) {
  if (['不限人數', '人數不限'].includes(event.teamSize)) return '不限人數';
  if (event.teamSizeMin && event.teamSizeMax) return event.teamSizeMin === event.teamSizeMax ? `${event.teamSizeMax} 人` : `${event.teamSizeMin}～${event.teamSizeMax} 人`;
  if (event.teamSizeMax) return `最多 ${event.teamSizeMax} 人`;
  const range = String(event.teamSize || '').match(/^(\d+)～(\d+)人$/u);
  if (range) return `${range[1]}～${range[2]} 人`;
  const maximum = String(event.teamSize || '').match(/^(\d+)人$/u);
  if (maximum) return `最多 ${maximum[1]} 人`;
  if (event.participation === 'team') return '隊伍制';
  if (event.participation === 'individual') {
    if (event.kind === 'competition' || event.kind === 'ctf') return '個人參賽';
    if (event.kind === 'training') return '個人申請';
    return '個人報名';
  }
  return '';
}

function topicLine(topics) {
  if (!topics?.length) return '';
  const labels = topics.map((topic) => TOPIC_LABELS[topic] || topic).filter(Boolean);
  return `🧩 ${labels.slice(0, 3).join('、')}`;
}

function scheduleLine(event, timeZone) {
  const start = event.startsAt || event.start;
  const finish = event.endsAt || event.finish || start;
  if (start && finish && !event.allDay) return `📅 ${formatDisplayDate(start, timeZone, true)}～${formatDisplayDate(finish, timeZone, true, false)}`;
  if (start && finish && event.allDay) {
    const end = start.getTime() === finish.getTime() ? '' : `～${formatDisplayDate(finish, timeZone, false, false)}`;
    return `📅 ${formatDisplayDate(start, timeZone)}${end}`;
  }
  if (event.dateText) return `📅 ${event.dateText}（詳細時間請見官網）`;
  return '📅 活動日期請見官網';
}

function deadlineLine(event, timeZone, current) {
  const deadline = (event.deadlines || []).find(({ at, kind }) => DEADLINE_LABELS[kind] && kind !== 'unknown' && new Date(at) >= current);
  if (!deadline) return '';
  return `⏳ ${DEADLINE_LABELS[deadline.kind] || DEADLINE_LABELS.unknown} ${formatDisplayDate(new Date(deadline.at), timeZone, true)}`;
}

function publicPlace(event) {
  const country = String(event.country || '').trim();
  const city = String(event.city || '').trim();
  const venue = String(event.venue || '').trim();
  const taiwan = /^(?:台灣|臺灣|Taiwan)$/iu.test(country);
  if (taiwan) return [city, venue].filter(Boolean).join('・');
  if (city || country) return [city, country].filter(Boolean).join(', ');
  return String(event.location || '').trim();
}

function locationLine(event) {
  const place = publicPlace(event);
  if (event.attendance === 'online') return '🌐 線上';
  if (event.attendance === 'onsite') return place ? `📍 ${place}` : '';
  if (event.attendance === 'hybrid') return place ? `🌐 線上／📍 ${place}` : '🌐 線上／實體';
  return '';
}

function fullAddressLine(event) {
  const address = String(event.address || '').trim();
  return address ? `地址：${address}` : '';
}

function audienceLine(audience) {
  const labels = { 'high-school': '限高中職學生', women: '限女性參與者', 'pre-exam': '需通過 Pre-exam' };
  const values = (audience || []).map((value) => labels[value]).filter(Boolean);
  return values.length ? `👤 ${values.join('、')}` : '';
}

function eventDecisionLine(event) {
  const decision = [topicLine(event.topics), directionLabel(event.directions, event.kind), KIND_LABELS[event.kind] || KIND_LABELS.event]
    .filter(Boolean).join(' · ');
  const facts = [LEVEL_LABELS[event.level], participationLabel(event)].filter(Boolean);
  return `${decision}${facts.length ? `｜${facts.join('｜')}` : ''}`;
}

function eventTimingLine(event, timeZone, current) {
  return [scheduleLine(event, timeZone), deadlineLine(event, timeZone, current)].filter(Boolean).join('；');
}

function createEventMessage(event, timeZone = 'Asia/Taipei', current = new Date()) {
  return {
    content: [
      `[${markdownLinkTitle(event.title)}](${event.officialUrl || event.url})`, eventDecisionLine(event),
      scheduleLine(event, timeZone), deadlineLine(event, timeZone, current),
      locationLine(event), audienceLine(event.audience),
    ].filter(Boolean).join('\n'),
    allowedMentions: { parse: [] }, flags: MessageFlags.SuppressEmbeds,
  };
}

module.exports = {
  createEventMessage, eventDecisionLine, eventTimingLine, formatCompactDate, formatCompactDateTime,
  fullAddressLine, locationLine, publicPlace,
};
