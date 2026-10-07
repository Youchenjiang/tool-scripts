import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const tempDir = mkdtempSync(join(tmpdir(), 'chrome-audit-e2e-'));
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const screenshotDir = 'C:\\Users\\LabStrix\\.gemini\\antigravity\\brain\\1bba9d14-0ce0-4cc0-ba73-826544e2a698\\slide_screenshots_v2';
try {
  mkdirSync(screenshotDir, { recursive: true });
} catch {}

console.log('🚀 啟動 Headless Chrome 進行真實視覺佈局與碰撞檢測 (1920x1080)...');
const chrome = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9232',
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
      const res = await fetch('http://127.0.0.1:9232/json/version');
      const data = await res.json();
      return data.webSocketDebuggerUrl;
    } catch {
      await wait(200);
    }
  }
  throw new Error('無法連接 Chrome CDP 除錯埠');
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

    // 建立新分頁並導向簡報
    const target = await client.send('Target.createTarget', {
      url: 'http://127.0.0.1:4173/s/workshop-202610-net-wireshark-v2'
    });
    const pageClient = new CDPClient(`ws://127.0.0.1:9232/devtools/page/${target.targetId}`);

    await pageClient.send('Page.enable');
    await pageClient.send('Runtime.enable');
    await pageClient.send('Emulation.setDeviceMetricsOverride', {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      mobile: false
    });

    // 等待 React 掛載
    await wait(3000);

    // 進入 Present 投影播放模式 (全螢幕 1920x1080 原生解析度)
    const presentRes = await pageClient.send('Runtime.evaluate', {
      expression: `(() => {
        const presentBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Present'));
        if (presentBtn) {
          presentBtn.click();
          return true;
        }
        return false;
      })()`,
      returnByValue: true
    });

    if (!presentRes.result.value) {
      throw new Error('未找到 Present 播放按鈕，無法進入 1080p 投影檢測模式！');
    }
    await wait(1200);

    const report = [];

    for (let slideIndex = 1; slideIndex <= 12; slideIndex++) {
      // 評估真實 DOM 元素座標、碰撞與字級
      const inspectScript = `(() => {
        // 1. 抓取頁尾 (Footer) 及其頂端座標
        const pageSpan = Array.from(document.querySelectorAll('span')).find(s => 
          (s.textContent || '').includes('NET-Wireshark ·')
        );
        const footer = pageSpan ? pageSpan.parentElement : null;
        const footerTop = footer ? footer.getBoundingClientRect().top : 1005;

        // 2. 抓取當前頁碼確認
        const pageText = pageSpan ? pageSpan.textContent : '';
        const pageMatch = pageText.match(/NET-Wireshark\\s*·\\s*(\\d+)\\s*\\/\\s*(\\d+)/);
        const actualPage = pageMatch ? parseInt(pageMatch[1], 10) : null;

        // 3. 抓取標題
        const h1 = document.querySelector('h1');
        const title = h1 ? h1.innerText.trim().replace(/\\s+/g, ' ') : '';

        // 4. 抓取內容容器 (.rise 且排除 header/title)
        const rises = Array.from(document.querySelectorAll('.rise'));
        const contentBox = rises.length >= 3 ? rises[2] : rises[rises.length - 1];
        const contentChildren = contentBox ? Array.from(contentBox.querySelectorAll('*')) : [];

        let maxBottom = 0;
        let lowestElement = null;
        const collisions = [];
        const canvasOverflows = [];

        for (const el of contentChildren) {
          if (footer && (el === footer || footer.contains(el))) continue;
          const rect = el.getBoundingClientRect();
          if (rect.height <= 0 || rect.width <= 0) continue;

          if (rect.bottom > maxBottom) {
            maxBottom = rect.bottom;
            lowestElement = {
              tag: el.tagName,
              text: el.innerText ? el.innerText.trim().slice(0, 50).replace(/\\n/g, ' ') : '',
              top: Math.round(rect.top),
              bottom: Math.round(rect.bottom),
              height: Math.round(rect.height)
            };
          }

          // 物理碰撞檢測：內容最底端侵入頁尾頂端
          if (rect.bottom > footerTop + 1) {
            collisions.push({
              tag: el.tagName,
              text: el.innerText ? el.innerText.trim().slice(0, 50).replace(/\\n/g, ' ') : '',
              bottom: Math.round(rect.bottom),
              footerTop: Math.round(footerTop),
              overlap: Math.round(rect.bottom - footerTop)
            });
          }

          // 1080p 畫面底部溢出檢測
          if (rect.bottom > 1080) {
            canvasOverflows.push({
              tag: el.tagName,
              text: el.innerText ? el.innerText.trim().slice(0, 50).replace(/\\n/g, ' ') : '',
              bottom: Math.round(rect.bottom)
            });
          }
        }

        // 5. 檢測最小字級 (Typography Floor < 30px) - 使用標準 TreeWalker 遍歷真實文字節點
        const tinyText = [];
        if (contentBox) {
          const walker = document.createTreeWalker(contentBox, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
              if (!node.textContent || !node.textContent.trim()) return NodeFilter.FILTER_REJECT;
              return NodeFilter.FILTER_ACCEPT;
            }
          });
          while (walker.nextNode()) {
            const node = walker.currentNode;
            const parent = node.parentElement;
            if (!parent) continue;
            if (footer && footer.contains(parent)) continue;
            const fs = parseFloat(window.getComputedStyle(parent).fontSize);
            if (fs < 29.5) {
              tinyText.push({ text: node.textContent.trim().slice(0, 30), fontSize: fs, tag: parent.tagName });
            }
          }
        }

        // 6. 檢測頂部眉題 (Eyebrow)：二合一、無時間戳記、字級 18~24px、與大標題間距 >= 15px
        const headerRise = rises.find(r => {
          const style = r.getAttribute('style') || '';
          return style.includes('top: 36') || style.includes('top:36') || style.includes('top: 48') || style.includes('top:48') || style.includes('top: 42') || style.includes('top:42');
        });
        const eyebrowSpan = headerRise ? headerRise.querySelector('span') : null;
        const eyebrowText = eyebrowSpan ? (eyebrowSpan.innerText || '').trim() : '';
        const eyebrowRect = eyebrowSpan ? eyebrowSpan.getBoundingClientRect() : null;
        const h1Rect = h1 ? h1.getBoundingClientRect() : null;
        let eyebrowIssue = null;

        if (headerRise && headerRise.children.length > 1) {
          eyebrowIssue = '頂部標籤未二合一（發現 ' + headerRise.children.length + ' 個並排標籤，規範必須收斂為單一 eyebrow 標籤）';
        } else if (eyebrowText && /\b\d{1,2}:\d{2}\b/.test(eyebrowText)) {
          eyebrowIssue = '眉題包含時間戳記 ("' + eyebrowText + '")，違反「不需要時間」規範';
        } else if (eyebrowText.includes('幹嘛')) {
          eyebrowIssue = '眉題包含口語化字詞 ("' + eyebrowText + '")';
        } else if (eyebrowText.length > 16) {
          eyebrowIssue = '眉題文字過長 (' + eyebrowText.length + ' 字 > 16 字: "' + eyebrowText + '")';
        } else if (['，', ',', '。', '！', '!', '？', '?', '：', ':'].some(p => eyebrowText.includes(p))) {
          eyebrowIssue = '眉題包含標點符號，疑似塞入內文或心法長句: "' + eyebrowText + '"';
        } else if (eyebrowRect && eyebrowRect.width > 450) {
          eyebrowIssue = '眉題寬度過寬 (' + Math.round(eyebrowRect.width) + 'px > 450px)，破壞頂部視覺平衡';
        } else if (eyebrowSpan) {
          const fs = parseFloat(window.getComputedStyle(eyebrowSpan).fontSize);
          if (fs < 17.5 || fs > 24.5) {
            eyebrowIssue = '眉題字級異常 (' + fs + 'px，規範必須在 18px ~ 24px 輔助標籤層級)';
          } else if (eyebrowRect && h1Rect) {
            const gap = Math.round(h1Rect.top - eyebrowRect.bottom);
            if (gap < 15) {
              eyebrowIssue = '眉題與大標題垂直間距過近 (' + gap + 'px < 15px 安全距離，產生擠壓碰撞)';
            }
          }
        }

        return {
          title,
          actualPage,
          footerTop: Math.round(footerTop),
          maxBottom: Math.round(maxBottom),
          safetyMargin: Math.round(footerTop - maxBottom),
          lowestElement,
          collisionCount: collisions.length,
          worstCollision: collisions.length > 0 ? collisions[0] : null,
          canvasOverflowCount: canvasOverflows.length,
          tinyTextCount: tinyText.length,
          tinyTextSample: tinyText.slice(0, 3),
          eyebrowIssue
        };
      })()`;

      const evalRes = await pageClient.send('Runtime.evaluate', {
        expression: inspectScript,
        returnByValue: true
      });

      const res = evalRes.result.value;
      const issues = [];
      let status = 'PASS';

      if (res.actualPage !== slideIndex) {
        issues.push(`頁碼不符 (期望 P.${slideIndex}, 實際 P.${res.actualPage})`);
        status = 'FAIL';
      }

      if (res.collisionCount > 0) {
        issues.push(`頁尾文字物理重疊 (Overlap ${res.worstCollision.overlap}px)`);
        status = 'FAIL';
      }

      if (res.canvasOverflowCount > 0) {
        issues.push(`超出 1080p 畫面底部`);
        status = 'FAIL';
      }

      if (res.safetyMargin < 15) {
        issues.push(`安全呼吸邊距過緊 (僅 ${res.safetyMargin}px, 建議 >= 20px)`);
        status = 'FAIL';
      }

      if (res.tinyTextCount > 0) {
        issues.push(`字級未達 30px 規範 (${res.tinyTextCount} 處違規, 如: "${res.tinyTextSample[0]?.text}" ${res.tinyTextSample[0]?.fontSize}px)`);
        status = 'FAIL';
      }

      if (res.eyebrowIssue) {
        issues.push(res.eyebrowIssue);
        status = 'FAIL';
      }

      // 儲存真實渲染截圖
      const padNum = String(slideIndex).padStart(2, '0');
      const shot = await pageClient.send('Page.captureScreenshot', { format: 'png' });
      const shotPath = join(screenshotDir, `slide_${padNum}.png`);
      writeFileSync(shotPath, Buffer.from(shot.data, 'base64'));

      report.push({
        slide: slideIndex,
        page: res.actualPage,
        title: res.title,
        status,
        footerTop: res.footerTop,
        maxBottom: res.maxBottom,
        safetyMargin: res.safetyMargin,
        lowestElement: res.lowestElement,
        issues,
        shotPath
      });

      console.log(`[Slide ${padNum}/12] P.${res.actualPage} | ${status === 'PASS' ? '✅ PASS' : '❌ FAIL'} | 標題: "${res.title}"`);
      console.log(`          頁尾頂端: ${res.footerTop}px | 內容最底: ${res.maxBottom}px | 留白邊距: +${res.safetyMargin}px`);
      if (issues.length > 0) {
        for (const iss of issues) {
          console.log(`          ⚠️  ${iss}`);
        }
      }

      // 切換下一頁
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

    console.log('\n================================================================');
    console.log('       🎯 HEADLESS BROWSER 視覺碰撞與版面物理檢測總結            ');
    console.log('================================================================');

    let passCount = 0;
    let failCount = 0;

    for (const r of report) {
      const padNum = String(r.slide).padStart(2, '0');
      if (r.status === 'PASS') {
        passCount++;
        console.log(`\x1b[32m[PASS]\x1b[0m 頁面 ${padNum} (P.${r.page}): ${r.title}`);
        console.log(`       ↳ 留白安全呼吸感: +${r.safetyMargin}px (最底元素: <${r.lowestElement?.tag}> "${r.lowestElement?.text.slice(0, 30)}...")`);
      } else {
        failCount++;
        console.log(`\x1b[31m[FAIL]\x1b[0m 頁面 ${padNum} (P.${r.page}): ${r.title}`);
        for (const iss of r.issues) {
          console.log(`       ↳ \x1b[31m${iss}\x1b[0m`);
        }
      }
    }

    console.log(`\n統計結果: 共 12 頁，通過: ${passCount} 頁，失敗: ${failCount} 頁`);
    console.log(`截圖已儲存至: ${screenshotDir}\n`);

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
  console.error('執行視覺檢測時發生錯誤:', err);
  process.exit(1);
});

