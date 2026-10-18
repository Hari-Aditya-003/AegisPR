export function bindMotionControl(button, root) {
  if (!button) return;
  button.addEventListener('click', () => {
    const paused = root.dataset.motion !== 'paused';
    if (paused) root.dataset.motion = 'paused';
    else delete root.dataset.motion;
    button.setAttribute('aria-pressed', String(paused));
    button.textContent = paused ? 'Resume animation' : 'Pause animation';
  });
}

if (typeof document !== 'undefined') {
  bindMotionControl(document.getElementById('motion-control'), document.documentElement);
}
