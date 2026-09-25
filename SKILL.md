---
name: dutify-api
version: 2026.09.25.1
description: Work with Dutify Hub recordings, calls and Lens, PM tasks and workspaces, Wiki pages, and Roadmarq feedback through the HTTP APIs. Discover the deployed catalog before constructing requests. Use for Dutify queries, changes, event subscriptions, and cross-product workflows; load only relevant product references.
---

# Dutify API

One HTTP skill for Hub, PM, Wiki, and Roadmarq. Requested resources determine the product; the supplied credential determines authority. Direct HTTP works independently of MCP.

## Authentication and selection

Read [authentication and routing](references/routing.md) before the first request with a credential or when diagnosing authorization failures.

- `du_live_`: personal key shared across granted products and current accessible workspaces.
- `dk_live_`: existing Suite key with its fixed workspace and resource restrictions.
- `dh_live_`: existing Hub key with its fixed workspace and recording visibility.
- `dw_live_`: one workspace and a named member with explicit product grants; read [workspace integration keys](references/hub/integration-keys.md) and verify deployed support. Issuance is available when contract v1 is deployed.
- Unknown credential families require a deployed contract.

Send `X-API-Key` from the configured secret source. Personal workspace data calls use `X-Dutify-Workspace`: the Suite identifier for Suite operations and canonical UUID for Hub. Discover candidates first, resolve names, and clarify ambiguous write destinations. Never switch credentials or workspaces as an automatic retry after denial.

Calendar events are account-owned; processing assignment does not change ownership. Read Hub prompt guidance before changing that assignment. Cross-product writes are separately authorized operations: preserve successful results and report a later failure without repeating completed writes.

## Discover the deployed contract

| Product | Existing catalog |
| --- | --- |
| PM, Wiki, Roadmarq | `https://dutify.ai/mp/api/v1/api-catalog` |
| Hub | `https://dutify.ai/api/v1/api-catalog` |

Read the tag list, then `/{tag}` for operation/schema detail. Suite tags are grouped by service. A tag shared by products can have merged detail; use an unambiguous product-specific tag or report the limitation. Read the applicable reference before constructing payloads.

Catalog paths are absolute from the host root: do not concatenate a prefixed `baseUrl` with an already-prefixed path. Use the configured Dutify origin and verified operation path. Never send credentials to arbitrary response-supplied hosts. Catalog visibility is not authorization.

For MCP setup, `hub_*` tool names and legacy endpoint compatibility, read [connector guidance](references/connector.md). Confirm advertised tools before relying on the unified route. Existing HTTP clients need no connector migration.

## Topic references

| Work | Read |
| --- | --- |
| Suite conventions, IDs, names and pagination | [Suite guide](references/suite-guide.md) |
| Existing Suite key scopes and errors | [Auth](references/auth.md), [errors](references/errors.md) |
| Personal credentials, delegation, policy and quotas | [Personal keys](references/personal-keys.md) |
| PM tasks, comments, attachments and relationships | [Tasks](references/tasks.md), [task types](references/task-types.md) |
| Custom fields and views | [Custom fields](references/custom-fields.md), [views](references/views.md); preserve their identifier/value rules |
| Wiki content, search and attachments | [Wiki](references/wiki.md) |
| Roadmarq requests and bugs | [Roadmarq](references/roadmarq.md) |
| Sprints, imports, dashboards/forms | [Sprints](references/sprints.md), [imports](references/imports.md), [dashboards/forms](references/dashboards-forms.md) |
| Members, admin, notifications and filters | [Members](references/members.md), [admin](references/admin.md), [notifications](references/notifications.md), [filters](references/filters.md) |
| Webhooks and event streams | [Webhooks](references/webhooks.md); preserve JWT-only ticket requirements |
| Hub auth, workspace discovery and errors | [Hub auth](references/hub/auth.md), [workspaces](references/hub/workspace.md), [errors](references/hub/errors.md) |
| Calls, transcripts and action-item exports | [Calls](references/hub/calls.md) |
| Recordings, reprocessing and signed links | [Recordings](references/hub/recordings.md) |
| Calendar events and prompts | [Prompts](references/hub/prompts.md), [Hub personal keys](references/hub/personal-keys.md) |
| Lens conversations | [Lens](references/hub/lens-chat.md) |
| Hub settings and integrations | [Settings](references/hub/settings.md), [integrations](references/hub/integrations.md); preserve interactive consent requirements |

## Version and distribution

Canonical source: `https://github.com/dutifyai/dutify-cloud-ai-skill`. Version `2026.09.25.1` also appears in [VERSION](VERSION). For version-sensitive work compare the installed version, canonical release and deployed catalog. Installing instructions does not deploy a backend or connector.

Maintainers update frontmatter and `VERSION` together; subsequent releases that day use a `.N` suffix. Hub reference copies are checked/exported with `scripts/sync_hub_references.py`. The existing `dutify-hub-api` distribution remains independently usable.
