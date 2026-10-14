import type { VerificationRun } from "@/lib/types";


export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function createVerification(pullRequestUrl: string): Promise<{ id: string }> {
  const response = await fetch(`${apiUrl}/api/verifications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pull_request_url: pullRequestUrl }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Verification could not start" }));
    throw new Error(payload.detail ?? "Verification could not start");
  }
  return response.json();
}

export async function requestRepair(runId: string, findingId: string): Promise<VerificationRun> {
  const response = await fetch(`${apiUrl}/api/verifications/${runId}/repair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_id: findingId }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Repair verification could not start" }));
    throw new Error(payload.detail ?? "Repair verification could not start");
  }
  return response.json();
}

