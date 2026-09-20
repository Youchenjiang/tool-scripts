const test = require('node:test');
const assert = require('node:assert/strict');
const { completeness, eventScore, isTaiwanEvent, participationReason } = require('../src/event-curation');

const now = new Date('2026-09-20T00:00:00Z');
function event(overrides = {}) {
  return {
    title: 'Security event', kind: 'conference', startsAt: '2026-09-25T00:00:00Z', deadlines: [],
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
