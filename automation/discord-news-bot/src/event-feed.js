const USER_AGENT = 'CyberNewsSentinel/1.0 (+Discord security event notifier)';
const { classifyEvent } = require('./event-classifier');
const { isEligibleEvent } = require('./event-eligibility');
const { deduplicateEvents, eventEndTime, eventStartTime, normalizeEventRecord } = require('./event-model');
const { fetchTaiwanDeadlineEvents } = require('./event-sources/taiwan-deadlines');
const { fetchKktixEvents } = require('./event-sources/kktix');
const { fetchIcalEvents } = require('./event-sources/ical');
const { parseOwaspEventPage } = require('./event-sources/owasp-pages');
const { loadEventSourceRegistry } = require('./event-source-registry');

function cleanScalar(value) {
  const text = String(value || '').trim();
  if ((text.startsWith('"') && text.endsWith('"'))
      || (text.startsWith("'") && text.endsWith("'"))) {
    return text.slice(1, -1);
  }
  return text;
}

function parseTeamSize(description) {
  const text = String(description || '').replace(/\s+/gu, ' ');
  const rangePatterns = [
    /team\s*size\s*[:\-]?\s*(\d+)\s*[–—~\-]\s*(\d+)\s*(?:members?|players?|people)?/iu,
    /teams?\s+of\s+(\d+)\s*[–—~\-]\s*(\d+)\s*(?:members?|players?|people)/iu,
  ];
  for (const pattern of rangePatterns) {
    const match = text.match(pattern);
    if (match) return `${match[1]}～${match[2]}人`;
  }
  const maximumPatterns = [
    /(?:maximum|max\.?|up to)\s+(?:team\s+size\s+of\s+)?(\d+)\s*(?:members?|players?|people)/iu,
    /team\s*size\s*[:\-]?\s*(\d+)\s*(?:members?|players?|people)?/iu,
    /teams?\s+of\s+(\d+)\s*(?:members?|players?|people)/iu,
  ];
  for (const pattern of maximumPatterns) {
    const match = text.match(pattern);
    if (match) return `${match[1]}人`;
  }
  return '';
}

async function fetchText(url, fetchImpl) {
  const response = await fetchImpl(url, {
    headers: { Accept: 'application/json, text/plain;q=0.9, */*;q=0.8', 'User-Agent': USER_AGENT },
  });
  if (!response.ok) throw new Error(`${new URL(url).host} returned HTTP ${response.status}`);
  return response.text();
}

