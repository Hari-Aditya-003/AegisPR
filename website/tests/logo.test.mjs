import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../dist/landing.css', import.meta.url), 'utf8');

function declarationsFor(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const styles = {};
  for (const match of source.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'g'))) {
    for (const declaration of match[1].split(';')) {
      const separator = declaration.indexOf(':');
      if (separator > 0) styles[declaration.slice(0, separator).trim()] = declaration.slice(separator + 1).trim();
    }
  }
  return styles;
}

function assertCompleteShield(style) {
  const width = parseFloat(style.width);
  const height = parseFloat(style.height);
  const crop = style.background?.match(/aegispr-logo\.jpg['"]?\)\s+(?:center|50%)\s+(-?[\d.]+)(%|px)\s*\/\s*([\d.]+)px/);
  assert.ok(crop, 'the mark must use the supplied artwork with explicit crop geometry');
  const imageWidth = Number(crop[3]);
  const scale = imageWidth / 1408;
  const offsetX = (width - imageWidth) / 2;
  const offsetY = crop[2] === '%' ? (height - 768 * scale) * Number(crop[1]) / 100 : Number(crop[1]);
  assert.ok(offsetX + 532 * scale >= 0, 'left side of the shield is clipped');
  assert.ok(offsetX + 877 * scale <= width, 'right side of the shield is clipped');
  assert.ok(offsetY + 104 * scale >= 0, 'top of the shield is clipped');
  assert.ok(offsetY + 513 * scale <= height, 'bottom point of the shield is clipped');
}

// The supplied 1408 × 768 image contains the complete shield in this rectangle.
// Model CSS background placement to catch cropping at each responsive breakpoint.
for (const viewport of [1280, 800, 390, 320]) {
  test(`brand shield stays inside its viewport at ${viewport}px`, () => {
    const style = {};
    for (const line of css.split('\n')) {
      const breakpoint = line.match(/^@media\(max-width:(\d+)px\)/);
      if (line.startsWith('@media') && (!breakpoint || viewport > Number(breakpoint[1]))) continue;
      for (const match of line.matchAll(/(?:^|[}])(?:\.nav )?\.brand-mark\{([^}]+)\}/g)) {
        for (const declaration of match[1].split(';')) {
          const separator = declaration.indexOf(':');
          if (separator > 0) style[declaration.slice(0, separator)] = declaration.slice(separator + 1);
        }
      }
    }
    const width = parseFloat(style.width);
    const height = parseFloat(style.height);
    const shorthand = style.background.match(/\)\s+50%\s+(-?[\d.]+)(%|px)\s*\/\s*([\d.]+)px/);
    assert.ok(shorthand, 'expected explicit crop geometry');
    const imageWidth = parseFloat(style['background-size'] || shorthand[3]);
    const scale = imageWidth / 1408;
    const position = style['background-position']?.match(/(?:center|50%)\s+(-?[\d.]+)(%|px)/);
    const value = Number(position?.[1] ?? shorthand[1]);
    const unit = position?.[2] ?? shorthand[2];
    const offsetY = unit === '%' ? (height - 768 * scale) * value / 100 : value;
    const offsetX = (width - imageWidth) / 2;
    assert.ok(offsetX + 532 * scale >= 0, 'left edge clipped');
    assert.ok(offsetX + 877 * scale <= width, 'right edge clipped');
    assert.ok(offsetY + 104 * scale >= 0, 'top edge clipped');
    assert.ok(offsetY + 513 * scale <= height, 'bottom edge clipped');
  });
}

test('application and interactive demo headers show the complete supplied shield', () => {
  const appCss = readFileSync(new URL('../../frontend/app/globals.css', import.meta.url), 'utf8');
  const demoCss = readFileSync(new URL('../dist/brand.css', import.meta.url), 'utf8');
  assertCompleteShield(declarationsFor(appCss, '.brand-shield'));
  assertCompleteShield(declarationsFor(demoCss, '.brand .brand-mark'));
});

test('interactive demo uses the same shield and split wordmark as the public website', () => {
  const demoHtml = readFileSync(new URL('../dist/demo/index.html', import.meta.url), 'utf8');
  assert.match(demoHtml, /class="brand-mark" aria-hidden="true"/);
  assert.match(demoHtml, /Aegis<span class="brand-light">PR<\/span>/);
});

test('interactive demo wordmark text is not styled as another icon', () => {
  const demoCss = readFileSync(new URL('../dist/brand.css', import.meta.url), 'utf8');
  const style = declarationsFor(demoCss, '.brand .brand-light');
  assert.equal(style.display, 'inline');
  assert.equal(style.width, 'auto');
  assert.equal(style.height, 'auto');
  assert.equal(style.border, '0');
  assert.equal(style['font-family'], 'inherit');
});
