# Tasks — search, create, update, attachments, recurrence

## Orient: what's in this workspace?

Before doing anything else, get a one-shot bundle of the workspace structure. Tag: **Context (Lite)**.

```http
GET https://dutify.ai/mp/api/v1/workspaces/{wsRef}/lite/context
X-API-Key: dk_live_…
```

Returns workspace metadata (identifier + name + members), the spaces/folders/lists tree, workspace-level taskType / relationshipType / tag names, and per-list effective statuses / priorities / custom-fields / taskType defaults. Sprints and sprint-groups are NOT in this bundle — fetch them separately via the non-lite `Sprints` and `Sprint Groups` tags. Cache the rest for the session; structure rarely changes mid-task.

The default response is **everything**, which on a large workspace can be heavy. The endpoint takes a few query knobs to narrow the call:

| Param | Default | Effect |
|---|---|---|
| `?shallow=true` | `false` | Skip per-list expansion entirely — just members + space/folder/list skeletons. Fastest. |
| `?space={name}` | (all spaces) | Narrow to one space by name. Members + workspace-level metadata still returned. |
| `?includeTaskTypes=false` | `true` | Drop the workspace task-type list and the per-list task-type echo. |
| `?includeRelationshipTypes=false` | `true` | Drop the workspace relationship-type list. |
| `?includeCustomFields=false` | `true` | Drop the per-list custom-field arrays. Other levels unaffected. |
| `?includeTags=false` | `true` | Drop tag aggregates at workspace + per-space level. |

`shallow=true` overrides the per-area `include*` flags — they all become `false` when shallow is set.

`{wsRef}` accepts the workspace **identifier** OR display **name** under JWT auth (`findByIdentifier` first, name fallback by exact match — first-match wins on collisions). Under API-key auth the path workspace MUST equal the bound identifier byte-for-byte; passing a name 403s.

## Find tasks by name / status / assignee

Tag: **Search (Lite)**. The endpoint is `GET /v1/tasks/lite/search` (NOT `/v1/tasks/lite` — that path is the create endpoint and per-ref operations). The workspace identifier is the **`workspace`** query parameter (not `workspaceRef`) and is required.

```http
GET https://dutify.ai/mp/api/v1/tasks/lite/search?workspace={wsId}&status=In%20Progress&assignee=alex@dutify.ai
X-API-Key: dk_live_…
```

Repeatable filters (pass the same key multiple times for OR semantics): `status`, `priority`, `tag`, `taskType`, `assignee`. Other filters: `parent` (key/identifier), `q` (free text over title+description), `space` (name), `list` (identifier), `includeClosed` (default `false`), `includeArchived` (alias for `includeClosed`), `includeSubtasks` (default `true`), `limit` (default 50, max 200), `cursor`.

Response is a `LitePageResponse<LiteTaskResponse>` — `{items: [...], nextCursor: "..."}`. Each item has the short key (`PROJ-42`) and stable `identifier` (`tsk_…`) — use the short key for further lite calls, the stable identifier when an endpoint requires it (e.g. bulk change-type).

## Create a task

Tag: **Tasks (Lite)**. Field names: `title` (not `name`), `list` (not `listRef`); `list` takes the list **identifier** — resolve names → identifiers via `/lite/context` first. Workspace is scoped automatically by the API key, so there's no `workspaceRef` field on the body.

```http
POST https://dutify.ai/mp/api/v1/tasks/lite
X-API-Key: dk_live_…
Content-Type: application/json

{
  "title": "Write Q4 plan",
  "list": "lst_abc123",
  "status": "To Do",
  "priority": "High",
  "assignees": ["alex@dutify.ai"],
  "description": "Outline goals and OKRs"
}
```

Returns the new task as a flat `LiteTaskResponse` including its short key (`PROJ-7`) and stable `identifier`. Use the short key in any subsequent reference (comments, relationships, status updates).

### Retry-safety: the `Idempotency-Key` header

`POST /v1/tasks/lite` (and a handful of other create endpoints — folders, spaces) is annotated `@Idempotent`. Pass an `Idempotency-Key: <opaque-string>` header to opt into deduplication.

**The actual semantics are narrower than Stripe-style idempotency** — read carefully:

- The server does a Redis `SETNX` on `idem:<your-key>` with a 5-minute TTL. The body is NOT hashed and the original response is NOT cached.
- A second request with the same key inside 5 minutes is **rejected with `409 DUPLICATE_REQUEST`**, regardless of body.
- The 409 does NOT replay the original response. There is no "got my response back" semantic — you only get back "we already saw this key, but we won't tell you what happened the first time".
- After 5 minutes the key is reusable, with no carryover.
- If Redis is down, the filter fails *open* (allows the request through unchecked).