function normalizeCtfTimeEvent(event) {
  const start = new Date(event.start);
  const finish = new Date(event.finish);
  if (!event.id || !event.title || !Number.isFinite(start.getTime())
      || !Number.isFinite(finish.getTime())) return null;
  const url = String(event.url || event.ctftime_url || '').trim();
  if (!/^https?:\/\//iu.test(url)) return null;
  const description = String(event.description || '').replace(/\s+/gu, ' ').trim().slice(0, 4_000);
  const classificationText = [
    event.format ? `CTF format: ${event.format}` : '',
    event.restrictions ? `Restrictions: ${event.restrictions}` : '',
  ].filter(Boolean).join('\n');
  return normalizeEventRecord({
    id: `ctftime:${event.id}`,
    sourceId: 'ctftime',
    title: String(event.title).trim(),
    url,
    start,
    finish,
    allDay: false,
    dateText: '',
    description,
    classificationText,
    teamSize: parseTeamSize(description),
    location: String(event.location || (event.onsite ? '' : 'On-line')).trim(),
    attendance: event.onsite ? 'onsite' : 'online',
    source: 'CTFtime',
    kind: 'ctf',
  });
}

async function fetchCtfTimeEvents({ baseUrl, start, finish, fetchImpl = fetch }) {
  const endpoint = new URL(baseUrl);
  endpoint.searchParams.set('limit', '100');
  endpoint.searchParams.set('start', String(Math.floor(start.getTime() / 1000)));
  endpoint.searchParams.set('finish', String(Math.floor(finish.getTime() / 1000)));
  const body = await fetchText(endpoint, fetchImpl);
  let payload;
  try {
    payload = JSON.parse(body);
  } catch {
    throw new Error('CTFtime returned invalid JSON');
  }
  if (!Array.isArray(payload)) throw new Error('CTFtime returned an unexpected payload');
  return payload.map(normalizeCtfTimeEvent).filter(Boolean);
}

function parseOwaspEventsYaml(yaml) {
  const events = [];
  let category = '';
  let current = null;

  function finishCurrent() {
    if (current?.name && current?.startDate) events.push(current);
  }

  for (const rawLine of String(yaml || '').split(/\r?\n/u)) {
    const line = rawLine.trim();
    const categoryMatch = line.match(/^-\s+category:\s*(.+)$/u);
    if (categoryMatch) {
      finishCurrent();
      current = null;
      category = cleanScalar(categoryMatch[1]);
      continue;
    }
    const nameMatch = line.match(/^-\s+name:\s*(.+)$/u);
    if (nameMatch) {
      finishCurrent();
      current = { name: cleanScalar(nameMatch[1]), category };
      continue;
    }
    if (!current) continue;
    const fieldMatch = line.match(/^(start-date|dates|url|optional-text):\s*(.*)$/u);
    if (!fieldMatch) continue;
    const key = {
      'start-date': 'startDate',
      dates: 'dateText',
      url: 'url',
      'optional-text': 'description',
    }[fieldMatch[1]];
    current[key] = cleanScalar(fieldMatch[2]);
  }
  finishCurrent();
  return events;
}

function normalizeOwaspEvent(event) {
  const startDate = /^\d{4}-\d{2}-\d{2}$/u.test(event.startDate) ? event.startDate : '';
  if (!startDate || !event.name || !/^https?:\/\//iu.test(event.url || '')) return null;
  const start = new Date(`${startDate}T00:00:00Z`);
  return normalizeEventRecord({
    id: `owasp:${startDate}:${event.name.toLowerCase().replace(/[^a-z0-9]+/gu, '-').slice(0, 80)}`,
    sourceId: 'owasp',
    title: event.name,
    url: event.url,
    start,
    finish: start,
    startDate,
    allDay: true,
    dateText: event.dateText || startDate,
    description: event.description || '',
    teamSize: '',
    location: '',
    source: 'OWASP',
    kind: event.category === 'Global' || event.category === 'AppSec Days'
      ? 'conference'
      : 'community',
  });
}

async function fetchOwaspEvents({ url, fetchImpl = fetch, start, finish, maxDetails = 20 }) {
  const body = await fetchText(url, fetchImpl);
  const events = parseOwaspEventsYaml(body).map(normalizeOwaspEvent).filter(Boolean);
  const candidates = events.filter((event) => (!start || event.endsAt >= start) && (!finish || event.startsAt <= finish));
  const selected = new Set(candidates.slice(0, maxDetails));
  return Promise.all(events.map(async (event) => {
    if (!selected.has(event) || !event.url.startsWith('https://')) return event;
    try {
      const html = await fetchText(event.url, fetchImpl);
      return normalizeEventRecord({ ...event, ...parseOwaspEventPage(html, event.url, event.title) });
    } catch { return event; }
  }));
}

async function fetchSecurityEvents(config, { fetchImpl = fetch, now = new Date() } = {}) {
  const start = new Date(now.getTime() - (7 * 24 * 60 * 60_000));
  const finish = new Date(now.getTime() + (config.eventLookaheadDays * 24 * 60 * 60_000));
  const requests = [
    fetchCtfTimeEvents({ baseUrl: config.ctfTimeEventsUrl, start, finish, fetchImpl }),
    fetchOwaspEvents({ url: config.owaspEventsUrl, fetchImpl, start, finish, maxDetails: config.maxOwaspEventsPerRun }),
  ];
  if (config.taiwanDeadlinesEnabled) {
    requests.push(fetchTaiwanDeadlineEvents({
      url: config.taiwanDeadlinesUrl,
      start: now,
      finish,
      fetchImpl,
    }));
  }
  if (config.kktixEventsEnabled) {
    const kktixSources = loadEventSourceRegistry()
      .filter((source) => source.status === 'active' && source.mode === 'kktix_listing');
    for (const source of kktixSources) {
      requests.push(fetchKktixEvents({
        source,
        start: now,
        finish,
        fetchImpl,
        maxDetails: config.maxKktixEventsPerSource,
      }));
    }
  }
  if (config.icalEventsEnabled) {
    const calendarSources = loadEventSourceRegistry()
      .filter((source) => source.status === 'active' && source.mode === 'ical_calendar');
    for (const source of calendarSources) {
      requests.push(fetchIcalEvents({ source, start: now, finish, fetchImpl }));
    }
  }
  const sources = await Promise.allSettled(requests);
  const events = deduplicateEvents(
    sources.flatMap((result) => (result.status === 'fulfilled' ? result.value : [])),
  )
    .map(classifyEvent)
    .filter(isEligibleEvent)
    .filter((event) => eventEndTime(event) >= now.getTime())
    .filter((event) => eventStartTime(event) <= finish.getTime());
  const errors = sources
    .filter((result) => result.status === 'rejected')
    .map((result) => result.reason?.message || String(result.reason));
  if (events.length === 0 && errors.length === sources.length) {
    throw new Error(`All security event sources failed: ${errors.join('; ')}`);
  }
  return { events, errors };
}

module.exports = {
  fetchCtfTimeEvents,
  fetchOwaspEvents,
  fetchSecurityEvents,
  normalizeCtfTimeEvent,
  parseOwaspEventsYaml,
  parseTeamSize,
};
