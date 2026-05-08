# Saved filters (per list, per user)

Filters are **per-list** + **user-scoped** — each user saves their own filter views on a list, and they're not shared across workspace members. Tag: **Filters** (non-lite). Resource path is identifier-style.

## Endpoints

```http
GET    https://dutify.ai/mp/api/v1/lists/{listIdentifier}/filters
POST   https://dutify.ai/mp/api/v1/lists/{listIdentifier}/filters
DELETE https://dutify.ai/mp/api/v1/lists/{listIdentifier}/filters/{id}
```

`{listIdentifier}` is the stable list identifier (`lst_…`). `{id}` is a **numeric `Long`**, NOT a stable identifier — same quirk as time-entries (see `tasks.md`). Pull the id from the GET response. There is no PATCH/PUT — to change a saved filter, DELETE then POST.

## Save a filter

```http
POST https://dutify.ai/mp/api/v1/lists/{listIdentifier}/filters
X-API-Key: dk_live_…
Content-Type: application/json

{
  "name": "My Active P1 bugs",
  "filterGroups": [
    {
      "logicalOperator": "AND",
      "filters": [
        { "field": "status",   "operator": "equals",      "value": "In Progress" },
        { "field": "priority", "operator": "equals",      "value": "Critical" },
        { "field": "taskType", "operator": "equals",      "value": "Bug" }
      ]
    }
  ]
}
```

`FilterGroupDTO` / per-row filter shape varies by field type — pull the canonical schema from the catalog's **Filters** tag detail. The exact operator vocabulary (`equals`, `contains`, `before`, `after`, `between`, `is_empty`, …) depends on the field's underlying type.

Returns the saved `FilterAggregateDTO` echoing back `id` (numeric Long), `filterGroups`, `name`, `createdAt`, `updatedAt`. Save the `id` if you'll want to delete this filter later.

## List a user's saved filters on a list

```http
GET /v1/lists/{listIdentifier}/filters
```

Returns `FilterAggregateDTO[]` — only the **calling user's** filters; another user's saved filters on the same list are not visible. There's no cross-user filter listing endpoint.

## Delete

```http
DELETE /v1/lists/{listIdentifier}/filters/{id}
```

Numeric id. Returns 204. Only the owner can delete their own filter.

## Apply a filter to a search?

There is **no** "apply saved filter" endpoint in the lite search. To run a saved filter you have to fetch the `filterGroups` from the saved filter and translate them into `/v1/tasks/lite/search` query params yourself — saved filters are a UI affordance, not a server-side query handle. The full (non-lite) `Tasks` API has a richer filter-aware search, but the lite tag does not currently accept the `FilterAggregateDTO` shape directly.

## Scope

`filters:read` for GET, `filters:write` for POST/DELETE.
