import type { VerificationRun } from "@/lib/types";


export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const accessKey = "aegispr.deployment-access";
export const accessChangedEvent = "aegispr:access-changed";

export function saveAccessCode(code: string) {
  if (code.trim()) sessionStorage.setItem(accessKey, code.trim());
  else sessionStorage.removeItem(accessKey);
  window.dispatchEvent(new Event(accessChangedEvent));
}

function requestHeaders(json = false): Record<string, string> {
  const headers: Record<string, string> = json ? { "Content-Type": "application/json" } : {};
  const code = typeof window === "undefined" ? null : sessionStorage.getItem(accessKey);
  if (code) headers.Authorization = `Bearer ${code}`;
  return headers;
}

async function responseError(response: Response, fallback: string): Promise<Error> {
  if (response.status === 401) return new Error("Open Private deployment access above and save the deployment access code, then retry.");
  const payload = await response.json().catch(() => ({}));
  return new Error(typeof payload?.detail === "string" ? payload.detail : fallback);
}

export async function getVerification(runId: string): Promise<VerificationRun> {
  const response = await fetch(`${apiUrl}/api/verifications/${encodeURIComponent(runId)}`, {
    cache: "no-store", headers: requestHeaders(),
  });
  if (!response.ok) throw await responseError(response, response.status === 404 ? "Verification run was not found." : "Evidence could not be loaded. Please retry.");
  return response.json();
}

export async function createVerification(pullRequestUrl: string): Promise<{ id: string }> {
  const response = await fetch(`${apiUrl}/api/verifications`, {
    method: "POST",
    headers: requestHeaders(true),
    body: JSON.stringify({ pull_request_url: pullRequestUrl }),
  });
  if (!response.ok) {
    throw await responseError(response, "Verification could not start");
  }
  return response.json();
}

export async function requestRepair(runId: string, findingId: string): Promise<VerificationRun> {
  const response = await fetch(`${apiUrl}/api/verifications/${encodeURIComponent(runId)}/repair`, {
    method: "POST",
    headers: requestHeaders(true),
    body: JSON.stringify({ finding_id: findingId }),
  });
  if (!response.ok) {
    throw await responseError(response, "Repair verification could not start");
  }
  return response.json();
}

