import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { constants } from 'node:fs';
import { copyFile, lstat, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const website = 'https://hari-aditya-003.github.io/AegisPR/';
const app = 'http://127.0.0.1:3300';
const health = 'http://127.0.0.1:18880/health';
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const scenes = new Set(['preflight', 'brand', 'browser-illustration', 'python-evidence', 'manual-repair', 'node-evidence', 'gpu-health', 'remaining-work']);
let currentScene = 'SCENE preflight';

export function matchesHeroTitle(text) {
  return typeof text === 'string' && /trust.*PR.*Prove/i.test(text.replace(/\s+/g, ' '));
}

export function sceneCheckpoint(name) {
  if (!scenes.has(name)) throw new Error('Unknown scene');
  return `SCENE ${name}`;
}

export async function observedNavigation(responsePromise, navigationPromise) {
  const [response] = await Promise.all([responsePromise, navigationPromise]);
  return response;
}

export function validateFixture(run) {
  const fail = () => { throw new Error('Receipt validation failed'); };
  const checkExecution = (execution, status, code) => execution?.status === status
    && execution.exit_code === code && /^[a-f0-9]{40}$/.test(execution.commit)
    && execution.environment?.executor === 'docker'
    && execution.environment.network === 'none'
    && typeof execution.environment.command === 'string';
  if (!run || !uuid.test(run.id) || run.evidence_mode !== 'controlled_fixture'
    || run.model_used !== 'controlled-fixture-no-model' || run.status !== 'FIX_VERIFIED'
    || !['controlled-fixture://python', 'controlled-fixture://node'].includes(run.pull_request_url)
    || !['coupon-python', 'coupon-node'].includes(run.summary?.repository)
    || !/^[a-f0-9]{40}$/.test(run.summary.base_commit)
    || !/^[a-f0-9]{40}$/.test(run.summary.head_commit)
    || run.summary.base_commit === run.summary.head_commit
    || run.metrics?.context_accelerator !== 'not_used'
    || ['model_calls', 'input_tokens', 'output_tokens', 'accounted_cost_usd']
      .some(key => run.metrics?.[key] !== 0)
    || !run.findings?.length || run.findings.some(finding =>
      !checkExecution(finding.base_execution, 'PASSED', 0)
      || !checkExecution(finding.head_execution, 'FAILED', 1)
      || finding.base_execution.commit !== run.summary.base_commit
      || finding.head_execution.commit !== run.summary.head_commit)
    || run.repair?.status !== 'VERIFIED' || !run.repair.patch) fail();
  for (const name of ['existing_tests', 'generated_tests', 'build', 'lint']) {
    const checks = run.repair.checks?.filter(check => check.name === name);
    if (checks?.length !== 1) fail();
    const execution = checks[0].execution;
    if (['existing_tests', 'generated_tests'].includes(name)) {
      if (!checkExecution(execution, 'PASSED', 0)) fail();
    } else if (!(execution?.status === 'SKIPPED' || checkExecution(execution, 'PASSED', 0))) fail();
  }
  return run;
}

export function allowedRequest(rawUrl, method, ids) {
  try {
    const url = new URL(rawUrl);
    if (!['GET', 'OPTIONS'].includes(method) || url.username || url.password || url.search) return false;
    if (url.origin === new URL(website).origin) return url.pathname.startsWith('/AegisPR/');
    if (url.origin === app) return url.pathname === '/' || url.pathname.startsWith('/_next/')
      || url.pathname === '/favicon.ico' || url.pathname.startsWith('/brand/')
      || ids.some(id => uuid.test(id) && url.pathname === `/verifications/${id}`);
    if (url.origin === 'http://127.0.0.1:18080') return ids.some(id => uuid.test(id)
      && url.pathname === `/api/verifications/${id}`);
    return url.href === health;
  } catch { return false; }
}

export function safeOutput(message, privateValues = []) {
  if (typeof message !== 'string' || privateValues.some(value => value && message.includes(value))
    || /bearer\s|https?:\/\/|[a-f0-9]{64}/i.test(message)) throw new Error('Unsafe output rejected');
  return message;
}

export function validateRehearsalMarker(marker, fingerprint, now = Date.now()) {
  if (!marker || marker.version !== 1 || marker.success !== true || marker.fingerprint !== fingerprint
    || !Number.isFinite(marker.completed_at) || marker.completed_at > now
    || now - marker.completed_at > 3_600_000) throw new Error('Fresh rehearsal required');
}

async function assertNotSymlink(target) {
  try { if ((await lstat(target)).isSymbolicLink()) throw new Error('Unsafe local artifact path'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}

async function runDemo(mode) {
  const { chromium } = await import('@playwright/test');
  const outputDir = path.join(root, 'artifacts/demo');
  const markerPath = path.join(outputDir, 'rehearsal.json');
  const accessCode = (await readFile(path.join(root, 'artifacts/judge/access-code'), 'utf8')).trim();
  if (!/^[a-f0-9]{64}$/.test(accessCode)) throw new Error('Private local access code unavailable');
  const print = message => console.log(safeOutput(message, [accessCode]));
  const checkpoint = name => { currentScene = sceneCheckpoint(name); print(currentScene); };
  const evidenceDir = path.join(root, 'artifacts/judge/evidence');
  const receipts = [];
  for (const name of await readdir(evidenceDir)) {
    if (name.endsWith('.json')) receipts.push(validateFixture(JSON.parse(await readFile(path.join(evidenceDir, name), 'utf8'))));
  }
  receipts.sort((a, b) => String(b.started_at).localeCompare(String(a.started_at)));
  const python = receipts.find(run => run.pull_request_url === 'controlled-fixture://python');
  const node = receipts.find(run => run.pull_request_url === 'controlled-fixture://node');
  if (!python || !node) throw new Error('Both controlled receipts are required');
  const ids = [python.id, node.id];
  const fingerprint = createHash('sha256').update(await readFile(fileURLToPath(import.meta.url)))
    .update(JSON.stringify([python, node])).digest('hex');
  for (const target of [path.join(root, 'artifacts'), outputDir, markerPath]) await assertNotSymlink(target);
  await mkdir(outputDir, { recursive: true, mode: 0o700 });
  if (mode === '--record') validateRehearsalMarker(JSON.parse(await readFile(markerPath, 'utf8')), fingerprint);
  const record = mode === '--record';
  const takeDir = path.join(outputDir, `take-${Date.now()}`);
  if (record) await mkdir(takeDir, { mode: 0o700 });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 },
    serviceWorkers: 'block', ...(record ? { recordVideo: { dir: takeDir, size: { width: 1280, height: 720 } } } : {}) });
  let succeeded = false;
  const page = await context.newPage();
  const video = page.video();
  const pause = ms => page.waitForTimeout(record ? ms : Math.min(ms, 100));
  try {
    await context.route('**/*', route => allowedRequest(route.request().url(), route.request().method(), ids)
      ? route.continue() : route.abort('blockedbyclient'));
    await context.addInitScript(code => {
      if (location.origin === 'http://127.0.0.1:3300') sessionStorage.setItem('aegispr.deployment-access', code);
      const badge = () => {
        if (!document.body || document.getElementById('demo-draft')) return;
        const draft = document.createElement('div'); draft.id = 'demo-draft';
        draft.textContent = 'DRAFT · CONTROLLED CAPABILITIES';
        draft.style.cssText = 'position:fixed;top:12px;right:14px;z-index:1000000;border:1px solid #ffd784;border-radius:8px;background:#0a101bf5;color:#ffd784;padding:8px 12px;font:700 12px system-ui;pointer-events:none;letter-spacing:.8px';
        document.body.appendChild(draft);
      };
      new MutationObserver(badge).observe(document, { childList: true, subtree: true });
      document.addEventListener('DOMContentLoaded', badge, { once: true });
    }, accessCode);
    async function overlays(caption) {
      await page.evaluate(text => {
        for (const id of ['demo-cursor', 'demo-subtitle', 'demo-draft']) document.getElementById(id)?.remove();
        const cursor = document.createElement('div'); cursor.id = 'demo-cursor';
        cursor.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M5 3L19 12L12 13L9 20L5 3Z" fill="white" stroke="black" stroke-width="1.5" stroke-linejoin="round"/></svg>';
        cursor.style.cssText = 'position:fixed;z-index:999999;pointer-events:none;width:24px;height:24px;left:20px;top:20px;transition:left .1s,top .1s;filter:drop-shadow(1px 1px 2px #0008)';
        document.body.appendChild(cursor);
        document.onmousemove = event => { cursor.style.left = `${event.clientX}px`; cursor.style.top = `${event.clientY}px`; };
        const subtitle = document.createElement('div'); subtitle.id = 'demo-subtitle'; subtitle.textContent = text;
        subtitle.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:999998;text-align:center;padding:16px 28px;background:rgba(2,8,14,.94);color:white;font:500 20px/1.4 system-ui;pointer-events:none;border-top:1px solid #25d9c8';
        const draft = document.createElement('div'); draft.id = 'demo-draft'; draft.textContent = 'DRAFT · CONTROLLED CAPABILITIES';
        draft.style.cssText = 'position:fixed;top:12px;right:14px;z-index:1000000;border:1px solid #ffd784;border-radius:8px;background:#0a101bf5;color:#ffd784;padding:8px 12px;font:700 12px system-ui;pointer-events:none;letter-spacing:.8px';
        document.body.append(subtitle, draft);
      }, caption);
    }
    async function caption(text) {
      await page.locator('#demo-subtitle').evaluate((bar, value) => { bar.textContent = value; }, text);
    }
    async function navigate(url, text) {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 });
      await overlays(text);
    }
    async function reveal(locator) {
      await locator.waitFor({ state: 'visible', timeout: 15_000 });
      await locator.evaluate(element => element.scrollIntoView({ behavior: 'smooth', block: 'center' }));
      await pause(600);
      const box = await locator.boundingBox();
      assert.ok(box);
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 });
      await pause(300);
    }
    async function click(locator) { await reveal(locator); await locator.click(); await pause(450); }
    async function discover(label) {
      const fields = await page.locator('input,select,textarea,button,summary').evaluateAll(elements => elements
        .filter(element => element.getClientRects().length)
        .map(element => ({ tag: element.tagName, type: element.getAttribute('type') ?? '',
          id: element.id, text: element.tagName === 'INPUT' ? '' : element.textContent.trim().slice(0, 80) })));
      print(`${label}: ${JSON.stringify(fields)}`);
    }
    async function report(run, text) {
      const responsePromise = page.waitForResponse(response => response.url() === `http://127.0.0.1:18080/api/verifications/${run.id}` && response.request().method() === 'GET');
      const response = await observedNavigation(responsePromise, navigate(`${app}/verifications/${run.id}`, text));
      assert.equal(response.status(), 200);
      const actual = validateFixture(await response.json());
      assert.equal(actual.summary.base_commit, run.summary.base_commit);
      assert.equal(actual.summary.head_commit, run.summary.head_commit);
      await page.getByRole('heading', { name: 'Controlled fixture — not a live pull request review', exact: true }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'Generate and verify repair' }).count(), 0);
    }

    checkpoint('brand');
    await navigate(website, 'AegisPR checks changes with evidence. This hero is illustrative.');
    assert.ok(matchesHeroTitle(await page.locator('h1').innerText()));
    if (mode === '--discover') await discover('Landing page');
    await pause(7000);
    checkpoint('browser-illustration');
    await navigate(`${website}demo/`, 'Browser-only illustration: a coupon must never make a charge negative.');
    if (mode === '--discover') await discover('Browser illustration');
    for (const [selector, value] of [['#total', '10'], ['#discount', '20']]) {
      const input = page.locator(selector); await click(input); await input.fill('');
      await input.pressSequentially(value, { delay: record ? 90 : 1 });
    }
    await reveal(page.locator('#change')); await page.locator('#change').selectOption('buggy');
    await click(page.getByRole('button', { name: 'Run boundary check →', exact: true }));
    assert.equal((await page.locator('#base-status').innerText()).trim(), 'PASS');
    assert.equal((await page.locator('#head-status').innerText()).trim(), 'FAIL');
    await caption('Same boundary case: base passes, changed logic fails. Browser only.');
    await pause(7000);
    await click(page.getByRole('button', { name: 'Apply clamp & re-run', exact: true }));
    assert.match(await page.locator('#repair-result').innerText(), /pass|0|clamp/i);
    await caption('The browser example applies a prewritten clamp, not a model repair.');
    await pause(6000);
    checkpoint('python-evidence');
    await report(python, 'Real Docker receipts: fixed Python test, no model or live PR.');
    if (mode === '--discover') await discover('Python controlled report');
    await pause(4000);
    await click(page.locator('summary', { hasText: 'Inspect branch execution evidence' }));
    await reveal(page.getByRole('heading', { name: 'Base revision', exact: true }));
    assert.ok((await page.locator('body').innerText()).includes(python.summary.base_commit));
    await pause(5000);
    await reveal(page.getByRole('heading', { name: 'Fixture head revision', exact: true }));
    await caption('Actual commits, commands and failure logs make the result inspectable.');
    await pause(5000);
    checkpoint('manual-repair');
    await reveal(page.getByRole('heading', { name: 'Manual repair evidence', exact: true }));
    await caption('A manually authored repair passes the recorded checks.');
    await click(page.locator('summary', { hasText: 'Inspect repair check: generated tests' }));
    await pause(4000);
    await click(page.locator('summary', { hasText: 'View isolated patch' }));
    await pause(3000);
    await click(page.locator('summary', { hasText: 'test_generated.py' }));
    await caption('Fixed test artifact; unsupported build and lint checks stay SKIPPED.');
    await pause(5000);
    checkpoint('node-evidence');
    await report(node, 'The separate Node fixture also records real isolated execution.');
    if (mode === '--discover') await discover('Node controlled report');
    await reveal(page.getByRole('heading', { name: 'Manual repair evidence', exact: true }));
    assert.equal(node.repair.checks.find(check => check.name === 'build').execution.status, 'PASSED');
    await pause(7000);
    checkpoint('gpu-health');
    await navigate(health, 'Separate live GPU health: CUDA available. Not model-inference proof.');
    const actualHealth = JSON.parse(await page.locator('pre').innerText());
    assert.equal(actualHealth.status, 'ok');
    assert.equal(actualHealth.checks.gpu_accelerator, 'cuda');
    await page.evaluate(value => {
      document.body.style.cssText = 'margin:0;padding:90px 72px;background:#070c12;color:#d8f9ef;font:26px/1.6 monospace';
      const pre = document.querySelector('pre') ?? document.body.appendChild(document.createElement('pre'));
      pre.textContent = JSON.stringify(value, null, 2);
    }, actualHealth);
    await caption('“Configured” is configuration only, not a successful Nemotron call.');
    await pause(10000);
    checkpoint('remaining-work');
    await navigate(website, 'Still pending: funded live Nemotron inference and real PR acceptance.');
    await pause(8000);
    succeeded = true;
  } finally {
    await context.close();
    if (!succeeded && video) await video.delete();
    await browser.close();
  }
  if (mode === '--rehearse') {
    await writeFile(markerPath, JSON.stringify({ version: 1, success: true, fingerprint, completed_at: Date.now() }), { mode: 0o600 });
    print('REHEARSAL PASSED — all controlled story actions verified; no inference requested.');
  } else if (record) {
    const target = path.join(outputDir, 'controlled-capabilities.webm');
    await assertNotSymlink(target);
    await copyFile(await video.path(), target, constants.COPYFILE_EXCL);
    print('DRAFT VIDEO SAVED — artifacts/demo/controlled-capabilities.webm; not published.');
  } else print('DISCOVERY PASSED — fields mapped without input values; no inference requested.');
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const modes = process.argv.slice(2);
  if (modes.length !== 1 || !['--discover', '--rehearse', '--record'].includes(modes[0])) {
    console.error('Use exactly one mode: --discover, --rehearse, or --record.'); process.exitCode = 2;
  } else {
    runDemo(modes[0]).catch(() => {
      console.error(`CONTROLLED DEMO FAILED at ${currentScene} — check local access, receipts, tunnels and selectors. No footage published.`);
      process.exitCode = 1;
    });
  }
}
