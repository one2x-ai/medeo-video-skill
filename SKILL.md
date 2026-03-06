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

If no API Key is configured, the script outputs `"setup_required": true`.
1. Send the user this exact link: https://medeo.app/dev/apikey (this page auto-prompts registration if not logged in, then shows the API key)
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

## 6. Key Rules

1. **Always async** — `spawn-task` + `sessions_spawn` for generation
2. **One call for stories** — full storylines in one `--message`, never split
3. **Insufficient credits** — share recharge link from error output
4. **IM-native delivery** — After generation, deliver the video using the IM channel's native method (not just a URL):
   - **Feishu**: Use `scripts/feishu_send_video.py` to send the actual video file with cover image and duration. See [docs/feishu-send.md](docs/feishu-send.md).
   - **Other channels**: Use the channel's native method to send the video file directly (e.g. Telegram sendVideo, Discord file upload). Only fall back to sharing `video_url` as a link if native file sending is unavailable.
   - **Cover image URL**: The generate output JSON includes `thumbnail_url` — the API always returns this field. Constructed as `{ossBaseUrl}/{thumbnail_relative_path}` (e.g. `https://oss.prd.medeo.app/assets/medias/media_xxx.png`).
   - **Video URL**: Same pattern — `{ossBaseUrl}/{video_relative_path}` (e.g. `https://oss.prd.medeo.app/exported_video/v_xxx`).
5. **Timeline completion** — Medeo's backend is an AI agent. Generated images/videos must be added to the Timeline to trigger task completion and rendering. Always append to your prompt: "Add the generated video/image to the Timeline."

## 7. Error Handling

| Error | Action |
|-------|--------|
| `setup_required: true` | Guide user to register + configure key |
| Insufficient credits | Share recharge link from error output, retry after top-up |
| Compose/render timeout | Inform user, suggest retry. Complex scripts may take 15+ min |
| 401/403 | Key may be invalid or expired, ask user to regenerate |
| Upload 404 | Some image hosts block server-side fetch. Try a different URL source |

## 8. Reference Docs

- [docs/recipes.md](docs/recipes.md) — Full recipe browsing and pagination
- [docs/assets-upload.md](docs/assets-upload.md) — All supported formats, upload workflows
- [docs/feishu-send.md](docs/feishu-send.md) — Sending generated video via Feishu (cover image, duration, compression)

## 9. Data Storage

All data in `~/.openclaw/workspace/medeo-video/`: `config.json` (API key), `last_job.json` (latest job), `history/` (last 50 jobs).
