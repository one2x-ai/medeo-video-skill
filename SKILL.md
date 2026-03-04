---
name: medeo-video
version: 1.3.0
description: AI-powered video generation skill. Use when the user wants to generate videos from text descriptions, browse video recipes, upload assets, or manage video creation workflows.
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3"],"env":{"MEDEO_API_KEY":{"required":true,"description":"Medeo API key (starts with mk_)"}}},"tags":["video","ai-video","medeo","video-generation","rendering","recipes","media","upload"]}}
---

# Medeo Video Generator Skill

Generate AI videos from text descriptions. Medeo is an **AI video agent** — it handles full storylines, multi-scene narratives, and screenplays in a single call. Just describe what you want and Medeo handles shot composition, transitions, pacing, and music automatically.

> ⚠️ **Do NOT split stories into multiple calls.** Pass the entire screenplay/storyline in one `--message`. Medeo decomposes it into shots internally.

---

## 1. First-Time Setup

If no API Key is configured, the script outputs `"setup_required": true` with a registration link.

1. Share the registration link with the user
2. Once they provide the key: `python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_..."`

---

## 2. Generate a Video

> ⚠️ **Takes 5-30 minutes. Always use async flow (sessions_spawn).**

### Step 1: Build the task

```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "your video description or full screenplay"
```

Optional flags:

| Flag | Description |
|------|-------------|
| `--media-urls "URL1" "URL2"` | Input images/videos as reference material |
| `--recipe-id "recipe_01..."` | Use a pre-built template (see Section 4) |
| `--aspect-ratio "9:16"` | Vertical video (default: 16:9) |
| `--duration-ms 30000` | Target duration in milliseconds |

### Step 2: Spawn the async task

Use `sessions_spawn` with the returned args. Set `label: "medeo: <brief>"` and `runTimeoutSeconds: 2400`.

### Step 3: Notify the user

Tell them it's generating (typically 5-10 min). The sub-agent auto-announces the result when done.

---

## 3. Upload Assets (Images & Videos)

Pass image/video URLs directly with `--media-urls` during generation:

```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "Create a product showcase video for this sneaker" \
  --media-urls "https://example.com/front.jpg" "https://example.com/side.jpg"
```

Or upload separately to get an asset reference:

```bash
python3 {baseDir}/scripts/medeo_video.py upload --url "https://example.com/photo.jpg"
```

Supports: `.jpg`, `.png`, `.webp`, `.mp4`, `.mov`, `.gif`. Multiple URLs are space-separated.

> **Tip:** Higher resolution images and multiple angles produce better results. Full details: [docs/assets-upload.md](docs/assets-upload.md)

---

## 4. Browse Recipes (Templates)

```bash
python3 {baseDir}/scripts/medeo_video.py recipes
python3 {baseDir}/scripts/medeo_video.py recipes --cursor <cursor_value>
```

Use a recipe in generation:

```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "your description" \
  --recipe-id "recipe_01..."
```

Full details: [docs/recipes.md](docs/recipes.md)

---

## 5. Quick Commands (No spawn needed)

| Command | What it does |
|---------|-------------|
| `recipes` | List video templates |
| `upload --url "URL"` | Upload image/video asset |
| `last-job` | Check latest job status |
| `history` | View job history |
| `config` | Show current configuration |

---

## 6. Send Video via Feishu

After generation, send the actual video file instead of just a link:

```bash
python3 {baseDir}/scripts/feishu_send_video.py \
  --video /tmp/video.mp4 \
  --to "ou_xxx_or_oc_xxx" \
  --cover-url "https://thumbnail_url" \
  --duration 20875
```

For rich text (video + description):

```bash
python3 {baseDir}/scripts/feishu_send_video.py \
  --video /tmp/video.mp4 --to "oc_xxx" \
  --cover-url "https://thumb.jpg" --duration 20875 \
  --title "My Video" --text "Description here"
```

### Important rules:
- **ALWAYS include a cover image** (`--cover-url` or `--cover`). Without it, the video shows a blank/black thumbnail.
- **Duration is in milliseconds.** Omitting it shows 00:00 in the player.
- **File size limit ~25MB.** Compress large videos: `ffmpeg -i input.mp4 -c:v libx264 -crf 28 -preset fast -c:a aac -b:a 128k output.mp4`
- If no thumbnail URL available, extract first frame: `ffmpeg -i video.mp4 -vframes 1 -q:v 2 cover.jpg -y`

Full details: [docs/feishu-send.md](docs/feishu-send.md)

---

## 7. Key Rules for the Agent

1. **Always async** — use `spawn-task` + `sessions_spawn` for generation
2. **One call for stories** — pass full storylines in one `--message`, never split
3. **Cover image mandatory** — Feishu videos without cover show blank thumbnails
4. **Images/videos as input** — use `--media-urls` for reference photos, product images, or video clips
5. **Insufficient credits** — tell user to recharge, include the link from error output
6. **Large files (>25MB)** — compress with ffmpeg before sending via Feishu

---

## 8. Error Handling

| Error | Action |
|-------|--------|
| `setup_required: true` | Guide user to register + configure key |
| Insufficient credits | Share recharge link, retry after top-up |
| Upload/compose/render timeout | Inform user, suggest retry |
| 401/403 | Key may be invalid, ask user to regenerate |

---

## 9. Reference Docs

| Doc | Topic |
|-----|-------|
| [docs/recipes.md](docs/recipes.md) | Browse and use video templates |
| [docs/assets-upload.md](docs/assets-upload.md) | Upload images & videos as input |
| [docs/feishu-send.md](docs/feishu-send.md) | Send video via Feishu (cover, duration, rich text) |

---

## 10. Data Storage

All data in `~/.openclaw/workspace/medeo-video/`:

| Path | Purpose |
|------|---------|
| `config.json` | API Key configuration |
| `last_job.json` | Latest job record |
| `history/` | Job history (auto-retains last 50) |
