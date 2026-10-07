import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const tempDir = mkdtempSync(join(tmpdir(), 'chrome-audit-nav-'));
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const chrome = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9228',
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
      const res = await fetch('http://127.0.0.1:9228/json/version');
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
    const client = new CDPClient(wsUrl);
    const target = await client.send('Target.createTarget', {
      url: 'http://127.0.0.1:4173/s/workshop-202610-net-wireshark-fundamentals'
    });
    const pageClient = new CDPClient(`ws://127.0.0.1:9228/devtools/page/${target.targetId}`);
    await pageClient.send('Page.enable');
    await pageClient.send('Runtime.enable');
    await pageClient.send('Emulation.setDeviceMetricsOverride', {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      mobile: false
    });
    await wait(3000);

    // Enter Present mode
    await pageClient.send('Runtime.evaluate', {
      expression: `(() => {
        const presentBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Present'));
        if (presentBtn) presentBtn.click();
      })()`
    });
    await wait(1000);

    // Check page indicator
    let page = await pageClient.send('Runtime.evaluate', {
      expression: `(() => {
        const m = document.body.innerText.match(/NET-Wireshark\\s*·\\s*(\\d+)\\s*\\/\\s*(\\d+)/);
        return m ? m[1] : 'unknown';
      })()`,
      returnByValue: true
    });
    console.log('Initial Present Page:', page.result.value);

    // Send ArrowRight
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

    page = await pageClient.send('Runtime.evaluate', {
      expression: `(() => {
        const m = document.body.innerText.match(/NET-Wireshark\\s*·\\s*(\\d+)\\s*\\/\\s*(\\d+)/);
        return m ? m[1] : 'unknown';
      })()`,
      returnByValue: true
    });
    console.log('Page after ArrowRight:', page.result.value);

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
