const test = require('node:test');
const assert = require('node:assert/strict');
const { parseOwaspEventPage } = require('../src/event-sources/owasp-pages');

test('OWASP page enrichment classifies virtual conferences without a fake venue', () => {
  const result = parseOwaspEventPage('<p>A free virtual conference. Click the link here to access Track 1.</p>',
    'https://owasp.glueup.com/event/example', 'OWASP Anniversary Virtual Conference');
  assert.equal(result.attendance, 'online');
  assert.equal(result.venue, '');
});

test('OWASP page enrichment keeps detailed addresses out of concise place fields', () => {
  const fixtures = [
    ['https://appsecdays.pt/', 'Conference Location Fundação António Cupertino de Miranda Avenida da Boavista, 4245, 4100-140 Porto, Portugal',
      { city: 'Porto', country: 'Portugal', venue: 'Fundação António Cupertino de Miranda' }],
    ['https://god.owasp.de/2026/', 'Locationen IHK Haus der Wirtschaft, Lammstraße 13-17, in Karlsruhe.',
      { city: 'Karlsruhe', country: 'Germany', venue: 'IHK Haus der Wirtschaft' }],
    ['https://www.owaspappsecdays.fr/2026/index.html', 'La conférence se tiendra à "La Maison des Associations et de la Solidarité" au 10 rue des Terres au Curé, Paris 13e.',
      { city: 'Paris', country: 'France', venue: 'La Maison des Associations et de la Solidarité' }],
    ['https://appsecil.org/', 'October 06, 2026 | Tel Aviv Expo, Pavilion 10',
      { city: 'Tel Aviv', country: 'Israel', venue: 'Tel Aviv Expo, Pavilion 10' }],
  ];
  for (const [url, html, expected] of fixtures) {
    const result = parseOwaspEventPage(html, url);
    assert.equal(result.attendance, 'onsite');
    assert.deepEqual({ city: result.city, country: result.country, venue: result.venue }, expected);
  }
});
