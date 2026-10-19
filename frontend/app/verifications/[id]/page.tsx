"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ProofCard } from "@/components/proof-card";
import { VerificationTimeline } from "@/components/verification-timeline";
import { accessChangedEvent, getVerification, requestRepair } from "@/lib/api";
import type { VerificationRun } from "@/lib/types";


const terminalStatuses = new Set([
  "VERIFIED_WITHIN_SCOPE", "REGRESSION_FOUND", "FIX_VERIFIED", "PRE_EXISTING_FAILURE",
  "INCONCLUSIVE", "ENVIRONMENT_ERROR", "ANALYSIS_ONLY",
]);

export default function VerificationPage() {
  const params = useParams<{ id: string }>();
  const [run, setRun] = useState<VerificationRun | null>(null);
  const [error, setError] = useState("");
  const [repairError, setRepairError] = useState("");
  const [repairing, setRepairing] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const retry = () => setReloadKey(value => value + 1);
    window.addEventListener(accessChangedEvent, retry);
    return () => window.removeEventListener(accessChangedEvent, retry);
  }, []);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setError("");
    async function load() {
      try {
        const nextRun = await getVerification(params.id);
        if (!active) return;
        setRun(nextRun);
        if (!terminalStatuses.has(nextRun.status)) timer = setTimeout(load, 1500);
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : "Could not load verification.");
      }
    }
    load();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [params.id, reloadKey]);

  async function startRepair(findingId: string) {
    if (run?.evidence_mode === "controlled_fixture" || run?.model_used === "controlled-fixture-no-model") return;
    setRepairing(true);
    setRepairError("");
    try {
      const queued = await requestRepair(params.id, findingId);
      setRun(queued);
      setReloadKey((value) => value + 1);
    } catch (repairFailure) {
      setRepairError(
        repairFailure instanceof Error ? repairFailure.message : "Repair verification could not start.",
      );
    } finally {
      setRepairing(false);
    }
  }

  const retryButton = <button className="repair-button" type="button" onClick={() => setReloadKey(value => value + 1)}>Retry loading evidence</button>;
  if (error && !run) return <section className="report-shell"><div className="report-error" role="alert"><h1>Verification unavailable</h1><p>{error}</p>{retryButton}<a className="text-link" href="/">Start another verification</a></div></section>;
  if (!run) return <section className="report-shell"><div className="report-loading" role="status"><span aria-hidden="true" />Loading evidence workspace…</div></section>;

  const executed = run.findings.length;
  const passed = run.findings.filter((finding) => finding.head_execution.status === "PASSED").length;
  const isFixture = run.evidence_mode === "controlled_fixture" || run.model_used === "controlled-fixture-no-model";
  return (
    <section className="report-shell">
      {error && <div className="error-card" role="alert"><h2>Live updates paused</h2><p>{error}</p>{retryButton}</div>}
      {isFixture && <aside className="fixture-provenance" role="note" aria-labelledby="fixture-provenance-title">
        <p className="eyebrow">Evidence provenance</p>
        <h2 id="fixture-provenance-title">Controlled fixture — not a live pull request review</h2>
        <p>This run uses a fixed coupon fixture with prewritten tests and hypothesis. No model call or live GitHub pull request analysis was performed. Any repair shown was manually authored.</p>
        <p>Docker execution results below are recorded checks of this fixture, not model-generated evidence.</p>
      </aside>}
      <div className="report-heading">
        <div><p className="eyebrow">{isFixture ? "Controlled fixture run" : "Verification run"} · {run.id.slice(0, 8)}</p><h1>{run.summary?.title ?? (isFixture ? "Executing controlled coupon fixture" : "Analyzing pull request")}</h1><p>{isFixture ? "Local coupon fixture · fixed base and head revisions" : run.summary ? `${run.summary.owner}/${run.summary.repository} · PR #${run.summary.number}` : run.pull_request_url}</p></div>
        <span className={`run-status status-${run.status.toLowerCase()}`}>{run.status.replaceAll("_", " ")}</span>
      </div>
      <div className="report-grid">
        <div className="report-main">
          <section className="report-card"><h2>{isFixture ? "Fixture execution timeline" : "Agent timeline"}</h2><VerificationTimeline stages={run.stages} /></section>
          <section className="report-card">
            <div className="card-heading"><h2>Findings</h2><span>{run.findings.length} recorded</span></div>
            {run.findings.length === 0 ? <p className="empty-state">Findings appear after differential execution.</p> : run.findings.map((finding) => (
              <article className="finding" key={finding.id}>
                <div><span className={`severity ${finding.severity}`}>{finding.severity}</span><strong>{finding.classification.replaceAll("_", " ")}</strong></div>
                <h3>{finding.summary}</h3>
                <p>{finding.affected_file ?? "Affected location pending"}</p>
                <div className="comparison"><span>BASE <b>{finding.base_execution.status}</b></span><span>{isFixture ? "HEAD" : "PR"} <b>{finding.head_execution.status}</b></span></div>
                <details className="execution-details"><summary>Inspect branch execution evidence</summary><div className="execution-grid">{[finding.base_execution, finding.head_execution].map(execution => <section key={execution.branch}>
                  <h4>{execution.branch === "base" ? "Base revision" : isFixture ? "Fixture head revision" : "Pull request revision"}</h4>
                  <dl><div><dt>Commit</dt><dd>{execution.commit || "Not recorded"}</dd></div><div><dt>Duration</dt><dd>{execution.duration_ms} ms</dd></div><div><dt>Exit code</dt><dd>{execution.exit_code ?? "Not recorded"}</dd></div></dl>
                  <p>Executed command</p><pre>{execution.environment?.command ?? "Not recorded"}</pre><p>Standard output</p><pre>{execution.stdout || "No standard output captured."}</pre><p>Standard error</p><pre>{execution.stderr || "No standard error captured."}</pre>
                </section>)}</div></details>
                {finding.root_cause && <div className="root-cause"><span>{isFixture ? "Prewritten fixture explanation" : "Likely root cause"}</span><p>{finding.root_cause}</p></div>}
                {finding.explanation_error && <p className="scope-note">{finding.explanation_error}</p>}
                {!isFixture && finding.classification === "REGRESSION" && run.status === "REGRESSION_FOUND" && run.repair?.status !== "RUNNING" && (
                  <button className="repair-button" type="button" disabled={repairing} onClick={() => startRepair(finding.id)}>
                    {repairing ? "Generating repair…" : "Generate and verify repair"}
                  </button>
                )}
              </article>
            ))}
          </section>
          {run.repair && (
            <section className="report-card repair-card">
              <div className="card-heading"><h2>{isFixture ? "Manual repair evidence" : "Repair evidence"}</h2><span>{run.repair.status}</span></div>
              {run.repair.summary && <p className="repair-summary">{run.repair.summary}</p>}
              {run.repair.checks.length > 0 && <div className="repair-checks">{run.repair.checks.map((check) => (
                <div key={check.name}><span>{check.name.replaceAll("_", " ")}</span><strong className={`check-${check.execution.status.toLowerCase()}`}>{check.execution.status}</strong></div>
              ))}</div>}
              {run.repair.checks.map((check) => <details className="execution-details" key={check.name}>
                <summary>Inspect repair check: {check.name.replaceAll("_", " ")}</summary>
                <dl><div><dt>Commit</dt><dd>{check.execution.commit || "Not recorded"}</dd></div><div><dt>Duration</dt><dd>{check.execution.duration_ms} ms</dd></div><div><dt>Exit code</dt><dd>{check.execution.exit_code ?? "Not recorded"}</dd></div></dl>
                <p>Executed command</p><pre>{check.execution.environment?.command ?? check.command ?? "Not recorded"}</pre>
                <p>Standard output</p><pre>{check.execution.stdout || "No standard output captured."}</pre>
                <p>Standard error</p><pre>{check.execution.stderr || "No standard error captured."}</pre>
              </details>)}
              {run.repair.patch && <details><summary>View isolated patch</summary><pre>{run.repair.patch}</pre></details>}
              {run.repair.error && <p className="repair-error" role="alert">{run.repair.error}</p>}
            </section>
          )}
          {repairError && <p className="repair-error" role="alert">{repairError}</p>}
          {!!run.generated_tests?.length && <section className="report-card generated-test-card"><h2>{isFixture ? "Fixed fixture test artifacts" : "Generated test artifacts"}</h2>{run.generated_tests.map(test => <details key={test.id}><summary>{test.file_path}</summary><p>Command: <code>{test.test_command ?? "Not recorded"}</code></p><pre>{test.test_code}</pre></details>)}</section>}
          <section className="report-card"><h2>{isFixture ? "Prewritten fixture hypothesis" : "Risk hypotheses"}</h2>{!run.hypotheses.length && <p className="empty-state">No risk hypotheses recorded in this run.</p>}{run.hypotheses.map((hypothesis) => <article className="hypothesis" key={hypothesis.id}><span>{hypothesis.id}</span><div><strong>{hypothesis.description}</strong><p>{hypothesis.test_strategy}</p></div></article>)}</section>
        </div>
        <aside className="report-side">
          <ProofCard
            commit={run.summary?.head_commit ?? ""}
            status={run.status}
            existingTests={null}
            existingSuiteStatus={run.repair?.checks.find(check => check.name === "existing_tests")?.execution.status}
            generatedTests={{ passed, total: executed }}
            testLabel={isFixture ? "Fixed fixture tests" : undefined}
            regressions={run.metrics.regressions_found}
            buildStatus={run.repair?.checks.find(check => check.name === "build")?.execution.status ?? "Not recorded"}
          />
          <section className="metric-card"><h2>Run metrics</h2><dl><div><dt>{isFixture ? "Fixture files" : "Files analyzed"}</dt><dd>{run.metrics.files_analyzed}</dd></div><div><dt>{isFixture ? "Prewritten hypotheses" : "Hypotheses"}</dt><dd>{run.metrics.hypotheses_generated}</dd></div><div><dt>{isFixture ? "Fixed test artifacts" : "Generated tests"}</dt><dd>{run.metrics.generated_tests}</dd></div><div><dt>Context compute</dt><dd>{run.metrics.context_accelerator.toUpperCase()}</dd></div>
            {isFixture && <div><dt>Model inference</dt><dd>Not used (controlled fixture)</dd></div>}
            {run.metrics.input_tokens !== undefined && <div><dt>Tokens in / out</dt><dd>{run.metrics.input_tokens} / {run.metrics.output_tokens ?? 0}</dd></div>}
            {run.metrics.cache_hits !== undefined && <div><dt>Cached responses</dt><dd>{run.metrics.cache_hits}</dd></div>}
            {run.metrics.accounted_cost_usd !== undefined && <div><dt>App cost estimate</dt><dd>${run.metrics.accounted_cost_usd.toFixed(4)}</dd></div>}
          </dl>{run.metrics.accounted_cost_usd !== undefined && <p className="scope-note">Conservative app accounting, not the provider balance. Unknown usage may retain its maximum reservation.</p>}</section>
          {run.error && <section className="error-card"><h2>Environment error</h2><p>{run.error}</p></section>}
        </aside>
      </div>
      <p className="disclaimer">{run.disclaimer}</p>
    </section>
  );
}
