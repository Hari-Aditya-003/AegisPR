// Ordinary toggle buttons keep every option reachable with Tab / Enter / Space.
// All guides remain readable when JavaScript is unavailable.
export function bindGuide(buttons, panels) {
  function select(path) {
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.guide === path)));
    panels.forEach(panel => { panel.hidden = panel.id !== `guide-${path}`; });
  }
  buttons.forEach(button => button.addEventListener('click', () => select(button.dataset.guide)));
  if (buttons.length) select(buttons[0].dataset.guide);
}

if (typeof document !== 'undefined') {
  bindGuide([...document.querySelectorAll('[data-guide]')], [...document.querySelectorAll('.guide-panel')]);
}
