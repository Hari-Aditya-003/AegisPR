import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../dist/landing.css', import.meta.url), 'utf8');

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
