import test from 'node:test';
import assert from 'node:assert/strict';
import { verifyBoundary } from '../dist/demo/boundary.mjs';

test('identifies the oversized-discount regression and the repaired outcome', () => {
  assert.deepEqual(verifyBoundary(10, 20), {
    base: 0, head: -10, repair: 0, expected: 0, classification: 'REGRESSION_FOUND',
  });
});
test('does not invent a failure for a normal discount', () => {
  assert.equal(verifyBoundary(20, 5).classification, 'VERIFIED_WITHIN_SCOPE');
});
test('a safe implementation passes the same oversized-discount check', () => {
  assert.equal(verifyBoundary(10, 20, false).classification, 'VERIFIED_WITHIN_SCOPE');
});
test('currency uses integer cents to avoid subtraction noise', () => {
  assert.equal(verifyBoundary(0.3, 0.1).head, 0.2);
});
test('zero amounts are accepted', () => {
  assert.equal(verifyBoundary(0, 0).base, 0);
});
test('invalid or excessive inputs are rejected', () => {
  for (const input of [-1, NaN, Infinity, '10', Number.MAX_VALUE]) {
    assert.throws(() => verifyBoundary(input, 5), /amount/i);
    assert.throws(() => verifyBoundary(5, input), /amount/i);
  }
});
