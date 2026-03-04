---
name: medeo-video
version: 1.3.0
description: AI-powered video generation skill. Use when the user wants to generate videos from text descriptions, browse video recipes, upload assets, or manage video creation workflows.
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3"],"env":{"MEDEO_API_KEY":{"required":true,"description":"Medeo API key (starts with mk_)"}}},"tags":["video","ai-video","medeo","video-generation","rendering","recipes","media","upload"]}}
---

# Medeo Video Generator Skill

Generate AI videos from text descriptions. Medeo is an **AI video agent** that handles full storylines, multi-scene narratives, and screenplays in a single call.

Just describe what you want — from a one-liner to a full screenplay — and Medeo handles shot composition, transitions, pacing, and music automatically.

---

## 1. First-Time Setup

If no API Key is configured, the script outputs `"setup_required": true` with a registration link.

1. Share the registration link with the user
2. Once they provide the key: `python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_..."`

---

## 2. Generate a Video

> ⚠️ **Takes 5-30 minutes. Always use async flow (sessions_spawn).**

```bash
# Step 1: Build the task
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "your video description or screenplay"
```

Optional flags:
- `--media-urls "URL1" "URL2"` — input images/videos (see [docs/assets-upload.md](docs/assets-upload.md))
- `--recipe-id "recipe_01..."` — use a template (see [docs/recipes.md](docs/recipes.md))
- `--aspect-ratio "9:16"` — vertical video (default: 16:9)
- `--duration-ms 30000` — target duration in ms

```
# Step 2: Spawn the async task
sessions_spawn with the returned args (label: "medeo: ...", runTimeoutSeconds: 2400)

# Step 3: Tell the user it's being generated (5-10 min)
```

The sub-agent auto-announces the result when done.

---

## 3. Quick Commands (No spawn needed)

| Command | What it does |
|---------|-------------|
| `recipes` | List video templates → [docs/recipes.md](docs/recipes.md) |
| `upload --url "URL"` | Upload image/video asset → [docs/assets-upload.md](docs/assets-upload.md) |
| `last-job` | Check latest job status |
| `history` | View job history |

---

## 4. Send Video via Feishu

After generation, send the video directly to the user instead of a link.

```bash
python3 {baseDir}/scripts/feishu_send_video.py \
  --video /tmp/video.mp4 --to "ou_xxx" \
  --cover-url "https://thumb.jpg" --duration 20875
```

**Always include cover image and duration.** Full details: [docs/feishu-send.md](docs/feishu-send.md)

---

## 5. Key Rules for the Agent

1. **Always async** — use spawn-task + sessions_spawn for generation
2. **One call for stories** — pass full storylines in one `--message`, don't split into multiple calls
3. **Cover image mandatory** — Feishu videos without cover show blank thumbnails
4. **Images/videos as input** — use `--media-urls` to pass reference photos, product images, or video clips
5. **Insufficient credits** — tell user to recharge, include the link from error output
6. **Large files (>25MB)** — compress with ffmpeg before sending via Feishu

---

## 6. Error Handling

| Error | Action |
|-------|--------|
| `setup_required: true` | Guide user to register + configure key |
| Insufficient credits | Share recharge link, retry after top-up |
| Upload/compose/render timeout | Inform user, suggest retry |
| 401/403 | Key may be invalid, ask user to regenerate |

---

## 7. Reference Docs

| Doc | Topic |
|-----|-------|
| [docs/recipes.md](docs/recipes.md) | Browse and use video templates |
| [docs/assets-upload.md](docs/assets-upload.md) | Upload images & videos as input |
| [docs/feishu-send.md](docs/feishu-send.md) | Send video via Feishu (cover, duration, rich text) |

---

## 8. Data Storage

All data in `~/.openclaw/workspace/medeo-video/`:

| Path | Purpose |
|------|---------|
| `config.json` | API Key configuration |
| `last_job.json` | Latest job record |
| `history/` | Job history (auto-retains last 50) |
