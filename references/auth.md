# Authentication

## Account personal keys

`du_live_…` keys work across Hub and the suite. Create/manage them in account settings. Discover workspaces and select one per request using `X-Dutify-Workspace`; see [personal-keys.md](personal-keys.md). The workspace-binding rules below describe existing `dk_live_…` workspace keys. For personal keys, the same boundary applies to the workspace selected for this request.


## The header

Every data-access call needs `X-API-Key` with a `dk_live_…` workspace key or a `du_live_…` personal key. Workspace-key example:

```
X-API-Key: dk_live_<rest>
```

Workspace keys start with `dk_live_`; personal keys start with `du_live_` — `dk_test_` keys exist in some environments but production is `dk_live_`.

## Workspace keys: one key, one workspace

A `dk_live_…` workspace key is bound to exactly one workspace at provisioning time. The backend enforces this with a request-layer filter (`ApiKeyScopeFilter`):

> Reject any request whose URL contains a workspace identifier different from the key's bound one with `403 ACCESS_DENIED`.

Implications:

- You can't operate across multiple workspaces with one key. To act on a different workspace, provision a separate key.
- The filter does a strict identifier equality check **before** name resolution. So passing a workspace **name** in a path slot that takes the bound workspace will 403, even if the name is correct — you must pass the canonical identifier.
- Some path params (e.g. `/v1/workspaces/{wsRef}/lite/context`) accept names *for resolution* but the scope filter still runs first. In practice: just always use the identifier.

## Finding the bound workspace

If the user gives you a key but you don't know which workspace it belongs to, use the self-introspection endpoint — one call, no probing:

```http
GET https://dutify.ai/mp/api/v1/api-keys/current
X-API-Key: dk_live_…
```

Response (200):

```json
{
  "keyIdentifier": "key_…",
  "keyName": "MCP key for Cursor",
  "workspaceIdentifier": "ws_…",
  "workspaceName": "Acme Corp",
  "scopes": ["tasks:read", "tasks:write", "spaces:read"],
  "createdByUuid": "…"
}
```

This endpoint is **exempt from the scope filter** — even a key with no `workspaces:read` scope can call it, because otherwise scope discovery itself would be impossible. It is the canonical way to answer "what does this key let me do?" in one HTTP call. Refresh permission and scope metadata when needed; keys, scopes, and memberships can change. Never cache a personal-key access decision.

`/v1/api-keys/current` requires API-key authentication. Calling it with a JWT returns `400` — use the `/v1/users/current` family for JWT-context introspection instead.

Avoid the old workaround of listing `/v1/users/current/workspaces` and probing each workspace until one doesn't 403 — `/v1/api-keys/current` replaces it.

## Workspace identifier vs. name

Some endpoints accept either an identifier (slug-like, stable) or a name. The catalog response will tell you in the parameter description. When in doubt, use the identifier.

A workspace **name** that matches multiple workspaces returns `409 AMBIGUOUS_WORKSPACE`. The response body lists the candidate identifiers — pick one and retry with that.

## Where keys come from

Generate keys via the PM UI under workspace settings → API keys. The skill should never invent or guess keys. If the user hasn't supplied one, ask.

You can also list / inspect a workspace's keys (and the scopes each carries) via:

```http
GET https://dutify.ai/mp/api/v1/workspaces/{workspaceIdentifier}/api-keys
X-API-Key: dk_live_…
```

(This itself requires a key with `workspaces:read` scope.)

## Scopes — the second 403 cause

The API-key scope filter checks **two** things on every call: the selected personal-key workspace (or workspace-key binding) AND a per-resource scope. A 403 `ACCESS_DENIED` can mean either "wrong workspace in the path" OR "your key has no `tasks:write` scope" — the response message tells you which.

Each request is matched to a scope via the URL's most-specific path segment. `GET /v1/tasks/...` needs `tasks:read`; `POST /v1/tasks/lite` needs `tasks:write`; `POST /v1/spaces/lite` needs `spaces:write`; etc. Read methods (`GET`, `HEAD`, `OPTIONS`) check `:read`; everything else (`POST`, `PUT`, `PATCH`, `DELETE`) checks `:write`.

The complete scope vocabulary (from `ApiKeyScope` enum):

