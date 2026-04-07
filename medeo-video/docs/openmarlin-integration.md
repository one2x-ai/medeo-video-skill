# Medeo Video OpenMarlin Integration Notes

This note documents what the Medeo video skill currently returns for
OpenMarlin-facing integration. It is intentionally descriptive, not normative.

The current expectation is:

- `settlement` is the v1 strong cross-skill contract for billable skills.
- Other Medeo fields described below are skill-specific business/debug output
  unless and until `openmarlin-plugin` defines a broader generic convention.

## Current Generate Output

On a successful `generate` run, the skill returns the original Medeo business
result plus OpenMarlin-specific metadata.

Business result fields:

- `status`
- `created_at`
- `total_duration_seconds`
- `project_id`
- `video_draft_id`
- `video_draft_op_record_id`
- `video_url`
- `thumbnail_url`
- `metadata`
- `media_ids`
- `settings`
- `stages`

OpenMarlin-oriented additive fields:

- `upstream_video_url`
- `upstream_thumbnail_url`
- `usage_stats`
- `settlement`
- `transfer`
- `billing_fetch_error`

## Strong Contract vs Skill-Specific Fields

Strong contract now:

- `settlement`

Skill-specific fields for Medeo now:

- `video_url`
- `thumbnail_url`
- `upstream_video_url`
- `upstream_thumbnail_url`
- `usage_stats`
- `transfer`
- `billing_fetch_error`

These Medeo-specific fields are useful to downstream consumers, but they should
not yet be treated as a plugin-wide standard for all future billable skills.

## Field Semantics

`video_url` and `thumbnail_url`

- Preferred final URLs for downstream consumers.
- When transfer succeeds, these point at OpenMarlin object storage public URLs.
- When transfer is unavailable or fails, these fall back to the original Medeo
  OSS URLs.

`upstream_video_url` and `upstream_thumbnail_url`

- Present only when transfer succeeds.
- Preserve the original Medeo OSS URLs for audit/debugging.

`usage_stats`

- Raw Medeo ledger response from:
  `GET /oapi/v1/ledger/projects/{projectId}/usage_stats`
- Preserved for audit/debugging and possible later reconciliation.

`settlement`

- Narrow OpenMarlin-facing billing payload.
- Current shape:

```json
{
  "components": [
    {
      "type": "skill_external_api_cost",
      "amount": 1.261748,
      "unit": "usd",
      "description": "medeo project usage proj_..."
    }
  ],
  "subtotal": {
    "amount": 1.261748,
    "unit": "usd"
  }
}
```

- Current conversion rule:
  - `credits = abs(total_credits_nano) / 1e8`
  - `usd = credits * 0.045`

`transfer`

- Present when transfer was attempted.
- Current shape:

```json
{
  "video_public_url": "https://artifacts.openmarlin.ai/artifacts/...",
  "thumbnail_public_url": "https://artifacts.openmarlin.ai/artifacts/...jpg"
}
```

- On failure, `video_error` and/or `thumbnail_error` are returned instead.

`billing_fetch_error`

- Present when Medeo ledger lookup fails.
- Billing lookup is best-effort and does not fail the video job.

## Current Verified State

Verified in local integration testing:

- Medeo `usage_stats` lookup works and produces stable `settlement`.
- OpenMarlin transfer via `POST /v1/uploads/presign` works after the server OSS
  fix.
- Successful Medeo jobs can therefore produce:
  - transferred `video_url`
  - transferred `thumbnail_url`
  - raw `usage_stats`
  - normalized `settlement`

## Plugin Boundary

`openmarlin-plugin` should define any future broader cross-skill envelope. For
now, Medeo should be treated as:

- one concrete billable skill implementation
- one producer of a plugin-consumable `settlement`
- not the source of truth for a universal top-level result shape
