# Workspace members + invitations

There's no `(Lite)` tag for member management — these surfaces are non-lite. Most agents won't need them, but anything that provisions team members or onboards users will.

## List / remove / role-change workspace members

```http
GET    /v1/workspaces/{workspaceIdentifier}/users                              # list current members
PATCH  /v1/workspaces/{workspaceIdentifier}/users                              # change a user's role
DELETE /v1/workspaces/{workspaceIdentifier}/users?deletionUserUuid=<uuid>      # remove a user from the workspace
POST   /v1/workspaces/{workspaceIdentifier}/users/transfer-ownership           # move owner-flag to another member
POST   /v1/workspaces/{workspaceIdentifier}/users/leave                        # the calling user leaves the workspace
```

The PATCH body is `UpdateWorkspaceUserRequest` — typically `{userUuid, workspaceAccessLevelId}`. The DELETE path puts the target user's UUID in a query parameter, not the path. The `/leave` endpoint affects the *caller*, not someone you specify.

### The GET returns a paginated ENVELOPE, not an array

> ⚠️ **Breaking change (live since 2026-07-25).** `GET /v1/workspaces/{workspaceIdentifier}/users` used to return a bare `WorkspaceUserDTO[]`. It now returns a **paginated envelope**. Code that does `response.map(...)` on it will fail with `.map is not a function` — this shape change white-screened two products on release. The members are under **`users`**:

```json
{
  "users": [ /* WorkspaceUserDTO — uuid, email, full name, workspace access level */ ],
  "totalCount": 158,
  "page": 0,
  "size": 20,
  "totalPages": 8
}
```

Query parameters:

| Param | Notes |
|---|---|
| `page` | **0-based**. `@Min(0)`. |
| `size` | `@Min(1) @Max(100)` — **`size` ≥ 101 fails bean validation with a 400**, it is not clamped. |
| `search` | Optional case-insensitive substring over first name / last name / email. Applied **before** the page cut, so `totalCount` reflects the matching set. |
| `sortColumn` / `sortDirection` | Optional sort. |

> ⚠️ **`size` defaults to 20 when omitted** — this is the sneaky one. Omitting `size` does **not** return the whole roster; you silently get the first 20 members and no error. This has always been the behaviour, independent of the envelope change. **To enumerate every member, page until you've collected `totalCount`** (or pass `size` explicitly, max 100, and keep paging) — never assume one call gave you everyone.

Members whose underlying account no longer resolves are excluded **before** paging, so `totalCount` is an honest count of resolvable members and pages are a consistent size. (Previously they were dropped *after* the page cut, which produced variable-length pages.)

Scope: `users:read` (no `users:write` scope — invitation/role-change writes flow through the workspace's own scope).

## Sending and managing invitations

Workspace owner side (the workspace that's inviting):

```http
GET    /v1/workspaces/{workspaceIdentifier}/invitations                              # list pending invitations
POST   /v1/workspaces/{workspaceIdentifier}/invitations                              # send a new invitation
DELETE /v1/workspaces/{workspaceIdentifier}/invitations/{invitationIdentifier}       # cancel a pending invitation
```

Body for `POST` is `CreateInvitationRequest`:

```json
{
  "email": "alice@example.com",
  "workspaceAccessLevelId": 2
}
```

**Watch out:** the field is `workspaceAccessLevelId` — a numeric `Long`, not a stable identifier. Resolve it by listing `/v1/workspaces/{ws}/access-levels` first and reading the `id` field.

## Accept / decline (invitee side)

The invitee uses a separate resource that's **path-prefixed `/invitations` without `/v1`**:

```http
GET  /invitations                                                    # current user's pending invitations
POST /invitations/{invitationIdentifier}/accept
POST /invitations/{invitationIdentifier}/decline
```

This resource needs JWT auth — it's typically called by the invitee logged into Dutify, not via API key (an API key is bound to a workspace they're not in yet, so the call would 403). Surface invitations to the user and let them act in the UI; the accept/decline is more useful as a programmatic surface inside Dutify itself than via this skill.
