const test = require('node:test');
const assert = require('node:assert/strict');
const {
  canonicalUrl,
  deduplicateEvents,
  normalizeEventRecord,
} = require('../src/event-model');

function event(overrides = {}) {
  return {
    id: 'ctftime:3504',
    sourceId: 'ctftime',
    source: 'CTFtime',
    title: 'Holmes CTF 2026',
    url: 'https://example.com/events/holmes/?utm_source=newsletter',
    start: new Date('2026-09-18T04:00:00Z'),
    finish: new Date('2026-09-22T09:00:00Z'),
    kind: 'competition',
    topics: ['Web'],
    ...overrides,
  };
}

test('event model canonicalizes URLs and rejects incomplete records', () => {
  assert.equal(
    canonicalUrl('HTTPS://Example.COM/events/holmes/?utm_source=x#schedule'),
    'https://example.com/events/holmes',
  );
  assert.equal(normalizeEventRecord({ id: 'bad', title: 'Missing URL', source: 'test' }), null);
});

test('event model keeps structured place fields independently', () => {
  const normalized = normalizeEventRecord(event({
    attendance: 'onsite', venue: 'Conference Hall', city: 'Porto', country: 'Portugal',
    address: 'Avenida da Boavista 4245', location: 'Conference Hall / Avenida da Boavista 4245',
  }));
  assert.equal(normalized.venue, 'Conference Hall');
  assert.equal(normalized.city, 'Porto');
  assert.equal(normalized.country, 'Portugal');
  assert.equal(normalized.address, 'Avenida da Boavista 4245');
});

test('event model preserves aliases and normalized legacy date fields', () => {
  const normalized = normalizeEventRecord(event());
  assert.equal(normalized.officialUrl, 'https://example.com/events/holmes');
  assert.equal(normalized.startsAt.toISOString(), '2026-09-18T04:00:00.000Z');
  assert.equal(normalized.start, normalized.startsAt);
  assert.deepEqual(normalized.aliases, ['ctftime:3504']);
});

test('event model merges duplicate sources without replacing precise CTF times', () => {
  const [merged] = deduplicateEvents([
    event(),
    event({
      id: 'taiwan-deadlines:2026:holmes',
      sourceId: 'taiwan-security-deadlines',
      source: 'Taiwan Security Deadlines',
      url: 'https://example.com/events/holmes',
      start: null,
      finish: null,
      location: 'Taipei',
      topics: ['Pwn'],
      deadlines: [{ at: '2026-09-10T15:59:00Z', kind: 'registration' }],
    }),
  ]);

  assert.equal(merged.id, 'ctftime:3504');
  assert.equal(merged.startsAt.toISOString(), '2026-09-18T04:00:00.000Z');
  assert.equal(merged.location, 'Taipei');
  assert.deepEqual(merged.topics, ['Web', 'Pwn']);
  assert.deepEqual(merged.sources, ['ctftime', 'taiwan-security-deadlines']);
  assert.deepEqual(merged.aliases, ['ctftime:3504', 'taiwan-deadlines:2026:holmes']);
  assert.equal(merged.deadlines[0].kind, 'registration');
});
