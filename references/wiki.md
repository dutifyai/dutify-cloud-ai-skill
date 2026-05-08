# Wiki — list, read, write, search

Tag prefix: **Wiki Pages (Lite)** / **Wiki Spaces (Lite)** / **Wiki Search**. Base URL: `https://dutify.ai/api/wiki`. The `service` field on a catalog tag detail is `Codexum` — that's the internal codename for the same product.

## List wiki pages in a space

```http
GET https://dutify.ai/api/wiki/v1/workspaces/{workspaceIdentifier}/wiki/spaces/{spaceKey}/pages/lite
X-API-Key: dk_live_…
```

`spaceKey` is a short uppercase identifier like `ENG`, **not** the display name "Engineering". Resolve the name → key via `GET /api/wiki/v1/workspaces/{wsId}/wiki/spaces/lite` first, then pick the entry whose `name` matches.

Returns a flat list of `LitePageListItemDTO`. Each item is keyed by `slug` (there is **no `id` field** in the lite response — `slug` is the primary identifier). Item carries `slug`, `spaceKey`, `title`, `status` (`draft` | `published` | `archived`), `parentSlug` (null at the root), and timestamps. Bodies are not included — fetch each page individually for the body. By default only root-level pages are returned; pass `?parent={slug}` to walk children, or rebuild the tree client-side.

## Read or write a wiki page

Pages are addressed by **slug** under their space — there's no global `/pages/lite/{pageId}` endpoint. Body content is exchanged in **two mutually-exclusive formats**: Markdown (default) and TipTap/ProseMirror JSON.

```http
POST https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/spaces/{spaceKey}/pages/lite             # create under a space
GET  https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/spaces/{spaceKey}/pages/lite/{slug}      # read one page (with body)
PUT  https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/spaces/{spaceKey}/pages/lite/{slug}      # full update
POST https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/spaces/{spaceKey}/pages/lite/{slug}/move # move within / between spaces
```

There is no DELETE endpoint on the lite tag — page deletion goes through the non-lite Wiki Pages API.

### Body format — Markdown vs TipTap JSON

**Reading** (`GET …/{slug}`):
- Default (no query param) → response carries `markdown: "…"` and `format: "markdown"`. `content` is null.
- `?format=tiptap` → response carries `content: {…ProseMirror JSON…}` and `format: "tiptap"`. `markdown` is null.

**Writing** (`POST` create / `PUT` update): pass **either** `markdown: "…"` **or** `content: {…}` — sending both is rejected. Markdown is converted to TipTap server-side and supports the standard subset (headings, paragraphs, lists, tables, code blocks, links, basic formatting). Some features — mentions, inline labels, action buttons — are **TipTap-only** and require the `content` payload.

### Other create/update fields worth knowing

- `type: "page" | "folder"` on create — folders are organizational nodes that group children but don't carry their own body.
- `parent: "<parentSlug>"` on create — server resolves the slug to the parent's UUID; null/absent means root-of-space.
- `template: "<name>"` on create — case-sensitive template name resolved server-side.
- `isPublic`, `isEditPublic` — null inherits from the space.
- `icon`, `iconColor` — emoji name or `"icon:<name>"` prefix; hex color.

Empty pages legitimately have an empty body (depending on requested format: `markdown: ""` or `content: null`/empty doc). Don't treat that as an error.

## Wiki search — what query syntax is honored

Tag: **Wiki Search** (lite at `/v1/workspaces/{wsId}/wiki/search/lite`, full at `/v1/workspaces/{wsId}/wiki/search`).

```http
GET https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/search/lite?q=getting%20started&spaceKey=DOCS&limit=20
X-API-Key: dk_live_…
```

The `q` parameter is **plain free text**, not a query DSL — there's no documented support for AND / OR / quoted phrases / wildcards / fuzzy / boost. The backend just runs a Postgres full-text match. Validation rejects only ASCII control characters; max length is bounded (`WikiLimits.MAX_QUERY_LENGTH`). Rate-limited at **30 req/min** per JVM. Returns up to `limit` (default 20) `LiteSearchResultDTO` entries with slug, title, space key, highlighted excerpt, status, and `updatedAt` — no UUIDs.

## Required scopes

Wiki endpoints need their own scopes alongside `workspaces:read`:

- `wiki:pages:read` / `wiki:pages:write` for page list/get/create/update/move
- `wiki:spaces:read` / `wiki:spaces:write` for space-level operations
- `wiki:search:read` for search
- `wiki:comments:*`, `wiki:attachments:*`, `wiki:settings:*`, `wiki:export:read`, `wiki:import:write`, `wiki:dashboard:read`, `wiki:covers:read` for the corresponding wiki sub-surfaces

If you provisioned an API key without the wiki scopes, every wiki call 403s.
