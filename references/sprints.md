# Sprints (non-lite)

There is no `(Lite)` tag for sprints — every endpoint takes identifiers. Read sprint info via the rich `Sprints` and `Sprint Groups` tags in the catalog.

## Sprint groups

A sprint group is the per-space container that owns sprint cadence config. Path:

```http
GET    /v1/spaces/{spaceIdentifier}/sprint-groups
POST   /v1/spaces/{spaceIdentifier}/sprint-groups
GET    /v1/sprint-groups/{groupIdentifier}
PATCH  /v1/sprint-groups/{groupIdentifier}
DELETE /v1/sprint-groups/{groupIdentifier}
```

Most spaces have one default sprint group; you only need a second if the space runs parallel cadences.

## Sprint lifecycle

```http
POST   /v1/sprint-groups/{groupIdentifier}/sprints                    # create
GET    /v1/sprints/{sprintIdentifier}                                 # read (with task statistics)
PUT    /v1/sprints/{sprintIdentifier}                                 # update name / goal / dates
DELETE /v1/sprints/{sprintIdentifier}                                 # soft-delete; tasks lose their sprint association

POST   /v1/sprints/{sprintIdentifier}/start                           # NOT_STARTED → IN_PROGRESS
POST   /v1/sprints/{sprintIdentifier}/complete                        # IN_PROGRESS → DONE; SprintCompleteRequest body controls rollover
```

State machine: `NOT_STARTED` → `IN_PROGRESS` → `DONE`. Only **one** active sprint per group at a time — starting a second one with another active will fail.

## Sprint membership

```http
POST   /v1/sprints/{sprintIdentifier}/tasks/add                       # body: SprintTasksRequest with task identifiers
POST   /v1/sprints/{sprintIdentifier}/tasks/remove                    # body: same shape
GET    /v1/sprints/{sprintIdentifier}/tasks                           # list TaskDTO
```

Tasks added to a sprint must belong to the **same space** as the sprint group; cross-space membership is rejected. From the lite side, you can also assign a task to a sprint by PATCHing it: `PATCH /v1/tasks/lite/{ref}` with `{"sprintIdentifier": "<id>"}` (or `null` to remove).

## Per-list option lookup + burndown

```http
GET /v1/sprints/{sprintIdentifier}/task-options                      # effective statuses + priorities per list (the sprint's tasks may span lists)
GET /v1/sprints/{sprintIdentifier}/burndown                          # daily SprintSnapshot rows for burndown / burnup charts
```

`task-options` returns a `Map<listIdentifier, ListTaskOptionsDTO>` so a sprint board can show per-task dropdowns scoped to each task's own list (which may have status/priority overrides).

`burndown` returns daily snapshots — use these to render burndown/burnup charts without having to re-aggregate task history yourself.

## Required scope

`sprints:read` for GETs; `sprints:write` for everything else. Sprints do not have their own dedicated `(Lite)` resolver — names won't resolve here, pass identifiers everywhere.
