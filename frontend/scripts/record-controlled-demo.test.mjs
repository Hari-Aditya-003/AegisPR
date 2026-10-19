import assert from 'node:assert/strict';
import test from 'node:test';

import {
  allowedRequest,
  safeOutput,
  validateFixture,
  validateRehearsalMarker,
} from './record-controlled-demo.mjs';

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
