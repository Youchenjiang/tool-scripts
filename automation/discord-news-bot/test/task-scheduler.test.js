const assert = require('node:assert/strict');
const test = require('node:test');
const { scheduleRecurringTask } = require('../src/task-scheduler');

test('recurring task uses the requested interval and does not keep the process alive', () => {
  let callback;
  let delay;
  let unrefCalls = 0;
  const timer = { unref: () => { unrefCalls += 1; } };

  const returned = scheduleRecurringTask(() => {}, 30_000, (next, interval) => {
    callback = next;
    delay = interval;
    return timer;
  });

  assert.equal(typeof callback, 'function');
  assert.equal(delay, 30_000);
  assert.equal(unrefCalls, 1);
  assert.equal(returned, timer);
});

test('recurring task contains asynchronous failures', async () => {
  let callback;
  let calls = 0;
  scheduleRecurringTask(async () => {
    calls += 1;
    throw new Error('expected failure');
  }, 1_000, (next) => {
    callback = next;
    return { unref() {} };
  });

  callback();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(calls, 1);
});

test('recurring task rejects invalid registrations', () => {
  assert.throws(() => scheduleRecurringTask(null, 1_000), /task must be a function/u);
  assert.throws(() => scheduleRecurringTask(() => {}, 0), /intervalMs must be positive/u);
});