```http
POST https://dutify.ai/mp/api/v1/tasks/lite
X-API-Key: dk_live_…
Idempotency-Key: 9a1d3e7c-2c14-4d6a-9b91-1f5b3d2a8a01
Content-Type: application/json

{ "title": "Q4 plan", "list": "lst_abc123", "status": "To Do" }
```

The right way to use it: when you retry on a network/timeout error, send the same `Idempotency-Key`. If the first attempt actually landed, the retry gets 409 — that's your signal to **query by name/identifier** to find what was created (don't assume failure on 409). If the first attempt never landed, the retry succeeds normally. Generate a fresh UUID per logical operation; never reuse one across distinct operations.

If you need cross-session idempotency (across the 5-min window), derive the key deterministically from a business identifier (e.g. external task ID) and accept that operations spaced more than 5 min apart may double-create.

## Update a task by short key

PATCH is partial — only send fields you want to change. **When `{ref}` is a short key (e.g. `PROJ-7`), the `?workspace=` query parameter is REQUIRED** (the resolver needs it to disambiguate the workspace-scoped key). When `{ref}` is the stable `tsk_…` identifier, the query param can be omitted.

```http
PATCH https://dutify.ai/mp/api/v1/tasks/lite/PROJ-7?workspace={wsId}
X-API-Key: dk_live_…
Content-Type: application/json

{ "status": "In Progress", "priority": "Critical" }
```

The same `?workspace=` rule applies to GET / PUT / DELETE on `/v1/tasks/lite/{ref}` AND to all sub-resources rooted at it — `/v1/tasks/lite/{ref}/comments`, `/v1/tasks/lite/{ref}/relationships`, `/v1/tasks/lite/{ref}/subtasks` — whenever `{ref}` is a short key. With the stable `tsk_…` identifier the query is optional everywhere.

## Comment on a task

Tag: **Comments (Lite)**. The body field is `text` (not `body`), the workspace identifier is required as a `?workspace=` query parameter, and mentions must be listed in a separate `mentions` array — the inline `@<email>` token is **only rendered as a span if the email also appears in `mentions`**.

```http
POST https://dutify.ai/mp/api/v1/tasks/lite/PROJ-7/comments?workspace={wsId}
X-API-Key: dk_live_…
Content-Type: application/json

{
  "text": "Heads up @alex@dutify.ai — moving this up the queue.",
  "mentions": ["alex@dutify.ai"],
  "replyTo": "cmt_abc"
}
```

`replyTo` is optional — pass a parent comment identifier to thread. Reply chains cap at depth 50 (`Comment.MAX_PARENT_DEPTH`); going deeper returns `400 OPERATION_NOT_ALLOWED`. The check is a soft UX limit — there's no pessimistic locking, so concurrent inserts could in theory breach by ±1 in a tight race.

The response is a `LiteCommentResponse` with `text`, `author` email, timestamps, and the resolved `mentions` list. PATCH and DELETE on `…/comments/{commentIdentifier}` are also lite. Reactions on comments live on the **non-lite** path: `/v1/tasks/{taskIdentifier}/comments/{commentIdentifier}/reactions`.

## Task relationships

