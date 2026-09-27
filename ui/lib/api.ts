/**
 * API wrappers for the FastAPI backend.
 * All calls use NEXT_PUBLIC_API_URL — never hardcodes localhost.
 */

import type { PaymentResponse, TransactionsResponse } from "./types";

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "";
}

export async function postPayment(
  payment_id: string,
  amount: number,
  attempt?: number
): Promise<PaymentResponse> {
  const query = attempt ? `?attempt=${attempt}` : "";
  const res = await fetch(`${apiBase()}/payment${query}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_id, amount }),
  });
  if (!res.ok) {
    throw new Error(`POST /payment failed: ${res.status}`);
  }
  const payload = (await res.json()) as Record<string, unknown>;
  const transactionIds = Array.isArray(payload.transaction_ids)
    ? payload.transaction_ids.filter((value): value is string => typeof value === "string")
    : typeof payload.transaction_id === "string"
      ? [payload.transaction_id]
      : [];

  return {
    ...payload,
    payment_id: String(payload.payment_id ?? payment_id),
    transaction_ids: transactionIds,
    status: String(payload.status ?? "unknown"),
  } as PaymentResponse;
}

export async function getTransactions(): Promise<TransactionsResponse> {
  const res = await fetch(`${apiBase()}/transactions`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`GET /transactions failed: ${res.status}`);
  }
  return res.json() as Promise<TransactionsResponse>;
}

export async function resetStore(): Promise<void> {
  const adminResponse = await fetch(`${apiBase()}/admin/reset`, { method: "POST" });
  if (adminResponse.ok) return;

  const legacyResponse = await fetch(`${apiBase()}/reset`, { method: "POST" });
  if (!legacyResponse.ok) {
    throw new Error(`Reset failed: /admin/reset=${adminResponse.status}, /reset=${legacyResponse.status}`);
  }
}

export const adminReset = resetStore;

export function isApiConfigured(): boolean {
  const base = apiBase();
  return base.length > 0;
}
