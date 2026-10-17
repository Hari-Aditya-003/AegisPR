function cents(amount) {
  const value = Math.round(amount * 100);
  if (typeof amount !== 'number' || !Number.isFinite(amount) || amount < 0 || !Number.isSafeInteger(value)) {
    throw new RangeError('Enter a finite, non-negative amount within the supported range.');
  }
  return value;
}

// Browser port of the demo-store coupon fixture, not a repository execution engine.
export function verifyBoundary(total, discount, removeClamp = true) {
  const difference = cents(total) - cents(discount);
  const expected = Math.max(difference, 0) / 100;
  const base = expected;
  const head = removeClamp ? difference / 100 : expected;
  return {
    base, head, repair: expected, expected,
    classification: head === expected ? 'VERIFIED_WITHIN_SCOPE' : 'REGRESSION_FOUND',
  };
}
