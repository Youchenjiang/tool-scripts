const test = require('node:test');
const assert = require('node:assert/strict');
const { hasTaiwanEvidence, isEligibleEvent, isInDeliveryRegion } = require('../src/event-eligibility');

test('student calendars require public access and a security topic', () => {
  const event = { sourceId: 'ical:bamboofox', title: 'Web Security 工作坊', attendance: 'online' };
  assert.equal(isEligibleEvent(event), false);
  assert.equal(isEligibleEvent({ ...event, description: '對外開放，歡迎校外參加' }), true);
  assert.equal(isEligibleEvent({ ...event, description: '不對外開放' }), false);
  assert.equal(isEligibleEvent({ ...event, title: 'Git Workshop', description: '公開報名' }), false);
  assert.equal(isEligibleEvent({ ...event, sourceId: 'ical:scist' }), false);
});

test('routine club activities are excluded across sources', () => {
  for (const title of ['第一次社課 - Web Security', '社團迎新', '社團博覽會', '資安助教時間', '資安內部培訓']) {
    assert.equal(isEligibleEvent({ sourceId: 'kktix:example', title, description: '公開報名', attendance: 'online' }), false);
  }
  assert.equal(isEligibleEvent({ sourceId: 'ctftime', title: 'Example CTF', attendance: 'online' }), true);
  assert.equal(isEligibleEvent({ sourceId: 'kktix:example', title: '資安社群小聚', city: '台北' }), true);
});

test('delivery region keeps Taiwan and online events while excluding foreign onsite events', () => {
  assert.equal(isInDeliveryRegion({ attendance: 'online', country: 'United States' }), true);
  assert.equal(isInDeliveryRegion({ attendance: 'hybrid', city: 'Paris', country: 'France' }), true);
  assert.equal(isInDeliveryRegion({ attendance: 'onsite', city: '台北', country: '台灣' }), true);
  assert.equal(isInDeliveryRegion({ attendance: 'onsite', city: 'Porto', country: 'Portugal' }), false);
  assert.equal(isInDeliveryRegion({ attendance: 'unknown' }), false);
});

test('Taiwan evidence accepts structured places and the explicit local timezone', () => {
  assert.equal(hasTaiwanEvidence({ country: 'Taiwan' }), true);
  assert.equal(hasTaiwanEvidence({ city: 'Kaohsiung' }), true);
  assert.equal(hasTaiwanEvidence({ location: 'IEAT 會議中心，台北市' }), true);
  assert.equal(hasTaiwanEvidence({ timeZone: 'Asia/Taipei' }), true);
  assert.equal(hasTaiwanEvidence({ city: 'Karlsruhe', country: 'Germany' }), false);
});
