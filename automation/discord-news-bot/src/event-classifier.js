const TOPIC_RULES = [
  ['appsec', /\bappsec\b|application security|software security|secure software|secure coding|anwendungssicherheit|應用程式安全|應用安全|安全開發/iu],
  ['web', /\bweb(?:\s+(?:security|hacking|exploitation))?\b|網頁安全|網站安全/iu],
  ['api', /\bapi security\b|\bapi abuse\b|API 安全/iu],
  ['pwn', /\bpwn(?:able)?\b|binary exploitation|二進位漏洞|二進制漏洞/iu],
  ['reverse', /reverse engineering|\breversing\b|\breverse\b|逆向工程|逆向分析/iu],
  ['crypto', /\bcryptography\b|\bcrypto\b|密碼學/iu],
  ['forensics', /\bforensics?\b|\bdfir\b|數位鑑識|鑑識分析/iu],
  ['malware', /malware(?:\s+analysis)?|惡意程式(?:分析)?|惡意軟體(?:分析)?/iu],
  ['threat-intelligence', /threat intelligence|威脅情資/iu],
  ['threat-hunting', /threat hunting|威脅獵捕/iu],
  ['detection-engineering', /detection engineering|偵測工程|偵測規則/iu],
  ['network', /network security|網路安全|流量分析/iu],
  ['cloud', /cloud security|雲端安全/iu],
  ['ics', /(?:ics|ot|scada) security|工控安全|資安工控/iu],
  ['mobile', /android security|ios security|mobile security|行動安全|移動安全/iu],
  ['web3', /\bweb3\b|blockchain security|區塊鏈安全/iu],
  ['ai-security', /ai security|llm security|agentic security|人工智慧安全|生成式 ai 安全/iu],
  ['devsecops', /\bdevsecops\b|software supply chain|\bsbom\b|供應鏈安全/iu],
];

const RED_RULES = [
  /\bred team(?:ing)?\b/iu,
  /offensive security/iu,
  /penetration testing|\bpentest(?:ing)?\b/iu,
  /exploit development|漏洞利用|滲透測試|紅隊演練/iu,
];

const BLUE_RULES = [
  /\bblue team(?:ing)?\b/iu,
  /defensive security/iu,
  /security operations center|\bsoc\b/iu,
  /incident response|事件應變/iu,
  /threat hunting|威脅獵捕/iu,
  /detection engineering|偵測工程/iu,
  /\bdfir\b|數位鑑識/iu,
  /資安防護|防禦實戰/iu,
];

const PURPLE_EXPLICIT = /\bpurple team(?:ing)?\b|紫隊/iu;
const ADVERSARY_EVIDENCE = /adversary emulation|attack simulation|atomic red team|對手模擬|攻擊模擬/iu;
const DETECTION_EVIDENCE = /detection validation|detection engineering|偵測驗證|偵測工程|防禦驗證/iu;
const CTF_ATTACK_DEFENSE = /\battack\s*(?:&|and|-)\s*defen[cs]e\b|\bad[- ]ctf\b/iu;
const CTF_RED_TOPICS = new Set(['appsec', 'web', 'api', 'pwn', 'reverse']);
const CTF_BLUE_TOPICS = new Set(['forensics', 'threat-intelligence', 'threat-hunting', 'detection-engineering']);

function firstEvidence(text, rules) {
  for (const rule of rules) {
    const match = text.match(rule);
    if (match) return match[0];
  }
  return '';
}

function orderedTopics(text) {
  return TOPIC_RULES.flatMap(([topic, rule]) => {
    const match = rule.exec(text);
    return match ? [{ topic, evidence: match[0], index: match.index }] : [];
  }).sort((left, right) => left.index - right.index);
}

