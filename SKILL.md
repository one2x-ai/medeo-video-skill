---
name: medeo-video
version: 1.4.0
description: AI-powered video generation skill. Use when the user wants to generate videos from text descriptions, browse video recipes, upload assets, or manage video creation workflows.
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3"],"env":{"MEDEO_API_KEY":{"required":true,"description":"Medeo API key (starts with mk_)"}}},"tags":["video","ai-video","medeo","video-generation","rendering","recipes","media","upload"]}}
---

# Medeo Video Generator Skill

Generate AI videos from text. Medeo is an **AI video agent** that handles full storylines, multi-scene narratives, and screenplays in a single call — shot composition, transitions, pacing, and music are all automatic.

> ⚠️ **Do NOT split stories into multiple calls.** Pass the entire screenplay in one `--message`.

## 0. Pre-Flight Check (MANDATORY — run before anything else)

**Before running any command**, check if API key is configured:

```bash
python3 {baseDir}/scripts/medeo_video.py config 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if d.get('apiKey') else 'missing')"
```

- Output `ok` → proceed normally
- Output `missing` (or command fails) → **stop immediately**, do NOT run any other commands. Send the setup message using the **channel-appropriate method**:

**Feishu** — use Feishu API directly (NOT `message` tool — it won't render cards):
```python
import json, urllib.request
cfg = json.loads(open("/home/ec2-user/.openclaw/openclaw.json").read())
feishu = cfg["channels"]["feishu"]["accounts"]["default"]
token = json.loads(urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": feishu["appId"], "app_secret": feishu["appSecret"]}).encode(),
    headers={"Content-Type": "application/json"}
)).read())["tenant_access_token"]
card = {
    "config": {"wide_screen_mode": True},
    "header": {"title": {"tag": "plain_text", "content": "🎬 生成视频 — 需要先配置 API Key"}, "template": "blue"},
    "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "需要你的 **Medeo API Key** 才能生成视频。\n\n**获取步骤：**\n1. 访问 https://medeo.app/dev/apikey\n   - 没有账号会自动引导注册，登录后直接显示 API Key\n2. 复制 `mk_` 开头的 key，回复给我\n\n拿到 key 之后我帮你一键配置好。"}}],
}
urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
    data=json.dumps({"receive_id": "<USER_OPEN_ID>", "msg_type": "interactive", "content": json.dumps(card)}).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
))
```

**Telegram / Discord / 其他渠道** — 用 `message` tool 发普通文本（这些渠道支持 markdown，无需绕过）：
```
🎬 生成视频需要先配置 Medeo API Key

步骤：
1. 访问 https://medeo.app/dev/apikey（没有账号会引导注册，登录后显示 API Key）
2. 复制 mk_ 开头的 key，回复给我

拿到 key 之后我帮你一键配置好。
```

Once they provide the key: `python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_..."`

## 1. First-Time Setup

If no API Key is configured, the script outputs `"setup_required": true`.
1. Send the user this exact link: https://medeo.app/dev/apikey (this page auto-prompts registration if not logged in, then shows the API key)
2. Once they provide the key: `python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_..."`

## 2. Generate a Video (5-30 min, always async)

```bash
# Step 1: Build the task
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "your video description or full screenplay" \
  --deliver-to "oc_xxx_or_ou_xxx" \              # REQUIRED: delivery target (see below)
  --deliver-channel "feishu" \                   # REQUIRED: feishu|telegram|discord|other
  --media-ids "media_01..." \                    # optional: pre-uploaded media IDs
  --media-urls "https://example.com/ref.jpg" \   # optional: URLs (auto-uploaded inline)
  --recipe-id "recipe_01..." \                   # optional: use a template
  --aspect-ratio "9:16" \                        # optional: default 16:9
  --duration-ms 30000 \                          # optional: target duration ms
  --voice-id "voice_01..." \                     # optional: voice for narration
  --video-style-id "style_01..." \               # optional: visual style template
  --asset-sources ai_images my_uploaded_assets   # optional: restrict asset sources
```

### Asset Sources (`--asset-sources`)

Controls where Medeo's AI agent finds visuals. Choose one or more (space-separated):

| Source | Description |
|--------|-------------|
| `ai_images` | AI-generated images (default if media provided) |
| `ai_videos` | AI-generated video clips |
| `my_uploaded_assets` | Only use the images/videos you uploaded |
| `stock_videos` | Stock video library |

When you upload reference images (`--media-ids`/`--media-urls`), pass `--asset-sources my_uploaded_assets` to ensure Medeo uses **only** your images rather than generating new ones.

### Delivery Target (`--deliver-to`)

**This is critical** — determines where the generated video gets sent.

| Context | `--deliver-to` value | Example |
|---------|---------------------|---------|
| **Feishu group chat** | The group's `chat_id` (starts with `oc_`). Extract from inbound metadata `conversation_label` or `chat_id` — **strip the `chat:` prefix** if present (e.g. `chat:oc_xxx` → `oc_xxx`) | `oc_158fd3e54407cbe170697c6c954bd4f2` |
| **Feishu private chat** | The user's `open_id` (starts with `ou_`). Extract from inbound metadata `sender_id` — **strip the `user:` prefix** if present | `ou_f7f458f4d7b4ff49ec1b8de22a1e3206` |
| **Telegram** | The `chat_id` from the inbound message context | `-1001234567890` |
| **Discord** | The `channel_id` from the inbound message context | `1234567890123456` |

**How to determine group vs private on Feishu:**
- Check `is_group_chat` in the inbound metadata
- If `true` → use `conversation_label` / `chat_id` (the `oc_` value)
- If `false` → use `sender_id` (the `ou_` value)

Step 2: Use `sessions_spawn` with the returned args (`label: "medeo: <brief>"`, `runTimeoutSeconds: 2400`).
Step 3: Tell user it's generating. Sub-agent auto-announces when done.

## 3. Upload Assets

### 3a. From URL (image already has a public URL)

```bash
python3 {baseDir}/scripts/medeo_video.py upload --url "https://example.com/photo.jpg"
```

### 3b. From IM attachment (user sends image directly) ← NEW

Use `upload-file` when the user sends an image via Telegram, Discord, Feishu, or as a local file.
This uses the direct upload API (prepare → S3 presigned PUT → register) instead of URL-based upload.

**Trigger:** Only when the user **explicitly requests video generation** AND sends an image attachment in the same message (e.g. "帮我用这张图生成视频" / "make a video with this photo"). Do NOT auto-upload on every image message — other skills or conversations may involve images unrelated to video generation.

```bash
# From local file (downloaded by OpenClaw from attachment)
python3 {baseDir}/scripts/medeo_video.py upload-file \
  --file /tmp/user_photo.jpg

# From direct URL (Discord CDN, etc.)
python3 {baseDir}/scripts/medeo_video.py upload-file \
  --url "https://cdn.discordapp.com/attachments/..."

# From Telegram (file_id from message.photo[-1].file_id)
python3 {baseDir}/scripts/medeo_video.py upload-file \
  --telegram-file-id "AgACAgIAAxk..." \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN"

# From Feishu (message_id + image_key from message content)
python3 {baseDir}/scripts/medeo_video.py upload-file \
  --feishu-message-id "om_xxx" \
  --feishu-image-key "img_v3_xxx" \
  --feishu-app-token "$FEISHU_APP_TOKEN"
```

Output: `{"media_id": "media_01...", "filename": "photo.jpg"}`

Then pass `media_id` to generation:
```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "Create a video featuring this person" \
  --media-ids "media_01..."
```

### Platform-Specific Image Extraction Guide

| Platform | How to get image source | `upload-file` arg |
|----------|------------------------|-------------------|
| Telegram | `message.photo[-1].file_id` | `--telegram-file-id` |
| Discord | `message.attachments[0].url` (public CDN URL) | `--url` |
| Feishu | `message_id` + `image_key` from message content JSON | `--feishu-message-id` + `--feishu-image-key` |
| WhatsApp | Download attachment binary → save to `/tmp` | `--file` |
| Generic URL | Any direct image URL | `--url` |

**Note:** Discord attachment URLs are public CDN links — `--url` works directly. All other platforms require authentication to download.

### 3c. Inline in generate pipeline

```bash
# URL-based (existing behavior)
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "Product showcase for this sneaker" \
  --media-urls "https://example.com/front.jpg" "https://example.com/side.jpg"
```

Supports `.jpg`, `.png`, `.webp`, `.mp4`, `.mov`, `.gif`. Higher resolution + multiple angles = better results.

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
| `upload --url "URL"` | Upload from public URL (server-side fetch) |
| `upload-file --file /tmp/photo.jpg` | Upload from local file |
| `upload-file --url "https://..."` | Download URL → upload (for URLs that block server-side fetch) |
| `upload-file --telegram-file-id "..." --telegram-bot-token "$TOKEN"` | Upload Telegram image attachment |
| `upload-file --feishu-image-key "img_v3_..." --feishu-message-id "om_..."` | Upload Feishu image attachment |
| `last-job` | Latest job status |
| `history` | Job history |
| `config` | Current configuration |

## 6. Key Rules

1. **Always async** — `spawn-task` + `sessions_spawn` for generation
2. **One call for stories** — full storylines in one `--message`, never split
3. **Insufficient credits** — share recharge link from error output
4. **IM image upload** — Only upload images when the user explicitly asks for video generation with that image. Do NOT auto-upload every image message (user may have other skills installed). When triggered: run `upload-file` first → get `media_id` → pass to generation via `--media-ids`. Never ask the user for a URL if they already sent the image.
5. **IM-native delivery** — After generation, deliver the video using the IM channel's native method (not just a URL). Each channel has a dedicated delivery script:
   - **Feishu**: `python3 {baseDir}/scripts/feishu_send_video.py --video /tmp/result.mp4 --to "oc_xxx_or_ou_xxx" --cover-url "<thumbnail_url>" --duration <ms>` (use `oc_` chat_id for group chats, `ou_` open_id for private chats; `chat:oc_xxx` and `user:ou_xxx` prefixed forms are also accepted)
   - **Telegram**: `TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN python3 {baseDir}/scripts/telegram_send_video.py --video /tmp/result.mp4 --to "<chat_id>" --cover-url "<thumbnail_url>" --duration <seconds> --caption "🎬 Video ready!"`
   - **Discord**: `python3 {baseDir}/scripts/discord_send_video.py --video /tmp/result.mp4 --channel-id "<channel_id>" --caption "🎬 Video ready!"` (25 MB limit; for larger files, share video_url as link)
   - **WhatsApp / Signal / Other**: Use the `message` tool with `media` parameter, or share `video_url` as a link if native sending is unavailable.
   - **Cover image URL**: The generate output JSON includes `thumbnail_url` — the API always returns this field. Constructed as `{ossBaseUrl}/{thumbnail_relative_path}` (e.g. `https://oss.prd.medeo.app/assets/medias/media_xxx.png`).
   - **Video URL**: Same pattern — `{ossBaseUrl}/{video_relative_path}` (e.g. `https://oss.prd.medeo.app/exported_video/v_xxx`).
   - **Security**: Never pass bot tokens as CLI args (visible in `ps`). Always use env vars: `TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`.
6. **Timeline completion** — Medeo's backend is an AI agent. Generated images/videos must be added to the Timeline to trigger task completion and rendering. Always append to your prompt: "Add the generated video/image to the Timeline."

## 7. Error Handling

| Error | Action |
|-------|--------|
| `setup_required: true` | Guide user to register + configure key |
| `upload_prep_rejected` | File format/size rejected; check supported formats |
| `s3_put_failed` | S3 upload error; retry once |
| Insufficient credits | Share recharge link from error output, retry after top-up |
| Compose/render timeout | Inform user, suggest retry. Complex scripts may take 15+ min |
| 401/403 | Key may be invalid or expired, ask user to regenerate |
| Upload 404 | Some image hosts block server-side fetch; use `upload-file --url` to download first |

## 8. Reference Docs

- [docs/recipes.md](docs/recipes.md) — Full recipe browsing and pagination
- [docs/assets-upload.md](docs/assets-upload.md) — All upload paths (URL, local file, IM attachments), platform-specific guides, `upload` vs `upload-file` comparison
- [docs/feishu-send.md](docs/feishu-send.md) — Sending generated video via Feishu (cover image, duration, compression)
- [docs/multi-platform.md](docs/multi-platform.md) — Multi-platform video delivery (Feishu, Telegram, Discord, WhatsApp)

## 9. Data Storage

All data in `~/.openclaw/workspace/medeo-video/`: `config.json` (API key), `last_job.json` (latest job), `history/` (last 50 jobs).
