const test = require('node:test');
const assert = require('node:assert/strict');
const { classifyEvent } = require('../src/event-classifier');

function event(overrides = {}) {
  return {
    title: 'Security event',
    description: '',
    kind: 'competition',
    directions: [],
    topics: [],
    level: 'unspecified',
    participation: 'unspecified',
    evidence: {},
    ...overrides,
  };
}

test('classifier requires attack and detection evidence for inferred purple-team events', () => {
  const result = classifyEvent(event({
    description: 'Use Atomic Red Team for adversary emulation and detection validation.',
  }));
  assert.deepEqual(result.directions, ['purple']);
  assert.match(result.evidence.directions, /Atomic Red Team/iu);
  assert.match(result.evidence.directions, /detection validation/iu);
});

test('classifier treats independent red and blue tracks as a broad program instead of purple teaming', () => {
  const result = classifyEvent(event({
    description: 'Includes penetration testing and incident response tracks.',
  }));
  assert.deepEqual(result.directions, ['general']);
});

test('classifier does not label a generic CTF as red team', () => {
  const result = classifyEvent(event({
    title: 'Example CTF 2026',
    description: 'Challenges include Web, Pwn, Reverse, Crypto, and Forensics.',
  }));
  assert.deepEqual(result.directions, ['unspecified']);
  assert.deepEqual(result.topics, ['web', 'pwn', 'reverse', 'crypto', 'forensics']);
});

test('classifier recognizes broad conferences, explicit levels, and participation', () => {
  const result = classifyEvent(event({
    title: 'Security Community Conference',
    kind: 'conference',
    description: 'Beginner-friendly individual registration with cloud security sessions.',
  }));
  assert.deepEqual(result.directions, ['unspecified']);
  assert.equal(result.level, 'beginner');
  assert.equal(result.participation, 'individual');
  assert.deepEqual(result.topics, ['cloud']);
});

test('classifier uses official page evidence without treating conference type as a direction', () => {
  const result = classifyEvent(event({
    title: 'OWASP AppSec Days',
    kind: 'conference',
    classificationText: 'Agenda: API Security, AI Security, and Cloud Security for secure software teams.',
  }));
  assert.deepEqual(result.directions, ['unspecified']);
  assert.deepEqual(result.topics, ['appsec', 'api', 'ai-security', 'cloud']);
});

test('classifier labels independent offensive and defensive tracks as general', () => {
  const result = classifyEvent(event({
    kind: 'conference',
    classificationText: 'Separate penetration testing and incident response tracks.',
  }));
  assert.deepEqual(result.directions, ['general']);
  assert.match(result.evidence.directions, /penetration testing/iu);
  assert.match(result.evidence.directions, /incident response/iu);
});

test('classifier recognizes Chinese defensive training evidence', () => {
  const result = classifyEvent(event({
    title: '資安防護實戰菁英返校日',
    kind: 'training',
  }));
  assert.deepEqual(result.directions, ['blue']);
});

test('classifier does not infer advanced difficulty from speaker expertise', () => {
  const result = classifyEvent(event({
    description: 'Meet application security experts and security professionals.',
  }));
  assert.equal(result.level, 'unspecified');
});
