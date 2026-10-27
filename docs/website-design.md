# Public website and usage guide

Updated October 28, 2026. The public landing page is served from `website/dist/` through the GitHub Pages workflow. It is separate from the private Next.js verification application.

## Design

The requested ZeroTrace reference informed the charcoal background, mint accents, dotted field, framed navigation and restrained motion. The page uses AegisPR's own supplied logo and project-specific content; it does not import the reference site's assets or code. The hero retains the established “Don’t trust a PR. Prove it.” slogan required by the capability recorder.

The landing page has its own `landing.css`. Existing `styles.css`, `brand.css` and the browser experiment remain unchanged, avoiding accidental demo styling regressions. There are no added external fonts, trackers, libraries or inference calls.

## How to use

The `#verify-pr` section now gives authorized operators a GitHub PR field and a controlled example. It accepts only canonical public GitHub `/pull/NUMBER` URLs, then navigates to the fixed Dell Tailscale frontend with the public URL as a query parameter. It transfers **no** application access code or provider key. The private form prefills the URL but never auto-submits, so navigation alone cannot spend credits. The operator must connect to Tailscale, save the application access code, then press **Verify PR**. The resulting authenticated report contains the **Agent timeline** and evidence. This is not a public arbitrary-code review service; GitHub Pages cannot run the Docker-backed pipeline, and judges without private access cannot use this path.

The `#how-to-use` section has three selectable guides:

1. **Browser experiment:** no setup, keys or tokens. Fixed JavaScript implementations demonstrate the base/change/manual-repair comparison.
2. **Local judging build:** Linux and Docker setup, the launcher command, private access-code instructions, and the actual prewritten Python/Node fixture receipts. No model generation, GPU ranking or live PR claims.
3. **Live PR workflow:** server-side credentials, provider-credit prerequisites, private app authentication, PR verification and optional repair verification. The dated controlled-PR evidence and its `INCONCLUSIVE` outcome are explicitly disclosed.

The old `#use` anchor remains as a compatibility alias. All guide content is readable without JavaScript. Toggle buttons expose `aria-pressed` and `aria-controls`; native FAQ disclosures support keyboard use. Decorative motion respects `prefers-reduced-motion`, and the footer provides a pause/resume control that also disables smooth scrolling.

## Verification

Targeted automated checks:

```bash
node --test website/tests/*.test.mjs frontend/scripts/record-controlled-demo.test.mjs
git diff --check
```

October 21 result: **20 checks passed** (12 website checks and 8 recorder guards). New checks cover guide state, content scope, navigation targets, local assets and the recorder's heading contract. The missing guide and later heading regression were each reproduced before their respective fixes.

Browser inspection covered the desktop layout, 390px and 320px widths without horizontal overflow, all three guide choices, Enter-key guide activation, workflow stage changes, FAQ expansion, and the animation pause control. No browser console errors were observed during the checked interactions. These are targeted website checks, not a repeat of the October 19 backend/GPU acceptance matrix, a comprehensive accessibility audit, or new evidence of live model inference.

The private draft video was not re-recorded or uploaded for the October 21 redesign. No Dell service, production authentication, provider key or inference budget was changed then.

## October 25 evidence viewer

The public static build now includes `website/dist/evidence/`, linked from both the landing page and browser experiment. It displays the exact controlled-PR scope, pinned commits, selected base/head output values, three fresh Nemotron intent votes, `BEHAVIOR_CHANGE` finding and `INCONCLUSIVE` overall status. Its spending figures are explicitly **app estimates**, not a provider invoice. It has no form, provider key or PR-processing endpoint. It links to the dated receipt and the separate full local judging build. It is not the private full application.

The page was developed with red-to-green tests. All **25 website tests** passed locally. A local browser check at 1280px and 390px widths confirmed rendering, accessible disclosure content, no horizontal overflow and the intended links. This is not a comprehensive accessibility audit. Recheck the public GitHub Pages URL after deployment; local preview alone does not prove publication.

## October 26 evidence update

The read-only evidence page now leads with the [fresh Nemotron 3 Super run](live-pr-super-comparison-2026-10-26.md): one generated changed-function example, selected actual base/head outputs, four confirmation executions, three advisory intent votes, the `INCONCLUSIVE` overall status, exact run/commit IDs and app-estimated cost. The October 25 cached-Lightning-plan run remains below it with its separate provenance and spending. The landing-page status strip and browser-demo notice also point to the fresh run while preserving the demo's fixed-fixture disclosure. Both runs concern **one seeded PR**, not two benchmark cases. No secret, input form or model-spending endpoint was added to the public page.

The new test failed before the page change and passed afterward. All **26 website tests** passed locally. A local browser check at 1280px and 390px found no horizontal overflow; full-page screenshots were visually inspected. This is a static summary, not the private authenticated report or a comprehensive accessibility audit. Verify the live GitHub Pages deployment before treating it as published.

## October 28 PR handoff and timeline guide

The SQLite PR #883 recording showed a one-off local replay page; it did not include the product's PR form or Agent timeline. To remove that ambiguity, the landing page now has a visible **Verify a PR** entry point, URL validation, an example button, and a three-step guide to the private app's prefilled form, live timeline and evidence. The page labels the SQLite recording separately and discloses private Tailscale/access-code requirements and potential credit use.

Tests were written before implementation. The website and frontend tests were red for the missing handoff/prefill, then green after implementation. Local results: **29 website tests**, **35 frontend tests**, frontend typecheck and production build, and a zero-vulnerability production dependency audit. Headless browser checks at 1280px and 390px blocked an invalid URL, populated the controlled example, and found no horizontal overflow. An end-to-end browser handoff reached the Dell Tailscale app with the controlled PR URL prefilled; it did not press Verify PR or call Nebius. The Dell frontend container alone was rebuilt/restarted; backend and GPU worker were left unchanged. This evidence does not make the app publicly judge-accessible.