Lite path at `/v1/tasks/lite/{ref}/relationships` (POST/GET/DELETE). The body uses a `relationshipType` **name** (resolved against the workspace's relationship-type catalogue). Same `?workspace=` rule applies when `{ref}` is a short key. Scope `relationships:write` / `:read`.

## Attaching files to a task

There's no `(Lite)` attachment endpoint — both surfaces are non-lite and take identifiers everywhere.

### Create a task **with** attachments in one shot

```http
POST https://dutify.ai/mp/api/v1/tasks/with-attachments
X-API-Key: dk_live_…
Content-Type: multipart/form-data; boundary=----…

------…
Content-Disposition: form-data; name="task"
Content-Type: application/json

{ "title": "Bug repro", "taskList": {"identifier": "lst_abc"}, "status": {"identifier": "st_abc"}, "priority": {"identifier": "pr_abc"} }
------…
Content-Disposition: form-data; name="files"; filename="screenshot.png"
Content-Type: image/png

<binary>
------…--
```

This endpoint is non-lite — the `task` JSON part uses the **full** `TaskCreationRequest` shape (identifiers for status/priority/list, not names — see "Non-lite TaskCreationRequest shape" below). The `files` form field is repeatable. Endpoint is `@Idempotent`, so you can pass `Idempotency-Key` to dedupe retries.

### Upload a file to a custom-field "file" field

For tasks that have a file-type custom field, use:

```http
POST https://dutify.ai/mp/api/v1/tasks/{taskIdentifier}/custom-field-value/{customFieldValueIdentifier}/files
X-API-Key: dk_live_…
Content-Type: multipart/form-data

# form parts:  file=<binary>, fileName=<string>, fileSize=<bytes>
```

`fileName` and `fileSize` are required form fields alongside the binary. Returns `AttachmentDTO`. Per-workspace size cap depends on plan: FREE 10 MiB, PRO 100 MiB, BUSINESS 250 MiB, ENTERPRISE 1 GiB. Going over → 400 with the plan's cap in the message.

Other ops on the same path:
- `GET …/files` — list attachments on the field
- `GET …/files/{attachmentIdentifier}/url` — short-lived presigned download URL (use this rather than streaming the binary back through the API)
- `DELETE …/files/{attachmentIdentifier}` — remove

## Recurrence rules — what RRULE subset is supported

The `recurrenceRule` field on tasks (set on create/update via `recurrenceRule: "FREQ=WEEKLY;..."` or PATCHed via `/v1/tasks/{identifier}/recurrence-rule`) is parsed by `RecurrenceCalculator`, which supports a **strict subset** of iCalendar RRULE:

- `FREQ=` accepts only `DAILY` / `WEEKLY` / `MONTHLY`. **No** `YEARLY`, `HOURLY`, `MINUTELY`, `SECONDLY` — passing them silently falls back to daily-plus-1 behavior.
- `INTERVAL=<n>` — repeat every n units of FREQ.
- `BYDAY=` — comma-separated `MO,TU,WE,TH,FR,SA,SU` (used with WEEKLY).
- `BYMONTHDAY=` — day of month (used with MONTHLY).

Anything else (`UNTIL`, `COUNT`, `BYMONTH`, `BYWEEKNO`, `BYHOUR`, `WKST`, `BYSETPOS`, …) is **ignored** by the parser. Don't generate full iCal RRULEs and assume they'll be honored. Pass `null` or `""` on `RecurrenceRuleRequest` to clear.

Examples that work:

- `FREQ=DAILY` — every day
- `FREQ=DAILY;INTERVAL=3` — every 3 days
- `FREQ=WEEKLY;BYDAY=MO,WE,FR` — Mon/Wed/Fri
- `FREQ=MONTHLY;BYMONTHDAY=15` — 15th of each month

## Time tracking

`/v1/tasks/{taskIdentifier}/time-entries` (non-lite, identifier required). Two quirks:

- `{timeEntryId}` on `DELETE` and the response body's `id` field are **numeric `Long`** — NOT a stable `te_…`-style identifier. Other Dutify resources moved to slug-style identifiers; time-entries stayed numeric. Pull the id from the GET response.
- Body fields on `POST` are `timeSpent` (minutes, 0–10080 / max 7 days), `startedAt` (ISO instant), and optional `notes` (max 10000 chars). `userUuid` on the response is the user who logged the entry.

Scope: `time:read` / `time:write`.

## Cross-workspace task moves: not allowed

`POST /v1/tasks/bulk/move` and `PATCH /v1/tasks/{identifier}/move` both reject moves where the **target list is in a different workspace** with `400 OPERATION_NOT_ALLOWED` ("Cannot move task to a list in a different workspace"). API keys are workspace-bound anyway, so this only matters under JWT auth.

## Non-lite `TaskCreationRequest` shape (when `/tasks/with-attachments` insists)

The multipart attachment endpoint takes the **non-lite** request shape inside its `task` part. That means **identifiers, not names**, on every reference:

```json
{
  "title": "Bug repro",
  "description": "<rich-text>",
  "taskList": { "identifier": "lst_abc" },
  "status":   { "identifier": "st_open" },
  "priority": { "identifier": "pr_med" },
  "level":    { "identifier": "lvl_l2" },
  "taskType": { "identifier": "tt_bug" },
  "tags":     [ { "identifier": "tg_urgent" } ],
  "assigneesUuids": [ "<user-uuid>" ],
  "startDate": "2026-05-08T09:00:00Z",
  "dueDate":   "2026-05-15T17:00:00Z"
}
```

Resolve the identifiers via `/lite/context` first (or the per-resource list endpoints). Don't try to send `"status": "In Progress"` here — it'll deserialize to `StatusDTO{name="In Progress", identifier=null}` and the service rejects it.
