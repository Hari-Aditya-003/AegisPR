interface ProofCardProps {
  commit: string;
  status: string;
  existingTests: { passed: number; total: number };
  generatedTests: { passed: number; total: number };
  regressions: number;
  buildStatus: string;
}

const statusLabels: Record<string, string> = {
  VERIFIED_WITHIN_SCOPE: "VERIFIED WITHIN TESTED SCOPE",
  REGRESSION_FOUND: "REGRESSION DETECTED",
  FIX_VERIFIED: "FIX VERIFIED",
  ANALYSIS_ONLY: "ANALYSIS ONLY",
  INCONCLUSIVE: "INCONCLUSIVE",
  ENVIRONMENT_ERROR: "ENVIRONMENT ERROR",
  PRE_EXISTING_FAILURE: "PRE-EXISTING FAILURE",
  QUEUED: "QUEUED",
  RUNNING: "VERIFICATION IN PROGRESS",
};

export function ProofCard({
  commit,
  status,
  existingTests,
  generatedTests,
  regressions,
  buildStatus,
}: ProofCardProps) {
  const tone = status === "REGRESSION_FOUND" ? "danger" : status === "VERIFIED_WITHIN_SCOPE" ? "verified" : "neutral";
  return (
    <article className={`proof-card ${tone}`} aria-label="Verification proof card">
      <div className="proof-topline">
        <span className="proof-mark">AEGIS</span>
        <span className="status-dot" aria-hidden="true" />
        <span>{statusLabels[status] ?? status.replaceAll("_", " ")}</span>
      </div>
      <dl className="proof-grid">
        <div><dt>Commit</dt><dd>{commit.slice(0, 8) || "Pending"}</dd></div>
        <div><dt>Existing tests</dt><dd>{existingTests.passed}/{existingTests.total}</dd></div>
        <div><dt>Generated tests</dt><dd>{generatedTests.passed}/{generatedTests.total}</dd></div>
        <div><dt>Build</dt><dd>{buildStatus}</dd></div>
        <div><dt>Regressions</dt><dd>{regressions}</dd></div>
      </dl>
      <p className="scope-note">Evidence is limited to the analyses and tests executed in this run.</p>
    </article>
  );
}

