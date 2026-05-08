# Error handling

The lite endpoints return structured JSON errors so you can self-correct without re-listing every reference table. Two on-the-wire shapes — handle both.

## Two error shapes

**FR (Roadmarq) and Wiki (Codexum)** — flat:

```json
{
  "code": "BAD_REQUEST",
  "message": "status 'in pogress' not found. Valid options: To Do, In Progress, Done",
  "field": "status",
  "provided": "in pogress",
  "validOptions": ["To Do", "In Progress", "Done"]
}
```

**Project Management** — nested under `details`:

```json
{
  "errorCode": "VALIDATION_ERROR",
  "message": "status 'in pogress' not found. Valid options: To Do, In Progress, Done",
  "details": {
    "field": "status",
    "providedName": "in pogress",
    "validOptions": ["To Do", "In Progress", "Done"]
  }
}
```

The PM `errorCode` is a stable enum value, not the HTTP reason phrase. See the table below for the real values — there is no `BAD_REQUEST` / `NOT_FOUND` / `RATE_LIMITED` / `SERVER_ERROR` codes; PM uses domain-specific names.

Normalize them on the way in. A small helper:

```python
def normalize_error(payload, status):
    code = payload.get("code") or payload.get("errorCode") or f"HTTP_{status}"
    details = payload.get("details") or {}
    return {
        "status": status,
        "code": code,
        "message": payload.get("message", "(no message)"),
        "field": payload.get("field") or details.get("field"),
        "provided": payload.get("provided") or details.get("providedName"),
        "validOptions": payload.get("validOptions") or details.get("validOptions"),
    }
```

## Self-correction policy

When `validOptions` is present:

1. Look at `provided` vs. `validOptions`. The user (or the LLM that built the payload) typed something close to a real value.
2. Pick the closest match (case-insensitive substring or smallest Levenshtein distance is usually obvious).
3. Retry the call **once** with the corrected value.
4. If the retry also fails, surface the error to the user. Do not loop.

When `validOptions` is absent (network errors, 401s, 500s), don't retry blindly — the problem is structural, not a typo.

## Status code reference

These are the actual `errorCode` enum values PM emits, not HTTP reason phrases. Roadmarq / Wiki use the same conventions but their codes live under the flat `code` field rather than `errorCode`.

| Status | Typical PM `errorCode` | Meaning | What to do |
|---|---|---|---|
| 400 | `VALIDATION_ERROR` | Validation, bad enum, missing required field, bad input shape | Check `details.field` + `details.validOptions`, retry once |
| 400 | `OPERATION_NOT_ALLOWED` | Business-logic refusal (e.g. can't delete SYSTEM type, can't move to closed list) | Read `message`; do not blind-retry |
| 401 | `AUTHENTICATION_FAILED` | Bad / missing key, expired token | Stop — ask the user for a valid `dk_live_…` key |
| 402 | `QUOTA_EXCEEDED` | Plan limit hit (seats, lists, automations, …) | Surface to user; cannot retry without upgrade |
| 403 | `ACCESS_DENIED` | Workspace in path ≠ key's bound workspace, or required scope/permission missing | Use the bound workspace identifier; check the key's scopes |
| 404 | resource-specific (`TASK_NOT_FOUND`, `WORKSPACE_NOT_FOUND`, `TASK_TYPE_NOT_FOUND`, `LIST_NOT_FOUND`, …) | Resource doesn't exist or isn't visible to this key | Verify the identifier; list to confirm |
| 409 | `ALREADY_EXISTS` / `NAME_ALREADY_EXISTS` | Duplicate name, key, or unique constraint hit | User may want to update instead |
| 409 | `CONCURRENT_MODIFICATION` | Someone else changed the resource between your fetch and write | Re-fetch and re-apply |
| 409 | `DUPLICATE_REQUEST` | Idempotency key collision | Drop or change the idempotency key |
| 409 | `ENTITY_IN_USE` | Trying to delete something with dependents (e.g. a custom field with values) | Detach dependents first, or use the reassignment flow |
| 429 | `RATE_LIMIT_EXCEEDED` | Slow down | Exponential backoff; check `Retry-After` if present |
| 5xx | `INTERNAL_ERROR` / `SERVICE_UNAVAILABLE` / `EXTERNAL_SERVICE_TIMEOUT` | Backend or downstream issue | Don't retry more than once or twice; surface to user |

There is **no** `BAD_REQUEST`, `UNAUTHORIZED`, `NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `SERVER_ERROR`, or `AMBIGUOUS_WORKSPACE` code in PM. Workspace name collisions don't fail — `LiteWorkspaceContextService` silently picks the first match by `name`. To target a specific workspace deterministically, use the **identifier** in the path (and when a key is bound, the identifier MUST equal the bound one or you get `403 ACCESS_DENIED` from the API-key scope filter, before any name resolution happens).

## Rate-limit response

When a per-IP / per-key rate ceiling is hit, the call returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 47
Content-Type: application/json

{ "message": "Too many requests. Try again later.", "errorCode": "RATE_LIMIT_EXCEEDED" }
```

`Retry-After` is in seconds. Default ceilings (configurable per deployment via `dutify.rate-limit.*` properties):

| Surface | Default cap |
|---|---|
| API key (per key) | 300 req/min |
| Authenticated JWT (per user) | 600 req/min |
| Public share / public form (per IP) | 30 req/min |
| Login | 10 req/min |
| Register | 5 req/min |
| Password change | 5 req/min |

Specific Roadmarq lite endpoints add their own per-method caps (e.g. `/requests/lite/{id}` DELETE is 30/min via `@RateLimit`) — these stack on top of the global cap.

## Network-level errors

If the request never gets a response — DNS failure, connection refused, timeout — that's not a Dutify error, it's an infrastructure error. Surface it as such; don't pretend the API said something it didn't.

## What to tell the user when something fails

- A typo or bad enum: explain what they typed and what the valid options were. Often you can just retry quietly.
- An auth failure: explain that the key is invalid or bound to a different workspace, and what they need to provide.
- A permission failure: name the resource and the access level required.
- A 5xx: say the backend errored, don't speculate about why.
