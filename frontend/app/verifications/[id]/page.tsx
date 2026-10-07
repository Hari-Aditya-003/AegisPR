"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ProofCard } from "@/components/proof-card";
import { VerificationTimeline } from "@/components/verification-timeline";
import { apiUrl } from "@/lib/api";
import type { VerificationRun } from "@/lib/types";


const terminalStatuses = new Set([
  "VERIFIED_WITHIN_SCOPE", "REGRESSION_FOUND", "FIX_VERIFIED", "PRE_EXISTING_FAILURE",
  "INCONCLUSIVE", "ENVIRONMENT_ERROR", "ANALYSIS_ONLY",
]);

export default function VerificationPage() {
  const params = useParams<{ id: string }>();
  const [run, setRun] = useState<VerificationRun | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const response = await fetch(`${apiUrl}/api/verifications/${params.id}`, { cache: "no-store" });
        if (!response.ok) throw new Error("Verification run was not found.");
        const nextRun: VerificationRun = await response.json();
        if (!active) return;
        setRun(nextRun);
        if (!terminalStatuses.has(nextRun.status)) timer = setTimeout(load, 1500);
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : "Could not load verification.");
      }
    }
    load();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [params.id]);

  if (error) return <section className="report-shell"><div className="report-error"><h1>Verification unavailable</h1><p>{error}</p></div></section>;
  if (!run) return <section className="report-shell"><div className="report-loading"><span />Loading evidence workspace…</div></section>;

  const executed = run.findings.length;
  const passed = run.findings.filter((finding) => finding.head_execution.status === "PASSED").length;
  return (
    <section className="report-shell">
      <div className="report-heading">
        <div><p className="eyebrow">Verification run · {run.id.slice(0, 8)}</p><h1>{run.summary?.title ?? "Analyzing pull request"}</h1><p>{run.summary ? `${run.summary.owner}/${run.summary.repository} · PR #${run.summary.number}` : run.pull_request_url}</p></div>
        <span className={`run-status status-${run.status.toLowerCase()}`}>{run.status.replaceAll("_", " ")}</span>
      </div>
      <div className="report-grid">
        <div className="report-main">
          <section className="report-card"><h2>Agent timeline</h2><VerificationTimeline stages={run.stages} /></section>
          <section className="report-card">
            <div className="card-heading"><h2>Findings</h2><span>{run.findings.length} recorded</span></div>
            {run.findings.length === 0 ? <p className="empty-state">Findings appear after differential execution.</p> : run.findings.map((finding) => (
              <article className="finding" key={finding.id}>
                <div><span className={`severity ${finding.severity}`}>{finding.severity}</span><strong>{finding.classification.replaceAll("_", " ")}</strong></div>
                <h3>{finding.summary}</h3>
                <p>{finding.affected_file ?? "Affected location pending"}</p>
                <div className="comparison"><span>BASE <b>{finding.base_execution.status}</b></span><span>PR <b>{finding.head_execution.status}</b></span></div>
                {finding.root_cause && <div className="root-cause"><span>Likely root cause</span><p>{finding.root_cause}</p></div>}
              </article>
            ))}
          </section>
          <section className="report-card"><h2>Risk hypotheses</h2>{run.hypotheses.map((hypothesis) => <article className="hypothesis" key={hypothesis.id}><span>{hypothesis.id}</span><div><strong>{hypothesis.description}</strong><p>{hypothesis.test_strategy}</p></div></article>)}</section>
        </div>
        <aside className="report-side">
          <ProofCard
            commit={run.summary?.head_commit ?? ""}
            status={run.status}
            existingTests={{ passed: 0, total: 0 }}
            generatedTests={{ passed, total: executed }}
            regressions={run.metrics.regressions_found}
            buildStatus={run.status === "RUNNING" ? "PENDING" : "RECORDED"}
          />
          <section className="metric-card"><h2>Run metrics</h2><dl><div><dt>Files analyzed</dt><dd>{run.metrics.files_analyzed}</dd></div><div><dt>Hypotheses</dt><dd>{run.metrics.hypotheses_generated}</dd></div><div><dt>Generated tests</dt><dd>{run.metrics.generated_tests}</dd></div><div><dt>Context compute</dt><dd>{run.metrics.context_accelerator.toUpperCase()}</dd></div></dl></section>
          {run.error && <section className="error-card"><h2>Environment error</h2><p>{run.error}</p></section>}
        </aside>
      </div>
      <p className="disclaimer">{run.disclaimer}</p>
    </section>
  );
}
