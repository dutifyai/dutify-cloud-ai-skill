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

Returns are `WorkspaceUserDTO[]` on the list — each entry carries the user's UUID, email, full name, and the workspace access level they hold.

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
