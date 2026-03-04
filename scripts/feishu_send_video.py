#!/usr/bin/env python3
"""
飞书发送视频消息

用法：
    python3 feishu_send_video.py \
        --video /path/to/video.mp4 \
        --to ou_xxx \
        [--cover /path/to/cover.jpg | --cover-url https://...] \
        [--duration 20875]

流程：
    1. 上传视频文件（file_type=mp4, 带 duration）→ 拿到 file_key
    2. 上传封面图（image_type=message）→ 拿到 image_key（可选）
    3. 发送 media 消息（msg_type=media）

关键点：
    - msg_type 必须是 "media"（不是 "video" 也不是 "file"）
    - 上传视频时 file_type 用 "mp4"
    - duration 单位是毫秒，上传时传入，否则显示 00:00
    - 封面图通过 im/v1/images 上传拿 image_key，放到 content 里
    - 不带封面也能发，但显示效果差（黑色背景无预览）
    
飞书 API 参考：
    - 上传文件: POST /open-apis/im/v1/files
    - 上传图片: POST /open-apis/im/v1/images
    - 发送消息: POST /open-apis/im/v1/messages
"""

import argparse
import json
import os
import requests
import sys

# 从 openclaw 配置读取飞书凭证
def get_feishu_credentials():
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    with open(config_path) as f:
        config = json.load(f)
    feishu = config.get("channels", {}).get("feishu", {})
    app_id = feishu.get("appId", "")
    app_secret = feishu.get("appSecret", "")
    if not app_id or not app_secret:
        # fallback to hardcoded (medeo storyboard app)
        app_id = "cli_a9178756e37a9bb4"
        app_secret = "32jWOOxcCOcgYf59lUGChu65UEIsslVC"
    return app_id, app_secret


def get_tenant_token():
    app_id, app_secret = get_feishu_credentials()
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def upload_video(token, video_path, duration_ms=None):
    """上传视频文件，返回 file_key"""
    data = {"file_type": "mp4", "file_name": os.path.basename(video_path)}
    if duration_ms:
        data["duration"] = str(int(duration_ms))

    with open(video_path, "rb") as f:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files={"file": (os.path.basename(video_path), f, "video/mp4")},
        )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise Exception(f"Upload failed: {result}")
    return result["data"]["file_key"]


def upload_cover(token, cover_source):
    """上传封面图，返回 image_key。cover_source 可以是本地路径或 URL"""
    if cover_source.startswith("http"):
        # 从 URL 下载
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
    """发送 media 消息"""
    content = {"file_key": file_key}
    if image_key:
        content["image_key"] = image_key

    # 判断 to 是 open_id 还是 chat_id
    if to.startswith("oc_"):
        receive_id_type = "chat_id"
    else:
        receive_id_type = "open_id"

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
    parser = argparse.ArgumentParser(description="飞书发送视频消息")
    parser.add_argument("--video", required=True, help="视频文件路径")
    parser.add_argument("--to", required=True, help="接收人 open_id (ou_xxx) 或群 chat_id (oc_xxx)")
    parser.add_argument("--cover", help="封面图路径或 URL")
    parser.add_argument("--cover-url", help="封面图 URL（--cover 的别名）")
    parser.add_argument("--duration", type=int, help="视频时长（毫秒）")
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
    print(json.dumps({
        "status": "ok",
        "message_id": msg_id,
        "file_key": file_key,
        "image_key": image_key,
    }))


if __name__ == "__main__":
    main()
