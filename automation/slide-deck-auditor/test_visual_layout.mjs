import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const tempDir = mkdtempSync(join(tmpdir(), 'chrome-audit-'));
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const screenshotDir = 'C:\\Users\\LabStrix\\.gemini\\antigravity\\brain\\1bba9d14-0ce0-4cc0-ba73-826544e2a698\\slide_screenshots';
try {
  mkdirSync(screenshotDir, { recursive: true });
} catch {}

console.log('Spawning headless Chrome...');
const chrome = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9224',
  '--disable-gpu',
  `--user-data-dir=${tempDir}`,
  '--window-size=1920,1080',
  'about:blank'
], { stdio: 'ignore' });

async function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function getWsUrl() {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch('http://127.0.0.1:9224/json/version');
      const data = await res.json();
      return data.webSocketDebuggerUrl;
    } catch {
      await wait(200);
    }
  }
  throw new Error('Chrome failed to start in time');
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
    this.ready = new Promise((resolve) => {
      this.ws.onopen = resolve;
    });
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
  }

  async send(method, params = {}) {
    await this.ready;
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async close() {
    this.ws.close();
  }
}

async function run() {
  try {
    const wsUrl = await getWsUrl();
    console.log('Connected to Chrome CDP:', wsUrl);
    const client = new CDPClient(wsUrl);

    // Create target page
    const target = await client.send('Target.createTarget', {
      url: 'http://127.0.0.1:4173/s/workshop-202610-net-wireshark-fundamentals'
    });
    const pageWsUrl = `ws://127.0.0.1:9224/devtools/page/${target.targetId}`;
    const pageClient = new CDPClient(pageWsUrl);

    await pageClient.send('Page.enable');
    await pageClient.send('Runtime.enable');
    await pageClient.send('Emulation.setDeviceMetricsOverride', {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      mobile: false
    });

    console.log('Navigating to deck and waiting for React mount...');
    // Wait until deck mounts
    let mounted = false;
    for (let i = 0; i < 40; i++) {
      const check = await pageClient.send('Runtime.evaluate', {
        expression: `Boolean(document.querySelector('.rise') || document.querySelector('h1'))`,
        returnByValue: true
      });
      if (check.result.value) {
        mounted = true;
        break;
      }
      await wait(250);
    }

    if (!mounted) {
      throw new Error('Slide deck failed to mount in DOM after 10s!');
    }
    console.log('Deck successfully mounted in DOM.');

    // Ensure we start at slide 1
    for (let i = 0; i < 15; i++) {
      await pageClient.send('Input.dispatchKeyEvent', {
        type: 'rawKeyDown',
        key: 'Home',
        code: 'Home',
        windowsVirtualKeyCode: 36
      });
      await wait(50);
    }
    await wait(500);

    const report = [];

    for (let slideIndex = 1; slideIndex <= 12; slideIndex++) {
      console.log(`\n=============================================`);
      console.log(`Inspecting Slide ${slideIndex} / 12`);
      console.log(`=============================================`);

      // Evaluate visual layout bounds
      const inspectScript = `(() => {
        // Find footer
        const allDivs = Array.from(document.querySelectorAll('div, footer'));
        const footer = allDivs.find(d => {
          const style = d.getAttribute('style') || '';
          return style.includes('bottom: 30') || d.textContent.includes('NET-Wireshark');
        });

        const footerRect = footer ? footer.getBoundingClientRect() : null;
        const footerTop = footerRect ? footerRect.top : 1010;

        // Slide title
        const h1 = document.querySelector('h1');
        const title = h1 ? h1.textContent.trim().replace(/\\s+/g, ' ') : '';
        const bodyText = document.body.textContent || '';
        const pageIndicatorMatch = bodyText.match(/NET-Wireshark\\s*·\\s*(\\d+)\\s*\\/\\s*(\\d+)/);
        const currentPage = pageIndicatorMatch ? parseInt(pageIndicatorMatch[1], 10) : null;

        // Check all rendered visible elements
        const allElements = Array.from(document.querySelectorAll('body *'));
        let maxBottom = 0;
        let worstElement = null;
        const collisions = [];
        const canvasOverflows = [];

        for (const el of allElements) {
          if (footer && (el === footer || footer.contains(el))) continue;
          if (['HTML', 'BODY', 'SCRIPT', 'STYLE'].includes(el.tagName)) continue;
          
          const rect = el.getBoundingClientRect();
          // Filter out full-page containers (height > 900) or 0-size elements
          if (rect.height <= 0 || rect.width <= 0 || rect.height >= 950) continue;
          if (rect.top < 30) continue;

          if (rect.bottom > maxBottom) {
            maxBottom = rect.bottom;
            worstElement = {
              tag: el.tagName,
              text: el.textContent.trim().slice(0, 60),
              bottom: Math.round(rect.bottom),
              height: Math.round(rect.height),
              top: Math.round(rect.top)
            };
          }

          // Check footer collision (element bottom pushes into footer top)
          if (footer && rect.bottom > footerTop + 2) {
            collisions.push({
              tag: el.tagName,
              text: el.textContent.trim().slice(0, 60),
              bottom: Math.round(rect.bottom),
              footerTop: Math.round(footerTop),
              overlap: Math.round(rect.bottom - footerTop)
            });
          }

          // Check canvas overflow (> 1080)
          if (rect.bottom > 1080) {
            canvasOverflows.push({
              tag: el.tagName,
              text: el.textContent.trim().slice(0, 60),
              bottom: Math.round(rect.bottom)
            });
          }
        }

        // Check font size floor (< 30px) across text elements
        const tinyText = [];
        for (const el of document.querySelectorAll('p, span, div, li, code, h1, h2, h3')) {
          if (footer && footer.contains(el)) continue;
          if (el.children.length > 0 && Array.from(el.children).some(c => ['P','DIV','LI','H1','H2','H3'].includes(c.tagName))) continue;
          const text = el.textContent.trim();
          if (!text) continue;
          const fs = parseFloat(window.getComputedStyle(el).fontSize);
          if (fs < 29.5) {
            tinyText.push({ text: text.slice(0, 30), fontSize: fs, tag: el.tagName });
          }
        }

        return {
          title,
          currentPage,
          footerTop: Math.round(footerTop),
          maxBottom: Math.round(maxBottom),
          safetyMargin: Math.round(footerTop - maxBottom),
          worstElement,
          collisionCount: collisions.length,
          worstCollision: collisions.length > 0 ? collisions[0] : null,
          canvasOverflowCount: canvasOverflows.length,
          tinyTextCount: tinyText.length,
          tinyTextSample: tinyText.slice(0, 3)
        };
      })()`;

      const evalRes = await pageClient.send('Runtime.evaluate', {
        expression: inspectScript,
        returnByValue: true
      });

      const res = evalRes.result.value;
      console.log(`Slide ${slideIndex} (Page ${res.currentPage}): "${res.title}"`);
      console.log(`  Footer Top: ${res.footerTop}px | Max Content Bottom: ${res.maxBottom}px | Safety Margin: ${res.safetyMargin}px`);

      let status = 'PASS';
      const issues = [];

      if (res.collisionCount > 0) {
        status = 'FAIL';
        console.error(`  ❌ [COLLISION] Overlaps footer by ${res.worstCollision.overlap}px! Element: <${res.worstCollision.tag}> "${res.worstCollision.text}"`);
        issues.push(`Footer collision by ${res.worstCollision.overlap}px`);
      }

      if (res.canvasOverflowCount > 0) {
        status = 'FAIL';
        console.error(`  ❌ [OVERFLOW] Element exceeds 1080px screen bottom!`);
        issues.push(`Canvas overflow (>1080px)`);
      }

      if (res.tinyTextCount > 0) {
        status = 'FAIL';
        console.error(`  ❌ [TYPOGRAPHY FLOOR] Found ${res.tinyTextCount} elements with fontSize < 30px!`);
        console.error(`     Sample:`, res.tinyTextSample);
        issues.push(`Font size < 30px (${res.tinyTextCount} instances)`);
      }

      if (status === 'PASS') {
        console.log(`  ✅ [PASS] Layout pristine: ${res.safetyMargin}px breathing room, font >= 30px.`);
      }

      report.push({
        slide: slideIndex,
        page: res.currentPage,
        title: res.title,
        status,
        margin: res.safetyMargin,
        issues
      });

      // Take screenshot
      const shot = await pageClient.send('Page.captureScreenshot', { format: 'png' });
      writeFileSync(join(screenshotDir, `slide_${slideIndex}.png`), Buffer.from(shot.data, 'base64'));

      // Press ArrowRight to go to next slide
      await pageClient.send('Input.dispatchKeyEvent', {
        type: 'rawKeyDown',
        key: 'ArrowRight',
        code: 'ArrowRight',
        windowsVirtualKeyCode: 39
      });
      await pageClient.send('Input.dispatchKeyEvent', {
        type: 'keyUp',
        key: 'ArrowRight',
        code: 'ArrowRight',
        windowsVirtualKeyCode: 39
      });

      await wait(600);
    }

    console.log('\n=============================================');
    console.log('       BROWSER E2E LAYOUT AUDIT RESULTS      ');
    console.log('=============================================');
    let failCount = 0;
    for (const r of report) {
      if (r.status === 'FAIL') {
        failCount++;
        console.log(`❌ Slide ${r.slide} (P.${r.page} - ${r.title}): FAILED -> ${r.issues.join(', ')}`);
      } else {
        console.log(`✅ Slide ${r.slide} (P.${r.page} - ${r.title}): PASSED (Safety Margin: +${r.margin}px)`);
      }
    }
    console.log(`\nFinal Verdict: ${12 - failCount} / 12 Slides Passed (${failCount} Failures)\n`);

    await pageClient.close();
    await client.close();

    if (failCount > 0) {
      process.exit(1);
    }
  } finally {
    chrome.kill();
    try {
      rmSync(tempDir, { recursive: true, force: true });
    } catch {}
  }
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
