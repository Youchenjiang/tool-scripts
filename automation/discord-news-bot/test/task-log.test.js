const assert = require('node:assert/strict');
const test = require('node:test');
const { createTaskErrorRecord, createTaskLogRecord } = require('../src/task-log');

test('task log records operational counts and trigger context', () => {
  const record = createTaskLogRecord('events', 'schedule', {
    checked: 12,
    discovered: 3,
    published: 1,
    activityPublished: 2,
    sourceErrors: ['CTFtime: HTTP 503'],
    reminders: { sent: 4, failed: 1, recipients: ['private-user'] },
    at: '2026-09-24T08:00:00.000Z',
  });

  assert.deepEqual(record, {
    task: 'events',
    trigger: 'schedule',
    outcome: 'completed',
    completedAt: '2026-09-24T08:00:00.000Z',
    checked: 12,
    discovered: 3,
    published: 1,
    activityPublished: 2,
    sourceErrors: ['CTFtime: HTTP 503'],
    reminders: { sent: 4, failed: 1 },
  });
});

test('task log allowlist excludes credentials and internal payloads', () => {
  const record = createTaskLogRecord('news', 'startup', {
    skipped: true,
    reason: '尚未設定規則',
    apiKey: 'secret',
    databaseUrl: 'postgres://secret',
    articles: [{ private: true }],
  }, () => new Date('2026-09-24T08:00:00.000Z'));

  assert.deepEqual(record, {
    task: 'news',
    trigger: 'startup',
    outcome: 'skipped',
    completedAt: '2026-09-24T08:00:00.000Z',
    reason: '尚未設定規則',
  });
});

test('task errors use a bounded structured shape', () => {
  const record = createTaskErrorRecord('sources', 'schedule', new Error('HTTP 429'),
    () => new Date('2026-09-24T08:00:00.000Z'));

  assert.deepEqual(record, {
    task: 'sources',
    trigger: 'schedule',
    outcome: 'failed',
    error: 'HTTP 429',
    completedAt: '2026-09-24T08:00:00.000Z',
  });
});
