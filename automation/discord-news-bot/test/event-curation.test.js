const test = require('node:test');
const assert = require('node:assert/strict');
const { completeness, curateWeeklyEntries, eventScore, isTaiwanEvent, participationReason } = require('../src/event-curation');

const now = new Date('2026-09-20T00:00:00Z');
function event(overrides = {}) {
  return {
    title: 'Security event', sourceId: 'test', kind: 'conference', startsAt: '2026-09-25T00:00:00Z', deadlines: [],
    directions: ['general'], topics: [], level: 'unspecified', participation: 'unspecified',
    attendance: 'unknown', location: '', description: '', timeZone: '', ...overrides,
  };
}

test('curation score favours imminent confirmed activities without hiding its inputs', () => {
  const sparse = event({ startsAt: '2026-10-15T00:00:00Z' });
  const actionable = event({
    deadlines: [{ at: '2026-09-22T00:00:00Z', kind: 'registration' }], attendance: 'online',
    level: 'foundational', participation: 'team', teamSizeMax: 5, topics: ['web'], directions: ['red'],
  });
  assert.ok(completeness(actionable) > completeness(sparse));
  assert.ok(eventScore(actionable, now) > eventScore(sparse, now));
});

test('Taiwan detection uses explicit timezone or location evidence', () => {
  assert.equal(isTaiwanEvent(event({ timeZone: 'Asia/Taipei' })), true);
  assert.equal(isTaiwanEvent(event({ location: '高雄' })), true);
  assert.equal(isTaiwanEvent(event({ location: 'Berlin' })), false);
});

test('participation reason only restates confirmed level and topic metadata', () => {
  assert.equal(participationReason(event({ level: 'foundational', topics: ['web', 'pwn'] })),
    '適合已有基礎，想練習 Web、Pwn 的成員。');
  assert.equal(participationReason(event({ kind: 'competition', directions: ['unspecified'] })),
    '適合想透過競賽檢驗目前技術能力的成員。');
});

test('weekly curation keeps category diversity and groups excess competitions', () => {
  const entries = [
    ...Array.from({ length: 7 }, (_, index) => ({
      key: `ctf-${index}`,
      event: event({ title: `CTF ${index}`, kind: 'ctf', startsAt: `2026-09-${21 + index}T00:00:00Z` }),
    })),
    { key: 'blue', event: event({ title: 'Blue workshop', kind: 'workshop', directions: ['blue'] }) },
    { key: 'community', event: event({ title: 'Community meetup', kind: 'community' }) },
  ];
  const result = curateWeeklyEntries(entries, now, 8);
  assert.ok(result.selected.some(({ key }) => key === 'blue'));
  assert.ok(result.selected.some(({ key }) => key === 'community'));
  assert.equal(result.selected.filter(({ event: item }) => item.kind === 'ctf').length, 3);
  assert.equal(result.competitionOverflow.length, 4);
});

test('weekly curation prioritizes near registration deadlines', () => {
  const entries = [
    { key: 'later', event: event({ startsAt: '2026-09-21T00:00:00Z' }) },
    { key: 'deadline', event: event({
      startsAt: '2026-10-10T00:00:00Z', deadlines: [{ at: '2026-09-21T00:00:00Z', kind: 'registration' }],
    }) },
  ];
  assert.equal(curateWeeklyEntries(entries, now, 1).selected[0].key, 'deadline');
});

test('weekly curation prevents one source or activity kind from dominating the digest', () => {
  const entries = [
    ...Array.from({ length: 5 }, (_, index) => ({
      key: `owasp-${index}`,
      event: event({ title: `OWASP Conference ${index}`, sourceId: 'owasp', startsAt: `2026-09-${21 + index}T00:00:00Z` }),
    })),
    { key: 'training', event: event({ title: 'Training', sourceId: 'local', kind: 'training' }) },
    { key: 'workshop', event: event({ title: 'Workshop', sourceId: 'community', kind: 'workshop' }) },
  ];
  const result = curateWeeklyEntries(entries, now, 8);
  assert.equal(result.selected.filter(({ event: item }) => item.sourceId === 'owasp').length, 2);
  assert.ok(result.selected.some(({ key }) => key === 'training'));
  assert.ok(result.selected.some(({ key }) => key === 'workshop'));
});
