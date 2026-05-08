# dutify-api — Claude Code skill

A Claude Code (and Claude.ai) skill that teaches an LLM how to use the Dutify HTTP API directly: discover endpoints via the aggregated catalog at `https://dutify.ai/mp/api/v1/api-catalog`, call the right "lite" tag with an `X-API-Key`, and self-correct on `validOptions` errors instead of guessing endpoint shapes from memory.

**Covers all three Dutify backends** in one skill: Project Management, Wiki/Codexum, and Roadmarq (Feature Requests + Bugs).

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
ls ~/.claude/skills/dutify-api/references/       # 15 topic files
```

Then in any Claude Code session, ask "what's the URL for the Dutify task-type catalogue endpoint?" — Claude should pick up the skill, load `references/task-types.md`, and answer.

## How the skill is laid out

The skill is **topic-indexed** rather than a single big document. `SKILL.md` is the orientation file an LLM always sees; the 15 reference files in `references/` are loaded on-demand based on the topic map.

| File | Topic |
|---|---|
| `SKILL.md` | Orientation: discover→call flow, lite-vs-non-lite, link map, pagination, the worked sprint example |
| `references/auth.md` | API key header, the 40+ scopes, bound workspace, `/v1/users/current/workspaces` |
| `references/errors.md` | PM nested vs FR/Wiki flat envelopes, error-code vocabulary, rate-limit response, network errors |
| `references/tasks.md` | `/lite/context`, search, create, update, comments, relationships, attachments, recurrence, time entries, `Idempotency-Key`, non-lite `TaskCreationRequest`, cross-workspace move |
| `references/task-types.md` | Catalogue, the 9 SYSTEM rows, cascade default (3 levels — list→folder→space, no workspace fallback), single + bulk type changes, default-at-level setters, reassignment-on-delete |
| `references/wiki.md` | Wiki pages list/read/write, Markdown vs TipTap body formats, search query syntax |
| `references/roadmarq.md` | Feature requests + bugs, per-board short-ID prefixes, lite verbs (`/votes` not `/vote`, `/moderation` not `/moderate`), `?workspaceIdentifier=` query rule |
| `references/webhooks.md` | Subscriptions, payload envelope, `X-Webhook-Signature-256`, retry schedule, WebSocket ticket flow, activity log read shape |
| `references/custom-fields.md` | Custom-field CRUD (lite), value-setting on tasks, formula configuration (structured JSON), rollup configuration |
| `references/dashboards-forms.md` | `/v1/dashboard/lite`, form admin (config + submissions + CSV export), public form submission |
| `references/sprints.md` | Sprint groups, sprint lifecycle (start/complete/rollover), membership, burndown — non-lite |
| `references/imports.md` | CSV import: preview → confirm flow, one-shot upload, polling job status |
| `references/admin.md` | Plan-quota errors (402 `QUOTA_EXCEEDED`), status / priority / level CRUD per scope, teams, whiteboard collab token |
| `references/members.md` | Workspace member list / role / remove, invitations send / cancel / accept / decline |
| `references/notifications.md` | List + count + mark-read, page-style pagination quirk, `data` field is a real JSON object (unlike activity log) |
| `references/filters.md` | Saved filters per list, per user, numeric `Long id`, no "apply saved filter" endpoint on lite search |

## Authentication

Every data-access call needs `X-API-Key: dk_live_<rest>`. Generate keys via the PM UI under workspace settings → API keys. One key is bound to one workspace; the scope filter rejects path-workspace mismatches with `403 ACCESS_DENIED`. See `references/auth.md` for the full scope vocabulary (PM, wiki, and feedback families).

## Why a topic-indexed skill rather than one long doc

Skills load fully whenever they're triggered — a 1500-line single doc would burn that much context per task. Splitting orientation in `SKILL.md` and detail per topic means a wiki-only task only loads `wiki.md`; a webhook setup loads `webhooks.md` + `auth.md`; nothing else. SKILL.md is ~165 lines; each reference averages ~95 lines.

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
