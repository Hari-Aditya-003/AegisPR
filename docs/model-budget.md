# Model selection and $25 credit protection

## What is verified

Catalog availability and API authentication are verified. A bounded model-only completion succeeded on October 23 after credits were added; see the [dated receipt](live-nebius-check.md). A later [controlled-PR attempt](live-pr-attempt-2026-10-24.md) generated and executed one Nemotron-written example but ended `INCONCLUSIVE`; the saved example's offline replay found a stable output difference. Neither establishes model quality on PRs. Do not report an output-quality score, latency comparison, successful model-generated repair, or a winning model until a measured acceptance run exists.

The repository default changed from Ultra to `nvidia/Nemotron-3_5-Lightning` as a lower-cost evaluation candidate. A [dated October 26 trial](live-pr-super-comparison-2026-10-26.md) also ran `nvidia/nemotron-3-super-120b-a12b` against one seeded PR: it generated an executable changed-function test and found a stable behavior change, after earlier Lightning plans failed validation. The prompts and validation changed between trials, so this is not a controlled model-quality comparison or proof that Super is universally better. Planning still uses one configured model and does not automatically escalate; an optional, explicitly configured intent ensemble can route its existing three advisory votes to three different Nemotron models. Using every catalog model is neither a correctness test nor a hackathon requirement.

The [Nebius public catalog](https://tokenfactory.nebius.com/api/public/models_info), checked October 18, lists these NVIDIA model IDs and USD prices per million input/output tokens:

| Model ID | Input | Output |
| --- | ---: | ---: |
| `nvidia/Nemotron-3_5-Lightning` | 0.06 | 0.24 |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 0.06 | 0.24 |
| `nvidia/nemotron-3-super-120b-a12b` | 0.30 | 0.90 |
| `nvidia/Nemotron-3.5-Super-VL` | 0.30 | 0.90 |
| `nvidia/Nemotron-3-Ultra-550b-a55b` | 1.00 | 3.00 |

Prices and availability can change; check the account catalog before spending. Vision is not required for the current text/code workflow. A catalog listing is not evidence that an application has used that model.

## Enforced application controls

- Persistent SQLite ledger alongside the run database: `inference-budget.sqlite3`. Keep this volume across restarts; deleting it resets app accounting and removes cached responses.
- Before a provider call, an atomic reservation checks a $20 total estimate, $0.25 per verification, and five provider attempts per verification (including explanations and repairs). The remaining $5 of the planned $25 is contingency, not an account-level restriction.
- Input is capped at 32,000 UTF-8 bytes per request after prompt assembly. Planning context uses at most eight documents with bounded excerpts, a bounded diff, and at most two experiments. This intentionally sacrifices broad repository coverage to protect credits; the report is scope-limited.
- Output limits: initial plan 8,192 tokens and one eligible malformed-plan correction 4,096; test refinement 1,536; intent vote 256; explanation 512; repair 2,048. The larger planning allowance covers one compact test file, not additional model calls. The SDK is configured with zero automatic retries and a 45-second request timeout. HTTP 402 is visible; no background retry loop spends credits.
- A failed generated base test may consume up to two budgeted refinement calls. A stable output difference may consume three separate intent votes only if the remaining five-call admission window permits all three; otherwise it remains unreviewed and inconclusive. By default the three calls use `NEBIUS_MODEL`. To opt into model diversity, set `INTENT_REVIEW_MODELS` to exactly three distinct, comma-separated, priced NVIDIA Nemotron IDs; for example Lightning, Nano and Super from the table above. Each vote uses its model's verified admission price and its own cache key. A failed or budget-blocked vote stops the sequence, preserves completed votes, and reports an incomplete, unclear review. There are no automatic retry calls.
- Admission estimates use UTF-8 byte counts plus a protocol margin and a price allowlist. Unknown model prices fail closed. Reported provider usage replaces the reservation; missing usage or ambiguous failures retain conservative reservations. Explicit request rejections release the monetary reservation but still count as attempts.
- Exact request fingerprints reuse persisted structured responses. Cache hits do not send provider requests, but test execution still occurs independently. A changed model, stage, prompt, or output bound changes the key.
- Authenticated `/api/budget` and run metrics expose app accounting, token usage, and cache hits. An optional explanation failure does not erase independently reproduced test evidence.
- Production `/api/*` is gated by a separate private access code and existing create/repair rate limits. Never put `NEBIUS_API_KEY` in a browser or a static site.

These are **app-side admission estimates, not a guaranteed provider hard spending cap or an account balance**. Tokenization, pricing changes, provider accounting, another app using the same key, prior account usage, or deleting the ledger can make actual bills differ. Reconcile the provider usage page; do not raise limits or enable unattended paid loops without that check. A budget of zero blocks new paid requests (cached responses can still be reused).

Three different models can reduce same-model repetition, but their judgments can still share errors. A unanimous `intended` or `unintended` opinion is not evidence that the author approved that interpretation. The product retains `BEHAVIOR_CHANGE` and overall `INCONCLUSIVE` until a human confirms the intent. The October 26 live report predates the cross-model option and used three votes from Super; the ensemble currently has local mocked-provider tests, not a measured live-PR accuracy result.

## Minimal live evaluation with the available credits

Use a fixed seeded regression and a no-regression control with exact base/head commits. Compare Lightning against Ultra only if necessary, with the same capped context and a total trial ceiling below $0.50. Capture valid schema, collected executable test, correct differential outcome, false positives, repair checks, provider token usage, latency, and cost per successful verification. Select the cheapest candidate meeting the acceptance criteria. Do not infer quality from price or size.

Reserve judging credits before recording. A controlled public PR has now been reviewed with live model-generated testing, but an independent real-PR benchmark, a public full-application judging route, and the entrant's final YouTube demonstration remain outstanding; see [submission readiness](submission-readiness.md).
