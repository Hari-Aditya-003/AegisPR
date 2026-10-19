# Draft capability recording

This is a **capability preview, not the final end-to-end hackathon submission video**. Successful live Nemotron inference and actual PR acceptance remain unverified until usable credits are confirmed. Do not replace those missing observations with fixture footage or invent model feedback.

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

## Before final submission

After usable credits are confirmed, complete and measure the actual NVIDIA/Nebius PR workflow within the application's spending limits. Replace the relevant draft scenes with real generated-test/PR/repair evidence and truthful model feedback. Review every frame for secrets, misleading labels and unsupported claims; verify duration, English content, public viewing and current organizer video requirements. Upload only with the account owner's approval and use the resulting supported video-platform URL in the submission form. A local WebM or GitHub Pages link is not automatically a valid replacement for that field.
