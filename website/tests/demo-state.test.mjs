import test from 'node:test';
import assert from 'node:assert/strict';

test('editing experiment inputs invalidates old evidence and disables the old repair', async () => {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      value: '', hidden: ['results', 'repair-result', 'input-error'].includes(id), textContent: '',
      listeners: {}, classList: { toggle() {} },
      addEventListener(name, listener) { this.listeners[name] = listener; },
    });
    return elements.get(id);
  };
  globalThis.document = { getElementById: element };
  try {
    await import('../dist/demo/demo.mjs');
    for (const [id, event] of [['total', 'input'], ['discount', 'input'], ['change', 'change']]) {
      element('total').value = '10';
      element('discount').value = '20';
      element('change').value = 'buggy';
      element('experiment').listeners.submit({ preventDefault() {} });
      assert.equal(element('results').hidden, false);
      element('repair').listeners.click();
      assert.equal(element('repair-result').hidden, false);
      assert.equal(typeof element(id).listeners[event], 'function', `${id} must invalidate stale evidence`);
      element(id).listeners[event]();
      assert.equal(element('results').hidden, true);
      assert.equal(element('repair-result').hidden, true);
      assert.equal(element('idle').hidden, false);
      element('repair').listeners.click();
      assert.equal(element('repair-result').hidden, true, 'cannot re-use evidence after its inputs changed');
    }
  } finally { delete globalThis.document; }
});
