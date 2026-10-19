import assert from 'node:assert/strict';
import test from 'node:test';

import {
  allowedRequest,
  matchesHeroTitle,
  observedNavigation,
  safeOutput,
  sceneCheckpoint,
  setupReadOnlyNetwork,
  validateFixture,
  validateRehearsalMarker,
} from './record-controlled-demo.mjs';

test('hero assertion tolerates rendered line breaks without accepting unrelated headings', () => {
  assert.equal(matchesHeroTitle('Don’t trust a PR.\nProve it.'), true);
  assert.equal(matchesHeroTitle('Don’t trust a PR. Prove it.'), true);
  assert.equal(matchesHeroTitle('Different page'), false);
});

test('diagnostic checkpoints contain only fixed scene names', () => {
  assert.equal(sceneCheckpoint('python-evidence'), 'SCENE python-evidence');
  for (const name of ['python-navigation', 'python-response-validation', 'python-provenance',
    'python-open-branches', 'python-base-reveal', 'python-head-reveal',
    'node-navigation', 'node-response-validation', 'node-provenance']) {
    assert.equal(sceneCheckpoint(name), `SCENE ${name}`);
  }
  assert.throws(() => sceneCheckpoint('c'.repeat(64)), /Unknown scene/);
  assert.throws(() => sceneCheckpoint('https://unsafe.test'), /Unknown scene/);
});

test('navigation failure still observes the pending response rejection during cleanup', async () => {
  let rejectResponse;
  const response = new Promise((resolve, reject) => { rejectResponse = reject; });
  await assert.rejects(observedNavigation(response, Promise.reject(new Error('Navigation failed'))), /Navigation failed/);
  rejectResponse(new Error('Context closed'));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(await observedNavigation(Promise.resolve('receipt'), Promise.resolve()), 'receipt');
});

test('network setup closes all WebSockets and keeps HTTP requests read-only', async () => {
  let httpRoute;
  let socketRoute;
  await setupReadOnlyNetwork({
    async route(pattern, handler) { assert.equal(pattern, '**/*'); httpRoute = handler; },
    async routeWebSocket(pattern, handler) { assert.equal(pattern, '**/*'); socketRoute = handler; },
  }, [id]);
  let continued = 0;
  let aborted = 0;
  const request = method => ({
    request: () => ({ url: () => `http://127.0.0.1:18080/api/verifications/${id}`, method: () => method }),
    continue: async () => { continued++; }, abort: async () => { aborted++; },
  });
  await httpRoute(request('GET'));
  await httpRoute(request('POST'));
  let closed = false;
  await socketRoute({ close: async options => { closed = true; assert.equal(options.code, 1008); } });
  assert.equal(continued, 1); assert.equal(aborted, 1); assert.equal(closed, true);
});

const id = '8fbe82b9-ba35-488d-9bcc-54b89fb2ea1c';
const execution = (status, exitCode) => ({
  status, exit_code: exitCode, commit: (status === 'FAILED' ? 'b' : 'a').repeat(40),
  environment: { executor: 'docker', network: 'none', command: 'pytest -q' },
  stdout: 'actual receipt', stderr: '',
});
const receipt = () => ({
  id, evidence_mode: 'controlled_fixture', model_used: 'controlled-fixture-no-model',
  pull_request_url: 'controlled-fixture://python', status: 'FIX_VERIFIED',
  summary: { repository: 'coupon-python', base_commit: 'a'.repeat(40), head_commit: 'b'.repeat(40) },
  metrics: { model_calls: 0, input_tokens: 0, output_tokens: 0, accounted_cost_usd: 0, context_accelerator: 'not_used' },
  findings: [{ base_execution: execution('PASSED', 0), head_execution: execution('FAILED', 1) }],
  repair: { status: 'VERIFIED', patch: '--- a/coupon.py\n+++ b/coupon.py', checks: [
    { name: 'existing_tests', execution: execution('PASSED', 0) },
    { name: 'generated_tests', execution: execution('PASSED', 0) },
    { name: 'build', execution: { status: 'SKIPPED' } },
    { name: 'lint', execution: { status: 'SKIPPED' } },
  ] },
});

