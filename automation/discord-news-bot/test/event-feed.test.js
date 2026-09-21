const test = require('node:test');
const assert = require('node:assert/strict');
const {
  fetchCtfTimeEvents,
  fetchOwaspEvents,
  fetchSecurityEvents,
  parseTeamSize,
} = require('../src/event-feed');

test('event feed extracts CTF team sizes without treating participant count as a limit', () => {
  assert.equal(parseTeamSize('Team Size: 1–4 Members'), '1～4人');
  assert.equal(parseTeamSize('Teams of 5 players compete together'), '5人');
  assert.equal(parseTeamSize('Open to everyone with 500 registered participants'), '');
});

test('security event feed includes active KKTIX organizers without AI evaluation', async () => {
  const atom = `<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry>
    <published>2026-10-02T10:00:00+08:00</published><link rel="alternate" type="text/html" href="https://hitcon.kktix.cc/events/cyber-range"/>
    <title>HITCON Cyber Range 企業藍隊競賽</title><summary>藍隊事件應變實戰</summary>
    <content>時間：2026/10/02 10:00(+0800)~17:00\n地點：台北</content></entry></feed>`;
  const detail = `<script type="application/ld+json">[{"@type":"Event","url":"https://hitcon.kktix.cc/events/cyber-range","startDate":"2026-10-02T10:00:00+08:00","endDate":"2026-10-02T17:00:00+08:00","location":{"name":"台北"},"offers":[{"name":"參賽票","validThrough":"2026-09-30T23:59:00+08:00"}]}]</script>`;
  const events = await fetchSecurityEvents({
    eventLookaheadDays: 120,
    ctfTimeEventsUrl: 'https://ctftime.test/events',
    owaspEventsUrl: 'https://owasp.test/events.yml',
    taiwanDeadlinesEnabled: false,
    kktixEventsEnabled: true,
    maxKktixEventsPerSource: 20,
    icalEventsEnabled: false,
  }, {
    now: new Date('2026-09-19T00:00:00Z'),
    fetchImpl: async (url) => {
      const value = String(url);
      if (value.startsWith('https://ctftime.test/')) return { ok: true, text: async () => '[]' };
      if (value === 'https://owasp.test/events.yml') return { ok: true, text: async () => '' };
      if (value === 'https://hitcon.kktix.cc/events/cyber-range') return { ok: true, text: async () => detail };
      if (value.includes('hitcon.kktix.cc/events.atom')) return { ok: true, text: async () => atom };
      if (value.includes('.kktix.cc/events.atom')) return { ok: true, text: async () => '<feed xmlns="http://www.w3.org/2005/Atom"></feed>' };
      throw new Error(`Unexpected URL ${value}`);
    },
  });
  assert.equal(events.events.length, 1);
  assert.equal(events.events[0].sourceId, 'kktix:hitcon');
  assert.deepEqual(events.events[0].directions, ['blue']);
  assert.equal(events.events[0].deadlines[0].kind, 'registration');
});

test('security event feed includes active public calendars without AI evaluation', async () => {
  const calendar = `BEGIN:VCALENDAR\r
BEGIN:VEVENT\r
DTSTART:20261007T103000Z\r
DTEND:20261007T130000Z\r
UID:web-security@example.com\r
SUMMARY:Web Security 公開工作坊\r
DESCRIPTION:對外開放，歡迎校外參加\r
LOCATION:EC329\r
END:VEVENT\r
END:VCALENDAR`;
  const result = await fetchSecurityEvents({
    eventLookaheadDays: 120,
    ctfTimeEventsUrl: 'https://ctftime.test/events',
    owaspEventsUrl: 'https://owasp.test/events.yml',
    taiwanDeadlinesEnabled: false,
    kktixEventsEnabled: false,
    icalEventsEnabled: true,
  }, {
    now: new Date('2026-09-19T00:00:00Z'),
    fetchImpl: async (url) => {
      const value = String(url);
      if (value.startsWith('https://ctftime.test/')) return { ok: true, text: async () => '[]' };
      if (value === 'https://owasp.test/events.yml') return { ok: true, text: async () => '' };
      if (value.includes('nctucscbamboofox')) return { ok: true, text: async () => calendar };
      if (value.includes('calendar.google.com/calendar/ical/')) {
        return { ok: true, text: async () => 'BEGIN:VCALENDAR\r\nEND:VCALENDAR' };
      }
      throw new Error(`Unexpected URL ${value}`);
    },
  });
  assert.equal(result.events.length, 1);
  assert.equal(result.events[0].sourceId, 'ical:bamboofox');
  assert.deepEqual(result.events[0].topics, ['web']);
});

test('CTFtime source requests a bounded window and normalizes official event links', async () => {
  let requestedUrl = '';
  const events = await fetchCtfTimeEvents({
    baseUrl: 'https://ctftime.test/api/v1/events/',
    start: new Date('2026-09-18T00:00:00Z'),
    finish: new Date('2026-10-18T00:00:00Z'),
    fetchImpl: async (url) => {
      requestedUrl = String(url);
      return {
        ok: true,
        text: async () => JSON.stringify([{
          id: 3504,
          title: 'Holmes CTF 2026',
          start: '2026-09-18T04:00:00Z',
          finish: '2026-09-22T09:00:00Z',
          url: 'https://ctf.hackthebox.com/event/details/holmes-3504',
          ctftime_url: 'https://ctftime.org/event/3504/',
          description: 'Team Size: 5 Members',
          participants: 900,
          onsite: false,
        }]),
      };
    },
  });

  assert.match(requestedUrl, /limit=100/u);
  assert.match(requestedUrl, /start=1789689600/u);
  assert.equal(events[0].url, 'https://ctf.hackthebox.com/event/details/holmes-3504');
  assert.equal(events[0].teamSize, '5人');
  assert.equal(events[0].kind, 'ctf');
});

test('OWASP source parses the official events data file', async () => {
  const events = await fetchOwaspEvents({
    url: 'https://example.test/events.yml',
    fetchImpl: async (url) => ({
      ok: true,
      text: async () => String(url).endsWith('events.yml') ? `
- category: AppSec Days
  events:
  - name: OWASP 25th Anniversary Virtual Conference
    start-date: 2026-09-22
    dates: September 22, 2026
    url: https://owasp.example/event
    optional-text: A virtual community event.
` : '<p>A free virtual conference. Click the link here to access Track 1.</p>',
    }),
  });

  assert.equal(events.length, 1);
  assert.equal(events[0].title, 'OWASP 25th Anniversary Virtual Conference');
  assert.equal(events[0].kind, 'conference');
  assert.equal(events[0].startDate, '2026-09-22');
  assert.equal(events[0].attendance, 'online');
});
