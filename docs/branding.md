# AegisPR visual identity

The owner-supplied `AegisPR.jpg` is used unchanged in the application and project
website. The canonical application asset is `frontend/public/brand/aegispr-logo.jpg`;
the static website carries the same image at `website/dist/aegispr-logo.jpg`.
Header crops are presentation-only CSS backgrounds of the supplied artwork.

## Palette

| Role | Color |
| --- | --- |
| Background | `#05090c` |
| Surface | `#0c171b` |
| Primary text | `#edf8f7` |
| Secondary text | `#8da4a7` |
| Cyan | `#09d4ee` |
| Emerald | `#00e5a4` |

The application and website share the near-black canvas, cyan-to-emerald accents,
bordered panels, and monospace evidence details. The original asset is also used
for browser icons.

## Interaction and motion

- The application preview lets visitors select regression, safe-change, and
  repaired examples and switch between evidence and test code.
- The example is explicitly labeled; it does not invoke the backend or claim
  real inference or completed review results.
- The website stage selector updates its explanation and code example together.
- Buttons expose selected state using `aria-pressed`, and work with the keyboard.
- Entry transitions, orbit details, logo glow, panel hover states, active-stage
  pulses, and architecture arrows use CSS animations without animation packages.
- `prefers-reduced-motion: reduce` disables decorative animation and transitions.
- Skip links provide keyboard access to the main content.

## Validation

Frontend unit tests cover every preview outcome and the code/evidence toggle.
Browser tests cover keyboard interaction, loading the logo, mobile layout, and
reduced motion, alongside the existing verification and repair workflows.
Manual automated browser checks found no horizontal overflow at application
widths 320, 390, 700, 768, 1024, and 1440 pixels, or website widths 320, 390, 768,
and 1440 pixels, and no JavaScript runtime errors.

Local screenshots are saved under `artifacts/brand-refresh/` (ignored by Git).
