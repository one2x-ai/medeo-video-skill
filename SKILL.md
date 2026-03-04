---
name: medeo-video
version: 1.2.0
description: AI-powered video generation skill. Use when the user wants to generate videos from text descriptions, browse video recipes, upload assets, or manage video creation workflows.
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3"],"env":{"MEDEO_API_KEY":{"required":true,"description":"Medeo API key (starts with mk_)"}}},"tags":["video","ai-video","medeo","video-generation","rendering","recipes","media","upload"]}}
---

# Medeo Video Generator Skill

This skill lets you generate AI videos from text descriptions on behalf of the user.
- Goal: the user just describes the video they want, and you handle everything
- Video generation takes a few minutes; results are automatically sent when done

---

## 0. What Is Medeo?

Medeo is an **AI video agent** — not just a simple text-to-video tool. It can:
- **Create coherent multi-scene story videos** from a single prompt or screenplay
- **Break down scripts into shots** automatically (storyboard, scenes, transitions)
- **Handle complex narratives** with character continuity, mood progression, and plot arcs
- **Choose appropriate styles, music, and pacing** based on the story content

**Important: You do NOT need to split stories into separate video calls.** Just pass the full storyline, screenplay, or scene descriptions in one `--message` and Medeo will produce a single coherent video with all the scenes.

Example prompts that work great:
- A full screenplay with multiple scenes and dialogue
- A storyboard with scene-by-scene descriptions
- A narrative arc: "Tell a story about X who does Y and then Z happens"
- A simple one-liner: "A lobster cooking pasta on the beach at sunset"

Medeo handles all the creative decisions (shot composition, transitions, pacing, music) internally. You just need to convey the user's creative intent as clearly as possible.

You can tell the user:
> Medeo is an AI video creation agent. Just describe what video you want — anything from a simple scene to a full storyline with multiple chapters — and it will handle the rest. It typically takes 5-10 minutes.

---

## 1. First-Time Setup (No API Key)

When the user first wants to make a video and no API Key is configured, the script will output `"setup_required": true` with a registration link.

**What to do:**

1. Read the `step1` field from the script's stderr output for the registration link
2. Tell the user:
   > To use video generation, you need to register and get an API Key first.
   > Please visit **[step1 link]** to register and get your API Key (starts with `mk_`), then send it to me and I'll configure it.
3. Once the user provides the API Key:
   ```bash
   python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_their_key"
   ```
4. Confirm to the user that setup is complete.

---

## 2. Standard Video Generation Flow

> ⚠️ **Video generation takes 5-30 minutes. Always use async flow (sessions_spawn). Never wait synchronously!**

**Step 1: Generate the task description**

```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "the user's video description or full screenplay"
```

Optional parameters (add based on user needs):
- `--media-urls "URL1" "URL2"` — user-provided media assets
- `--recipe-id "recipe_01..."` — specific video recipe/template
- `--aspect-ratio "9:16"` — vertical video (default: 16:9 horizontal)
- `--duration-ms 30000` — target duration in milliseconds

**Prompt tips:**
- For story videos, include the full narrative with scene descriptions in one message
- Mention style preferences (e.g., "Pixar-like 3D", "cinematic", "anime")
- Describe mood/tone transitions if the story has emotional arcs
- Character descriptions help with consistency across scenes

**Step 2: Call sessions_spawn with the returned `sessions_spawn_args`**

```json
{
  "task": "<task text from spawn-task output>",
  "label": "medeo: <video description>",
  "runTimeoutSeconds": 2400
}
```

**Step 3: Inform the user immediately**

> Video is being generated in the background. It should be ready in 5-10 minutes. I'll send it to you automatically when it's done.

The sub-agent will auto-announce the video URL when complete.

---

## 3. Handling Insufficient Credits

If generation fails due to insufficient credits:

1. Tell the user their Medeo credits have run out and they need to top up
2. Include the recharge link from the error output
3. Once they've recharged, re-run the generation flow

---

## 4. Quick Query Commands (No spawn needed, run directly)

**User asks "what video templates are available":**
```bash
python3 {baseDir}/scripts/medeo_video.py recipes
```

**User wants to upload assets:**
```bash
python3 {baseDir}/scripts/medeo_video.py upload --url "asset_url"
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

## 5. Recovering Interrupted Jobs

If video generation was interrupted:

```bash
# Check last job status
python3 {baseDir}/scripts/medeo_video.py last-job

