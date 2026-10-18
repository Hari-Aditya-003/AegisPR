import { verifyBoundary } from './boundary.mjs';

const byId = id => document.getElementById(id);
let latest;
const money = value => value.toFixed(2);
function invalidateEvidence() {
  latest = undefined;
  byId('results').hidden = true;
  byId('repair-result').hidden = true;
  byId('input-error').hidden = true;
  byId('idle').hidden = false;
  byId('idle').textContent = 'Inputs changed. Run the experiment again to create current evidence.';
}
for (const id of ['total', 'discount']) byId(id).addEventListener('input', invalidateEvidence);
byId('change').addEventListener('change', invalidateEvidence);
byId('experiment').addEventListener('submit', event => {
  event.preventDefault();
  byId('input-error').hidden = true;
  byId('repair-result').hidden = true;
  try {
    const total = byId('total').value;
    const discount = byId('discount').value;
    if (!total.trim() || !discount.trim()) throw new Error('Enter both amounts.');
    latest = verifyBoundary(Number(total), Number(discount), byId('change').value === 'buggy');
    const regression = latest.classification === 'REGRESSION_FOUND';
    byId('idle').hidden = true;
    byId('results').hidden = false;
    byId('classification').textContent = latest.classification.replaceAll('_', ' ');
    byId('classification').classList.toggle('danger', regression);
    byId('base-status').textContent = 'PASS';
    byId('head-status').textContent = regression ? 'FAIL' : 'PASS';
    byId('head-status').classList.toggle('failed', regression);
    byId('base-value').textContent = `actual: ${money(latest.base)} · expected: ${money(latest.expected)}`;
    byId('head-value').textContent = `actual: ${money(latest.head)} · expected: ${money(latest.expected)}`;
    byId('conclusion').textContent = regression ? 'The baseline passes, but removing the clamp makes the changed version fail the same check.' : 'Both versions pass this input. No regression was reproduced within this experiment.';
    byId('repair').hidden = !regression;
  } catch (error) {
    latest = undefined;
    byId('results').hidden = true;
    byId('idle').hidden = false;
    byId('input-error').textContent = error.message;
    byId('input-error').hidden = false;
  }
});
byId('repair').addEventListener('click', () => {
  if (!latest) return;
  byId('repair-result').hidden = false;
  byId('repair-value').textContent = `actual: ${money(latest.repair)} · expected: ${money(latest.expected)}`;
});
function preset(total, discount) {
  byId('total').value = total;
  byId('discount').value = discount;
  byId('change').value = 'buggy';
  byId('experiment').requestSubmit();
}
byId('oversized').addEventListener('click', () => preset(10, 20));
byId('normal').addEventListener('click', () => preset(20, 5));
