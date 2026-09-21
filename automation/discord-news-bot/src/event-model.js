function validDate(value) {
  if (value === null || value === undefined || value === '') return null;
  const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  return Number.isFinite(date.getTime()) ? date : null;
}

function canonicalUrl(value) {
  try {
    const url = new URL(String(value || '').trim());
    if (!['http:', 'https:'].includes(url.protocol)) return '';
    url.hash = '';
    for (const key of [...url.searchParams.keys()]) {
      if (/^(?:utm_.+|fbclid|gclid)$/iu.test(key)) url.searchParams.delete(key);
    }
    url.hostname = url.hostname.toLowerCase();
    if (url.pathname !== '/') url.pathname = url.pathname.replace(/\/+$/u, '');
    return url.href;
  } catch {
    return '';
  }
}

function cleanText(value, limit = 8_000) {
  return String(value || '').replace(/\s+/gu, ' ').trim().slice(0, limit);
}

function uniqueStrings(values) {
  return [...new Set((Array.isArray(values) ? values : [])
    .map((value) => cleanText(value, 100))
    .filter(Boolean))];
}

function normalizeDeadlines(deadlines) {
  return (Array.isArray(deadlines) ? deadlines : []).flatMap((deadline) => {
    const at = validDate(deadline?.at ?? deadline);
    if (!at) return [];
    return [{
      at,
      kind: cleanText(deadline?.kind || 'unknown', 40) || 'unknown',
      note: cleanText(deadline?.note, 500),
    }];
  }).sort((left, right) => left.at - right.at);
}

function normalizeEventRecord(input) {
  const title = cleanText(input?.title, 300);
  const url = canonicalUrl(input?.officialUrl || input?.url);
  const sourceId = cleanText(input?.sourceId || input?.source, 80).toLowerCase();
  const startsAt = validDate(input?.startsAt ?? input?.start);
  const endsAt = validDate(input?.endsAt ?? input?.finish) || startsAt;
  if (!input?.id || !title || !url || !sourceId) return null;

  const teamSizeMin = Number.isInteger(input.teamSizeMin) && input.teamSizeMin > 0
    ? input.teamSizeMin : null;
  const teamSizeMax = Number.isInteger(input.teamSizeMax) && input.teamSizeMax > 0
    ? input.teamSizeMax : null;
  return {
    ...input,
    id: cleanText(input.id, 300),
    aliases: uniqueStrings([input.id, ...(input.aliases || [])]),
    sourceId,
    source: cleanText(input.source || input.sourceId, 80),
    sources: uniqueStrings([sourceId, ...(input.sources || [])]),
    title,
    officialUrl: url,
    url,
    description: cleanText(input.description),
    classificationText: cleanText(input.classificationText),
    startsAt,
    endsAt,
    start: startsAt,
    finish: endsAt,
    dateText: cleanText(input.dateText, 300),
    deadlines: normalizeDeadlines(input.deadlines),
    timeZone: cleanText(input.timeZone, 80),
    attendance: cleanText(input.attendance || 'unknown', 30) || 'unknown',
    location: cleanText(input.location, 300),
    venue: cleanText(input.venue, 200),
    city: cleanText(input.city, 100),
    country: cleanText(input.country, 100),
    address: cleanText(input.address, 300),
    kind: cleanText(input.kind || 'event', 40) || 'event',
    directions: uniqueStrings(input.directions),
    topics: uniqueStrings(input.topics),
    level: cleanText(input.level || 'unspecified', 30) || 'unspecified',
    participation: cleanText(input.participation || 'unspecified', 30) || 'unspecified',
    teamSizeMin,
    teamSizeMax,
    teamSize: cleanText(input.teamSize, 50),
    audience: uniqueStrings(input.audience),
    evidence: input.evidence && typeof input.evidence === 'object' ? { ...input.evidence } : {},
  };
}