# If compose finished but render didn't start, render directly
python3 {baseDir}/scripts/medeo_video.py render --video-draft-op-record-id "op_..."

# If still composing, check progress
python3 {baseDir}/scripts/medeo_video.py compose-status --chat-session-id "csess_..."
```

---

## 6. Command Reference

| Command | Description | Duration |
|---------|-------------|----------|
| `recipes` | List available video recipes/templates | Instant |
| `generate` | Full pipeline: upload → compose → render | 5-30 min |
| `spawn-task` | Generate async task description (for sessions_spawn) | Instant |
| `upload` | Upload media assets | 5-30 sec |
| `compose` | AI composition only (no render) | 1-5 min |
| `render` | Render video only | 20 sec - 2 min |
| `config` | View current config | Instant |
| `config-init` | Configure API Key | Instant |
| `last-job` | View latest job status | Instant |
| `history` | View job history | Instant |

---

## 7. Error Handling

| Error | What to do |
|-------|-----------|
| No API Key (`setup_required: true`) | Guide user to register, then configure key |
| Insufficient credits | Guide user to recharge, then retry |
| Upload/compose/render timeout | Tell user it timed out, suggest retry |
| 401/403 auth failure | API Key may be invalid, ask user to regenerate |
| Network errors | Script auto-retries; if all fail, inform user |

---

## 8. Tips for the Agent

- **Always use async flow** (spawn-task + sessions_spawn) for video generation
- If the user says "make a video", check if the description is specific enough; if too vague, ask for more detail
- **For story/narrative videos, pass the entire storyline in one `--message`** — Medeo will handle scene decomposition, transitions, and continuity automatically
- **Do NOT split a story into multiple separate video calls** — Medeo is an AI agent that understands full narratives and produces coherent multi-scene videos
- If the user provides image/video links, use `--media-urls`
- After generation, send the video directly — don't be verbose about it
- If the user asks about progress, use `last-job` to check status
- **When sending video via Feishu, ALWAYS include a cover image** — without it the video shows as a blank/black thumbnail. Use `feishu_send_video.py` with `--cover-url` (from Medeo thumbnail) or extract the first frame with ffmpeg. Never skip this step.

---

## 9. Send Video via Feishu (Instead of Links)

After video generation completes, if running in a Feishu environment, send the actual video file to the user instead of just a link.

**Mode 1: Video only (media message)**
```bash
python3 {baseDir}/scripts/feishu_send_video.py \
  --video /tmp/video.mp4 \
  --to "ou_user_open_id" \
  --cover-url "https://thumbnail_url" \
  --duration 20875
```

**Mode 2: Video + text (rich post message)**
```bash
python3 {baseDir}/scripts/feishu_send_video.py \
  --video /tmp/video.mp4 \
  --to "oc_group_chat_id" \
  --cover-url "https://thumbnail_url" \
  --duration 20875 \
  --title "My First Video" \
  --text "Here is my first AI-generated video!\nIt took 6 minutes from idea to final cut."
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `--video` | Yes | Local video file path |
| `--to` | Yes | Recipient open_id (ou_xxx) or group chat_id (oc_xxx) |
| `--cover` / `--cover-url` | No | Cover image local path or URL (no preview without it) |
| `--duration` | No | Video duration in milliseconds (shows 00:00 if omitted) |
| `--title` | No | Post title (triggers rich text mode) |
| `--text` | No | Text content (triggers rich text mode, supports \n for newlines) |

When `--title` or `--text` is provided, the script sends a rich text post (msg_type=post) with embedded video and text in one message. Otherwise it sends a video-only media message.

**Full workflow (after generation completes):**
1. Get `video_url` and `thumbnail_url` from the generation result
2. Download video locally: `curl -o /tmp/video.mp4 <video_url>`
3. Run the send script with appropriate parameters

**Technical details:**
- Video-only: `msg_type: "media"` with file_key + image_key
- Video + text: `msg_type: "post"` with `{"tag": "media"}` and `{"tag": "text"}` rows
- Upload video with `file_type: "mp4"` and include `duration` (milliseconds)
- Cover image is uploaded via `im/v1/images` to get `image_key`

---

## 10. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MEDEO_API_KEY` | **Yes** | Medeo API Key (starts with `mk_`) |

---

## 11. Data Storage

All data is stored in `~/.openclaw/workspace/medeo-video/`:

| Path | Purpose |
|------|---------|
| `config.json` | API Key configuration |
| `last_job.json` | Latest job record |
| `history/` | Job history (auto-retains last 50) |