test('accepts only zero-inference controlled Docker receipts', () => {
  assert.equal(validateFixture(receipt()).id, id);
  for (const change of [
    r => { r.evidence_mode = 'pr_review'; },
    r => { r.model_used = 'nvidia/model'; },
    r => { r.metrics.model_calls = 1; },
    r => { r.metrics.input_tokens = 1; },
    r => { r.metrics.output_tokens = 1; },
    r => { r.metrics.accounted_cost_usd = 0.01; },
    r => { r.metrics.context_accelerator = 'cuda'; },
    r => { delete r.metrics.model_calls; },
    r => { r.findings[0].head_execution.status = 'ERROR'; },
    r => { r.findings[0].head_execution.commit = 'a'.repeat(40); },
    r => { r.findings[0].base_execution.commit = 'b'.repeat(40); },
    r => { r.findings[0].base_execution.exit_code = 1; },
    r => { r.findings[0].head_execution.exit_code = 0; },
    r => { r.summary.head_commit = r.summary.base_commit; },
    r => { r.findings[0].base_execution.environment.executor = 'mock'; },
    r => { r.repair.checks.pop(); },
    r => { r.repair.checks[0].execution.status = 'FAILED'; },
    r => { r.id = '../secret'; },
  ]) {
    const changed = receipt(); change(changed);
    assert.throws(() => validateFixture(changed), /Receipt validation failed/);
  }
});

test('network admission permits only fixed read-only evidence surfaces', () => {
  const accepted = [
    'https://hari-aditya-003.github.io/AegisPR/',
    'https://hari-aditya-003.github.io/AegisPR/demo/',
    'http://127.0.0.1:3300/_next/static/chunks/main.js',
    `http://127.0.0.1:18080/api/verifications/${id}`,
    'http://127.0.0.1:18880/health',
  ];
  for (const url of accepted) assert.equal(allowedRequest(url, 'GET', [id]), true);
  for (const [url, method] of [
    ['https://api.tokenfactory.nebius.com/v1/chat/completions', 'POST'],
    ['http://127.0.0.1:18080/api/verifications', 'POST'],
    [`http://127.0.0.1:18080/api/verifications/${id}/repair`, 'POST'],
    ['http://127.0.0.1:18080/api/budget', 'GET'],
    ['http://127.0.0.1:18880/api/verifications', 'GET'],
    ['https://hari-aditya-003.github.io/other/', 'GET'],
    ['https://hari-aditya-003.github.io.evil.test/AegisPR/', 'GET'],
    ['http://user:password@127.0.0.1:3300/', 'GET'],
    ['http://127.0.0.1:3300/?key=private', 'GET'],
    ['file:///etc/passwd', 'GET'],
    ['not a URL', 'GET'],
  ]) assert.equal(allowedRequest(url, method, [id]), false);
});

test('safe output rejects private codes and unsafe URLs', () => {
  const secret = 'c'.repeat(64);
  assert.equal(safeOutput('REHEARSAL PASSED', [secret]), 'REHEARSAL PASSED');
  assert.throws(() => safeOutput(`Access ${secret}`, [secret]), /Unsafe output rejected/);
  assert.throws(() => safeOutput('https://evil.test/?token=x', []), /Unsafe output rejected/);
  assert.throws(() => safeOutput('Bearer hidden', []), /Unsafe output rejected/);
});

test('recording requires a fresh matching successful rehearsal', () => {
  const now = 1_000_000;
  const marker = { version: 1, success: true, fingerprint: 'same', completed_at: now - 1000 };
  assert.doesNotThrow(() => validateRehearsalMarker(marker, 'same', now));
  for (const changed of [
    { ...marker, success: false }, { ...marker, fingerprint: 'changed' },
    { ...marker, completed_at: now - 3_600_001 },
    { ...marker, completed_at: now + 1 }, null,
  ]) assert.throws(() => validateRehearsalMarker(changed, 'same', now), /Fresh rehearsal required/);
});