function normalizedTitle(value) {
  return cleanText(value, 300).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

function eventDay(event) {
  if (event.startDate) return String(event.startDate);
  return event.startsAt ? event.startsAt.toISOString().slice(0, 10) : '';
}

function sameEvent(left, right) {
  if (left.officialUrl === right.officialUrl) return true;
  if (left.aliases.some((id) => right.aliases.includes(id))) return true;
  const leftTitle = normalizedTitle(left.title);
  const rightTitle = normalizedTitle(right.title);
  const leftDay = eventDay(left);
  return Boolean(leftTitle && leftTitle === rightTitle && leftDay && leftDay === eventDay(right));
}

const SOURCE_PRIORITY = {
  organizer: 40,
  ctftime: 30,
  owasp: 30,
  'taiwan-security-deadlines': 20,
};

function sourcePriority(event) {
  if (event.sourceId.startsWith('kktix:')) return 35;
  if (event.sourceId.startsWith('ical:')) return 35;
  return SOURCE_PRIORITY[event.sourceId] || 10;
}

function prefer(primary, secondary, key) {
  return primary[key] !== null && primary[key] !== undefined && primary[key] !== ''
    ? primary[key] : secondary[key];
}

function mergeEventRecords(left, right) {
  const [primary, secondary] = sourcePriority(left) >= sourcePriority(right)
    ? [left, right] : [right, left];
  return {
    ...secondary,
    ...primary,
    aliases: uniqueStrings([...left.aliases, ...right.aliases]),
    sources: uniqueStrings([...left.sources, ...right.sources]),
    description: prefer(primary, secondary, 'description'),
    classificationText: prefer(primary, secondary, 'classificationText'),
    startsAt: prefer(primary, secondary, 'startsAt'),
    endsAt: prefer(primary, secondary, 'endsAt'),
    start: prefer(primary, secondary, 'startsAt'),
    finish: prefer(primary, secondary, 'endsAt'),
    dateText: prefer(primary, secondary, 'dateText'),
    deadlines: normalizeDeadlines([...left.deadlines, ...right.deadlines]),
    timeZone: prefer(primary, secondary, 'timeZone'),
    attendance: primary.attendance !== 'unknown' ? primary.attendance : secondary.attendance,
    location: prefer(primary, secondary, 'location'),
    venue: prefer(primary, secondary, 'venue'),
    city: prefer(primary, secondary, 'city'),
    country: prefer(primary, secondary, 'country'),
    address: prefer(primary, secondary, 'address'),
    directions: uniqueStrings([...left.directions, ...right.directions]),
    topics: uniqueStrings([...left.topics, ...right.topics]),
    audience: uniqueStrings([...left.audience, ...right.audience]),
    evidence: { ...secondary.evidence, ...primary.evidence },
  };
}

function deduplicateEvents(events) {
  const merged = [];
  for (const rawEvent of events) {
    const event = normalizeEventRecord(rawEvent);
    if (!event) continue;
    const index = merged.findIndex((candidate) => sameEvent(candidate, event));
    if (index === -1) merged.push(event);
    else merged[index] = mergeEventRecords(merged[index], event);
  }
  return merged;
}

function eventEndTime(event) {
  const end = validDate(event.endsAt ?? event.finish ?? event.startsAt ?? event.start);
  const lastDeadline = normalizeDeadlines(event.deadlines).at(-1)?.at;
  return end?.getTime() ?? lastDeadline?.getTime() ?? Number.NEGATIVE_INFINITY;
}

function eventStartTime(event) {
  const start = validDate(event.startsAt ?? event.start);
  const firstDeadline = normalizeDeadlines(event.deadlines)[0]?.at;
  return start?.getTime() ?? firstDeadline?.getTime() ?? Number.POSITIVE_INFINITY;
}

module.exports = {
  canonicalUrl,
  deduplicateEvents,
  eventEndTime,
  eventStartTime,
  mergeEventRecords,
  normalizeDeadlines,
  normalizeEventRecord,
  sameEvent,
};
