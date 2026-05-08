# Task types — discovery, cascade defaults, bulk changes

Every workspace gets nine SYSTEM task types seeded at creation, plus any CUSTOM types the workspace adds afterwards.

## The 9 SYSTEM rows

| systemKey | name | pluralName | icon | color |
|---|---|---|---|---|
| `SYSTEM_TASK` | `Task` | `Tasks` | `ClipboardList` | gray |
| `SYSTEM_BUG` | `Bug` | `Bugs` | `Bug` | red |
| `SYSTEM_FEATURE` | `Feature` | `Features` | `Sparkles` | blue |
| `SYSTEM_IMPROVEMENT` | `Improvement` | `Improvements` | `Lightbulb` | green |
| `SYSTEM_MILESTONE` | `Milestone` | `Milestones` | `Flag` | orange |
| `SYSTEM_EPIC` | `Epic` | `Epics` | `Trophy` | purple |
| `SYSTEM_INVOICE` | `Invoice` | `Invoices` | `CreditCard` | teal |
| `SYSTEM_DOCUMENT` | `Document` | `Documents` | `FileText` | slate |
| `SYSTEM_FORM` | `Form` | `Forms` | `ListChecks` | indigo |

## Discover the catalogue

```http
GET https://dutify.ai/mp/api/v1/workspaces/{wsId}/task-types
X-API-Key: dk_live_…
```

Returns `TaskTypeDTO[]` — `id`, `identifier`, `name`, `description`, `icon` (legacy single-string), `creatorUuid` (CUSTOM rows only), `origin` (`SYSTEM` | `CUSTOM`), `systemKey` (`SYSTEM_*` for SYSTEM, null for CUSTOM), `systemDefault` (true only for `SYSTEM_TASK`), `singularName`, `pluralName`, `iconKind` (`icon` | `emoji`), `iconValue`, `color` (palette token, not free hex), `sortOrder`, `reassignStatus` (`ACTIVE` | `PENDING_REASSIGN`), `reassignTargetId` (when PENDING_REASSIGN), `taskCount` (zero, not null, when no tasks).

The lite name-resolver matches against the **`name`** field only — not `singularName`, not `identifier`. Match is exact and case-sensitive.

## Cascade default — only three levels, no workspace fallback

When a task is created without an explicit `taskType`, the backend resolves the default by walking **three** levels:

```
COALESCE(list.default_task_type_id, folder.default_task_type_id, space.default_task_type_id)
```

The workspace itself has no `defaultTaskTypeId` field. If all three levels are null (which is the default state for fresh workspaces), the task is created **untyped** — `task_type_id IS NULL`, and the response's `taskType` is `null`. `SYSTEM_TASK` exists in the catalogue but is *not* an automatic fallback; nothing magically attaches it.

`GET /v1/workspaces/{wsRef}/lite/context` echoes `defaultTaskTypeIdentifier` on each space, folder, and list so you can predict what a fresh task will inherit. Field is `null` when no override is set at that level.

## Setting a default (non-lite write endpoints — take identifiers)

```http
PUT https://dutify.ai/mp/api/v1/spaces/{spaceIdentifier}/default-task-type
PUT https://dutify.ai/mp/api/v1/folders/{folderIdentifier}/default-task-type
PUT https://dutify.ai/mp/api/v1/lists/{listIdentifier}/default-task-type
```

Body is `SetDefaultTaskTypeRequest`:

```json
{ "taskTypeIdentifier": "tt_bug" }
```

Pass `taskTypeIdentifier: null` to clear the override at that level (so the level inherits from the next one up).

## Change a single task's type

`PATCH /v1/tasks/lite/{ref}` with the type **name** (lite name-resolution applies):

```http
PATCH https://dutify.ai/mp/api/v1/tasks/lite/PROJ-7?workspace={wsId}
X-API-Key: dk_live_…
Content-Type: application/json

{ "taskType": "Bug" }
```

Pass `{"taskType": null}` instead to clear the type and make the task untyped. PATCH tri-state: omit the field entirely → no change; present with a string → resolve and set; present with `null` → clear.

## Bulk-change types — non-lite, identifier-based

For changing many tasks at once (≤5000 per call):

```http
POST https://dutify.ai/mp/api/v1/tasks/bulk/change-type
X-API-Key: dk_live_…
Content-Type: application/json

{
  "taskIdentifiers": ["tsk_…", "tsk_…"],
  "targetTaskTypeIdentifier": "tt_bug",   // or null to clear
  "workspaceIdentifier": "ws_…"
}
```

`taskIdentifiers` are **stable identifiers** (`tsk_…`), NOT short keys (`PROJ-42`). The endpoint does not resolve type names — pass the type **identifier** (`tt_…`) you got from the catalogue, or `null` to clear. Sync threshold is 500 (configurable per deployment).

- **Sync 200 response** (`taskIdentifiers.length` ≤ 500): `{processedCount, skippedCount, skippedIdentifiers, targetTaskType, batchId, jobId: null, totalCount: null, statusUrl: null}`. `skippedIdentifiers` is the list of task IDs the user lacked EDIT on; they're counted in `skippedCount` and skipped silently. `batchId` is a UUID matching the audit-log row.
- **Async 202 response** (>500): `{processedCount: 0, skippedCount, skippedIdentifiers, targetTaskType: null, batchId, jobId, totalCount, statusUrl: "/v1/bulk-jobs/{jobId}"}`. The upfront permission filter still runs synchronously (so `skippedCount` and `skippedIdentifiers` reflect tasks the user can't edit), but `processedCount` only goes up as the async worker finishes — poll `statusUrl` for live counts and terminal status.

## Two-step bulk recipe

```http
GET https://dutify.ai/mp/api/v1/tasks/lite/search?workspace={wsId}&list=lst_abc&limit=200
# → response.items[].identifier — collect stable identifiers, not short keys

GET https://dutify.ai/mp/api/v1/workspaces/{wsId}/task-types
# → find the row with name="Bug", read its identifier (e.g. "tt_bug")

POST https://dutify.ai/mp/api/v1/tasks/bulk/change-type
{ "taskIdentifiers": [...], "targetTaskTypeIdentifier": "tt_bug", "workspaceIdentifier": "ws_acme" }
```

## Deleting a custom task type triggers reassignment, not a hard delete

`DELETE /v1/workspaces/{wsId}/task-types/{taskTypeIdentifier}` always returns `202 Accepted`. It marks the type `reassignStatus: PENDING_REASSIGN` and asynchronously reassigns every assigned task to a target type. Pass the target as the `?reassignTo=tt_…` **query parameter**; omitting it (or blank) defaults to the workspace's `SYSTEM_TASK` row. Poll `GET /v1/workspaces/{wsId}/task-types/{taskTypeIdentifier}/reassignment` for status; once the row is fully reassigned and deleted, that GET returns `404` — that's the terminal "done" signal. SYSTEM types cannot be deleted.
