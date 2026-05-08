# CSV import — preview / confirm flow

Tag: **Imports** (non-lite). Three-step flow: preview, confirm mappings, poll job status. There's also a one-shot direct upload that skips the mapping step.

## Two-step flow (preview → confirm)

### 1. Preview the file and get suggested mappings

```http
POST https://dutify.ai/mp/api/v1/workspaces/{workspaceIdentifier}/import/csv/preview
X-API-Key: dk_live_…
Content-Type: multipart/form-data

# form parts:
#   file=<binary CSV, max 10 MiB, must end in .csv>
#   taskListIdentifier=<lst_…>   (required — target list identifier, not name)
```

Returns `ImportPreviewDTO` with:

- The CSV header row
- A small sample of rows
- Suggested column→field mappings (Title, Description, Status, Priority, Assignees, due/start dates, custom fields)
- An import `jobIdentifier` in `PREVIEW` status

### 2. Confirm the mappings to start the actual import

```http
POST https://dutify.ai/mp/api/v1/workspaces/{workspaceIdentifier}/import/{jobIdentifier}/confirm
X-API-Key: dk_live_…
Content-Type: application/json

{
  "columnMappings": [
    { "columnIndex": 0, "targetField": "title" },
    { "columnIndex": 1, "targetField": "status" },
    { "columnIndex": 2, "targetField": "priority" },
    { "columnIndex": 3, "targetField": "customField:Severity" }
  ]
}
```

The job transitions out of `PREVIEW` and async processing kicks off. Returns the `ImportJobDTO`.

### 3. Poll the job

```http
GET /v1/workspaces/{workspaceIdentifier}/import/{jobIdentifier}
```

Returns `ImportJobDTO` with `status` (`PREVIEW` | `RUNNING` | `COMPLETED` | `FAILED`), progress counters, and on terminal status, a list of created task identifiers + a list of per-row failures with messages.

## One-shot flow (skip preview)

When you already know the column mapping and want to avoid the round-trip, post the CSV directly:

```http
POST https://dutify.ai/mp/api/v1/workspaces/{workspaceIdentifier}/import/csv
X-API-Key: dk_live_…
Content-Type: multipart/form-data

# form parts:  file=<binary>, taskListIdentifier=<lst_…>
```

Returns the `ImportJobDTO` immediately. Behind the scenes the server applies its default mapping based on the header row. Best used when you control the CSV format end-to-end.

## Constraints

- File **must** end in `.csv`.
- **10 MiB** size cap (the resource enforces this directly with a 400 — independent of plan).
- `taskListIdentifier` is required — there is no "import into the workspace generally" mode; pick a target list.
- Scope: `imports:write`. There is no `imports:read` scope — the `GET …/{jobIdentifier}` and list endpoints are open to anyone with workspace VIEW (the AuthorizeAccess on the resource enforces it).
