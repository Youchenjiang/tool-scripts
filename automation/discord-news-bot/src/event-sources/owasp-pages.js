const { decodeHtml } = require('../news-feed');

function asArray(value) { return Array.isArray(value) ? value : value ? [value] : []; }

function uniqueText(values, limit = 8_000) {
  const seen = new Set();
  const parts = [];
  for (const value of values) {
    const text = decodeHtml(value).replace(/\s+/gu, ' ').trim();
    const key = text.toLowerCase();
    if (!text || seen.has(key)) continue;
    seen.add(key);
    parts.push(text);
  }
  return parts.join('\n').slice(0, limit);
}

function jsonLdEvent(html) {
  for (const match of String(html || '').matchAll(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/giu)) {
    try {
      const values = asArray(JSON.parse(match[1])).flatMap((value) => value?.['@graph'] || value);
      const event = values.find((value) => /Event$/u.test(String(value?.['@type'] || '')));
      if (event) return event;
    } catch { /* inspect the next block */ }
  }
  return null;
}

function structuredPlace(value) {
  const locations = asArray(value?.location);
  const virtual = locations.some((item) => /VirtualLocation/iu.test(String(item?.['@type'] || '')));
  const physical = locations.find((item) => item && typeof item === 'object'
    && !/VirtualLocation/iu.test(String(item['@type'] || '')));
  const address = physical?.address && typeof physical.address === 'object' ? physical.address : {};
  const mode = String(value?.eventAttendanceMode || '');
  const online = virtual || /OnlineEventAttendanceMode/iu.test(mode);
  const onsite = Boolean(physical) || /OfflineEventAttendanceMode/iu.test(mode);
  return {
    attendance: online && onsite ? 'hybrid' : online ? 'online' : onsite ? 'onsite' : 'unknown',
    venue: String(physical?.name || '').trim(),
    city: String(address.addressLocality || '').trim(),
    country: String(address.addressCountry?.name || address.addressCountry || '').trim(),
    address: String(address.streetAddress || (typeof physical?.address === 'string' ? physical.address : '')).trim(),
  };
}

function structuredClassification(value) {
  if (!value) return [];
  const nested = [
    ...asArray(value.subEvent), ...asArray(value.subjectOf), ...asArray(value.workFeatured),
  ];
  return [
    value.name, value.description, value.keywords,
    ...nested.flatMap((item) => (typeof item === 'object'
      ? [item?.name, item?.headline, item?.description, item?.keywords]
      : [item])),
  ];
}

function pageClassification(html, structured) {
  const values = [...structuredClassification(structured)];
  const markup = String(html || '').replace(/<(?:script|style)[^>]*>[\s\S]*?<\/(?:script|style)>/giu, ' ');
  for (const match of markup.matchAll(/<meta[^>]+(?:name|property)=["'](?:description|keywords|og:description)["'][^>]+content=["']([^"']+)["'][^>]*>/giu)) {
    values.push(match[1]);
  }
  for (const match of markup.matchAll(/<(?:h[1-4]|li)[^>]*>([\s\S]*?)<\/(?:h[1-4]|li)>/giu)) {
    values.push(match[1]);
  }
  return uniqueText(values);
}

function sourceSpecificPlace(url, text) {
  const host = new URL(url).hostname.toLowerCase();
  if (host === 'appsecdays.pt') return {
    attendance: 'onsite', venue: text.includes('Fundação António Cupertino de Miranda')
      ? 'Fundação António Cupertino de Miranda' : '', city: 'Porto', country: 'Portugal',
    address: text.match(/Avenida da Boavista,?\s*4245,?\s*4100-140 Porto/iu)?.[0] || '',
  };
  if (host === 'god.owasp.de') return {
    attendance: 'onsite', venue: text.includes('IHK Haus der Wirtschaft') ? 'IHK Haus der Wirtschaft' : '',
    city: 'Karlsruhe', country: 'Germany',
    address: text.match(/Lammstraße 13-17/iu)?.[0] || '',
  };
  if (host.endsWith('owaspappsecdays.fr')) return {
    attendance: 'onsite', venue: text.match(/"(La Maison des Associations et de la Solidarité)"/iu)?.[1] || '',
    city: 'Paris', country: 'France', address: text.match(/10 rue des Terres au Curé/iu)?.[0] || '',
  };
  if (host === 'appsecil.org') return {
    attendance: 'onsite', venue: text.match(/(?:The )?(Tel Aviv Expo,?\s*Pavilion 10)/iu)?.[1] || '',
    city: 'Tel Aviv', country: 'Israel', address: '',
  };
  return null;
}

function parseOwaspEventPage(html, url, title = '') {
  const text = decodeHtml(html).replace(/\s+/gu, ' ').trim();
  const structuredEvent = jsonLdEvent(html);
  const structured = structuredPlace(structuredEvent);
  const specific = sourceSpecificPlace(url, text);
  const virtual = /\bvirtual conference\b|free virtual conference|click the link here.*Track 1/iu.test(`${title}\n${text}`);
  const result = specific || structured;
  if (virtual && result.attendance === 'unknown') result.attendance = 'online';
  return { ...result, classificationText: pageClassification(html, structuredEvent) };
}

module.exports = { parseOwaspEventPage };