| Resource family | `:read` scope | `:write` scope |
|---|---|---|
| Tasks | `tasks:read` | `tasks:write` |
| Spaces | `spaces:read` | `spaces:write` |
| Lists | `lists:read` | `lists:write` |
| Folders | `folders:read` | `folders:write` |
| Custom fields | `custom_fields:read` | `custom_fields:write` |
| Workspaces | `workspaces:read` | `workspaces:write` |
| Webhooks | `webhooks:read` | `webhooks:write` |
| Sprints / sprint-groups | `sprints:read` | `sprints:write` |
| Tags | `tags:read` | `tags:write` |
| Teams | `teams:read` | `teams:write` |
| Time tracking | `time:read` | `time:write` |
| Forms | `forms:read` | `forms:write` |
| Whiteboards | `whiteboards:read` | `whiteboards:write` |
| Filters | `filters:read` | `filters:write` |
| Relationships / relationship-types | `relationships:read` | `relationships:write` |
| Resource views | `views:read` | `views:write` |
| Automations | `automations:read` | `automations:write` |
| Dashboards | `dashboards:read` | `dashboards:write` |
| Notifications | `notifications:read` | `notifications:write` |
| Activity log | `activity_log:read` | (no write) |
| Users | `users:read` | (no write) |
| Imports | (no read) | `imports:write` |
| Lookup tables (`custom-field-types`, `custom-field-icon-options`, `status-types`, `access-levels`, …) | `metadata:read` | (no write) |
| Wiki pages | `wiki:pages:read` | `wiki:pages:write` |
| Wiki spaces | `wiki:spaces:read` | `wiki:spaces:write` |
| Wiki comments | `wiki:comments:read` | `wiki:comments:write` |
| Wiki attachments | `wiki:attachments:read` | `wiki:attachments:write` |
| Wiki search | `wiki:search:read` | (no write) |
| Wiki dashboard | `wiki:dashboard:read` | (no write) |
| Wiki settings | `wiki:settings:read` | `wiki:settings:write` |
| Wiki export / import | `wiki:export:read` | `wiki:import:write` |
| Wiki cover images | `wiki:covers:read` | (no write) |
| Roadmarq boards | `feedback:boards:read` | `feedback:boards:write` |
| Roadmarq requests | `feedback:requests:read` | `feedback:requests:write` |
| Roadmarq bugs | `feedback:bugs:read` | `feedback:bugs:write` |
| Roadmarq comments | `feedback:comments:read` | `feedback:comments:write` |
| Roadmarq votes | (no read) | `feedback:votes:write` |
| Roadmarq moderation | (no read) | `feedback:moderation:write` |
| Roadmarq settings | `feedback:settings:read` | `feedback:settings:write` |
| Roadmarq notifications | `feedback:notifications:read` | `feedback:notifications:write` |
| Roadmarq attachments | `feedback:attachments:read` | `feedback:attachments:write` |

A few endpoints are **hard-denied for API keys regardless of scopes** — `/v1/external-connections/*` and `/v1/internal/*` (which is gated by the separate `X-Internal-Token` shared secret). Don't try to call those with an API key; they always 403.

## Common auth failures

| Status | PM code | What it means | Fix |
|---|---|---|---|
| 401 | (often empty body — Quarkus auth layer) or `AUTHENTICATION_FAILED` | Missing, malformed, or revoked key | Check the header, regenerate the key |
| 401 | as above | Key starts with neither `dk_live_` nor `du_live_` | Wrong environment or typo |
| 403 | `ACCESS_DENIED` | Key is valid but the path differs from the selected workspace or workspace-key binding | Use the bound workspace identifier (see `/v1/users/current/workspaces`) |
| 403 | `ACCESS_DENIED` | Key is valid and workspace matches, but the key's scopes don't cover this endpoint, OR the user lacks the required permission level | Check the key's scopes; the user may need higher access (VIEW/EDIT/ADMIN) on that resource |

There is no `UNAUTHORIZED` / `FORBIDDEN` / `AMBIGUOUS_WORKSPACE` enum value in PM. Workspace name ambiguity does not surface as an error — the resolver picks the first match silently. The API-key scope filter compares `pathWorkspace.equals(boundWorkspaceIdentifier)` byte-for-byte before any name resolution, so passing a workspace **name** in the path slot when the key is bound to an **identifier** fails the comparison and 403s — even if the name would have resolved to the right workspace.

## Storing the key

When scripting against the API, read the key from an environment variable (`DUTIFY_API_KEY`) or a secrets store. Never inline it into source files or commit it to git.

### Personal-key denials

Personal-key authentication uses a flat `{code, message}` response. Check the status and code before suggesting a different key.

| Status | Code | Action |
| --- | --- | --- |
| 400 | `WORKSPACE_REQUIRED` | Discover accessible workspaces and send the selected canonical identifier in `X-Dutify-Workspace`. The key format is valid. |
| 401 | authentication failure | Check for a missing, invalid, expired, or revoked key, including a revoked or expired delegating parent. Both the product's workspace-key prefix and `du_live_` are supported. |
| 402 | `PERSONAL_API_KEY_LIMIT_REACHED` | Workspace keys have priority. Ask an administrator to upgrade capacity or disable personal-key access in workspace Security settings; do not switch workspaces to bypass the limit. |
| 403 | `PERSONAL_API_KEYS_DISABLED` / `PERSONAL_API_KEY_ACCESS_DENIED` / `ACCESS_DENIED` | Check workspace opt-out, current membership, product access, selected workspace, and scopes. Retry only after the relevant condition changes. Downstream products may normalize the code to `PERSONAL_API_KEY_ACCESS_DENIED`. |
| 503 | `PERSONAL_API_KEY_AUTHORITY_UNAVAILABLE` | Authorization could not reach its authority. Retry a read with bounded backoff; report a persistent outage. Never substitute cached authorization or repeat a mutation whose outcome is unknown. |
