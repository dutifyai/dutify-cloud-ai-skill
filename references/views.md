# Views — Lite API and MCP behavior

Tag: **Views (Lite)**. Views are scoped to `workspace`, `space`, `folder`, or `list`. Non-workspace scopes need the parent identifier (`scopeIdentifier`), so resolve names through `GET /v1/workspaces/{wsIdentifier}/lite/context` first.

## Endpoints

```text
GET    https://dutify.ai/mp/api/v1/views/lite?scope=list&scopeIdentifier=lst_...
GET    https://dutify.ai/mp/api/v1/views/lite/{viewIdentifier}
POST   https://dutify.ai/mp/api/v1/views/lite
PUT    https://dutify.ai/mp/api/v1/views/lite/{viewIdentifier}
DELETE https://dutify.ai/mp/api/v1/views/lite/{viewIdentifier}
POST   https://dutify.ai/mp/api/v1/views/lite/{viewIdentifier}/clone
```

Types accepted by Lite create: `list`, `board`, `table`, `dashboard`, `gantt`, `calendar`, `gallery`. `form` and `whiteboard` use richer/non-lite surfaces.

## One call for create, atomic with columns + filters

`POST /v1/views/lite` accepts the full view in a single request: structural fields plus `groupBy`, `sortBy`, `sortDirection`, `columns`, and `filters`. The body shape is `LiteViewCreationRequest`:

```json
{
  "scope": "list",
  "scopeIdentifier": "lst_abc",
  "name": "Sprint Board",
  "type": "board",
  "isPrivate": false,
  "groupBy": "status",
  "sortBy": "dueDate",
  "sortDirection": "asc",
  "columns": [
    { "columnIdentifier": "title", "isMandatory": true, "fixed": true },
    { "columnIdentifier": "status", "isMandatory": true },
    { "columnIdentifier": "priority", "isMandatory": false },
    { "columnIdentifier": "AHs6MtrAIq", "isMandatory": false }
  ],
  "filters": [
    {
      "precedingLogic": "AND",
      "filters": [
        { "field": "status", "operator": "equals", "value": "Open" }
      ]
    }
  ]
}
```

The whole thing runs in one transaction on the server. If any part fails — invalid `columnIdentifier`, bad filter shape, scope/type incompatibility — the entire create rolls back and you get a 400 with no orphan view in the database. Receiving `201` means the view exists and is fully configured the way you asked.

This is true for **both** the direct HTTP path and the MCP `pm_create_view` tool — same single-request contract. (Pre-existing callers that POSTed only structural fields and then PUT columns/filters still work; the PUT path is unchanged.)

## Identifier rules — `groupBy`, `sortBy`, `columnIdentifier`

All three take the **same** form everywhere:

- **System task fields:** bare name. `title`, `taskKey`, `assignees`, `startDate`, `dueDate`, `status`, `priority`, `timeEntries`.
- **Custom fields:** the **raw** custom-field identifier — `AHs6MtrAIq`. **NOT** `cf_AHs6MtrAIq`. **NOT** the display name.

Resolve the raw id from `GET /v1/workspaces/{ws}/lite/context` (the `identifier` field on each custom-field DTO is the raw form — store it as-is, don't prefix it).

### Why "raw id, not `cf_<id>`" matters

The validation surface is uneven across these three slots — `cf_<id>` fails differently on each, but it's never the right form:

| Slot | What happens with `cf_<id>` |
|---|---|
| `columns[].columnIdentifier` | **Loud failure.** Backend strictly validates against the system-field list and the resolved raw custom-field-id set. Returns 400 `"Invalid column identifier: cf_<x>. Must be either a system field or an existing custom field."` |
| `groupBy` / `sortBy` (lite POST + PUT body) | **Silent failure.** The lite write path doesn't validate these — the literal string `"cf_<x>"` is stored verbatim in `data.groupby` / `data.sortby`. The frontend then reads it back and looks up the custom field with `customFields.find(f => f.identifier === groupby)`. The lookup misses (because `f.identifier` is the raw id), so the view falls back to ungrouped/unsorted. You get 201 + a view that doesn't do what you asked. |
| Dedicated `/group-by` endpoint | Canonicalizes correctly. Validates `findByIdentifier(groupType)` against raw ids and stores `customField.getIdentifier()` (raw). Use this surface if you want write-time validation rather than the silently-tolerant lite slot. |

The "use raw id everywhere" rule keeps you out of all three traps. Don't swallow create responses (`.catch(() => null)` hides write paths that "succeed" but produce an unusable view).

Display names (`"Recommended Action"`, `"Score"`) are wrong on all three — 400 on `columns[]`, silent failure on `groupBy`/`sortBy`.

`sortDirection` is `"asc"` or `"desc"`.

When extracting desired columns from a user request, spreadsheet, import spec, or project description, keep header/custom-field names plain. Do **not** add emoji prefixes to names for visual icons; custom-field icons come from the field's separate `emoji` metadata (and `color`) — see [custom-fields.md](custom-fields.md) §"Picking the `emoji` value". `GET /v1/custom-field-icon-options` returns the supported icon/emoji keys.

`isMandatory` is serialized with that exact JSON property name. `fixed: true` pins/fixes the column when the frontend supports it; omit `fixed` otherwise.

## Editing an existing view with `PUT`

`PUT /v1/views/lite/{identifier}` updates an existing view. Every field is independently optional — `null` (or absent) means **no change**. The merge rules:

| Field | `null` / absent | empty (`""` or `[]`) | non-empty |
|---|---|---|---|
| `name`, `isPrivate`, `sortDirection` | no change | n/a | overwrite |
| `groupBy`, `sortBy` | no change | clears the setting (empty string) | overwrite |
| `columns` | no change | n/a (would hide every column — service rejects) | fully replaces current column order |
| `filters` | no change | `[]` clears all filters | fully replaces current filter groups |

`filters` is a `List<FilterGroupDTO>` — each group has its own conditions and a `precedingLogic` (`AND` / `OR`) for how it combines with the previous group. See the catalog tag detail for the full `FilterGroupDTO` schema. Invalid `columnIdentifier` entries on a PUT 400 the call, same as on POST.

Lite `GET` / list responses are intentionally flat and do not include `data.columnOrder` / `data.filterGroups`. If you need to confirm column or filter state after a write, use the rich resource-view endpoint (`GET /v1/resource-views/lists/{viewId}` for list-scoped views, and so on per scope).

## Deleting a view

`DELETE /v1/views/lite/{identifier}` removes a view. Requires EDIT on the view (same as PUT).

When a list/folder/space/workspace is created, the backend auto-seeds one **mandatory** view (`isMandatory: true`, name "List", type `list`) so the parent always has something to render. The old rule was "mandatory views can never be deleted" — that has been **relaxed**:

- **Mandatory view, ≥ 1 other view exists at the same parent** → `204 No Content`. The seed is deletable as long as it's not the last view standing.
- **Mandatory view, no siblings** → `409 Conflict` with `errorCode: "OPERATION_NOT_ALLOWED"` and a message indicating the last view cannot be deleted. The view stays. To actually replace the seed, POST your own view first, then DELETE the seed.
- **Non-mandatory view** → `204 No Content`, unchanged. (The count guard only kicks in for the mandatory marker; in practice every parent has exactly one mandatory view, so the "last view" check effectively prevents zeroing out the parent.)
- View not found → `404`.
- Missing EDIT → `403`.

This means the typical "I want my custom board as the only view" flow is: POST your board, DELETE the seed `List`. The first DELETE attempt before POSTing the replacement will 409 — that's the guard working.
