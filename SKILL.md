---
name: dutify-api
description: Use the Dutify HTTP "lite" APIs directly. Discover endpoints via the aggregated catalog at https://dutify.ai/mp/api/v1/api-catalog (which spans Project Management, Wiki/Codexum, and Feature Requests/Roadmarq), drill into a tag with /api-catalog/{tag} for full operation + schema detail, then call the endpoint with an X-API-Key header. Use this skill whenever the user wants to query, create, or update Dutify tasks, wiki pages, spaces, lists, feature requests, bugs, comments, sprints, custom fields, or any other Dutify resource — even when they don't say "API" explicitly. Prefer this over guessing endpoints from memory; the catalog is the source of truth.
---

# Dutify Light API

Direct HTTP access to the Dutify suite (Project Management, Wiki, Feature Requests) via the "lite" APIs that take human-readable names instead of UUIDs.

## When to use this skill

The user is asking to do something against a Dutify workspace. Typical signals:

- "create a task in the Marketing space called X"
- "list bugs assigned to alex@dutify.ai"
- "what wiki pages live under the Engineering space"
- "bump the priority of PROJ-42 to High"
- "what does the lite tasks API look like" / "show me the schema for X"

## Topic map — load only what you need

This SKILL.md covers the orientation. Each focused reference below is loaded on demand:

| Reference | When to read |
|---|---|
| [auth.md](references/auth.md) | API key header, scopes, bound workspace, `/v1/users/current/workspaces` |
| [errors.md](references/errors.md) | Error envelopes (PM nested vs FR/Wiki flat), error-code vocabulary, rate-limit response, network errors |
| [tasks.md](references/tasks.md) | `/lite/context`, search, create, update, comments, relationships, attachments, recurrence, time entries, `Idempotency-Key`, non-lite TaskCreationRequest, cross-workspace move |
| [task-types.md](references/task-types.md) | Catalogue, the 9 SYSTEM rows, cascade default (3 levels — list→folder→space, no workspace fallback), single + bulk type changes, default-at-level setters, reassignment-on-delete |
| [wiki.md](references/wiki.md) | Wiki pages list/read/write, Markdown vs TipTap, search query syntax |
| [roadmarq.md](references/roadmarq.md) | Feature requests + bugs, per-board short-ID prefixes, lite verbs (`/votes` not `/vote`, `/moderation` not `/moderate`), `?workspaceIdentifier=` query rule |
| [webhooks.md](references/webhooks.md) | Subscriptions, payload envelope, `X-Webhook-Signature-256`, retry schedule, WebSocket ticket flow, activity log read shape |
| [custom-fields.md](references/custom-fields.md) | Custom-field CRUD (lite), value-setting on tasks, formula configuration (structured JSON), rollup configuration (sourceList + aggregator) |
| [views.md](references/views.md) | Views (Lite): create/list/get/update/clone, column visibility/order, filters, MCP create behavior |
| [dashboards-forms.md](references/dashboards-forms.md) | `/v1/dashboard/lite`, form admin (config + submissions + CSV export), public form submission |
| [sprints.md](references/sprints.md) | Sprint groups, sprint lifecycle (start/complete/rollover), membership, burndown — non-lite |
| [imports.md](references/imports.md) | CSV import: preview → confirm flow, one-shot upload, polling job status |
| [admin.md](references/admin.md) | Plan-quota errors (402 `QUOTA_EXCEEDED`), status / priority / level CRUD per scope, teams, whiteboard collab token |
| [members.md](references/members.md) | Workspace member list / role / remove, invitations send / cancel / accept / decline |
| [notifications.md](references/notifications.md) | List + count + mark-read; page-style pagination quirk; `data` is a real JSON object (unlike activity log) |
| [filters.md](references/filters.md) | Saved filters per list, per user; numeric `Long id`; no "apply saved filter" endpoint on lite search |

When in doubt, fetch the catalog tag detail first — it's the deployed contract.

## Core idea: discover, then call

The PM backend exposes a single aggregated catalog that lists every endpoint across all three backends (PM, Wiki/Codexum, Roadmarq). Always start there — never assume an endpoint shape from memory, because the catalog is what's actually deployed.

Three steps for any task:

1. **List tags** — `GET https://dutify.ai/mp/api/v1/api-catalog`. Returns the three services and their tags. Pick the tag closest to what the user wants.
2. **Get tag detail** — `GET https://dutify.ai/mp/api/v1/api-catalog/{tag}`. URL-encode tag names with spaces or parentheses (`Tasks (Lite)` → `Tasks%20%28Lite%29`). Returns `{tag, description, service, baseUrl, operations[], schemas{}}` — operations have `method`, `path`, `summary`, `description`, `parameters`, `requestBody`, `responses`; schemas resolve `$ref` values.
3. **Call the endpoint.** Send `X-API-Key: dk_live_…` and (for write endpoints) `Content-Type: application/json`. **Footgun:** the catalog's `path` field is *absolute from the host root* — it already includes the same prefix that's in `baseUrl`. So `path` looks like `/api/wiki/v1/...` and `baseUrl` is `https://dutify.ai/api/wiki`; naive `{baseUrl}{path}` concatenation produces `https://dutify.ai/api/wiki/api/wiki/v1/...` and 404s. Either use `https://dutify.ai` + `path`, or strip the duplicated prefix from `path` before concatenating with `baseUrl`. The `baseUrl` field is mostly informational — telling you which backend the tag lives on, not how to compose the URL.

