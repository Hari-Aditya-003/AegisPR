const PR_PATTERN = /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/[1-9][0-9]*\/?$/;
const PRIVATE_VERIFIER = 'http://hari-dell-g15-5510.tail8849b3.ts.net:3000/';
export const EXAMPLE_PR = 'https://github.com/Hari-Aditya-003/AegisPR-acceptance/pull/1';

export function normalizePrUrl(value) {
  if (typeof value !== 'string' || value.length > 300) return null;
  const trimmed = value.trim();
  return PR_PATTERN.test(trimmed) ? trimmed.replace(/\/$/, '') : null;
}

export function buildVerifierUrl(value) {
  const prUrl = normalizePrUrl(value);
  if (!prUrl) throw new TypeError('A canonical public GitHub pull request URL is required.');
  const destination = new URL(PRIVATE_VERIFIER);
  destination.searchParams.set('pr', prUrl);
  destination.hash = 'verify-title';
  return destination.toString();
}

export function bindPrHandoff(form, input, error, exampleButton) {
  if (!form || !input || !error || !exampleButton) return;
  const showError = message => {
    error.textContent = message;
    error.hidden = !message;
    input.setAttribute('aria-invalid', String(Boolean(message)));
  };
  exampleButton.addEventListener('click', () => {
    input.value = EXAMPLE_PR;
    showError('');
    input.focus();
  });
  input.addEventListener('input', () => showError(''));
  form.addEventListener('submit', event => {
    event.preventDefault();
    const prUrl = normalizePrUrl(input.value);
    if (!prUrl) {
      showError('Paste a public GitHub pull request URL, for example https://github.com/owner/repo/pull/42.');
      input.focus();
      return;
    }
    window.location.assign(buildVerifierUrl(prUrl));
  });
}

if (typeof document !== 'undefined') {
  bindPrHandoff(
    document.querySelector('#pr-handoff-form'),
    document.querySelector('#public-pr-url'),
    document.querySelector('#pr-handoff-error'),
    document.querySelector('#example-pr'),
  );
}
