# Notifications

User-facing notification feed. Tag: **Notifications** (non-lite). All endpoints scope to the authenticated user — agents read their *own* feed and mark their own items as read.

## List and count

```http
GET https://dutify.ai/mp/api/v1/notifications/workspace/{workspaceIdentifier}
X-API-Key: dk_live_…
```

Query params:

| Param | Default | Effect |
|---|---|---|
| `?unreadOnly=true` | `false` | Drop already-read notifications. Most agents want this. |
| `?page=<int>` | `0` | Page-style pagination (NOT cursor). |
| `?size=<int>` | (server default) | 1–100. |
| `?sortColumn=<col>` | (server default) | Sort key. |
| `?sortDirection=ASC` or `DESC` | (server default) | |

Returns `NotificationDTO[]`:

```json
{
  "identifier": "ntf_abc123",
  "type": "TASK_ASSIGNED",
  "data": { "...activity-specific JSON..." },   // arbitrary nested object, NOT a stringified JSON like ActivityLogDTO
  "createdAt": "2026-05-08T12:00:00Z",
  "readStatus": false
}
```

> Unlike `ActivityLogDTO.data` (which is a JSON-encoded string), `NotificationDTO.data` is a real nested JSON object — `JsonNode` server-side, native object on the wire. No double-parse needed.

Quick unread count without fetching the list:

```http
GET /v1/notifications/workspace/{workspaceIdentifier}/unread-count
```

Returns a bare `Long` — just `42`, not wrapped in an envelope.

## Mark read

```http
PUT /v1/notifications/{identifier}/read                              # one notification
PUT /v1/notifications/workspace/{workspaceIdentifier}/read-all       # everything in this workspace
```

`/read` takes the notification's stable identifier (`ntf_…`). The `/read-all` endpoint flips every unread notification in the named workspace at once — useful for "clear inbox" affordances.

## Scope

`notifications:read` for GETs, `notifications:write` for the read-flip operations. There is no DELETE — notifications expire on their own; you can only mark them read.

## Watch out

- Pagination is **page-style** (`?page=&size=`), unlike most lite list endpoints which are cursor-based. Don't pass `?cursor=` here — it's silently ignored, you get page 0 every time.
- `data` shape varies by `type` (`TASK_ASSIGNED`, `MENTION`, `STATUS_CHANGED`, …) — there's no single schema. Inspect by `type` or fetch the catalog tag detail for the types you care about.
