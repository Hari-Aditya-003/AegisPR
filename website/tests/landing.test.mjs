import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8');

test('hero retains the stable project slogan used by the capability recorder', () => {
  const title = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)[1].replace(/<[^>]*>/g, ' ');
  assert.match(title, /trust[\s\S]*PR[\s\S]*Prove/);
});

test('landing page offers three clearly scoped how-to paths and a no-script fallback', () => {
  assert.match(html, /id="how-to-use"/);
  for (const path of ['browser', 'local', 'live']) {
    assert.match(html, new RegExp(`data-guide="${path}"`));
    assert.match(html, new RegExp(`id="guide-${path}"`));
  }
  assert.match(html, /<noscript>/);
  assert.match(html, /not a live PR review/i);
  assert.match(html, /usable Nebius credits/i);
  assert.match(html, /artifacts\/judge\/access-code/);
});

test('guide controller selects one panel and exposes its state to assistive technology', async () => {
  const { bindGuide } = await import('../dist/guide.mjs');
  const buttons = ['browser', 'local', 'live'].map(path => ({
    dataset: { guide: path }, attrs: {},
    setAttribute(name, value) { this.attrs[name] = value; },
    addEventListener(name, listener) { assert.equal(name, 'click'); this.click = listener; },
  }));
  const panels = buttons.map(button => ({ id: `guide-${button.dataset.guide}`, hidden: false }));
  bindGuide(buttons, panels);
  assert.deepEqual(panels.map(panel => panel.hidden), [false, true, true]);
  buttons[1].click();
  assert.deepEqual(panels.map(panel => panel.hidden), [true, false, true]);
  assert.deepEqual(buttons.map(button => button.attrs['aria-pressed']), ['false', 'true', 'false']);
  buttons[2].click();
  assert.deepEqual(panels.map(panel => panel.hidden), [true, true, false]);
  buttons[0].click();
  assert.deepEqual(panels.map(panel => panel.hidden), [false, true, true]);
});

test('navigation targets exist and essential local assets are present', () => {
  for (const [, target] of html.matchAll(/href="#([^"]+)"/g)) {
    assert.ok(html.includes(`id="${target}"`), `missing navigation target ${target}`);
  }
  for (const [, asset] of html.matchAll(/(?:src|href)="\.\/([^"#]+\.(?:css|mjs|js|jpg|svg))"/g)) {
    assert.ok(readFileSync(new URL(`../dist/${asset}`, import.meta.url)).length > 0, asset);
  }
});
