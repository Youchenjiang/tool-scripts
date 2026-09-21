const test = require('node:test');
const assert = require('node:assert/strict');
const {
  fetchKktixEvents, isActionableKktixEvent, parseKktixAtom, parseKktixEventPage, safeEventUrl,
} = require('../src/event-sources/kktix');

const source = {
  id: 'hitcon', name: 'HITCON', feedUrl: 'https://hitcon.kktix.cc/events.atom?locale=zh-TW',
};

const atom = `<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>tag:hitcon.kktix.cc,2005:Event/1</id><published>2026-10-02T10:00:00+08:00</published>
    <link rel="alternate" type="text/html" href="https://hitcon.kktix.cc/events/cyber-range"/>
    <title>Cyber Range 企業藍隊競賽</title><summary type="text">事件應變與偵測實戰</summary>
    <content type="html">時間：2026/10/02 10:00(+0800)~17:00\n地點：台北會議中心 / 台北市</content></entry>
  <entry><id>tag:hitcon.kktix.cc,2005:Event/2</id><published>2024-01-01T10:00:00+08:00</published>
    <link rel="alternate" type="text/html" href="https://hitcon.kktix.cc/events/old"/><title>Old Event</title>
    <content type="html">時間：2024/01/01 10:00(+0800)~17:00\n地點：台北</content></entry>
  <entry><published>2026-10-03T10:00:00+08:00</published><link rel="alternate" href="https://evil.example/events/injected"/>
    <title>Injected</title><content>時間：2026/10/03 10:00(+0800)~17:00</content></entry>
</feed>`;

const detail = `<html><script type="application/ld+json">[{"@context":"http://schema.org","@type":"Event","name":"Cyber Range","url":"https://hitcon.kktix.cc/events/cyber-range","startDate":"2026-10-02T10:00:00.000+08:00","endDate":"2026-10-02T17:00:00.000+08:00","location":{"@type":"EventVenue","name":"台北會議中心","address":"台北市"},"offers":[{"@type":"Offer","name":"參賽票","validThrough":"2026-09-30T23:59:00.000+08:00"}]}]</script></html>`;
const onlineDetail = `<html><script type="application/ld+json">[{"@type":"Event","url":"https://hitcon.kktix.cc/events/cyber-range","startDate":"2026-10-02T10:00:00+08:00","endDate":"2026-10-02T17:00:00+08:00","eventAttendanceMode":"https://schema.org/OnlineEventAttendanceMode","location":{"@type":"VirtualLocation","name":"Online Event"},"offers":[{"name":"資格通知","validThrough":"2026-09-22T17:00:00+08:00"}]}]</script><p>報名截止：2026 年 9 月 18 日 23:59</p><p>頒獎典禮地點：新北電競基地</p></html>`;

test('KKTIX Atom parser extracts event time, venue and security category without following foreign links', () => {
  const events = parseKktixAtom(atom, source);
  assert.equal(events.length, 2);
  assert.equal(events[0].id, 'kktix:hitcon:cyber-range');
  assert.equal(events[0].startsAt.toISOString(), '2026-10-02T02:00:00.000Z');
  assert.equal(events[0].endsAt.toISOString(), '2026-10-02T09:00:00.000Z');
  assert.equal(events[0].location, '台北會議中心 / 台北市');
  assert.equal(events[0].kind, 'competition');
  assert.equal(events[0].attendance, 'onsite');
});

test('KKTIX event page parser uses matching JSON-LD dates, location and ticket deadline', () => {
  const event = parseKktixEventPage(detail, 'https://hitcon.kktix.cc/events/cyber-range');
  assert.equal(event.endsAt.toISOString(), '2026-10-02T09:00:00.000Z');
  assert.equal(event.location, '台北會議中心 / 台北市');
  assert.equal(event.deadlines[0].at.toISOString(), '2026-09-30T15:59:00.000Z');
  assert.equal(event.deadlines[0].kind, 'registration');
  assert.throws(() => parseKktixEventPage(detail, 'https://hitcon.kktix.cc/events/other'), /matching structured data/u);
});

test('KKTIX parser keeps an online competition separate from its award venue and notification date', () => {
  const event = parseKktixEventPage(onlineDetail, 'https://hitcon.kktix.cc/events/cyber-range');
  assert.equal(event.attendance, 'online');
  assert.equal(event.location, '');
  assert.equal(event.venue, '');
  assert.equal(event.deadlines[0].at.toISOString(), '2026-09-18T15:59:00.000Z');
  assert.doesNotMatch(JSON.stringify(event), /新北電競基地|2026-09-22/u);
});

test('KKTIX fetch filters the date window before enriching candidate details', async () => {
  const requested = [];
  const events = await fetchKktixEvents({
    source,
    start: new Date('2026-09-19T00:00:00Z'),
    finish: new Date('2026-12-01T00:00:00Z'),
    fetchImpl: async (url) => {
      requested.push(String(url));
      return { ok: true, text: async () => String(url).includes('events.atom') ? atom : detail };
    },
  });
  assert.equal(events.length, 1);
  assert.equal(requested.length, 2);
  assert.equal(events[0].deadlines.length, 1);
});

test('KKTIX event URLs are restricted to the organizer feed host', () => {
  assert.equal(safeEventUrl('https://evil.example/events/test', source.feedUrl), '');
  assert.equal(safeEventUrl('https://hitcon.kktix.cc/account', source.feedUrl), '');
  assert.equal(safeEventUrl('https://hitcon.kktix.cc/events/test?locale=en', source.feedUrl), 'https://hitcon.kktix.cc/events/test');
});

test('KKTIX publication skips events that started or explicitly closed registration', () => {
  const now = new Date('2026-09-19T00:00:00Z');
  assert.equal(isActionableKktixEvent({
    startsAt: new Date('2026-09-18T00:00:00Z'), deadlines: [],
  }, now), false);
  assert.equal(isActionableKktixEvent({
    startsAt: new Date('2026-10-02T00:00:00Z'),
    deadlines: [{ at: new Date('2026-09-18T15:59:00Z') }],
  }, now), false);
  assert.equal(isActionableKktixEvent({
    startsAt: new Date('2026-10-16T00:00:00Z'),
    deadlines: [{ at: new Date('2026-09-30T15:59:00Z') }],
  }, now), true);
});
