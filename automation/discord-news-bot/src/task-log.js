const RESULT_FIELDS = [
  'checked', 'discovered', 'evaluated', 'matched', 'published', 'rejected', 'errors',
  'activityDiscovered', 'activityPublished', 'succeeded', 'failed', 'initialSync',
];

function createTaskLogRecord(task, trigger, result = {}, now = () => new Date()) {
  const record = {
    task,
    trigger,
    outcome: result.skipped ? 'skipped' : 'completed',
    completedAt: result.at || now().toISOString(),
  };
  for (const field of RESULT_FIELDS) {
    if (['number', 'boolean'].includes(typeof result[field])) record[field] = result[field];
  }
  if (result.reason) record.reason = String(result.reason);
  if (Array.isArray(result.sourceErrors) && result.sourceErrors.length) {
    record.sourceErrors = result.sourceErrors.map(String);
  }
  if (Array.isArray(result.failures) && result.failures.length) {
    record.failures = result.failures.map(({ sourceId, message }) => ({
      sourceId: String(sourceId || ''),
      message: String(message || ''),
    }));
  }
  if (result.reminders && typeof result.reminders === 'object') {
    record.reminders = {
      sent: Number(result.reminders.sent || 0),
      failed: Number(result.reminders.failed || 0),
    };
  }
  return record;
}

function createTaskErrorRecord(task, trigger, error, now = () => new Date()) {
  return {
    task,
    trigger,
    outcome: 'failed',
    error: String(error?.message || error),
    completedAt: now().toISOString(),
  };
}

module.exports = { createTaskErrorRecord, createTaskLogRecord };
