import test from 'node:test';
import assert from 'node:assert/strict';
import { bindMotionControl } from '../dist/motion.mjs';

test('visitors can disable and restore decorative animation without storing personal data', () => {
  const root = { dataset: {} };
  const button = {
    attrs: {}, textContent: '',
    addEventListener(event, action) { assert.equal(event, 'click'); this.click = action; },
    setAttribute(name, value) { this.attrs[name] = value; },
  };
  bindMotionControl(button, root);
  button.click();
  assert.equal(root.dataset.motion, 'paused');
  assert.equal(button.attrs['aria-pressed'], 'true');
  assert.equal(button.textContent, 'Resume animation');
  button.click();
  assert.equal(root.dataset.motion, undefined);
  assert.equal(button.attrs['aria-pressed'], 'false');
  assert.equal(button.textContent, 'Pause animation');
});
