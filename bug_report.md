# Bug Report: Retry-Induced Duplicate Payment

## Summary

`POST /payment` can be called multiple times for the same logical `payment_id`, and the
service creates a new transaction record for each call. There is no idempotency enforcement.

## Reproduction

```bash
python reproduce_bug.py
```

Expected output:
```
Expected logical payments : 1
Actual transactions       : 2
BUG REPRODUCED [OK]
```

## Root Symptom

A single logical payment (identified by `payment_id`) results in **multiple transaction
records** in the in-memory store (`service/db.py`).

## Two Hypotheses

### H1 — Frontend/Client Retry
The duplicate is caused by frontend or client-side retry behavior.
A client that retries a failed POST /payment request with the same `payment_id` causes the
service to create a second transaction.

*Observable if true*: Disabling client retry (sending the payment request exactly once)
eliminates the duplicate.

*Observable if false*: With client retry disabled, duplicates still occur due to another source.

### H2 — Backend/Service Retry
The duplicate is caused by the service's own retry loop executing multiple backend
charge calls for a single incoming request, with no idempotency key check preventing
duplicate charges.

*Observable if true*: A single client request (no client retry) with `SERVICE_RETRY_ON_TIMEOUT > 0`
produces multiple transactions.

*Observable if false*: With the service retry loop disabled (SERVICE_RETRY_ON_TIMEOUT=0),
a single client request always produces exactly one transaction.

## Affected Code

- `service/main_buggy.py` — `process_payment()` function
  - Iterates through `range(attempts)` without breaking after the first success
  - Does not check `payment_id` against existing transactions before creating a new one
  - No idempotency key is passed to or checked at the backend layer

## Impact

A customer submitting one payment may be charged multiple times for the same transaction.

## Experiment Plan

1. **Experiment A** (`disable_frontend_retry`): Disable client retry (MAX_RETRIES=0), inject
   backend behavior that triggers service retry. If duplicate persists → H1 falsified.

2. **Experiment B** (`inject_backend_timeout`): Keep default service behavior
   (SERVICE_RETRY_ON_TIMEOUT=1). Single client request. If duplicate appears → H2 supported.
