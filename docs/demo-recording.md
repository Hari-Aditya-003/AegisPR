# Draft capability recording

This is a **capability preview, not the final end-to-end hackathon submission video**. A separate live Nemotron connectivity check succeeded on October 23, 2026. On October 25, a controlled public PR's saved model plan was replayed through the full app and real Docker execution without a new provider call; the stable behavior change remained `INCONCLUSIVE` on intent. The fixture footage below is **not** footage of that PR replay. Do not replace missing PR evidence with fixture footage or invent model feedback.

The recorder separates three evidence modes:

1. The public browser-only coupon experiment and its manually defined clamp repair.
2. Saved Python/Node Docker execution receipts from the isolated judging build. Tests, hypotheses and repairs are prewritten; exact commands, commits, logs and configured checks are real.
3. A fresh read-only health response from the separate Dell production app. `gpu_accelerator: cuda` reports current worker readiness. `nebius: configured` is credential presence, not successful inference, provider balance or a measured GPU speedup.

A persistent draft badge and scene captions keep those boundaries visible. The landing-page proof card is explicitly illustrative. A recording does not establish model quality, general correctness, security certification or eligibility.

## Prerequisites

- Install frontend dependencies and Playwright Chromium (`npm ci`, then `npx playwright install chromium` from `frontend`).
- Start and export the [credential-free judging build](judge-test-build.md). The private application code and actual receipt JSON files must be present under ignored `artifacts/judge/`; never substitute a provider key.
- The judging UI/API must be reachable on loopback `3300`/`18080`.
- This author's GPU scene additionally needs the actual Dell production `/health` response forwarded to loopback `18880`, with CUDA currently available. For a remote machine, use authenticated SSH port forwarding and retain strict host-key checks. Do not expose the private Docker-socket-backed application publicly or weaken SSH verification for a recording.
- The published GitHub Pages website must be reachable. The recorder does not silently fabricate an offline replacement or a healthy GPU result.

## Discover, rehearse, then record

```bash
cd frontend
npm run demo:test
npm run demo:discover
npm run demo:rehearse
npm run demo:record
```

Discovery maps the actual controls without printing input values. Rehearsal performs the complete scene sequence without video and saves a short-lived success marker tied to its input evidence. Recording requires that fresh matching rehearsal. It produces a captioned 1280×720 WebM under ignored `artifacts/demo/`; it does not upload or submit anything.

The script accepts only fixed read-only evidence surfaces. Verification/repair submissions and provider endpoints are excluded. The local deployment code is consumed privately and injected only into the judging UI's session storage; it is never typed, placed in a URL, printed or included in captions. Failed or incomplete footage is not a successful deliverable. Keep raw local artifacts private and review the final video before sharing it.

## October 19 local draft receipt

Discovery and the complete rehearsal succeeded before a recording was saved locally on October 19, 2026. This is a silent video with English captions, not an uploaded or submitted demonstration.

| Property | Observed value |
| --- | --- |
| Local output (Git-ignored) | `artifacts/demo/controlled-capabilities.webm` |
| Duration | 104.52 seconds |
| Encoding | VP8, 1280×720, 25 fps |
| File size | 6,726,722 bytes |
| SHA-256 | `6ede508303773017690448748da608f218830384b0589d7c6145aa9af262c17b` |
| Python / Node reports | `8fbe82b9-ba35-488d-9bcc-54b89fb2ea1c` / `caac6c13-5643-4847-8ea3-81889b921529` |

`ffprobe` verified the media metadata. Sampled frames at 7, 43, 53, 60, 70, 79, 90 and 96 seconds were visually inspected: the draft badge and scene captions were present, fixed test/manual-repair provenance remained visible, and no deployment code was visible in those samples. This is **sampled review, not an exhaustive frame-by-frame privacy audit**. The final scene explicitly states that funded live Nemotron inference and real PR acceptance remain pending. The GPU scene reads the actual production health endpoint; it does not establish successful model inference.

An earlier recording attempt and browser check timed out while the local SSH-forwarded API was intermittently unavailable. No failed take was published. After API health recovered, all four real-stack browser checks and a fresh complete rehearsal passed sequentially before this take. No host reboot, driver change, paid inference attempt or public upload was performed for the recording.

The final local regression run passed 211 standard checks plus those four real-stack browser checks (215 total), including eight recorder privacy/provenance guards. Type checking, production build and npm audit also passed. The separate production application's authenticated budget ledger remained at zero calls, zero input/output tokens and $0 estimated usage, with the $20 total / $0.25 per-run admission limits unchanged. This ledger is application-side accounting, not confirmation of provider balance. Local results do not establish that a later CI run passed.

## October 23 live credit-check recording

The later [live credit-check receipt](live-nebius-check.md) records a successful **model-only** JSON response from `nvidia/Nemotron-3_5-Lightning`. The first deliberately tiny output cap truncated one response; the final 512-token-cap request returned `{"status":"ready"}`. Both calls together used 74 input and 388 output tokens, with **$0.000099 app-estimated** cost. This is not a full PR review, GPU ranking, or provider invoice.

