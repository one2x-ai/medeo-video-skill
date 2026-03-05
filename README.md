# 🎬 Medeo Video Generator

AI-powered video generation skill for [OpenClaw](https://github.com/openclaw/openclaw) — create videos from text prompts using the [Medeo](https://medeo.app) platform.

---

## What Is This?

> Tell your AI assistant "make me a video about XX", and it will automatically generate the video using Medeo's AI platform, sending you the video link in a few minutes.

---

## ✨ Features

- **Text-to-Video** — Describe what you want, AI handles the rest
- **Media Upload** — Provide images/video URLs as creative assets
- **Recipe Templates** — Browse and use pre-built video styles
- **Full Pipeline** — Upload → AI Compose → Render, fully automated
- **Async Generation** — Runs in background, notifies you when done
- **Job History** — Track past video generation jobs

---

## 🚀 Quick Start (30 Seconds)

### 1. Install the Skill

Send this to your OpenClaw assistant:

```
Please install the medeo-video skill for video generation.
GitHub link: https://github.com/one2x-ai/medeo-video-skill
```

### 2. Get Your API Key

Your assistant will guide you to register and get an API key:

1. Click the link your assistant sends you to sign up
2. Get your API key (starts with `mk_`)
3. Send the API key to your assistant — it will configure everything

### 3. Start Making Videos!

Just tell your assistant what video you want:

```
Make me a video about the coffee brewing process, with a cozy atmosphere
```

```
Use this image to create a product promo video
[image URL]
```

```
Make me a vertical short video of a sunset timelapse
```

Your assistant will generate the video in the background (usually 5-10 min) and send you the link when it's done.

---

## 📋 Usage Examples

| What You Say | What Happens |
|-------------|-------------|
| "Make me a XX video" | Full auto video generation |
| "Make a video with these assets" + URLs | Upload assets + generate |
| "What video templates are available?" | List available recipes |
| "Is the last video done?" | Check recent job status |
| "Make a vertical short video" | 9:16 portrait video |

---

## 💰 Credits

- Video generation costs Medeo platform credits
- If credits run out, your assistant will prompt you to top up
- After recharging, just say "credits topped up, retry" to continue

---

## ⚙️ Advanced Usage

### Specify Video Parameters

```
Make a 30-second vertical video using the recipe_01... template
```

### Upload Assets Only

```
Upload this image to Medeo: [image URL]
```

### View History

```
Show me my recent videos
```

---

## 🔧 Requirements

- Python 3.6+
- `requests` library (auto-installed by assistant)

---

## 📁 Data Storage

All data is stored under `~/.openclaw/workspace/medeo-video/`:

| File | Purpose |
|------|---------|
| `config.json` | API key configuration |
| `last_job.json` | Latest video job record |
| `history/` | Historical job records (auto-keeps latest 50) |

---

## 🔗 Links

- [Medeo Platform](https://medeo.app)
- [API Documentation](https://docs.prd.medeo.app/)

---

## 📄 License

MIT License
