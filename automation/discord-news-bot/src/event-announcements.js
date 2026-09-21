const { MessageFlags } = require('discord.js');
const { currentEvents } = require('./event-board');
const { createEventMessage } = require('./event-publisher');

const MAX_CONTENT_LENGTH = 1900;
const MAX_SENT_IDS = 5000;

function aliasesFor(event) {
  return [...new Set([event.id, ...(event.aliases || [])].filter(Boolean))];
}

function activityText(event, config, now) {
  return createEventMessage(event, config.eventTimeZone, now).content;
}

function activityBatches(entries, config, now) {
  const heading = '**新增資安活動**\n';
  const batches = [];
  let batch = { entries: [], content: heading };
  for (const entry of entries) {
    const text = activityText(entry.event, config, now);
    const addition = `${batch.entries.length ? '\n\n' : ''}${text}`;
    if (batch.entries.length && batch.content.length + addition.length > MAX_CONTENT_LENGTH) {
      batches.push(batch);
      batch = { entries: [], content: heading };
    }
    batch.entries.push(entry);
    batch.content += `${batch.entries.length > 1 ? '\n\n' : ''}${text}`;
  }
  if (batch.entries.length) batches.push(batch);
  return batches;
}

function writeDeliveryState(state, sentIds, initializedAt) {
  state.activityDelivery = {
    initializedAt,
    sentIds: [...sentIds].slice(-MAX_SENT_IDS),
  };
}

async function publishNewActivities({ state, channel, config, now, save }) {
  const entries = currentEvents(state, now)
    .filter(({ event, stale }) => !stale && event.kind !== 'ctf');
  const previous = state.activityDelivery;
  const sentIds = new Set(previous?.sentIds || []);
  if (!previous?.initializedAt) {
    for (const { event } of entries) for (const id of aliasesFor(event)) sentIds.add(id);
    writeDeliveryState(state, sentIds, now.toISOString());
    await save(state);
    return { initialized: true, discovered: 0, published: 0 };
  }

  const discovered = entries.filter(({ event }) => !aliasesFor(event).some((id) => sentIds.has(id)));
  let published = 0;
  for (const batch of activityBatches(discovered, config, now)) {
    await channel.send({
      content: batch.content,
      allowedMentions: { parse: [] },
      flags: MessageFlags.SuppressEmbeds,
    });
    for (const { event } of batch.entries) for (const id of aliasesFor(event)) sentIds.add(id);
    writeDeliveryState(state, sentIds, previous.initializedAt);
    await save(state);
    published += 1;
  }
  return { initialized: false, discovered: discovered.length, published };
}

module.exports = { activityBatches, aliasesFor, publishNewActivities };