The local, Git-ignored `artifacts/demo/live-nebius-credit-check-retry-2026-10-23.webm` is a 17.76-second, 1280×720 VP8 silent recording with English captions. SHA-256: `f3a7a67ac27d28ac530485f433cc73c4462545546bfc613cdfe903018c06eb4c`. A sampled frame was visually inspected and shows the truthful live-model caption and cost estimate. The recording does not display credentials, but this was **sampled review, not a frame-by-frame privacy audit**. Do not upload it as the final submission video without owner review and approval.

## October 25 workflow screen recording

The owner requested a new screen recording of the process. Discovery and a complete no-video rehearsal passed before capture. The local, Git-ignored `artifacts/demo/aegispr-workflow-2026-10-25.webm` is 96.80 seconds, VP8 at 1280×720 and 25 fps, 6,974,541 bytes. SHA-256: `489cfccb428dae64b5dcd4a42bfe0ac6b8af4f35fe8e5b6a5d8a2f01ae3be046`. It is silent with English captions, private and not uploaded.

The recording shows the public site, an interactive browser-only coupon boundary check and prewritten clamp, then newly executed Python and Node controlled-fixture reports (`0aa65cd5-2e5e-4223-8b7e-87ce29de8b4c` and `2523e882-9ee3-4204-a12e-3e5da120cf0f`). Those reports contain actual isolated Docker commands, commits, logs and manual-repair checks, but **zero model calls** and no live GitHub PR review. The separate Dell production `/health` scene showed `status: ok` and `gpu_accelerator: cuda` during recording; it is not proof of Nebius inference or Nebius GPU hosting. The closing caption points to the separate saved-plan controlled-PR result as a stable behavior change with inconclusive intent. The top-right draft badge remains visible throughout.

Sampled frames at roughly 0, 12, 24, 36, 39, 48, 60, 72, 75 and 84 seconds were visually inspected for those labels and visible secrets; no access code or provider key was seen in those samples. This is **sampled inspection, not an exhaustive frame-by-frame privacy audit**. The recorder's request allowlist permits only fixed GET evidence surfaces, rejects model/budget/write endpoints and WebSockets, and injects the local app access code privately into session storage rather than typing or captioning it. Its nine guard tests passed. The user still owns the final public video and should review this draft before using any footage.

## October 25 real-time controlled-PR recording

The owner requested footage of a real-time PR verification. A private, Git-ignored
draft is at `artifacts/demo/aegispr-live-and-earlier-evidence-2026-10-25.webm`.
It is **88.72 seconds**, VP8 at **1280×720 and 25 fps**, 10,926,621 bytes;
SHA-256 `f62447bc9ce1eb67b3b0f99d5af36fc0830110f489af74af995537eaabc5d6db`.
It has English on-screen captions and no narration. It is not uploaded or the
owner's final submission video.

The first 55.68 seconds show a **new live full-app run**
`e7a3772e-7317-483e-bcea-f7377d0f7653` on the deliberately seeded public
PR. The operator discovered and rehearsed the browser selectors against an
existing result without submitting or spending credits, then made exactly one
UI submission while recording. The app ingested the PR, ranked context on the
Dell CUDA worker, made **one new Nemotron-3_5-Lightning call**, and executed a
generated test on base and head in Docker. It reported `INCONCLUSIVE`, with
one `INCONCLUSIVE` finding, no intent votes and no confirmation reruns. New
usage was 1,024 input and 551 output tokens, **$0.000194 app-estimated**. The
persistent ledger moved from 15 calls / $0.005130 to 16 calls / $0.005324
app-estimated. These are not provider billing or remaining-credit statements.

The new generated Python test did **not** call the changed function. Instead,
it printed hard-coded old/new formulas, producing identical stdout on the
two branches. This run did **not** prove a behavior change or regression.
The footage must not be clipped to imply that it did. The second scene is
explicitly labeled as an **earlier, separate controlled-PR run**
`6d6a108f-3b98-482c-9aeb-cc6494180c55`. That run had an actual stable
branch-output change and three advisory model intent votes, but its overall
status was also `INCONCLUSIVE` pending human assessment. The second scene is
read-only and made no new provider call. This is not a real-world accuracy
benchmark, Nebius-hosted GPU run or confirmed autonomous regression verdict.

`ffprobe` checked the composite's dimensions, frame rate, duration and size.
Frames sampled across the opening, live timeline, result, earlier finding,
branch execution and ending were visually inspected. The private access code
and provider key were not visible in those samples. This is **sampled review,
not exhaustive frame-by-frame security inspection**. The raw live and earlier
clips, local recorder and JSON receipt remain under ignored `artifacts/demo/`.

## Before final submission

For the final submission, show the dated live Nemotron call and controlled-PR results with their exact limits. Do not present the fixture walkthrough as fresh inference, or the newer inconclusive live take as a confirmed regression. Review every frame for secrets, misleading labels and unsupported claims; verify duration, English content, public viewing and current organizer video requirements. The owner has said they will prepare and upload the final video themselves. A local WebM or GitHub Pages link is not automatically a valid replacement for that field.
