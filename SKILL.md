---
name: medeo-video
version: 1.2.0
description: AI-powered video generation skill. Use when the user wants to create videos from text prompts, browse video templates, upload media assets, or manage the video creation pipeline.
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3"],"env":{"MEDEO_API_KEY":{"required":true,"description":"Medeo API key (starts with mk_)"}}},"tags":["video","ai-video","medeo","video-generation","rendering","recipes","media","upload"]}}
---

# Medeo Video Generator Skill

This skill enables you to help the user generate AI videos from text descriptions.
- Goal: The user only needs to describe what video they want — you handle the rest
- Video generation takes a few minutes; results are automatically sent when complete

---

## 0. One-Line Intro for the User

You can start by telling the user:
> This is an AI video generation tool. Just tell me what video you want, and I'll handle everything from asset preparation to rendering. You'll get the video link in a few minutes.

---

## 1. First-Time Setup (No API Key)

When the user first requests a video and no API key is configured, the script outputs `"setup_required": true` with a registration link.

**You must do the following:**

1. Read the `step1` field from the script's stderr output to get the registration link
2. Tell the user:
   > To use video generation, you need to register and get an API key first.
   > Please click **[link from step1]** to sign up and get your API key (starts with `mk_`), then send it to me and I'll configure it.
3. After the user sends the API key, run:
   ```bash
   python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_user_key_here"
   ```
4. Once configured, tell the user:
   > API key is set up! You can start making videos now — just tell me what you want.

---

## 2. Standard Video Generation Workflow

> ⚠️ **Important: Video generation takes 5-30 minutes. You MUST use async flow (sessions_spawn). Never wait synchronously!**

**Step 1: Generate the task description**

```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "user's video description"
```

Optional parameters (add based on user's needs):
- `--media-urls "URL1" "URL2"` — media assets provided by the user
- `--recipe-id "recipe_01..."` — use a specific video template
- `--aspect-ratio "9:16"` — portrait mode (default is 16:9 landscape)
- `--duration-ms 30000` — target duration in milliseconds

**Step 2: Call sessions_spawn with the returned `sessions_spawn_args`**

```json
{
  "task": "<task text returned by spawn-task>",
  "label": "medeo: <video description>",
  "runTimeoutSeconds": 2400
}
```

**Step 3: Immediately inform the user**

> Video is generating in the background. It should be ready in 5-10 minutes — I'll send you the result automatically 🎬

The sub-agent will automatically notify the user with the video link when done.

---

## 3. Handling Insufficient Credits

If the generation process returns an insufficient credits error (insufficient credits / quota exceeded):

1. Tell the user:
   > Your Medeo credits have run out. Please top up and let me know — I'll re-generate the video for you.
2. The error output includes a top-up link — send it to the user
3. After the user tops up, re-run the generation workflow

---

## 4. Quick Query Commands (Run directly, no spawn needed)

**User asks "what video templates are available":**
```bash
python3 {baseDir}/scripts/medeo_video.py recipes
```

**User wants to upload media assets:**
```bash
python3 {baseDir}/scripts/medeo_video.py upload --url "asset_URL"
```

**User asks "is the last video done yet":**
```bash
python3 {baseDir}/scripts/medeo_video.py last-job
```

**View history:**
```bash
python3 {baseDir}/scripts/medeo_video.py history
```

---

## 5. Resuming Interrupted Tasks

If video generation was interrupted:

```bash
# Check last task status
python3 {baseDir}/scripts/medeo_video.py last-job

# If compose is done but render hasn't started, render directly
python3 {baseDir}/scripts/medeo_video.py render --video-draft-op-record-id "op_..."

# If still composing, check progress
python3 {baseDir}/scripts/medeo_video.py compose-status --chat-session-id "csess_..."
```

---

## 6. Command Reference

| Command | Description | Duration |
|---------|-------------|----------|
| `recipes` | List available video templates | Instant |
| `generate` | Full pipeline: upload → compose → render | 5-30 min |
| `spawn-task` | Generate async task description (for sessions_spawn) | Instant |
| `upload` | Upload media assets | 5-30 sec |
| `compose` | AI composition only (no render) | 1-5 min |
| `render` | Render video only | 20s-2 min |
| `config` | Show current configuration | Instant |
| `config-init` | Configure API key | Instant |
| `last-job` | Show most recent task | Instant |
| `history` | Show job history | Instant |

---

## 7. Error Handling

| Error | What You Should Do |
|-------|-------------------|
| No API key (`setup_required: true`) | Guide user to register, configure key after they get it |
| Insufficient credits | Guide user to top up, re-generate after recharge |
| Upload/compose/render timeout | Tell user it timed out, suggest retry |
| 401/403 auth failure | API key may be expired, ask user to get a new one |
| Network error | Script auto-retries; if all fail, inform the user |

---

## 8. Tips for You

- **Always use async flow for video generation** (spawn-task + sessions_spawn) — never wait synchronously
- When the user says "make a video", check if the description is specific enough; ask follow-up questions if too vague
- If the user provides image/video URLs, include `--media-urls` parameter
- After generation completes, send the video link directly — no unnecessary chatter
- If the user asks "how's the progress", use `last-job` to check latest status

---

## 9. Send Video via Feishu (Instead of Links)

After video generation completes, if running in a Feishu environment, send the actual video file to the user instead of just a link.

**Send script:**
```bash
python3 {baseDir}/scripts/feishu_send_video.py \
  --video /tmp/video.mp4 \
  --to "ou_user_open_id" \
  --cover-url "https://thumbnail_url" \
  --duration 20875
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `--video` | Yes | Local video file path |
| `--to` | Yes | Recipient open_id (ou_xxx) or group chat_id (oc_xxx) |
| `--cover` / `--cover-url` | No | Cover image local path or URL (no preview without it) |
| `--duration` | No | Video duration in milliseconds (shows 00:00 if omitted) |

**Full workflow (after generation completes):**
1. Get `video_url` and `thumbnail_url` from the generation result
2. Download video locally: `curl -o /tmp/video.mp4 <video_url>`
3. Run the send script with `--cover-url <thumbnail_url>` and `--duration <duration_ms>`

**Technical details:**
- Feishu video messages use `msg_type: "media"` (not "video" or "file")
- Upload video with `file_type: "mp4"` and include `duration` (milliseconds)
- Cover image is uploaded via `im/v1/images` to get `image_key`

---

## 10. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MEDEO_API_KEY` | **Yes** | Medeo API key (starts with `mk_`) |

---

## 11. Data Storage

All data is stored under `~/.openclaw/workspace/medeo-video/`:

| Path | Purpose |
|------|---------|
| `config.json` | API key configuration |
| `last_job.json` | Most recent job record |
| `history/` | Historical job records (auto-keeps latest 50) |