function classifyDirections(event, text, topicMatches) {
  const explicitPurple = firstEvidence(text, [PURPLE_EXPLICIT]);
  const adversary = firstEvidence(text, [ADVERSARY_EVIDENCE]);
  const detection = firstEvidence(text, [DETECTION_EVIDENCE]);
  if (explicitPurple || (adversary && detection)) {
    return {
      values: ['purple'],
      evidence: explicitPurple || `${adversary}; ${detection}`,
    };
  }

  if (event.kind === 'ctf') {
    const attackDefense = firstEvidence(text, [CTF_ATTACK_DEFENSE]);
    if (attackDefense) return { values: ['red', 'blue'], evidence: attackDefense };
    const redTopics = topicMatches.filter(({ topic }) => CTF_RED_TOPICS.has(topic));
    const blueTopics = topicMatches.filter(({ topic }) => CTF_BLUE_TOPICS.has(topic));
    const values = [redTopics.length ? 'red' : '', blueTopics.length ? 'blue' : ''].filter(Boolean);
    if (values.length) {
      return {
        values,
        evidence: [...redTopics, ...blueTopics].map(({ evidence }) => evidence).join('; '),
      };
    }
  }

  const red = firstEvidence(text, RED_RULES);
  const blue = firstEvidence(text, BLUE_RULES);
  const values = [];
  if (red) values.push('red');
  if (blue) values.push('blue');
  if (values.length > 1) return { values: ['general'], evidence: [red, blue].join('; ') };
  if (values.length > 0) return { values, evidence: [red, blue].filter(Boolean).join('; ') };
  return { values: ['unspecified'], evidence: '' };
}

function classifyLevel(text) {
  const beginner = firstEvidence(text, [
    /beginner[- ]friendly|no experience required|no prior experience|introductory/iu,
    /myfirst|junior|零基礎|無需經驗|初學者|入門/iu,
  ]);
  if (beginner) return { value: 'beginner', evidence: beginner };

  const advanced = firstEvidence(text, [
    /\badvanced(?:-level)?\b|\bexpert-level\b|professional experience|qualification round|selection exam/iu,
    /高階|進階|實戰經驗|資格賽|選拔|甄選/iu,
  ]);
  if (advanced) return { value: 'advanced', evidence: advanced };

  const foundational = firstEvidence(text, [
    /basic knowledge|required fundamentals?|familiarity with|prerequisite/iu,
    /具備基礎|基礎知識|先備知識|需熟悉/iu,
  ]);
  if (foundational) return { value: 'foundational', evidence: foundational };
  return { value: 'unspecified', evidence: '' };
}

function classifyParticipation(event, text) {
  if (event.teamSizeMin || event.teamSizeMax || event.teamSize) {
    return { value: 'team', evidence: event.teamSize || 'explicit team size' };
  }
  const team = firstEvidence(text, [/team(?:s)?\s+(?:of|size)|隊伍|組隊|團隊參賽/iu]);
  if (team) return { value: 'team', evidence: team };
  const individual = firstEvidence(text, [/individual registration|individual participation|solo|個人報名|個人參賽|個人申請/iu]);
  if (individual) return { value: 'individual', evidence: individual };
  return { value: 'unspecified', evidence: '' };
}

function classifyEvent(event) {
  if (!event) return event;
  const text = [event.title, event.description, event.classificationText, event.dateText]
    .filter(Boolean).join('\n').replace(/https?:\/\/\S+/giu, ' ');
  const topicMatches = orderedTopics(text);
  const directions = classifyDirections(event, text, topicMatches);
  const level = classifyLevel(text);
  const participation = classifyParticipation(event, text);
  const existingDirections = event.directions?.filter((value) => value !== 'unspecified') || [];
  const existingTopics = event.topics || [];

  return {
    ...event,
    directions: existingDirections.length > 0 ? existingDirections : directions.values,
    topics: [...new Set([...existingTopics, ...topicMatches.map(({ topic }) => topic)])],
    level: event.level && event.level !== 'unspecified' ? event.level : level.value,
    participation: event.participation && event.participation !== 'unspecified'
      ? event.participation : participation.value,
    evidence: {
      ...event.evidence,
      ...(directions.evidence ? { directions: directions.evidence } : {}),
      ...(topicMatches.length > 0
        ? { topics: topicMatches.map(({ evidence }) => evidence).join('; ') }
        : {}),
      ...(level.evidence ? { level: level.evidence } : {}),
      ...(participation.evidence ? { participation: participation.evidence } : {}),
    },
  };
}

module.exports = { classifyEvent, orderedTopics };
