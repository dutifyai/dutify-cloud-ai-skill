# Webhooks, real-time updates, activity log

Three different ways to find out what happened: **webhooks** push events to your URL, **WebSocket** streams them to an open connection, **activity log** is a queryable read of past events.

## Subscribing to events (webhooks)

The `webhooks` scope lets a key manage webhook subscriptions for its workspace. Tag is **Webhooks** in the catalog (non-lite). All endpoints live under `/v1/workspaces/{workspaceIdentifier}/webhooks`:

```http
POST   /v1/workspaces/{ws}/webhooks                                 # create subscription
GET    /v1/workspaces/{ws}/webhooks                                 # list subscriptions
GET    /v1/workspaces/{ws}/webhooks/usage                           # plan-quota usage
GET    /v1/workspaces/{ws}/webhooks/{webhookIdentifier}             # one subscription
PATCH  /v1/workspaces/{ws}/webhooks/{webhookIdentifier}             # update url / events / active flag
DELETE /v1/workspaces/{ws}/webhooks/{webhookIdentifier}
GET    /v1/workspaces/{ws}/webhooks/{webhookIdentifier}/deliveries  # delivery log (cursor-paginated)
POST   /v1/workspaces/{ws}/webhooks/{id}/deliveries/{deliveryIdentifier}/replay
```

Subscription body:

```json
{
  "url": "https://yourapp.example.com/dutify-webhook",
  "name": "task lifecycle into Slack relay",
  "eventTypes": ["task-created", "task-deleted", "task-status-changed", "comment-added"],
  "scopeType": "TASK",            // optional: SPACE | FOLDER | TASK_LIST | TASK — narrows the events to one entity
  "scopeEntityIdentifier": "tsk_…" // required when scopeType is set
}
```

`eventTypes` is an array of dash-cased event addresses (matching `EventAddress` enum). There are 130+ events; common ones include `task-created`, `task-deleted`, `task-status-changed`, `task-priority-changed`, `task-assignee-added`, `task-assignee-removed`, `task-due-date-updated`, `task-start-date-updated`, `comment-added`, `comment-updated`, `comment-deleted`, `reaction-added`, `custom-field-value-updated`, `status-created`, `priority-created`, `space-deleted`, `folder-deleted`, `task-list-deleted`, `workspace-user-role-changed`. Pull the full list from the catalog's Webhooks tag detail.

The create response includes a one-time `secret` (HMAC key). Save it — subsequent reads do not return the secret.

## Outgoing webhook payload — what your endpoint receives

When a subscribed event fires, your URL receives a `POST` with `Content-Type: application/json` and this envelope:

```json
{
  "version": "1",
  "id": "wd_<delivery-identifier>",
  "type": "task-created",
  "timestamp": "2026-05-08T12:00:00Z",
  "workspaceIdentifier": "ws_abc",
  "data": { "...event-specific payload..." }
}
```

Headers carried alongside:

```
X-Webhook-Signature-256: sha256=<hex>     # HMAC-SHA256(secret, full body); note "sha256=" prefix
X-Webhook-Event:          task-created
X-Webhook-Delivery:       wd_<delivery-identifier>
Content-Type:             application/json
User-Agent:               Dutify-Webhooks/1.0
```

Verify the signature with `HMAC-SHA256(secret, raw-request-body)` and compare against the value **after** stripping the `sha256=` prefix.

**Retries:** failed deliveries are reattempted at +0s / +1min / +5min (3 attempts total). 2xx responses count as success; 4xx and 5xx both count as failures and trigger retry. After all 3 attempts fail, the delivery row stays in the log marked failed, and you can manually `POST .../deliveries/{deliveryId}/replay` to retry.

## Real-time updates via WebSocket

PM exposes a workspace-scoped real-time channel for live UI updates. Two-step ticket flow (no JWT in the WebSocket URL):

1. `POST /v1/websocket/ticket/{workspaceIdentifier}` (over plain HTTP with `X-API-Key` or JWT) → returns `{"ticket": "<random>"}`. **30-second TTL**, **single-use**.
2. Open WebSocket to `wss://dutify.ai/mp/api/websocket/workspace/{workspaceIdentifier}/{ticket}`. The ticket is consumed on connection.

Lose the ticket / take longer than 30 s? Just request a fresh one. Server pushes JSON messages typed by `WebsocketEventType` (`task_created`, `task_status_changed`, etc. — same event addresses as webhooks but **underscore-cased instead of dash-cased** on this channel). No client-to-server messages are accepted — read-only.

Webhook vs WebSocket choice: webhooks for a server-to-server pipeline (durable, retried), WebSocket for a UI-style "connection that's always open" pattern.

## Activity log read shape

Each entry from the `/v1/activity-log/...` endpoints is an `ActivityLogDTO`:

```json
{
  "id": 12345,
  "activityType": "TASK_STATUS_CHANGED",
  "activityLevel": "TASK",
  "entityIdentifier": "tsk_abc",
  "fullPath": "Acme/Engineering/Sprint Backlog/Fix login bug",
  "userIdentifier": "<uuid>",
  "userName": "Alice Example",
  "entityName": "Fix login bug",
  "description": "Changed status from Open to In Progress",
  "data": "{\"oldStatus\":\"Open\",\"newStatus\":\"In Progress\"}",
  "createdAt": "2026-05-08T12:00:00Z"
}
```

**Watch out:** the `data` field is a **JSON-encoded string**, not a nested object. To use it programmatically you have to `JSON.parse(entry.data)` after receiving the response. The shape inside `data` varies by `activityType` — there's no single schema; consult the catalog or just inspect by activity type.

Endpoints:

```http
GET /v1/activity-log/workspace/{workspaceIdentifier}/full
GET /v1/activity-log/workspace/{workspaceIdentifier}/own
GET /v1/activity-log/space/{spaceIdentifier}/full
GET /v1/activity-log/space/{spaceIdentifier}/own
GET /v1/activity-log/list/{listIdentifier}/full
GET /v1/activity-log/list/{listIdentifier}/own
GET /v1/activity-log/task/{taskIdentifier}/full
GET /v1/activity-log/task/{taskIdentifier}/own
```

`full` returns the whole feed at that scope; `own` filters to the current user's actions only. Cursor-paginated with `?size=` (1-100). Scope: `activity_log:read`.

## Choosing between the three

- **Activity log** — past tense; query when you need history.
- **Webhooks** — push, durable. Use when you have a stable HTTP endpoint and want server-to-server notifications. Includes retries.
- **WebSocket** — push, ephemeral. Use for live UI updates inside a session. No retries — drop and reconnect on close.
