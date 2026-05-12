# Custom fields — definitions, values, formula

## Manage custom-field definitions (lite CRUD)

In addition to setting custom-field VALUES on tasks (the `customFields` map on `POST /v1/tasks/lite`), you can manage the field DEFINITIONS via lite endpoints. Tag: **Custom Fields (Lite)**.

```http
POST   https://dutify.ai/mp/api/v1/custom-fields/lite                # create
PUT    https://dutify.ai/mp/api/v1/custom-fields/lite/{identifier}   # rename / visual metadata
DELETE https://dutify.ai/mp/api/v1/custom-fields/lite/{identifier}   # remove (cascades the field's values)
```

Create body:

```json
{
  "workspace": "ws_abc",
  "name": "Severity",
  "type": "dropdown",
  "emoji": "Flag",
  "color": "#FF0000",
  "scope": "list",            // one of: "workspace", "space", "list"
  "scopeName": "Bug List E2E", // ignored when scope=workspace; space NAME or list NAME otherwise
  "options": [{"value": "P1"}, {"value": "P2"}]
}
```

`type` is one of the canonical field-type **identifiers** from `CustomFieldTypeEnum`: `text`, `text_area`, `number`, `money`, `rating`, `progress_bar`, `date`, `checkbox`, `dropdown`, `labels`, `email`, `phone`, `website`, `location`, `file`, `people`, `task`, `relationship`, `math_formula`, `rollup`, `voting`, `multivote`, `comment`. Note the spelling — common mistakes: `formula` (use `math_formula`), `progress` (use `progress_bar`), `currency` (use `money`), `vote` (use `voting`), `url` (use `website`), `multiselect` (does not exist — use `labels` for tag-style multi-select). Pull the live list from the `metadata:read`-scoped `GET /v1/custom-field-types` to stay in sync as types are added. `scope` is one of `workspace` / `space` / `list`; for `space` and `list`, `scopeName` is the **name** (not identifier) and the resolver runs on it.

Keep custom-field names as plain display labels (`Severity`, `Target Date`). Do **not** prefix names with emoji for column/header icons. Field icons are separate metadata: Lite/rich custom-field create/update accepts `emoji` and `color`.

> ⚠ **Set `emoji` + `color` at creation time, every time.** If you omit them, the frontend falls back to `defaultIconsByFieldType`, which renders as a generic gray circle for most types — agents repeatedly create 10+ fields without these and end up with a wall of identical circles. Pick a semantic icon while you already have the field's purpose in hand; it's much harder to backfill later.

### Picking the `emoji` value

**Always prefer an emoji name over a structural icon name.** Emojis (🔥, 🚀, 💰, 📌, 🎯) communicate the field's meaning at a glance; structural icons (`Hash`, `Stack`, `FlowArrow`) look abstract and tend to blend together visually. Reach for an icon name **only** when nothing in the emoji list semantically matches the field's purpose.

Get the live list of valid keys from `GET /v1/custom-field-icon-options` — it's `@PermitAll` so no API key or workspace binding required:

```http
GET https://dutify.ai/mp/api/v1/custom-field-icon-options
```

Response (`CustomFieldIconOptionsDTO`):

```json
{
  "emojiNames":  ["rocket", "fire", "direct_hit", "white_check_mark", "moneybag",
                  "pushpin", "tada", "bulb", "warning", "lock", "..." ],   // ~120 entries
  "iconNames":   ["CalendarBlank", "Hash", "Star", "Wallet", "TagSimple",
                  "FlowArrow", "Stack", "Bug", "Bell", "..." ],            // ~125 entries
  "defaultIconsByFieldType": {
    "dropdown": "CaretCircleDown",
    "labels":   "TagSimple",
    "date":     "CalendarBlank",
    "number":   "Hash",
    "money":    "Wallet",
    "people":   "UsersThree",
    "...":      "..."
  }
}
```

`emojiNames` / `iconNames` are flat string lists (same set as the in-app picker — see `dutify-pm-frontend/src/components/shared/emoji-picker/emojiPicker.data.tsx`). `defaultIconsByFieldType` is the fallback when you leave `emoji` unset — that's where the gray-circle wall comes from. Pass the exact key string back as the `emoji` field on create/update.

Common mappings to commit to memory:

| Field purpose | Use |
|---|---|
| Severity / urgency / risk | `fire` |
| Target / goal / objective | `direct_hit` |
| Launch / release / shipped | `rocket` |
| Approval / done / success | `white_check_mark` |
| Money / budget / cost | `moneybag` |
| Location / address | `pushpin` |
| Date / deadline | `CalendarBlank` (icon — no good emoji match) |
| Idea / suggestion | `bulb` |
| Bug / issue | `Bug` (icon) |
| Warning / blocker | `warning` |
| Celebration / milestone | `tada` |

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

Field name → identifier resolution runs against the list's *effective* set (list + folder + space + workspace inheritance, filtered by your access). Values are passed through to the per-type validator unchanged — pass option name strings for dropdowns, numbers for numeric fields, ISO dates for date fields, etc.

