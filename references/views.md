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

`isMandatory` is serialized with that exact JSON property name. `fixed: true` pins/fixes the column when the frontend supports it; omit `fixed` otherwise.

## Direct HTTP flow

For a fully customized view over HTTP, do two calls:

1. `POST /v1/views/lite` with `scope`, `scopeIdentifier`, `name`, `type`, and optional `groupBy` / `sortBy` / `sortDirection`.
2. `PUT /v1/views/lite/{identifier}` with `columns` and/or `filters`.

Lite `GET` / list responses are intentionally flat and do not include `data.columnOrder`, so verify detailed column state through the rich resource-view endpoint if needed.

## MCP flow

The `dutify-mcp` tool `pm_create_view` accepts `columns` and `filters` even though Lite create does not. The MCP server performs the two-step flow internally: create the view, then immediately `PUT` the `columns` / `filters` to the created identifier. If using direct HTTP instead of MCP, do the two calls yourself.
