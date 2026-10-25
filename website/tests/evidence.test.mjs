import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const evidence = () => readFileSync(new URL('../dist/evidence/index.html', import.meta.url), 'utf8');

test('public evidence page identifies the controlled PR and the dated real-model stages', () => {
  const html = evidence();
  assert.match(html, /6d6a108f-3b98-482c-9aeb-cc6494180c55/);
  assert.match(html, /nvidia\/Nemotron-3_5-Lightning/);
  assert.match(html, /saved (?:model )?plan/i);
  assert.match(html, /three (?:new )?(?:paid )?intent-review calls/i);
  assert.match(html, /AegisPR-acceptance\/pull\/1/);
});

test('public evidence page shows branch observations, votes and conservative outcome', () => {
  const html = evidence();
  assert.match(html, /50[^<]*100/);
  assert.match(html, /-50/);
  assert.match(html, /0[^<]*10/);
  assert.match(html, /-10/);
  assert.match(html, /3\/3[^<]*unintended/i);
  assert.match(html, /INCONCLUSIVE/);
  assert.doesNotMatch(html, /<strong>REGRESSION_FOUND<\/strong>/);
  assert.match(html, /not proof of a confirmed regression/i);
});

test('public evidence page discloses scope and cannot accept credentials or run arbitrary PRs', () => {
  const html = evidence();
  assert.match(html, /controlled (?:seeded )?PR/i);
  assert.match(html, /not (?:an )?independent (?:real-world )?benchmark/i);
  assert.match(html, /app-estimated/i);
  assert.match(html, /Dell[^<]*CUDA/i);
  assert.match(html, /not a Nebius GPU/i);
  assert.doesNotMatch(html, /<input|<form|API_ACCESS_TOKEN|NEBIUS_API_KEY/);
  assert.match(html, /href="\.\.\/demo\/"/);
});
