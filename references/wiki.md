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

## Wiki search — keyword, semantic, or hybrid

Tag: **Wiki Search** (lite at `/v1/workspaces/{wsId}/wiki/search/lite`, full at `/v1/workspaces/{wsId}/wiki/search`).

```http
GET https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/search/lite?q=getting%20started&spaceKey=DOCS&limit=20&mode=hybrid
X-API-Key: dk_live_…
```

The `q` parameter is **plain free text**, not a query DSL (no AND / OR / quoted phrases / wildcards). Search is now **hybrid by default** — it blends Postgres full-text ranking with pgvector semantic similarity, so meaning-based matches surface even without the exact keywords. Control it with the optional **`mode`** param:

- `mode=hybrid` *(default)* — FTS ⊕ vector, weighted.
- `mode=semantic` — pure vector similarity.
- `mode=keyword` — the legacy FTS-only behavior.

If embeddings aren't available (no OpenAI key, provider down, or the corpus isn't indexed yet) search **fails open to keyword** automatically — it never errors. Validation rejects only ASCII control characters; max length is bounded (`WikiLimits.MAX_QUERY_LENGTH`). Rate-limited at **30 req/min** per JVM. Returns up to `limit` (default 20) `LiteSearchResultDTO` entries with slug, title, space key, highlighted excerpt, status, and `updatedAt` — no UUIDs.

## RAG retrieval — citable passages for agents

To **ground an answer** in wiki content (rather than just locate a page), use **retrieve** — it returns the most relevant **chunks** (passages) with citations and relevance scores instead of page metadata.

```http
POST https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/search/retrieve/lite
X-API-Key: dk_live_…
Content-Type: application/json

{ "query": "how do reactions work", "spaceKey": "DOCS", "limit": 5 }
```

`spaceKey` and `limit` (default 5) are optional. Returns an array of chunk results: `pageSlug`, `pageTitle`, `spaceKey`, `spaceName`, `chunkIndex`, `headingPath` (the `Title > H2 > H3` breadcrumb), `chunkText` (the quotable passage), `score` (0..1), `status`, `updatedAt`. The non-lite variant (`POST …/wiki/search/retrieve`) also returns `pageId`. Same fail-open-to-keyword behavior as search. (In the MCP server this is the `wiki_retrieve` tool; plain `wiki_search` stays the page finder.)

## Reindex (backfill embeddings) — admin

Embeddings are generated automatically as pages are created/edited. To (re)index an **existing** corpus on demand — e.g. right after enabling semantic search — trigger a workspace reindex:

```http
POST https://dutify.ai/api/wiki/v1/workspaces/{wsId}/wiki/search/reindex
X-API-Key: dk_live_…
```

Enqueues every page in the workspace for (re-)embedding (unchanged chunks are skipped via content hash) and returns `{ "enqueued": <count> }`. **Privileged:** the key's creator must hold workspace-admin (`MANAGE_CODEXUM_GENERAL_SETTINGS`; owners pass automatically) **and** the key must carry the **`wiki:pages:write`** scope (reindex reprocesses page content, so it's gated on the page-write scope, not search) — a key without it gets `403 Insufficient scope. Required: wiki:pages:write`.

## Required scopes

Wiki endpoints need their own scopes alongside `workspaces:read`:

- `wiki:pages:read` / `wiki:pages:write` for page list/get/create/update/move
- `wiki:spaces:read` / `wiki:spaces:write` for space-level operations
- `wiki:search:read` for search + RAG retrieve; reindex/backfill uses **`wiki:pages:write`** (it reprocesses page content)
- `wiki:comments:*`, `wiki:attachments:*`, `wiki:settings:*`, `wiki:export:read`, `wiki:import:write`, `wiki:dashboard:read`, `wiki:covers:read` for the corresponding wiki sub-surfaces

If you provisioned an API key without the wiki scopes, every wiki call 403s.
