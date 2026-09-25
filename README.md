> This distribution now covers Hub, PM, Wiki and Roadmarq. Existing installations retain the skill name `dutify-api`; Hub-only installations can keep `dutify-hub-api`. Personal `du_live_` keys work across granted products; old workspace keys retain product boundaries. See [routing](references/routing.md) and [connector compatibility](references/connector.md). The combined MCP route is adopted only after its separate release and tool-list verification.

# dutify-api — Claude Code skill

Version `2026.09.25.1` adds capability-aware guidance for `dw_live_` workspace credentials. Read [integration keys](references/hub/integration-keys.md) before using that family; updating instructions does not deploy the authority or consumers. The authority makes issuance available immediately when deployed.

A Claude Code (and Claude.ai) skill that teaches an LLM how to use the Dutify HTTP API directly: discover endpoints via the aggregated catalog at `https://dutify.ai/mp/api/v1/api-catalog`, call the right "lite" tag with an `X-API-Key`, and self-correct on `validOptions` errors instead of guessing endpoint shapes from memory.

**Covers Hub, Project Management, Wiki/Codexum, and Roadmarq** in one skill. Hub uses its catalog at `https://dutify.ai/api/v1/api-catalog`; the existing Suite catalog aggregates PM, Wiki and Roadmarq.

## Install

### User-level (any Claude Code session, any project)

```bash
git clone https://github.com/dutifyai/dutify-cloud-ai-skill.git ~/.claude/skills/dutify-api
```

After install, restart your Claude Code session (or `/clear`). The skill will auto-load when a prompt mentions Dutify ("create a task in…", "list bugs assigned to…", "what wiki pages live under…", etc.) — no need to invoke it explicitly.

### Project-level (only when working inside one project)

```bash
git clone https://github.com/dutifyai/dutify-cloud-ai-skill.git <your-project>/.claude/skills/dutify-api
```

### Verify

After install:

```bash
ls ~/.claude/skills/dutify-api/SKILL.md          # should exist
ls ~/.claude/skills/dutify-api/references/       # product references
```

Then in any Claude Code session, ask "what's the URL for the Dutify task-type catalogue endpoint?" — Claude should pick up the skill, load `references/task-types.md`, and answer.

## How the skill is laid out

The skill is **topic-indexed** rather than a single big document. `SKILL.md` is the orientation file an LLM always sees; the product reference files in `references/` are loaded on-demand based on the topic map.

| File | Topic |
|---|---|
| `SKILL.md` | All-product routing and topic map; Suite conventions remain in `references/suite-guide.md` |
| `references/auth.md` | API key header, the 40+ scopes, bound workspace via `/v1/api-keys/current` |
| `references/errors.md` | PM nested vs FR/Wiki flat envelopes, error-code vocabulary, rate-limit response, network errors |
| `references/tasks.md` | `/lite/context`, search, create, update, comments, relationships, attachments, recurrence, time entries, `Idempotency-Key`, non-lite `TaskCreationRequest`, cross-workspace move |
| `references/task-types.md` | Catalogue, the 9 SYSTEM rows, cascade default (3 levels — list→folder→space, no workspace fallback), single + bulk type changes, default-at-level setters, reassignment-on-delete |
| `references/wiki.md` | Wiki pages list/read/write, Markdown vs TipTap body formats, search query syntax |
| `references/roadmarq.md` | Feature requests + bugs, per-board short-ID prefixes, lite verbs (`/votes` not `/vote`, `/moderation` not `/moderate`), `?workspaceIdentifier=` query rule |
| `references/webhooks.md` | Subscriptions, payload envelope, `X-Webhook-Signature-256`, retry schedule, WebSocket ticket flow, activity log read shape |
| `references/custom-fields.md` | Custom-field CRUD (lite), value-setting on tasks, formula configuration (structured JSON), rollup configuration |
| `references/views.md` | Views (Lite): create/list/get/update/clone, column visibility/order, filters, MCP create behavior |
| `references/dashboards-forms.md` | `/v1/dashboard/lite`, form admin (config + submissions + CSV export), public form submission |
| `references/sprints.md` | Sprint groups, sprint lifecycle (start/complete/rollover), membership, burndown — non-lite |
| `references/imports.md` | CSV import: preview → confirm flow, one-shot upload, polling job status |
| `references/admin.md` | Plan-quota errors (402 `QUOTA_EXCEEDED`), status / priority / level CRUD per scope, teams, whiteboard collab token |
| `references/members.md` | Workspace member list / role / remove, invitations send / cancel / accept / decline |
| `references/notifications.md` | List + count + mark-read, page-style pagination quirk, `data` field is a real JSON object (unlike activity log) |
| `references/filters.md` | Saved filters per list, per user, numeric `Long id`, no "apply saved filter" endpoint on lite search |

## Authentication

Data-access calls use `X-API-Key`: `du_live_…` for granted products, `dk_live_…` for a Suite workspace, or `dh_live_…` for a Hub workspace. Create workspace keys in workspace settings and personal keys in account settings. Workspace keys retain their fixed binding; personal keys discover allowed workspaces and select one per call with `X-Dutify-Workspace`. See [authentication](references/auth.md) and [personal keys](references/personal-keys.md) for scopes and denial codes.

## Why a topic-indexed skill rather than one long doc

Skills load fully whenever they're triggered — a 1500-line single doc would burn that much context per task. Splitting orientation in `SKILL.md` and detail per topic means a wiki-only task only loads `wiki.md`; a webhook setup loads `webhooks.md` + `auth.md`; nothing else. The entry point is concise; each reference averages ~95 lines.

## Evaluation

`evals/evals.json` carries 5 prompts that exercise the skill end-to-end:
- `create-task-python` — production-quality Python script that creates a task by name
- `list-wiki-pages-curl` — curl + a notes file
- `update-fr-status` — a single-shot HTTP request to change a feature-request status
- `bulk-retype-tasks` — Python that finds all tasks in a list, looks up the workspace's task-type identifiers, and bulk-changes their type via the `/v1/tasks/bulk/change-type` endpoint
- `find-untyped-tasks` — curl + notes explaining the cascade-default chain and how `taskType: null` arises

These are intended for evaluation harnesses (e.g. Anthropic's skills-eval framework) that score `with_skill` vs `without_skill` runs against expectation lists.

## Contributing

The canonical source for this skill lives at `Dutify-suite/skills/dutify-api/` inside the Dutify suite monorepo; this GitHub mirror is for distribution. Edit at the source and re-publish; don't open PRs against this repo unless you're publishing a fix that's already merged upstream.

## License

Internal Dutify documentation. Use of the API requires a valid Dutify API key.

## Maintaining the Hub compatibility distribution

Canonical Hub references live in `references/hub`. Check copies with `python scripts/sync_hub_references.py --hub-skill <hub-repo>`; use `--write` to export manifest files. The Hub distribution ships complete references and never requires the all-product skill at runtime. Update both distributions and their version files together when shared behavior changes.
