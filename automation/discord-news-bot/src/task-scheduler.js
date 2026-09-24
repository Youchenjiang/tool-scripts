function scheduleRecurringTask(task, intervalMs, setIntervalImpl = setInterval) {
  if (typeof task !== 'function') throw new TypeError('task must be a function');
  if (!Number.isFinite(intervalMs) || intervalMs <= 0) throw new RangeError('intervalMs must be positive');

  const timer = setIntervalImpl(() => {
    void Promise.resolve().then(task).catch(() => {});
  }, intervalMs);
  timer.unref?.();
  return timer;
}

module.exports = { scheduleRecurringTask };
