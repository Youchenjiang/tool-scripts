const STUDENT_CALENDARS = new Set(['ical:scist', 'ical:bamboofox']);
const ROUTINE = /社課|迎新|社團博覽會|助教時間|內部培訓|例行社團|club meeting|members.only|internal training/iu;
const RESTRICTED = /不對外開放|未對外開放|僅限.{0,12}(?:社員|本校|校內)|限本校|限社員|not open to (?:the )?public/iu;
const PUBLIC = /對外開放|公開報名|開放校外|歡迎校外|不限學校|open to (?:the public|everyone|all)/iu;
const SECURITY = /資安|資訊安全|CTF|security|\bpwn\b|逆向|密碼學|鑑識|滲透|漏洞/iu;
const TAIWAN_COUNTRY = /^(?:台灣|臺灣|Taiwan|TW)$/iu;
const TAIWAN_PLACE = /(?:台灣|臺灣|台北|臺北|新北|基隆|桃園|新竹|苗栗|台中|臺中|彰化|南投|雲林|嘉義|台南|臺南|高雄|屏東|宜蘭|花蓮|台東|臺東|澎湖|金門|連江|Taiwan|Taipei|New Taipei|Keelung|Taoyuan|Hsinchu|Miaoli|Taichung|Changhua|Nantou|Yunlin|Chiayi|Tainan|Kaohsiung|Pingtung|Yilan|Hualien|Taitung|Penghu|Kinmen|Lienchiang)/iu;

function hasTaiwanEvidence(event) {
  if (TAIWAN_COUNTRY.test(String(event.country || '').trim())) return true;
  if (event.timeZone === 'Asia/Taipei') return true;
  return TAIWAN_PLACE.test([
    event.city, event.location, event.venue, event.address,
  ].filter(Boolean).join(' '));
}

function isInDeliveryRegion(event) {
  if (event.attendance === 'online' || event.attendance === 'hybrid') return true;
  return hasTaiwanEvidence(event);
}

function isEligibleEvent(event) {
  const text = `${event.title || ''}\n${event.description || ''}`;
  if (ROUTINE.test(text) || RESTRICTED.test(text)) return false;
  if (!isInDeliveryRegion(event)) return false;
  const sources = [event.sourceId, ...(event.sources || [])];
  if (sources.some((source) => STUDENT_CALENDARS.has(source))) {
    return PUBLIC.test(text) && SECURITY.test(text);
  }
  return true;
}

module.exports = { hasTaiwanEvidence, isEligibleEvent, isInDeliveryRegion };
