const path = require('node:path');

function readPositiveInteger(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

function readBoolean(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined) return fallback;
  if (['1', 'true', 'yes', 'on'].includes(raw.trim().toLowerCase())) return true;
  if (['0', 'false', 'no', 'off'].includes(raw.trim().toLowerCase())) return false;
  throw new Error(`${name} must be true or false`);
}

function required(name) {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function readTimeZone(name, fallback) {
  const value = process.env[name]?.trim() || fallback;
  try {
    new Intl.DateTimeFormat('en', { timeZone: value }).format();
  } catch {
    throw new Error(`${name} must be a valid IANA time zone`);
  }
  return value;
}

function loadConfig() {
  return {
    token: required('DISCORD_TOKEN'),
    clientId: process.env.DISCORD_CLIENT_ID?.trim() || '',
    guildId: process.env.DISCORD_GUILD_ID?.trim() || '',
    channelId: required('DISCORD_CHANNEL_ID'),
    pollIntervalMs: readPositiveInteger('POLL_INTERVAL_MINUTES', 30) * 60_000,
    lookbackMs: readPositiveInteger('LOOKBACK_HOURS', 48) * 60 * 60_000,
    maxArticlesPerRun: readPositiveInteger('MAX_ARTICLES_PER_RUN', 5),
    pushOnStart: readBoolean('PUSH_ON_START', true),
    publishInitialArticles: readBoolean('PUBLISH_INITIAL_ARTICLES', true),
    aiFilteringEnabled: readBoolean('AI_FILTER_ENABLED', true),
    maxAiEvaluationsPerRun: readPositiveInteger('MAX_AI_EVALUATIONS_PER_RUN', 10),
    aiMaxOutputTokens: readPositiveInteger('AI_MAX_OUTPUT_TOKENS', 800),
    aiApiKey: process.env.AI_API_KEY?.trim() || '',
    aiBaseUrl: process.env.AI_BASE_URL?.trim() || '',
    aiModel: process.env.AI_MODEL?.trim() || '',
    feedUrl: process.env.NEWS_FEED_URL?.trim()
      || 'https://thehackernews.com/feeds/posts/default?alt=json&redirect=false&max-results=50',
    sourceName: process.env.NEWS_SOURCE_NAME?.trim() || 'The Hacker News',
    sourceObservationEnabled: readBoolean('SOURCE_OBSERVATION_ENABLED', false),
    sourceObservationIntervalMs: readPositiveInteger('SOURCE_OBSERVATION_INTERVAL_MINUTES', 1440) * 60_000,
    maxSourcesPerRun: readPositiveInteger('MAX_SOURCES_PER_RUN', 3),
    eventsEnabled: readBoolean('EVENTS_ENABLED', true),
    eventChannelId: process.env.EVENT_CHANNEL_ID?.trim() || '1536696484286824519',
    eventPollIntervalMs: readPositiveInteger('EVENT_POLL_INTERVAL_MINUTES', 30) * 60_000,
    eventWeeklyEnabled: readBoolean('EVENT_WEEKLY_ENABLED', true),
    eventTimeZone: readTimeZone('EVENT_TIME_ZONE', 'Asia/Taipei'),
    eventLookaheadDays: readPositiveInteger('EVENT_LOOKAHEAD_DAYS', 120),
    ctfTimeEventsUrl: process.env.CTFTIME_EVENTS_URL?.trim()
      || 'https://ctftime.org/api/v1/events/',
    owaspEventsUrl: process.env.OWASP_EVENTS_URL?.trim()
      || 'https://raw.githubusercontent.com/OWASP/owasp.github.io/main/_data/events.yml',
    maxOwaspEventsPerRun: readPositiveInteger('MAX_OWASP_EVENTS_PER_RUN', 20),
    taiwanDeadlinesEnabled: readBoolean('TAIWAN_DEADLINES_ENABLED', true),
    taiwanDeadlinesUrl: process.env.TAIWAN_DEADLINES_URL?.trim()
      || 'https://raw.githubusercontent.com/stwater20/taiwan-security-deadlines/main/_data/conferences.yml',
    kktixEventsEnabled: readBoolean('KKTIX_EVENTS_ENABLED', true),
    maxKktixEventsPerSource: readPositiveInteger('MAX_KKTIX_EVENTS_PER_SOURCE', 20),
    icalEventsEnabled: readBoolean('ICAL_EVENTS_ENABLED', true),
    stateRetentionDays: readPositiveInteger('STATE_RETENTION_DAYS', 90),
    databaseUrl: process.env.DATABASE_URL?.trim() || '',
    statePath: path.join(__dirname, '..', 'data', 'state.json'),
  };
}

module.exports = { loadConfig, readBoolean, readPositiveInteger, readTimeZone };
