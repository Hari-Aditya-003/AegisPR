const stages=[
  ["CONTEXT ENGINE","Repository structure before speculation.","AegisPR discovers the stack, changed files, commands, and dependency neighborhood. The Dell NVIDIA GPU ranks relevant context with deterministic CUDA vector scoring."],
  ["NEMOTRON REASONING","Risks written as testable hypotheses.","Nebius Token Factory serves NVIDIA Nemotron with bounded, untrusted repository context. Each hypothesis names an affected surface and a concrete verification strategy."],
  ["TEST SYNTHESIS","A claim becomes runnable code.","The planner produces framework-native tests and explicit commands. Only allowlisted commands reach the sandbox; prose can never become a shell instruction."],
  ["DIFFERENTIAL RUNNER","Same experiment. Two commits.","Isolated Docker sandboxes execute the generated check against the base and pull request revisions with no runtime network, dropped capabilities, and resource limits."],
  ["EVIDENCE REPORT","Conclusions constrained by outcomes.","A deterministic matrix classifies the result and stores commit SHAs, commands, exit codes, logs, durations, generated test code, and the scope disclaimer."],
  ["REPAIR VERIFIER","A proposed fix must prove itself.","For confirmed regressions, Nemotron emits a minimal unified diff. AegisPR applies it only in an ephemeral checkout, then separately runs existing tests, the generated regression test, build, and lint. Only complete passing evidence becomes FIX_VERIFIED."]
];
const examples = [
  '$ aegis analyze owner/repo#42\n✓ changed files indexed\n✓ impact neighborhood ranked\n→ bounded context for Nemotron',
  'HYPOTHESIS H1\nDiscount exceeds the cart value.\n→ test input: total=10, discount=20',
  'def test_discount_boundary():\n    assert apply_coupon(10, 20) == 0',
  'BASE   → PASS · total = 0\nPR     → FAIL · total = -10\n→ identical test, two revisions',
  'CLASSIFICATION: REGRESSION\n✓ exact commits and commands\n✓ exit codes and execution logs',
  'REPAIR PROPOSAL\nreturn max(total - discount, 0)\n→ re-run every selected check'
];
const detail = document.querySelector('.stage-detail');
const stageButtons = [...document.querySelectorAll('.stage')];
stageButtons.forEach((button, index) => {
  button.setAttribute('aria-pressed', String(index === 0));
  button.addEventListener('click', () => {
    stageButtons.forEach(stage => {
      stage.classList.remove('active');
      stage.setAttribute('aria-pressed', 'false');
    });
    button.classList.add('active');
    button.setAttribute('aria-pressed', 'true');
    const [label, title, copy] = stages[index];
    document.querySelector('#stage-label').textContent = label;
    document.querySelector('#stage-title').textContent = title;
    document.querySelector('#stage-copy').textContent = copy;
    detail.querySelector('pre').textContent = examples[index];
    detail.classList.remove('changing');
    requestAnimationFrame(() => detail.classList.add('changing'));
  });
});
detail.querySelector('pre').textContent = examples[0];
const exampleNote = document.createElement('p');
exampleNote.className = 'caption';
exampleNote.textContent = 'Illustrative workflow · not a live execution';
detail.append(exampleNote);