There's also `GET /api-catalog/detailed` if you want the full thing in one shot, but it's large — prefer the per-tag endpoint when you know the tag.

## What the catalog covers

The aggregated catalog at `https://dutify.ai/mp/api/v1/api-catalog` covers **all three** Dutify backends. `ApiCatalogService` aggregates the OpenAPI specs of PM, Codexum (Wiki), and Roadmarq (Feature Requests & Bugs) and exposes them under one tag list. Each tag's detail response carries a `service` field that names the source (`Project Management`, `Codexum`, `Roadmarq`) and a `baseUrl` field that names the path prefix on `dutify.ai`.

| Service | `service` value | Base URL | Tag examples |
|---|---|---|---|
| Project Management | `Project Management` | `https://dutify.ai/mp/api` | Tasks, Tasks (Lite), Spaces, Lists, Sprints, Workspaces, Comments (Lite), Search (Lite), Context (Lite), Views (Lite), Task Types, Webhooks, … |
| Wiki | `Codexum` (the internal codename — same product as the user-facing "Wiki") | `https://dutify.ai/api/wiki` | Wiki Pages, Wiki Pages (Lite), Wiki Spaces, Wiki Spaces (Lite), Wiki Search, Wiki Comments, … |
| Feature Requests + Bugs | `Roadmarq` | `https://dutify.ai/api/roadmarq` | Boards (Lite), Requests (Lite), Bugs (Lite), Categories, Bug Status Levels, … |

Always read `baseUrl` from the tag-detail response when composing URLs; don't hard-code. The user-facing host is always `dutify.ai`; only the path prefix differs per service.

## Auth model — quick

Every data-access call needs `X-API-Key: dk_live_<rest>`. Keys are workspace-bound (one key, one workspace) and scope-gated (per resource family — see `auth.md`). The scope filter runs **before** any name resolution, so passing a workspace **name** in a path slot when the key is bound to the workspace **identifier** 403s — always use the identifier in scripts. Full table of scopes + auth failure modes in [auth.md](references/auth.md).

## What lite endpoints actually accept

The `(Lite)` tags are the agent-friendly surface, but "lite" doesn't mean "everything is a name." It means: *enum-ish fields and people get name/email lookups; structural references still need identifiers.*

| Kind of input | What lite endpoints accept | Examples |
|---|---|---|
| Status, priority, level, task type, custom field name | **Name — exact match, case-sensitive, no trimming.** "in progress" does NOT resolve to "In Progress". The resolver fails with `validOptions` listing the available names; pick one verbatim and retry. | `"In Progress"`, `"High"`, `"Bug"` |
| `taskType` on create | **Name OR omit entirely.** When omitted, the new task inherits the closest non-null default across only three levels — `list → folder → space`. There is **no workspace-level default**: if none of those three has a default set, the task is created **untyped** (`taskType: null` in the response). That's a valid persistent state, not an error. | `"Bug"` or absent |
| `taskType` on `PATCH /tasks/lite/{ref}` | **Name OR explicit `null`.** Sending `null` clears the type and makes the task untyped (PATCH tri-state semantics). | `"Bug"`, `null` |
| `description` on tasks | **Rich text** (HTML-ish content). Plain strings render fine but rich markup like `<p>`, `<strong>`, `<a>` is preserved. | `"Outline goals and OKRs"` |
| `parent` (subtask) | **Identifier OR short key**, capped at depth **10** by default (`dutify.limits.max-task-nesting-depth`). Going deeper returns 400 with a depth-limit message. | `"PROJ-42"` |
| Status types | The status's `type` field is one of `ACTIVE` / `DONE` / `CLOSED` — three discrete values, not a free string. `DONE` tasks stay visible by default; **`CLOSED` tasks are hidden unless `?includeClosed=true`** on search. "Done ≠ Closed" — read the type, not just the name. | — |
| Tags lifecycle | There is **no** `/v1/tags/lite` CRUD. Tags are created by inline name use (`tags: ["urgent"]`) on task create/update. Renaming or deleting a tag goes through the non-lite Tags API. | — |
| Custom field values | **Name** (option label, tag name, etc.) — same exact-match rules as above. | `"Q4 OKR"` |
| Tags | **Name**. Auto-created if missing (default gray colors). | `["urgent", "Q4"]` |
| Assignees, mentions | **Email**. | `"alex@dutify.ai"` |
| Task references (`parent`, `nextTo`, the path `{ref}` on get/update/delete) | **Identifier OR short key** (resolved by `getByIdentifierOrKey`). NOT a task title. | `"PROJ-42"` or a UUID |
| List, sprint, space, folder, workspace, custom-field IDs (when used as request fields, not `wsRef` path) | **Identifier**. Resolve names via `/lite/context` first. | `"lst_abc123"` |

