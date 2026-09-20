const DAY = 86400000;

const TOPIC_LABELS = {
  web: 'Web', pwn: 'Pwn', reverse: 'Reverse', crypto: 'Crypto', forensics: '鑑識', malware: '惡意程式',
  'threat-intelligence': '威脅情資', 'threat-hunting': '威脅獵捕', 'detection-engineering': '偵測工程',
  network: '網路安全', cloud: '雲端安全', ics: 'ICS/OT', mobile: '行動安全', web3: 'Web3', 'ai-security': 'AI 安全',
};

function timestamp(value) {
  const result = new Date(value || '').getTime();
  return Number.isFinite(result) ? result : Number.POSITIVE_INFINITY;
}

function futureDeadline(event, now) {
  return (event.deadlines || []).map(({ at }) => timestamp(at))
    .find((value) => Number.isFinite(value) && value >= now.getTime()) ?? Number.POSITIVE_INFINITY;
}

function isCompetition(event) { return ['ctf', 'competition'].includes(event.kind); }

function isTaiwanEvent(event) {
  return event.timeZone === 'Asia/Taipei'
    || /(?:台灣|臺灣|台北|臺北|新北|桃園|新竹|台中|臺中|台南|臺南|高雄|Taiwan|Taipei|Kaohsiung|Hsinchu)/iu
      .test(`${event.location || ''} ${event.description || ''}`);
}

function completeness(event) {
  return [
    timestamp(event.startsAt || event.start) !== Number.POSITIVE_INFINITY,
    event.attendance && event.attendance !== 'unknown',
    event.level && event.level !== 'unspecified',
    event.participation && event.participation !== 'unspecified',
    event.teamSize || event.teamSizeMin || event.teamSizeMax,
    event.directions?.some((value) => value !== 'unspecified'),
    event.topics?.length,
  ].filter(Boolean).length;
}

function eventScore(event, now = new Date()) {
  const startDistance = timestamp(event.startsAt || event.start) - now.getTime();
  const deadlineDistance = futureDeadline(event, now) - now.getTime();
  let score = completeness(event) * 3;
  if (deadlineDistance <= 3 * DAY) score += 90;
  else if (deadlineDistance <= 7 * DAY) score += 70;
  else if (deadlineDistance <= 14 * DAY) score += 35;
  if (startDistance >= 0 && startDistance <= 7 * DAY) score += 60;
  else if (startDistance <= 14 * DAY) score += 35;
  else if (startDistance <= 28 * DAY) score += 15;
  if (isTaiwanEvent(event)) score += 25;
  if (event.attendance === 'online' || event.attendance === 'hybrid') score += 12;
  if (event.directions?.some((value) => ['blue', 'purple'].includes(value))) score += 18;
  if (!isCompetition(event)) score += 10;
  return score;
}

function participationReason(event) {
  const topics = (event.topics || []).map((topic) => TOPIC_LABELS[topic] || topic).slice(0, 3);
  const level = { beginner: '剛開始接觸資安', foundational: '已有基礎', advanced: '已有實戰經驗' }[event.level];
  const direction = event.directions?.includes('purple') ? '攻防驗證'
    : event.directions?.includes('blue') ? '防禦、偵測或事件應變'
      : event.directions?.includes('red') ? '攻擊技術與漏洞利用' : '';
  if (topics.length && level) return `適合${level}，想練習 ${topics.join('、')} 的成員。`;
  if (topics.length) return `適合想接觸 ${topics.join('、')} 的成員。`;
  if (direction) return `適合想累積${direction}經驗的成員。`;
  if (event.kind === 'conference') return '適合想快速掌握近期資安議題與實務案例的成員。';
  if (event.kind === 'workshop' || event.kind === 'training') return '適合想透過實作建立經驗的成員。';
  if (event.kind === 'community') return '適合想交流實務經驗與認識資安社群的成員。';
  if (isCompetition(event)) return '適合想透過競賽檢驗目前技術能力的成員。';
  return '適合想進一步了解活動主題的成員。';
}

function curateWeeklyEntries(entries, now = new Date(), limit = 8) {
  const ranked = [...entries].sort((left, right) => eventScore(right.event, now) - eventScore(left.event, now)
    || timestamp(left.event.startsAt || left.event.start) - timestamp(right.event.startsAt || right.event.start));
  const selected = [];
  const selectedKeys = new Set();
  let competitionCount = 0;
  const sourceCounts = new Map();
  const kindCounts = new Map();
  const sourceGroup = (event) => String(event.sourceId || event.source || 'unknown').split(':')[0];
  function add(entry) {
    if (!entry || selectedKeys.has(entry.key) || selected.length >= limit) return false;
    if (isCompetition(entry.event) && competitionCount >= 3) return false;
    const source = sourceGroup(entry.event);
    if (!isCompetition(entry.event) && (sourceCounts.get(source) || 0) >= 2) return false;
    if (!isCompetition(entry.event) && (kindCounts.get(entry.event.kind) || 0) >= 2) return false;
    selected.push(entry); selectedKeys.add(entry.key);
    if (isCompetition(entry.event)) competitionCount += 1;
    sourceCounts.set(source, (sourceCounts.get(source) || 0) + 1);
    kindCounts.set(entry.event.kind, (kindCounts.get(entry.event.kind) || 0) + 1);
    return true;
  }

  ranked.filter(({ event }) => futureDeadline(event, now) - now.getTime() <= 7 * DAY).slice(0, 3).forEach(add);
  add(ranked.find(({ event }) => !isCompetition(event)));
  add(ranked.find(({ event }) => event.directions?.some((value) => ['blue', 'purple'].includes(value))));
  ranked.forEach(add);

  const remaining = ranked.filter(({ key }) => !selectedKeys.has(key));
  return {
    selected,
    competitionOverflow: remaining.filter(({ event }) => isCompetition(event)),
    otherOverflow: remaining.filter(({ event }) => !isCompetition(event)),
  };
}

module.exports = {
  DAY, completeness, curateWeeklyEntries, eventScore, futureDeadline, isCompetition, isTaiwanEvent, participationReason,
};
