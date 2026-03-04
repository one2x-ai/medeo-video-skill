# Uploading Assets (Images & Videos)

Medeo accepts user-provided images and video URLs as input assets for video generation. These can be used as reference images, character photos, scene backgrounds, or video clips to incorporate.

## Upload via URL

```bash
python3 {baseDir}/scripts/medeo_video.py upload --url "https://example.com/photo.jpg"
```

Returns an asset object with:
- `asset_id` — can be referenced in generation
- `url` — the processed asset URL

Supports: `.jpg`, `.png`, `.webp`, `.mp4`, `.mov`, `.gif`

## Use Assets in Video Generation

Pass image/video URLs directly with `--media-urls`:

```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "Create a product showcase video for this sneaker" \
  --media-urls "https://example.com/sneaker-front.jpg" "https://example.com/sneaker-side.jpg"
```

Multiple URLs are supported — pass them space-separated after `--media-urls`.

## Common Use Cases

| Use Case | How |
|----------|-----|
| Character reference photo | `--media-urls "photo_url"` + describe the character in `--message` |
| Product showcase | `--media-urls "product_images..."` + describe the video style in `--message` |
| Scene background | `--media-urls "background_url"` + describe what happens in the scene |
| Video clip input | `--media-urls "clip_url"` + describe how to use/remix the clip |
| Multiple references | Pass multiple URLs: `--media-urls "url1" "url2" "url3"` |

## Tips

- **Image quality matters** — higher resolution images produce better results
- **Multiple angles help** — for character/product videos, provide 2-3 reference images from different angles
- Medeo's AI agent will intelligently incorporate the assets into the video based on your `--message` description
- You don't need to upload separately if you have direct URLs — just pass them with `--media-urls`
