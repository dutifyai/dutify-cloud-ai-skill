# Dashboards and forms — admin reads

## Dashboard aggregates (lite)

Tag: **Dashboard (Lite)**. One endpoint covers the four scopes:

```http
GET https://dutify.ai/mp/api/v1/dashboard/lite?scope={workspace|space|folder|list}&scopeIdentifier={id}
X-API-Key: dk_live_…
```

Returns `DashboardAggregationDTO` — totals, per-status / per-priority / per-assignee counts, custom-field summaries — for the requested scope. `scopeIdentifier` is the parent's stable identifier (`ws_…`, `sp_…`, `fld_…`, `lst_…`). For `workspace` you need workspace membership; for `space` / `folder` / `list` you need VIEW access. Scope: `dashboards:read`.

## Form admin (authenticated)

Tag: **Forms** (non-lite, but called via the same authenticated workflow as the rest of PM):

```http
PATCH https://dutify.ai/mp/api/v1/forms/{viewIdentifier}/form-config       # configure the form
GET   https://dutify.ai/mp/api/v1/forms/{viewIdentifier}/submissions       # list submissions
GET   https://dutify.ai/mp/api/v1/forms/{viewIdentifier}/submissions/stats # aggregate stats (JSON)
POST  https://dutify.ai/mp/api/v1/forms/{viewIdentifier}/submissions/export # CSV streaming download
```

`viewIdentifier` is a regular resource-view identifier — get it from `/lite/context` or the views API. Scope: `forms:read` for GETs, `forms:write` for the config PATCH and the export POST.

### Form CSV export — what comes back

```http
POST https://dutify.ai/mp/api/v1/forms/{viewIdentifier}/submissions/export
X-API-Key: dk_live_…
```

Returns `Content-Type: text/csv; charset=UTF-8` with a `Content-Disposition: attachment; filename="form-submissions-<viewIdentifier>-<YYYY-MM-DD>.csv"`. The body streams (server-side `StreamingOutput`), so don't set request `Accept: application/json` — you get raw CSV.

## Public form submission (no auth)

Anyone with the public link can submit:

```http
GET  https://dutify.ai/mp/api/v1/public/forms/{publicLink}          # form definition (PublicFormDTO)
POST https://dutify.ai/mp/api/v1/public/forms/{publicLink}/submit   # submit a response
```

No `X-API-Key`, no JWT. Rate-limited per IP (default 30 req/min — see `errors.md`). Each submission creates a task on the underlying list per the form's `form-config` mapping. Returns `FormSubmissionDTO` echoing the resulting task short key. Public-share counterparts for tasks live on the same `/v1/public/...` prefix.
