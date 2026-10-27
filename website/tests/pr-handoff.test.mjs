import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { buildVerifierUrl, normalizePrUrl } from '../dist/pr-handoff.mjs';

const html = readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8');

test('public PR handoff accepts only canonical GitHub pull request URLs', () => {
  assert.equal(normalizePrUrl('  https://github.com/acme/store/pull/42/  '), 'https://github.com/acme/store/pull/42');
  for (const value of [
    '', 'https://example.com/acme/store/pull/42', 'http://github.com/acme/store/pull/42',
    'https://github.com.evil.test/acme/store/pull/42', 'https://github.com/acme/store/issues/42',
    'https://github.com/acme/store/pull/0', 'https://github.com/acme/store/pull/42?token=secret',
    'https://github.com/acme/store/pull/42#fragment', 'javascript:alert(1)',
  ]) assert.equal(normalizePrUrl(value), null, value);
});

test('handoff sends only the public PR URL to the fixed private verifier', () => {
  const url = new URL(buildVerifierUrl('https://github.com/acme/store/pull/42'));
  assert.equal(url.protocol, 'http:');
  assert.equal(url.hostname, 'hari-dell-g15-5510.tail8849b3.ts.net');
  assert.equal(url.port, '3000');
  assert.equal(url.searchParams.get('pr'), 'https://github.com/acme/store/pull/42');
  assert.equal(url.hash, '#verify-title');
  assert.equal([...url.searchParams.keys()].join(','), 'pr');
  assert.throws(() => buildVerifierUrl('https://evil.test/pull/42'));
});

test('website explains where the real PR form and agent timeline live', () => {
  assert.match(html, /id="verify-pr"/);
  assert.match(html, /id="public-pr-url"/);
  assert.match(html, /id="pr-handoff-form"/);
  assert.match(html, /Agent timeline/);
  assert.match(html, /private.*access/i);
  assert.match(html, /does not run.*PR/i);
  assert.match(html, /href="#verify-pr"/);
  assert.match(html, /pr-handoff\.mjs/);
});