So the typical lite write flow is two calls: `GET /lite/context` to resolve any space/list/sprint **names** to identifiers, then the actual `POST/PATCH /lite/...` with the identifier in `list`/`sprintIdentifier` and names everywhere else. When the user only knows names ("create a task in Marketing/Backlog"), this is unavoidable.

When matching fails, the error body includes `validOptions` — see [errors.md](references/errors.md) for the full contract.

Non-lite tags (e.g. plain `Tasks`) require identifiers everywhere and are mostly for the Dutify frontends. Prefer `(Lite)` unless the user specifically needs UUID-level control.

## Pagination

Lite list/search endpoints use cursor pagination only — `limit` (default 50, max **200** for `/v1/tasks/lite/search`; defaults vary slightly per endpoint, the catalog `parameters` block has the authoritative numbers) plus an opaque `cursor`. The response wrapper is `LitePageResponse` with shape `{items: [...], nextCursor: "..."}`. There is **no** `total` count and no `offset` — paginate by passing back the previous response's `nextCursor` until it comes back `null`.

## Calling pattern (Python)

Pseudocode that works in any language with an HTTP client. **Don't trust the field names below verbatim — get them from the catalog tag detail.** This snippet uses field names that match the deployed `Tasks (Lite)` schema at the time of writing, but the catalog is the source of truth:

```python
import requests, urllib.parse, os

API_KEY = os.environ["DUTIFY_API_KEY"]
CATALOG = "https://dutify.ai/mp/api/v1/api-catalog"

# 1. Pick a tag
tags = requests.get(CATALOG).json()

# 2. Drill in to discover exact field names + which fields take names vs identifiers
tag = "Tasks (Lite)"
detail = requests.get(f"{CATALOG}/{urllib.parse.quote(tag)}").json()
base_url = detail["baseUrl"]

# 3. Resolve any structural references to identifiers first (lite tasks need a list IDENTIFIER,
#    not a list name — see "What lite endpoints actually accept" above).
#    NB: with API-key auth, the {wsRef} path slot MUST be the workspace IDENTIFIER (e.g.
#    'ws_abc123'), not the display name. The ApiKeyScopeFilter compares it byte-for-byte
#    against the key's bound workspace identifier and 403s on mismatch — even if the
#    name would have resolved to the right workspace under JWT auth.
WORKSPACE_ID = os.environ["DUTIFY_WORKSPACE_IDENTIFIER"]   # e.g. "ws_abc123"
ctx = requests.get(
    f"https://dutify.ai/mp/api/v1/workspaces/{WORKSPACE_ID}/lite/context",
    headers={"X-API-Key": API_KEY},
).json()
list_id = next(
    l["identifier"]
    for s in ctx["spaces"] if s["name"].lower() == "marketing"
    for l in s.get("lists", []) + [l for f in s.get("folders", []) for l in f.get("lists", [])]
    if l["name"].lower() == "backlog"
)

# 4. Now call the create endpoint — names for status/priority/assignees, identifier for list.
#    Note: use `https://dutify.ai` + the catalog's `path` field. Don't concatenate
#    base_url with `path` — they overlap.
resp = requests.post(
    "https://dutify.ai/mp/api/v1/tasks/lite",
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    json={
        "title": "Write Q4 plan",   # not "name"
        "list": list_id,            # identifier, not "Backlog"
        "status": "To Do",          # name (resolved server-side)
        "priority": "High",         # name
        "assignees": ["alex@dutify.ai"],
    },
)
resp.raise_for_status()
print(resp.json())
```

If the host language already has an HTTP idiom (Node `fetch`, `curl`, `axios`, `httpx`), use that — the structure is the same.

## Putting it together — a worked example

A "set up a new sprint with three tasks" flow needs to mix lite + non-lite because there's no `(Lite)` tag for sprints. End-to-end:

1. `GET /v1/workspaces/{ws}/lite/context` → confirm the space and list exist; pull their identifiers.
2. `GET /v1/spaces/{spaceIdentifier}/sprint-groups` → pick the sprint group identifier (or list one and create if missing — both non-lite).
3. `POST /v1/sprints` with `{sprintGroupIdentifier, name, startDate, endDate, …}` (non-lite — see the catalog `Sprints` tag for the exact body) → response carries the new sprint's identifier.
4. `POST /v1/tasks/lite × 3` to create the tasks. Note: `LiteTaskCreationRequest` has no sprint field; you put the task in a list via `list: <listIdentifier>` and assign it to the sprint in step 5.
5. For each new task, `PATCH /v1/tasks/lite/{shortKey}?workspace={wsId}` with `{ "sprintIdentifier": "<sprintIdentifier>" }` (the lite PATCH does take `sprintIdentifier`). Pass `null` instead to remove a task from a sprint.
6. To verify, hit `GET /v1/sprints/{sprintIdentifier}/tasks` (non-lite — the lite search endpoint has no sprint filter).

If any step fails with a `validOptions` body, retry once with the corrected name. If it fails again, surface the error.
