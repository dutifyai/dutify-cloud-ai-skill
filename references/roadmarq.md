# Roadmarq — feature requests and bugs

Tag prefix: **Requests (Lite)** / **Bugs (Lite)** / **Boards (Lite)**. Base URL: `https://dutify.ai/api/roadmarq`. The `service` field on a catalog tag detail is `Roadmarq`. **Roadmarq IS in the aggregated catalog** (alongside PM and Codexum) — pull tag detail from there for canonical paths.

## Find a feature request or bug by short ID

Feature requests typically use `FR-42`-style keys, bugs typically `BG-99` — but the prefix is **per-board** (each board declares its own `requestPrefix` and `bugPrefix`), so don't hardcode `FR`/`BG`. Pull the actual prefixes from `LiteBoardSummaryDTO` via the boards-lite tag.

> **Required on every Roadmarq lite endpoint:** the `workspaceIdentifier` **query parameter**. The Roadmarq backend does NOT derive the workspace from the API key — every call must include `?workspaceIdentifier=<your-bound-workspace-id>` (or `&workspaceIdentifier=...` if the URL already has query params). Omitting it returns a 400. This is different from PM and Wiki, where the workspace is in the path.

```http
GET   https://dutify.ai/api/roadmarq/v1/requests/lite/FR-42?workspaceIdentifier=<wsId>
GET   https://dutify.ai/api/roadmarq/v1/bugs/lite/BG-99?workspaceIdentifier=<wsId>
PATCH https://dutify.ai/api/roadmarq/v1/requests/lite/FR-42/status?workspaceIdentifier=<wsId>
POST  https://dutify.ai/api/roadmarq/v1/requests/lite/FR-42/comments?workspaceIdentifier=<wsId>
```

## Roadmarq lite action verbs (verified)

The lifecycle pattern is `{base}/v1/{collection}/lite/{shortId}/{action}` and `workspaceIdentifier` always rides along as a query param. Action verbs as actually wired in the resource:

- **Feature requests** (`/v1/requests/lite/{shortId}/...`): `comments`, `votes` (plural), `status`, `moderation`. DELETE on `/{shortId}` itself.
- **Bug reports** (`/v1/bugs/lite/{shortId}/...`): `comments`, `status`, `assignee`, `visibility`, `affected`, `moderation`. DELETE on `/{shortId}` itself.

Watch out for two common verb mistakes: it's `/votes` (not `/vote`) and `/moderation` (not `/moderate`). Confirm any other verb against the catalog tag detail before calling.

## Per-method rate limits

DELETE on `/v1/requests/lite/{id}` and `/v1/bugs/lite/{id}` carries its own `@RateLimit(30 req/min)` guard, on top of the global API-key cap (300 req/min). 429 responses come from either ceiling.

## Required scopes

- `feedback:requests:read` / `feedback:requests:write`
- `feedback:bugs:read` / `feedback:bugs:write`
- `feedback:boards:read` / `feedback:boards:write`
- `feedback:comments:read` / `feedback:comments:write`
- `feedback:votes:write` (no read scope — votes are aggregate counts on the resource itself)
- `feedback:moderation:write`
- `feedback:settings:*`, `feedback:notifications:*`, `feedback:attachments:*`

Keys without the `feedback:*` scopes 403 every Roadmarq call regardless of workspace match.
