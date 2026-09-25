# Authentication and product routing

| Key | Authority and discovery | Data access |
| --- | --- | --- |
| `du_live_` | PM `GET /mp/api/v1/api-keys/current`; `GET /mp/api/v1/personal-api-keys/workspaces` without workspace selection | Granted products in currently accessible workspaces, subject to scopes, membership, policy and quota |
| `dk_live_` | PM `GET /mp/api/v1/api-keys/current` | Suite only, bound workspace and existing resource restrictions |
| `dh_live_` | Hub `GET /api/v1/api-keys/current`; workspace names through `/api/v1/workspaces` when permitted | Hub only, bound workspace and existing recording visibility |
| `dw_live_` | PM `GET /mp/api/v1/api-keys/current`, requiring `INTEGRATION` identity | Explicit products in one workspace, with current member permissions; no account-wide calendar |

Prefixes route validation; they do not establish identity. Authenticate with the correct authority. Do not probe all products with an unknown credential. Omit secrets from scripts, reports and debug output.

Personal discovery provides canonical UUID (`id`), Suite `identifier`, and product access flags. Hub calls use the UUID; Suite calls use the identifier. Bind each operation independently, including concurrent work; defaults do not expand authority. Raw resource IDs still require backend ownership checks.

No key rotation is required merely because the connector or skill is unified. A Hub-only key remains insufficient to create a PM task; a Suite-only key remains insufficient to read a Hub call. Explain missing product access and obtain a suitable user-supplied credential if needed. Never mint a credential as an implicit recovery action.

401 requires correcting rejected authentication. 403 requires resolving the specific scope, membership, product or workspace denial. 402 quota denials follow [personal-key guidance](personal-keys.md). Availability errors do not mean a credential is invalid. Preserve completed mutation IDs/results after partial failure.

Read [workspace integration keys](hub/integration-keys.md) for metadata and versioned, interactive-only management. An all-product HTTP catalog remains a separate stage. Use existing catalogs until a deployed capability supplies a newer version. Unsupported routes may justify using an existing catalog; denials and outages do not justify changing identity, workspace or policy.
