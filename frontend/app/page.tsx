"use client";

import { useRouter } from "next/navigation";

import { VerificationForm } from "@/components/verification-form";
import { createVerification } from "@/lib/api";


const features = [
  ["Change intelligence", "Maps the pull request, changed functions, tests, and dependency neighborhood before reasoning."],
  ["Adversarial generation", "Nemotron converts explicit risk hypotheses into targeted tests designed to challenge the change."],
  ["Differential execution", "Runs the same generated test on base and head commits to isolate regressions introduced by the PR."],
  ["Auditable evidence", "Preserves commits, commands, logs, exit codes, durations, generated tests, and bounded conclusions."],
  ["Repair verification", "Keeps fixes minimal and accepts them only after existing and generated checks pass again."],
  ["GPU context ranking", "Uses the Dell RTX GPU to prioritize relevant repository context before Nemotron planning."],
];

export default function HomePage() {
  const router = useRouter();

  async function startVerification(pullRequestUrl: string) {
    const run = await createVerification(pullRequestUrl);
    router.push(`/verifications/${run.id}`);
  }

  return (
    <>
      <section className="hero">
        <div className="hero-glow" aria-hidden="true" />
        <VerificationForm onSubmit={startVerification} />
        <aside className="terminal-card" aria-label="Example differential verification result">
          <div className="terminal-bar"><span /><span /><span /><b>AEG-08 · differential run</b></div>
          <div className="terminal-body">
            <p><em>HYPOTHESIS</em> Discount may exceed cart value</p>
            <div className="branch-result"><span>BASE</span><strong className="pass">PASS</strong><code>total = 0</code></div>
            <div className="branch-result"><span>PR</span><strong className="fail">FAIL</strong><code>total = -50</code></div>
            <div className="verdict"><span>REGRESSION VERIFIED</span><small>Failure isolated to pull request</small></div>
          </div>
        </aside>
      </section>

      <section className="trust-strip" aria-label="Core technologies">
        <span>NVIDIA Nemotron</span><i>+</i><span>Nebius Token Factory</span><i>+</i><span>CUDA GPU worker</span><i>+</i><span>Isolated Docker sandboxes</span>
      </section>

      <section className="section" id="how-it-works">
        <div className="section-heading"><p className="eyebrow">Differential verification</p><h2>Reasoning becomes an experiment.</h2></div>
        <div className="process-grid">
          {["Inspect", "Hypothesize", "Generate", "Execute", "Compare", "Prove"].map((step, index) => (
            <article key={step}><span>{String(index + 1).padStart(2, "0")}</span><h3>{step}</h3><p>{[
              "Read the PR, repository map, diff, tests, and relevant dependencies.",
              "Name concrete failure modes before writing tests.",
              "Create framework-native adversarial tests for those risks.",
              "Run identical tests in isolated base and head environments.",
              "Classify the result matrix without model guesswork.",
              "Attach executable evidence to every conclusion.",
            ][index]}</p></article>
          ))}
        </div>
      </section>

      <section className="section muted" id="features">
        <div className="section-heading"><p className="eyebrow">Product capabilities</p><h2>Everything a reviewer needs to verify the claim.</h2></div>
        <div className="feature-grid">
          {features.map(([title, description]) => <article key={title}><span className="feature-icon">◆</span><h3>{title}</h3><p>{description}</p></article>)}
        </div>
      </section>

      <section className="section architecture" id="architecture">
        <div className="section-heading"><p className="eyebrow">Architecture</p><h2>Two compute planes. One evidence trail.</h2></div>
        <div className="architecture-flow" role="img" aria-label="GitHub flows into AegisPR orchestration, Nebius Nemotron reasoning, Dell CUDA ranking, Docker execution, and an evidence report">
          <div><small>INPUT</small><strong>GitHub PR</strong></div><b>→</b>
          <div><small>CONTROL</small><strong>Aegis Orchestrator</strong></div><b>→</b>
          <div className="split"><span><small>REASON</small><strong>Nebius · Nemotron</strong></span><span><small>RANK</small><strong>Dell RTX · CUDA</strong></span></div><b>→</b>
          <div><small>EXECUTE</small><strong>Isolated sandboxes</strong></div><b>→</b>
          <div><small>OUTPUT</small><strong>Evidence report</strong></div>
        </div>
      </section>

      <section className="section use-section">
        <div><p className="eyebrow">How to use AegisPR</p><h2>Paste one URL. Inspect every claim.</h2></div>
        <ol>
          <li><span>1</span><p><strong>Open a public GitHub pull request.</strong> Copy its canonical URL.</p></li>
          <li><span>2</span><p><strong>Start verification.</strong> Watch repository, impact, model, and sandbox stages live.</p></li>
          <li><span>3</span><p><strong>Review the proof.</strong> Inspect branch results, generated test code, logs, and root cause.</p></li>
          <li><span>4</span><p><strong>Repair with evidence.</strong> Generate a minimal patch and verify it against all selected checks.</p></li>
        </ol>
      </section>
    </>
  );
}

