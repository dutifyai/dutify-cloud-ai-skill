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

## Columns are selected by `PUT`, not initial `POST`

The Lite create endpoint creates the view with default columns. To choose visible columns, update the created view with `columns`. The list order is the display order. A column not present in the list is hidden.

When extracting desired columns from a user request, spreadsheet, import spec, or project description, keep header/custom-field names plain. Do **not** add emoji prefixes to names for visual icons; custom-field icons come from the field's separate `emoji` metadata (and `color`) or from the frontend's field-type default icon. Use `GET /v1/custom-field-icon-options` when you need supported icon/emoji keys.

```json
{
  "columns": [
    { "columnIdentifier": "title", "isMandatory": true, "fixed": true },
    { "columnIdentifier": "status", "isMandatory": true },
    { "columnIdentifier": "priority", "isMandatory": false },
    { "columnIdentifier": "cf_severity", "isMandatory": false }
  ]
}
```

`columnIdentifier` is either a system task field (`title`, `taskKey`, `assignees`, `dueDate`, `status`, `priority`, etc.) or a custom-field identifier available to that list/scope. Invalid identifiers return 400. Use `/lite/context` to get available custom-field identifiers.

Headers come from the underlying system/custom-field display names. For new custom fields that will be shown as columns, use names like `Severity` or `Target Date`; set `emoji` / `color` metadata separately when an explicit icon is needed.

`isMandatory` is serialized with that exact JSON property name. `fixed: true` pins/fixes the column when the frontend supports it; omit `fixed` otherwise.

## Direct HTTP flow

For a fully customized view over HTTP, do two calls:

1. `POST /v1/views/lite` with `scope`, `scopeIdentifier`, `name`, `type`, and optional `groupBy` / `sortBy` / `sortDirection`.
2. `PUT /v1/views/lite/{identifier}` with `columns` and/or `filters`.

`groupBy` and `sortBy` take **column identifiers**, same set as `columnIdentifier` above (system field name like `title`, `status`, `priority`, `dueDate`, or `cf_xxx` for a custom field — resolvable via `/lite/context`). Display names return 400; the call does not silently fall back, so don't swallow the create response (`.catch(() => null)` will hide a real validation error). `sortDirection` is `"asc"` or `"desc"`.

On `PUT /v1/views/lite/{identifier}`, every field is independently optional — `null` (or absent) means **no change**. When `columns` is provided, the list **fully replaces** the current column order (entries must reference valid column identifiers or the call 400s). When `filters` is provided, the list **fully replaces** the current filters; an empty array `[]` clears them all. `filters` is a `List<FilterGroupDTO>` — each group has its own conditions and a `precedingLogic` (`AND`/`OR`) for how it combines with the previous group; see the catalog tag detail for the full `FilterGroupDTO` schema. The same merge-vs-replace rule applies to `groupBy`/`sortBy`: an empty string (not `null`) clears the setting.

Lite `GET` / list responses are intentionally flat and do not include `data.columnOrder`, so verify detailed column state through the rich resource-view endpoint if needed.

## MCP flow

The `dutify-mcp` tool `pm_create_view` accepts `columns` and `filters` even though Lite create does not. The MCP server performs the two-step flow internally: create the view, then immediately `PUT` the `columns` / `filters` to the created identifier. If using direct HTTP instead of MCP, do the two calls yourself.
