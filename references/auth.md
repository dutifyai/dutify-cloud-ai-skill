# Authentication

## The header

Every data-access call needs:

```
X-API-Key: dk_live_<rest>
```

Keys always start with `dk_live_`. If yours doesn't, it's wrong — `dk_test_` keys exist in some environments but production is `dk_live_`.

## One key, one workspace

A Dutify API key is bound to exactly one workspace at provisioning time. The backend enforces this with a request-layer filter (`ApiKeyScopeFilter`):

> Reject any request whose URL contains a workspace identifier different from the key's bound one with `403 ACCESS_DENIED`.

Implications:

- You can't operate across multiple workspaces with one key. To act on a different workspace, provision a separate key.
- The filter does a strict identifier equality check **before** name resolution. So passing a workspace **name** in a path slot that takes the bound workspace will 403, even if the name is correct — you must pass the canonical identifier.
- Some path params (e.g. `/v1/workspaces/{wsRef}/lite/context`) accept names *for resolution* but the scope filter still runs first. In practice: just always use the identifier.

## Finding the bound workspace

If the user gives you a key but you don't know which workspace it belongs to:

```http
GET https://dutify.ai/mp/api/v1/users/current/workspaces
X-API-Key: dk_live_…
```

Returns the user's full workspace list. The one your key works against will be flagged in the response (or you can find out by trying a scoped call and seeing which one doesn't 403). Cache this — it doesn't change often.

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

The API-key scope filter checks **two** things on every call: the bound workspace AND a per-resource scope. A 403 `ACCESS_DENIED` can mean either "wrong workspace in the path" OR "your key has no `tasks:write` scope" — the response message tells you which.

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
| Lookup tables (`status-types`, `access-levels`, …) | `metadata:read` | (no write) |
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
| 401 | as above | Key doesn't start with `dk_live_` | Wrong environment or typo |
| 403 | `ACCESS_DENIED` | Key is valid but the workspace in the path isn't the bound one | Use the bound workspace identifier (see `/v1/users/current/workspaces`) |
| 403 | `ACCESS_DENIED` | Key is valid and workspace matches, but the key's scopes don't cover this endpoint, OR the user lacks the required permission level | Check the key's scopes; the user may need higher access (VIEW/EDIT/ADMIN) on that resource |

There is no `UNAUTHORIZED` / `FORBIDDEN` / `AMBIGUOUS_WORKSPACE` enum value in PM. Workspace name ambiguity does not surface as an error — the resolver picks the first match silently. The API-key scope filter compares `pathWorkspace.equals(boundWorkspaceIdentifier)` byte-for-byte before any name resolution, so passing a workspace **name** in the path slot when the key is bound to an **identifier** fails the comparison and 403s — even if the name would have resolved to the right workspace.

## Storing the key

When scripting against the API, read the key from an environment variable (`DUTIFY_API_KEY`) or a secrets store. Never inline it into source files or commit it to git.
