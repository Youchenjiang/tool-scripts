import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const tempDir = mkdtempSync(join(tmpdir(), 'chrome-audit-debug-'));
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const chrome = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9231',
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
      const res = await fetch('http://127.0.0.1:9231/json/version');
      const data = await res.json();
      return data.webSocketDebuggerUrl;
    } catch {
      await wait(200);
    }
  }
  throw new Error('Chrome failed to start');
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
    const client = new CDPClient(wsUrl);
    const target = await client.send('Target.createTarget', {
      url: 'http://127.0.0.1:4173/s/workshop-202610-net-wireshark-fundamentals'
    });
    const pageClient = new CDPClient(`ws://127.0.0.1:9231/devtools/page/${target.targetId}`);
    await pageClient.send('Page.enable');
    await pageClient.send('Runtime.enable');
    await pageClient.send('Emulation.setDeviceMetricsOverride', {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      mobile: false
    });
    await wait(3000);

    // Click Present
    await pageClient.send('Runtime.evaluate', {
      expression: `(() => {
        const presentBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Present'));
        if (presentBtn) presentBtn.click();
      })()`
    });
    await wait(1200);

    // Test on Slide 1 and Slide 11
    const testBounds = await pageClient.send('Runtime.evaluate', {
      expression: `(() => {
        const pageSpan = Array.from(document.querySelectorAll('span')).find(s => 
          (s.textContent || '').includes('NET-Wireshark ·')
        );
        const footer = pageSpan ? pageSpan.parentElement : null;
        const footerTop = footer ? footer.getBoundingClientRect().top : 1005;

        // Content container
        const rise = document.querySelectorAll('.rise');
        const contentBox = rise.length >= 3 ? rise[2] : rise[rise.length - 1];
        const contentChildren = contentBox ? Array.from(contentBox.querySelectorAll('*')) : [];

        let maxBottom = 0;
        let lowest = null;
        for (const el of contentChildren) {
          const rect = el.getBoundingClientRect();
          if (rect.height > 0 && rect.bottom > maxBottom) {
            maxBottom = rect.bottom;
            lowest = { tag: el.tagName, text: el.textContent.trim().slice(0, 40), bottom: rect.bottom };
          }
        }

        return {
          footerTop,
          maxBottom,
          margin: footerTop - maxBottom,
          lowest
        };
      })()`,
      returnByValue: true
    });

    console.log('Slide 1 Content Bounds:', testBounds.result.value);

    // Navigate to Slide 11
    for (let i = 1; i <= 10; i++) {
      await pageClient.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
      await pageClient.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
      await wait(300);
    }
    await wait(800);

    const testSlide11 = await pageClient.send('Runtime.evaluate', {
      expression: `(() => {
        const pageSpan = Array.from(document.querySelectorAll('span')).find(s => 
          (s.textContent || '').includes('NET-Wireshark ·')
        );
        const footer = pageSpan ? pageSpan.parentElement : null;
        const footerTop = footer ? footer.getBoundingClientRect().top : 1005;

        const rise = document.querySelectorAll('.rise');
        const contentBox = rise.length >= 3 ? rise[2] : rise[rise.length - 1];
        const contentChildren = contentBox ? Array.from(contentBox.querySelectorAll('*')) : [];

        let maxBottom = 0;
        let lowest = null;
        for (const el of contentChildren) {
          const rect = el.getBoundingClientRect();
          if (rect.height > 0 && rect.bottom > maxBottom) {
            maxBottom = rect.bottom;
            lowest = { tag: el.tagName, text: el.textContent.trim().slice(0, 40), bottom: rect.bottom };
          }
        }

        return {
          page: pageSpan ? pageSpan.textContent : null,
          footerTop,
          maxBottom,
          margin: footerTop - maxBottom,
          lowest
        };
      })()`,
      returnByValue: true
    });

    console.log('Slide 11 Content Bounds:', testSlide11.result.value);

    await pageClient.close();
    await client.close();
  } finally {
    chrome.kill();
    try {
      rmSync(tempDir, { recursive: true, force: true });
    } catch {}
  }
}

run().catch(console.error);
