---
name: medeo-video
version: 1.3.0
description: AI-powered video generation skill. Use when the user wants to generate videos from text descriptions, browse video recipes, upload assets, or manage video creation workflows.
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3"],"env":{"MEDEO_API_KEY":{"required":true,"description":"Medeo API key (starts with mk_)"}}},"tags":["video","ai-video","medeo","video-generation","rendering","recipes","media","upload"]}}
---

# Medeo Video Generator Skill

Generate AI videos from text. Medeo is an **AI video agent** that handles full storylines, multi-scene narratives, and screenplays in a single call — shot composition, transitions, pacing, and music are all automatic.

> ⚠️ **Do NOT split stories into multiple calls.** Pass the entire screenplay in one `--message`.

## 1. First-Time Setup

If no API Key is configured, the script outputs `"setup_required": true` with a registration link.
1. Share the registration link with the user
2. Once they provide the key: `python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_..."`

## 2. Generate a Video (5-30 min, always async)

```bash
# Step 1: Build the task
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "your video description or full screenplay" \
  --media-urls "https://example.com/ref.jpg" \  # optional: input images/videos
  --recipe-id "recipe_01..." \                   # optional: use a template
  --aspect-ratio "9:16" \                        # optional: default 16:9
  --duration-ms 30000                            # optional: target duration ms
```

Step 2: Use `sessions_spawn` with the returned args (`label: "medeo: <brief>"`, `runTimeoutSeconds: 2400`).
Step 3: Tell user it's generating. Sub-agent auto-announces when done.

## 3. Upload Assets

Pass image/video URLs as input with `--media-urls` (space-separated, multiple supported):
```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "Product showcase for this sneaker" \
  --media-urls "https://example.com/front.jpg" "https://example.com/side.jpg"
```

Or upload separately: `python3 {baseDir}/scripts/medeo_video.py upload --url "https://example.com/photo.jpg"`

Supports `.jpg`, `.png`, `.webp`, `.mp4`, `.mov`, `.gif`. Higher resolution + multiple angles = better results.

Common use cases:
- **Character reference**: `--media-urls "photo_url"` + describe in `--message`
- **Product showcase**: `--media-urls "product1.jpg" "product2.jpg"`
- **Video clip input**: `--media-urls "clip_url"` + describe how to remix

See [docs/assets-upload.md](docs/assets-upload.md) for full details.

## 4. Browse Recipes

```bash
python3 {baseDir}/scripts/medeo_video.py recipes              # list templates
python3 {baseDir}/scripts/medeo_video.py recipes --cursor <c>  # paginate
```

Use in generation: `--recipe-id "recipe_01..."`. See [docs/recipes.md](docs/recipes.md).

## 5. Quick Commands (no spawn needed)

| Command | Description |
|---------|-------------|
| `recipes` | List video templates |
| `upload --url "URL"` | Upload image/video asset |
| `last-job` | Latest job status |
| `history` | Job history |
| `config` | Current configuration |

## 6. Send Video via Feishu

```bash
python3 {baseDir}/scripts/feishu_send_video.py \
  --video /tmp/video.mp4 --to "ou_xxx_or_oc_xxx" \
  --cover-url "https://thumbnail_url" --duration 20875
```

Add `--title "Title" --text "Description"` for rich text mode (video + text in one message).

**Rules:**
- **ALWAYS include cover image** — without it, video shows blank/black thumbnail
- **Duration in milliseconds** — omitting shows 00:00
- **Max ~25MB** — compress: `ffmpeg -i in.mp4 -c:v libx264 -crf 28 -preset fast -c:a aac -b:a 128k out.mp4`
- No thumbnail? Extract first frame: `ffmpeg -i video.mp4 -vframes 1 -q:v 2 cover.jpg -y`

See [docs/feishu-send.md](docs/feishu-send.md).

## 7. Key Rules

1. **Always async** — `spawn-task` + `sessions_spawn` for generation
2. **One call for stories** — full storylines in one `--message`, never split
3. **Cover image mandatory** — blank thumbnails without it
4. **Insufficient credits** — share recharge link from error output
5. **Large files** — compress with ffmpeg before Feishu send

## 8. Error Handling

| Error | Action |
|-------|--------|
| `setup_required: true` | Guide user to register + configure key |
| Insufficient credits | Share recharge link from error output, retry after top-up |
| Compose/render timeout | Inform user, suggest retry. Complex scripts may take 15+ min |
| 401/403 | Key may be invalid or expired, ask user to regenerate |
| Upload 404 | Some image hosts block server-side fetch. Try a different URL source |

## 9. Reference Docs

For deeper details beyond what's covered above:
- [docs/recipes.md](docs/recipes.md) — Full recipe browsing and pagination
- [docs/assets-upload.md](docs/assets-upload.md) — All supported formats, upload workflows
- [docs/feishu-send.md](docs/feishu-send.md) — Rich text mode, technical details, troubleshooting

## 10. Data Storage

All data in `~/.openclaw/workspace/medeo-video/`: `config.json` (API key), `last_job.json` (latest job), `history/` (last 50 jobs).
