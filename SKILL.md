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

## Topic map — READ the reference for any surface you touch

**This is not optional.** Each reference file below documents non-obvious wire shapes, validator quirks, and footguns that have already broken real callers. SKILL.md is orientation — it does **not** restate what's in the references. Before you write code that hits an endpoint, **open the matching reference and read the relevant section in full.** Skimming the table is not reading the reference.

Rule of thumb: if you're about to construct a request body, set custom-field metadata, choose a `columnIdentifier`, format a date, or pick a label value — **stop and load the reference first.** The footguns are specifically the things you'd guess wrong from training data: labels accept identifiers OR display values (not arbitrary strings); dates need ISO 8601 (PG `timestamptz::text` doesn't qualify); view custom-field references (`groupBy`, `sortBy`, `columnIdentifier`) take the **raw** custom-field identifier (`AHs6MtrAIq`), NOT `cf_<id>` and not the display name; custom-field icons come from `emoji` metadata, not from emoji prefixes in the name.

| Reference | **Must read before** |
|---|---|
| [auth.md](references/auth.md) | Sending the first request with a new key, debugging any 401/403, picking scopes |
| [errors.md](references/errors.md) | Writing any error-handling branch — PM has nested envelopes, FR/Wiki are flat; `validOptions` retry contract |
| [tasks.md](references/tasks.md) | Any task create/update, comments, relationships, attachments, recurrence, time entries, `Idempotency-Key` |
| [task-types.md](references/task-types.md) | Anything that sets or relies on `taskType` (3-level cascade, no workspace fallback, untyped is valid) |
| [wiki.md](references/wiki.md) | Wiki pages list/read/write, Markdown vs TipTap, search query syntax |
| [roadmarq.md](references/roadmarq.md) | Feature requests + bugs — short-ID prefixes, lite verbs (`/votes` not `/vote`), `?workspaceIdentifier=` rule |
| [webhooks.md](references/webhooks.md) | Subscriptions, payload envelope, signature verification, retry schedule, WebSocket ticket flow |
| [custom-fields.md](references/custom-fields.md) | **MANDATORY for any custom-field work.** Per-type value shapes (labels, dropdown, date, money, file, …), `emoji`/`color` metadata, formula + rollup configs. Skipping this is the #1 cause of silent validation failures and ugly default-icon UI. |
| [views.md](references/views.md) | **MANDATORY for any view work.** POST accepts `columns` + `filters` atomically with the create. For custom-field references in `groupBy` / `sortBy` / `columns[].columnIdentifier`, use the **raw** custom-field id (`AHs6MtrAIq`) — NOT `cf_<id>`. `columnIdentifier` 400s on `cf_` prefix; `groupBy`/`sortBy` silently accept it but the frontend won't render the grouping. |
| [dashboards-forms.md](references/dashboards-forms.md) | `/v1/dashboard/lite`, form admin (config + submissions + CSV export), public form submission |
| [sprints.md](references/sprints.md) | Sprint groups, sprint lifecycle, membership, burndown — non-lite endpoint shapes |
| [imports.md](references/imports.md) | CSV import: preview → confirm flow, polling job status |
| [admin.md](references/admin.md) | Plan-quota 402, status/priority/level CRUD per scope, teams, whiteboard collab token |
| [members.md](references/members.md) | Workspace member list/role/remove, invitations |
| [notifications.md](references/notifications.md) | List + count + mark-read; page-style pagination quirk |
| [filters.md](references/filters.md) | Saved filters per list, per user; numeric `Long id`; no "apply saved filter" on lite search |

When in doubt, fetch the catalog tag detail first — it's the deployed contract — and **then** read the reference that covers it.

## Pre-flight checklist before any write

Walk this before you start typing the request body. If you can't answer one, the corresponding reference covers it:

1. **Scope** — does the API key have the scope this endpoint requires? Confirm with `GET /v1/api-keys/current`. ([auth.md](references/auth.md))
2. **Identifiers vs names** — which fields take which? Lite is *enum-ish + people use names; structural references stay as identifiers.* ([SKILL.md "What lite endpoints actually accept"](#what-lite-endpoints-actually-accept))
3. **Per-type value shapes** — for custom-field values, look up the type in [custom-fields.md](references/custom-fields.md). Date → ISO 8601 (not `2026-05-08 00:00:00+00`). Labels → option display value OR identifier. Money → number or `{amount, currency}`. File/people/task have their own shapes.
4. **Visual metadata** — for any list, custom-field, or workspace structure you create, set `icon`/`emoji` + `color` at creation time. Skipping them is what produces the "everything is a gray circle" UI. ([SKILL.md "Structure creation defaults"](#structure-creation-defaults))
5. **View columns** — `groupBy` / `sortBy` / `columns[].columnIdentifier` all take system field names (`status`, `priority`, `dueDate`, …) or the **raw** custom-field identifier (`AHs6MtrAIq`). **Never** `cf_<id>` and never display names. `columnIdentifier` rejects `cf_<id>` with 400; `groupBy`/`sortBy` silently accept it and then the frontend can't resolve it, so grouping/sorting fails to render. Use `/lite/context` to resolve raw ids. ([views.md](references/views.md))
6. **Idempotency** — for create endpoints clients may retry, send `Idempotency-Key`. ([tasks.md](references/tasks.md))

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

**Lite and non-lite write paths converge.** For task writes, the lite endpoint resolves names → identifiers and then forwards the request to the same underlying service the non-lite endpoint uses (`LiteTaskRequestMapper` → `ReferenceResolver.resolveCustomFields` → rich path). Per-type value validation (handlers in `service/customfield/handler/`) runs once, after convergence. So a `customFields` value shape that works in lite works identically in non-lite, and vice versa. Choose the surface based on what your caller has on hand (names vs. UUIDs), not based on which "features" you think each supports — they support the same writes.

## Structure creation defaults

**Set visual metadata at creation time.** Every creatable structure on the Dutify side has a separate `icon`/`emoji` + `color` slot. Leaving these unset doesn't produce a tasteful fallback — it produces the default-by-type icon, which is usually a generic gray circle and looks broken next to user-created content. Whenever you know the semantic purpose of the thing you're creating, fill them in. Don't put emoji or icon text in the name itself.

**Always prefer an emoji over a structural icon.** Emojis carry meaning at a glance (🔥 = severity, 🚀 = launch, 💰 = budget) and match how humans skim a column header. Structural icons (`Hash`, `Stack`, `FlowArrow`) are abstract and look more like a CAD diagram than a label — fall back to them **only** when no emoji name fits the field's semantic purpose.

Look up the valid keys with one HTTP call (the endpoint is `@PermitAll` — no scope check, no workspace binding):

```http
GET https://dutify.ai/mp/api/v1/custom-field-icon-options
```

Response shape (`CustomFieldIconOptionsDTO`):

```json
{
  "emojiNames":  ["rocket", "fire", "direct_hit", "white_check_mark", "moneybag", "pushpin", "tada", "bulb", "..." ],
  "iconNames":   ["CalendarBlank", "Hash", "Star", "Wallet", "TagSimple", "FlowArrow", "Stack", "..." ],
  "defaultIconsByFieldType": {
    "dropdown": "CaretCircleDown",
    "labels":   "TagSimple",
    "date":     "CalendarBlank",
    "number":   "Hash",
    "money":    "Wallet",
    "...":      "..."
  }
}
```

`emojiNames` and `iconNames` are flat lists of accepted string keys (~120 emojis, ~125 icons — same set the in-app picker uses). `defaultIconsByFieldType` is what the frontend falls back to when you leave `emoji` unset — that's where the "everything looks the same" comes from. Pick from `emojiNames` first; only reach into `iconNames` if nothing semantic fits.

**Lists** — `POST /v1/lists/lite` takes `icon` + `color`:

```json
{
  "workspace": "ws_abc",
  "space": "Engineering",
  "folder": "Q2 Roadmap",
  "name": "Launch Tasks",
  "icon": "rocket",
  "color": "#4A90D9"
}
```

**Custom fields** — `POST /v1/custom-fields/lite` takes `emoji` + `color`. **This is the one agents miss most.** A column without `emoji` set renders as a default-by-type icon — usually a circle. If you're scripting field creation from a list spec, map each field's semantic purpose to an icon key in the same loop where you set the name:

```json
{
  "workspace": "ws_abc",
  "name": "Severity",
  "type": "dropdown",
  "emoji": "fire",
  "color": "#FF4444",
  "scope": "list",
  "scopeName": "Bug List",
  "options": [{"value": "P1"}, {"value": "P2"}]
}
```

Common mappings: severity/urgency → `fire`; target/goal → `direct_hit`; launch/release → `rocket`; approval/done → `white_check_mark`; location → `pushpin`; budget/money → `moneybag`; date/deadline → `calendar` (or icon `CalendarBlank`). When in doubt, read [custom-fields.md](references/custom-fields.md) §"Manage custom-field definitions".

**Spaces / workspaces** — also accept icon + color at create time; see the catalog `Spaces` / `Workspaces` tags.

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
