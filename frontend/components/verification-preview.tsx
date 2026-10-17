"use client";

import Image from "next/image";
import { useState } from "react";

const examples = [
  { label: "Regression", result: "REGRESSION FOUND", head: "FAIL", value: "-10.00", detail: "The same test passes before the change and fails after it.", code: "return total - discount", tone: "danger" },
  { label: "Safe change", result: "VERIFIED WITHIN SCOPE", head: "PASS", value: "0.00", detail: "Both revisions pass this boundary check. Other behavior is outside its scope.", code: 'return max(total - discount, Decimal("0"))', tone: "success" },
  { label: "Verified repair", result: "FIX VERIFIED", head: "PASS", value: "0.00", detail: "Illustrative repaired result after the selected checks pass.", code: 'return max(total - discount, Decimal("0"))', tone: "success" },
];

export function VerificationPreview() {
  const [selected, setSelected] = useState(0);
  const [showCode, setShowCode] = useState(false);
  const example = examples[selected];

  return (
    <aside className="preview-studio" aria-label="Interactive verification example">
      <div className="logo-orbit">
        <span className="orbit orbit-one" aria-hidden="true" />
        <span className="orbit orbit-two" aria-hidden="true" />
        <Image src="/brand/aegispr-logo.jpg" alt="AegisPR shield and branching circuit logo" width={1400} height={768} preload unoptimized className="hero-logo" />
        <span className="orbit-label">CODE. CHALLENGE. CONFIRM.</span>
      </div>
      <div className="terminal-card interactive-terminal">
        <div className="terminal-bar"><span /><span /><span /><b>coupon_boundary.py</b><span className="preview-badge">PLAYGROUND</span></div>
        <div className="preview-options" role="group" aria-label="Choose an example">
          {examples.map((item, index) => <button key={item.label} type="button" aria-pressed={selected === index} onClick={() => setSelected(index)}>{item.label}</button>)}
        </div>
        <div className="terminal-body">
          <div className="preview-toolbar"><p><em>BOUNDARY CHECK</em>discount &gt; cart total</p><button type="button" onClick={() => setShowCode(!showCode)}>{showCode ? "Show evidence" : "Show test code"}</button></div>
          {showCode ? <pre className="preview-code"><span># generated boundary test · example</span>{'\ndef test_discount_boundary():\n    assert apply_coupon(10, 20) == 0\n\n# implementation\n'}{example.code}</pre> : <div className="preview-result" key={example.label} aria-live="polite">
            <div className="branch-result"><span>BASE</span><strong className="pass">PASS</strong><code>total = 0.00</code></div>
            <div className="branch-result"><span>{selected === 2 ? "FIX" : "PR"}</span><strong className={example.head === "FAIL" ? "fail" : "pass"}>{example.head}</strong><code>total = {example.value}</code></div>
            <div className={`verdict preview-${example.tone}`}><span>{example.result}</span><small>{example.detail}</small></div>
          </div>}
          <p className="preview-disclaimer">Interactive example · not a live review</p>
        </div>
      </div>
    </aside>
  );
}