The non-obvious value shapes (the ones agents tend to guess wrong):

- **`labels`** — array of strings (e.g. `"Matched Products": ["Dutify", "Voxor"]`). For a field that **has** predefined options, each string must match an option's `value` (display name) **or** its `identifier` — same lookup rule as `dropdown`. For a field that has **no** predefined options, new labels are auto-created. `[]` clears all. Distinct from the top-level `tags: [...]` field on `POST /v1/tasks/lite` — `tags` are workspace-wide; `labels` is a list/space/workspace-scoped custom field inside `customFields`. Setting `tags` does **not** populate a `Labels` column.
- **`dropdown`** — string that matches an option's `value` (display name) **or** its `identifier`. Either works.
- **`checkbox`** — boolean, or a lenient string (`"true"`/`"false"`/`"yes"`/`"no"`/`"1"`/`"0"`/`"on"`/`"off"`/`"checked"`/`"unchecked"`, case-insensitive), or a number (`0` = false, non-zero = true).
- **`date`** — ISO 8601 string (`2026-05-08T00:00:00Z` or `2026-05-08`), a Unix timestamp number (the handler auto-detects: `≤ 1e12` is treated as seconds, `> 1e12` as milliseconds), or a structured object `{dateTime, includeTime?, timeZone?}`. **Footgun:** Postgres `timestamptz::text` renders as `2026-05-08 00:00:00+00` (space separator, `+00` offset) — that is **not** valid ISO 8601 and the handler will reject it. Cast explicitly: `to_char(col AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')`, or use `extract(epoch from col)` for the Unix-timestamp form. Same caveat for any source that defaults to a non-ISO date string.
- **`money`** — plain number or numeric string (defaults to USD), or a structured object `{amount, currency?}` where `currency` is a 3-letter ISO code (uppercased server-side).
- **`email`, `phone`, `website`, `location`** — each accepts a plain string (the most-important field — email address, phone number, URL, address respectively) **or** a structured object with extra fields. Read the catalog's request schema for the object form when you need it (`{email, displayName, verified}` for `email`; `{number, countryCode, extension}` for `phone`; `{url, title, description}` for `website`; `{address, city, state, country, zipCode, latitude, longitude}` for `location` with the constraint that `latitude` and `longitude` are paired and must both be set or both omitted).
- **`people`, `task`** — single identifier string **or** an array of identifier strings. `people` identifiers must resolve to workspace members.
- **`rollup`** — array of source-task identifier strings (the common case), a single string id, or a full `RollupValueDTO` object. The aggregation is computed server-side from the field's `RollupConfigurationDTO`; you only pick which source tasks contribute.
- **`math_formula`** — server-computed from the formula config; values posted via `customFields` are effectively ignored at compute time. Treat as read-only.

For file-type custom fields, see the Tasks reference (`tasks.md`) on file uploads.

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
- **One** of: `rollupFieldIdentifier` (a custom field **available** on the source list — defined on the list itself OR inherited from its folder chain / space / workspace; the validator walks the list's hierarchy) **or** `rollupTaskField` (a native task field — `dueDate`, `createdAt`, `updatedAt`, `estimatedTime`, `timeSpent`).
- `calculation` — exactly one of: `none` | `sum` | `average` | `earliest_date` | `latest_date` | `range` | `count`. The regex validates this — anything else 400s.
- `targetType` is set by the backend (don't bother sending it on writes). Determined from `calculation` × source field type.

Common pairings:

- `rollupTaskField: "estimatedTime"` + `calculation: "sum"` → numeric total (minutes)
- `rollupTaskField: "dueDate"` + `calculation: "latest_date"` → roll-up due date
- `rollupTaskField: "dueDate"` + `calculation: "range"` → date range string (earliest → latest)
- `rollupFieldIdentifier: "<some-number-field>"` + `calculation: "average"` → numeric average
- any source + `calculation: "count"` → integer count of rollup-value entries

Setting a rollup VALUE on a specific task means picking which source tasks to aggregate — that's done via the `customFields: {fieldName: [...source-task-identifiers]}` map on the task at write time.

## Dedicated endpoints for specific types

The `customFields` map is the normal write surface for all settable types. A few types have additional dedicated endpoints for richer operations:

- **`file` content upload:** `POST /v1/tasks/{taskIdentifier}/custom-field-value/{customFieldValueIdentifier}/files` (multipart with `file`, `fileName`, `fileSize`). Per-plan size caps enforced server-side. Requires EDIT access on the task. See `tasks.md` for the full file-upload pattern.
- **`voting` / `multivote` vote casting:** `POST` and `DELETE /v1/tasks/{taskIdentifier}/custom-field/{customFieldIdentifier}/votes`. Auto-creates the CFV record if needed. Requires COMMENT access. Setting a string via the `customFields` map does **not** cast a vote — it just stores a string value.

The `relationship` custom-field **type** is distinct from task-to-task **relationships**. Task-to-task links between tasks (with a typed `RelationshipType`) live at `POST /v1/tasks/lite/{ref}/relationships` — that's a different feature, not a custom-field value.
