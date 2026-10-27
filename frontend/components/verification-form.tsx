"use client";

import { FormEvent, useEffect, useState } from "react";


interface VerificationFormProps {
  onSubmit: (pullRequestUrl: string) => Promise<void> | void;
}

const pullRequestPattern = /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/[1-9][0-9]*\/?$/;

export function VerificationForm({ onSubmit }: VerificationFormProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const handedOffUrl = new URLSearchParams(window.location.search).get("pr");
    if (handedOffUrl && handedOffUrl.length <= 300 && pullRequestPattern.test(handedOffUrl)) {
      setValue(handedOffUrl.replace(/\/$/, ""));
    }
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = value.trim();
    if (!pullRequestPattern.test(normalized)) {
      setError("Enter a public GitHub pull request URL.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit(normalized);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Verification could not start.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="verify-panel" aria-labelledby="verify-title">
      <p className="eyebrow">Autonomous evidence-backed PR verification</p>
      <div className="hero-intro"><span className="intro-line" />The next checkpoint for your code.</div>
      <h1 id="verify-title">Don&apos;t trust a PR. <span>Prove it.</span></h1>
      <p className="hero-copy">
        AegisPR turns Nemotron&apos;s risk hypotheses into executable tests, runs them against both commits,
        and reports what the evidence actually proves.
      </p>
      <form onSubmit={handleSubmit} noValidate>
        <label htmlFor="pr-url">GitHub pull request</label>
        <div className="url-row">
          <input
            id="pr-url"
            name="pull_request_url"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="https://github.com/owner/repository/pull/42"
            autoComplete="url"
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "pr-error" : "pr-hint"}
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Starting…" : "Verify PR"}
          </button>
        </div>
        <p className="field-hint" id="pr-hint">Public repositories are supported. Opening this page never starts a review; pressing Verify PR may use Nebius credits. The Agent timeline appears on the report page after a run starts.</p>
        {error && <p className="field-error" id="pr-error" role="alert">{error}</p>}
      </form>
      <div className="hero-assurances"><span><i aria-hidden="true">✓</i> Exact commit comparison</span><span><i aria-hidden="true">✓</i> Isolated execution</span><span><i aria-hidden="true">✓</i> Evidence you can inspect</span></div>
    </section>
  );
}

