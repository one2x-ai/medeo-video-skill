#!/usr/bin/env python3
"""
Send video messages via Feishu (Lark) Open API.

Upload a video file and send it as a media message with optional
cover image and duration display.

Usage:
    python3 feishu_send_video.py \
        --video /path/to/video.mp4 \
        --to ou_xxx \
        [--cover /path/to/cover.jpg | --cover-url https://...] \
        [--duration 20875]

How it works:
    1. Upload video file (file_type=mp4, with duration) -> get file_key
    2. Upload cover image (image_type=message) -> get image_key (optional)
    3. Send media message (msg_type=media)

Important notes:
    - msg_type must be "media" (not "video" or "file")
    - Upload video with file_type "mp4"
    - duration is in milliseconds; omitting it shows 00:00
    - Cover image is uploaded via im/v1/images to get image_key
    - Without cover, the video shows a black background with no preview

Feishu API reference:
    - Upload file: POST /open-apis/im/v1/files
    - Upload image: POST /open-apis/im/v1/images
    - Send message: POST /open-apis/im/v1/messages
"""

import argparse
import json
import os
import requests
import sys


def get_feishu_credentials():
    """Read Feishu app credentials from openclaw config."""
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    with open(config_path) as f:
        config = json.load(f)
    feishu = config.get("channels", {}).get("feishu", {})
    app_id = feishu.get("appId", "")
    app_secret = feishu.get("appSecret", "")
    if not app_id or not app_secret:
        raise Exception("Feishu credentials not configured. Check channels.feishu in ~/.openclaw/openclaw.json")
    return app_id, app_secret


def get_tenant_token():
    """Get Feishu tenant_access_token."""
    app_id, app_secret = get_feishu_credentials()
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def upload_video(token, video_path, duration_ms=None):
    """
    Upload a video file to Feishu. Returns file_key.

    Args:
        token: tenant_access_token
        video_path: local path to the video file
        duration_ms: video duration in milliseconds (shows 00:00 if omitted)
    """
    filename = os.path.basename(video_path)
    form_data = {"file_type": "mp4", "file_name": filename}
    if duration_ms:
        form_data["duration"] = str(int(duration_ms))

    with open(video_path, "rb") as f:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            data=form_data,
            files={"file": (filename, f, "video/mp4")},
        )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise Exception(f"Video upload failed: {result}")
    return result["data"]["file_key"]


def upload_cover(token, cover_source):
    """
    Upload a cover image to Feishu. Returns image_key.

    Args:
        token: tenant_access_token
        cover_source: local image path or remote URL
    """
    if cover_source.startswith("http"):
        img_resp = requests.get(cover_source, timeout=30)
        img_resp.raise_for_status()
        img_data = img_resp.content
        filename = "cover.jpg"
    else:
        with open(cover_source, "rb") as f:
            img_data = f.read()
        filename = os.path.basename(cover_source)

    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"image_type": "message"},
        files={"image": (filename, img_data, "image/jpeg")},
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise Exception(f"Cover upload failed: {result}")
    return result["data"]["image_key"]


def send_media_message(token, to, file_key, image_key=None):
    """
    Send a media message via Feishu.

    Args:
        token: tenant_access_token
        to: recipient open_id (ou_xxx) or chat_id (oc_xxx)
        file_key: uploaded video file_key
        image_key: uploaded cover image_key (optional)
    """
    content = {"file_key": file_key}
    if image_key:
        content["image_key"] = image_key

    receive_id_type = "chat_id" if to.startswith("oc_") else "open_id"

    resp = requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": to,
            "msg_type": "media",
            "content": json.dumps(content),
        },
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise Exception(f"Send failed: {result}")
    return result["data"]["message_id"]


def main():
    parser = argparse.ArgumentParser(description="Send video messages via Feishu Open API")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--to", required=True, help="Recipient open_id (ou_xxx) or chat_id (oc_xxx)")
    parser.add_argument("--cover", help="Cover image local path")
    parser.add_argument("--cover-url", help="Cover image remote URL")
    parser.add_argument("--duration", type=int, help="Video duration in milliseconds")
    args = parser.parse_args()

    cover = args.cover or args.cover_url

    token = get_tenant_token()

    print(f"[feishu] Uploading video: {args.video}", file=sys.stderr)
    file_key = upload_video(token, args.video, args.duration)
    print(f"[feishu] Video file_key: {file_key}", file=sys.stderr)

    image_key = None
    if cover:
        print(f"[feishu] Uploading cover: {cover}", file=sys.stderr)
        image_key = upload_cover(token, cover)
        print(f"[feishu] Cover image_key: {image_key}", file=sys.stderr)

    msg_id = send_media_message(token, args.to, file_key, image_key)
    print(f"[feishu] Sent successfully: message_id={msg_id}", file=sys.stderr)

    print(json.dumps({
        "status": "ok",
        "message_id": msg_id,
        "file_key": file_key,
        "image_key": image_key,
    }))


if __name__ == "__main__":
    main()
