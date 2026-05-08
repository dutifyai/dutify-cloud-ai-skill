# Admin surfaces — quotas, teams, status/priority CRUD, whiteboards

The lower-traffic admin surfaces. Most agents won't touch these, but they're there if you need them.

## Plan / quota errors (`QUOTA_EXCEEDED`)

Some endpoints sit behind a paywall. A 402 + `QUOTA_EXCEEDED` is what you get when the workspace's plan doesn't cover the requested feature. Real triggers (from `PlanQuotaService`):

| Feature gated | Required plan |
|---|---|
| Public sharing of tasks/forms | Pro and above |
| Specific dashboard widgets (varies per widget) | Pro and above |
| Bulk operations (e.g. `POST /v1/tasks/bulk/*`) | Business and above |
| Custom roles & permissions (`workspace-access-levels`) | Business and above |
| Full API export (folder/space/workspace-wide CSV) | Enterprise only |

The 402 response body is the regular `ErrorResponse` shape with `errorCode: "QUOTA_EXCEEDED"`. No `validOptions` — there's nothing to retry; you have to upgrade or not call. Surface the message to the user verbatim; it tells them which plan unlocks the feature.

## Status / priority / level CRUD

Statuses, priorities, and levels live **per-list / per-space** with hierarchical inheritance — there is no workspace-level "global statuses" table. Manage them at the level they're authored at:

```http
# Statuses (per-list, with optional inheritance flag)
GET    /v1/lists/{listIdentifier}/statuses           # effective set (with parent fallback)
GET    /v1/lists/{listIdentifier}/statuses/own       # only this list's own rows (no inheritance)
POST   /v1/lists/{listIdentifier}/statuses
PATCH  /v1/lists/{listIdentifier}/statuses/{statusIdentifier}
DELETE /v1/lists/{listIdentifier}/statuses/{statusIdentifier}
POST   /v1/lists/{listIdentifier}/statuses/reorder
POST   /v1/lists/{listIdentifier}/statuses/reassign  # reassign tasks before deleting a status

# Priorities — same structure, swap "statuses" for "priorities"
# Levels — only at /v1/spaces/{identifier}/task-levels (levels don't exist on lists)

# At space scope, the same ops live at /v1/spaces/{identifier}/{statuses,priorities,task-levels}
# At workspace scope, /v1/workspaces/{identifier}/{statuses,priorities}
```

Each status carries a `type` field of `ACTIVE` / `DONE` / `CLOSED` (see SKILL.md). Reordering uses `/reorder` with a body that lists identifiers in the new order. Deleting a status with assigned tasks goes through the `/reassign` endpoint to migrate the tasks first.

## Teams

```http
POST   /v1/workspaces/{workspaceIdentifier}/teams              # create
GET    /v1/workspaces/{workspaceIdentifier}/teams              # list
GET    /teams/{identifier}                                      # detail (note: NO /v1 prefix on this resource)
PATCH  /teams/{identifier}
DELETE /teams/{identifier}
POST   /teams/{identifier}/members                              # add member by uuid/email
DELETE /teams/{identifier}/members/{memberIdentifier}
```

`TeamResource` is path-prefixed `/teams` (without `/v1`) — slightly inconsistent with the rest of the API. Scope: `teams:read` / `teams:write`.

Teams are used in access-control: a private space/list can grant access to a team rather than per-user.

## Whiteboards (collab token only)

The whiteboard editor is a Hocuspocus / Yjs surface — beyond what an HTTP-only agent can drive. The HTTP API exposes only the parts you'd want to script:

```http
GET  /v1/views/{viewIdentifier}/collab/token            # short-lived JWT to authenticate to the Hocuspocus WS
GET  /v1/views/{viewIdentifier}/whiteboard-comments     # list comments on whiteboard objects
POST /v1/views/{viewIdentifier}/whiteboard-comments
```

The collab token is a JWT consumed by the `pm-collab` Hocuspocus server (`wss://pm-collab.dutify.ai`) — get the token from the HTTP API, then connect to the WS with it. Editing actual whiteboard content via the HTTP API is not supported; do that through the Yjs WebSocket if you really need it.

Templates are at `/v1/whiteboard-templates` (list/CRUD) — useful when seeding a workspace with starter whiteboards.

## What's NOT here

- Plan upgrades / billing — `/v1/billing/*` exists but billing operations are gated behind the Stripe redirect flow; agents can read `GET /v1/workspaces/{ws}/billing/status` but they can't *change* the plan via the API.
- Activity log writes — read-only by design (writes happen as side effects of other operations).
- Keycloak user management — Dutify proxies a small subset (`/v1/users/current/*`); user CRUD lives in the Keycloak admin console.
