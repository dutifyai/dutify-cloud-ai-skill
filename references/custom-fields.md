# Custom fields — definitions, values, formula

## Manage custom-field definitions (lite CRUD)

In addition to setting custom-field VALUES on tasks (the `customFields` map on `POST /v1/tasks/lite`), you can manage the field DEFINITIONS via lite endpoints. Tag: **Custom Fields (Lite)**.

```http
POST   https://dutify.ai/mp/api/v1/custom-fields/lite                # create
PATCH  https://dutify.ai/mp/api/v1/custom-fields/lite/{identifier}   # rename / re-option
DELETE https://dutify.ai/mp/api/v1/custom-fields/lite/{identifier}   # remove (cascades the field's values)
```

Create body:

```json
{
  "workspace": "ws_abc",
  "name": "Severity",
  "type": "dropdown",
  "scope": "list",            // one of: "workspace", "space", "list"
  "scopeName": "Bug List E2E", // ignored when scope=workspace; space NAME or list NAME otherwise
  "options": [{"name": "P1"}, {"name": "P2"}]
}
```

`type` is one of the field-type names (`text`, `dropdown`, `multiselect`, `number`, `date`, `checkbox`, `email`, `url`, `phone`, `rating`, `progress`, `currency`, `location`, `formula`, `rollup`, `relationship`, `file`, `vote`, … — pull the live list from the `metadata:read`-scoped `GET /v1/custom-field-types`). `scope` is one of `workspace` / `space` / `list`; for `space` and `list`, `scopeName` is the **name** (not identifier) and the resolver runs on it.

## Setting field values on a task

Lite create/update accept a `customFields: {fieldName: value}` map:

```http
POST https://dutify.ai/mp/api/v1/tasks/lite
{
  "title": "...",
  "list": "lst_abc",
  "customFields": {
    "Severity": "P1",
    "Sprint": "2026-Q2-W3"
  }
}
```

Field name → identifier resolution runs against the list's *effective* set (list + folder + space + workspace inheritance, filtered by your access). Values are passed through to the per-type validator unchanged — pass option name strings for dropdowns, numbers for numeric fields, ISO dates for date fields, etc. For file-type custom fields, see the Tasks reference (`tasks.md`) on file uploads.

## Formula fields are structured JSON, not strings

When you create a custom field with `type: "formula"`, the `configuration` is **not** a spreadsheet expression like `=A+B*2`. It's a structured config:

```json
{
  "operator": "SUBTRACT",
  "operandA": { "type": "TASK_FIELD", "field": "dueDate" },
  "operandB": { "type": "TASK_FIELD", "field": "createdAt" }
}
```

Operators: only `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`. Operand types: another custom field (by id), another `MATH_FORMULA` field (recursion!), a `ROLLUP` field (treated as NUMBER), or a `TASK_FIELD` reference (`dueDate` / `createdAt` / `updatedAt` = DATE; `estimatedTime` / `timeSpent` = NUMBER).

Result type is auto-determined from operand types per a published matrix (see catalog tag detail for `MathFormulaConfigurationDTO`). Examples:

- DATE − DATE → NUMBER (duration)
- DATE + NUMBER → DATE (date shift)
- MONEY ÷ MONEY → NUMBER (ratio)
- MONEY × NUMBER → MONEY
- mixed numerics → NUMBER

Validation runs server-side on create/update; the response carries the resolved `targetType` so you don't have to compute it client-side.

## Rollup fields are also structured JSON

Rollup is the sibling of formula — it pulls values from a different list and aggregates them. `RollupConfigurationDTO`:

```json
{
  "sourceListIdentifier": "lst_abc123",
  "rollupFieldIdentifier": "cf_severity",   // OR "rollupTaskField": "estimatedTime" — mutually exclusive
  "calculation": "sum"
}
```

- `sourceListIdentifier` (required) — the list whose tasks supply the source values. Pick tasks from this list as rollup-value entries on the rollup-field-bearing task.
- **One** of: `rollupFieldIdentifier` (a custom field on the source list) **or** `rollupTaskField` (a native task field — `dueDate`, `createdAt`, `updatedAt`, `estimatedTime`, `timeSpent`).
- `calculation` — exactly one of: `none` | `sum` | `average` | `earliest_date` | `latest_date` | `range` | `count`. The regex validates this — anything else 400s.
- `targetType` is set by the backend (don't bother sending it on writes). Determined from `calculation` × source field type.

Common pairings:

- `rollupTaskField: "estimatedTime"` + `calculation: "sum"` → numeric total (minutes)
- `rollupTaskField: "dueDate"` + `calculation: "latest_date"` → roll-up due date
- `rollupTaskField: "dueDate"` + `calculation: "range"` → date range string (earliest → latest)
- `rollupFieldIdentifier: "<some-number-field>"` + `calculation: "average"` → numeric average
- any source + `calculation: "count"` → integer count of rollup-value entries

Setting a rollup VALUE on a specific task means picking which source tasks to aggregate — that's done via the `customFields: {fieldName: [...source-task-identifiers]}` map on the task at write time.

