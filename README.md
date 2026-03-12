# 🎬 Medeo Video Generator

用 AI 从文字生成视频。告诉你的 AI 助手"帮我做个 XX 视频"，它会自动调用 [Medeo](https://medeo.app) 平台生成，几分钟后把视频发给你。

---

## 安装

### 方法一：在 OpenClaw 中安装（推荐）

对你的 AI 助手说：

```
安装 medeo-video 技能，GitHub 地址：https://github.com/one2x-ai/medeo-video-skill
```

### 方法二：手动安装

```bash
cd ~/.agents/skills/
git clone https://github.com/one2x-ai/medeo-video-skill.git medeo-video
```

安装完成后重启 OpenClaw Gateway：

```bash
openclaw gateway restart
```

---

## 配置 API Key（首次使用必须）

安装后第一次使用时，助手会自动提示你配置 API Key：

1. 打开 👉 **https://medeo.app/dev/apikey**
   - 没有账号？页面会自动引导你注册，登录后直接显示 API Key
2. 复制 `mk_` 开头的 Key
3. 发给助手，它会自动帮你配好

就这么简单，一次配置永久有效。

---

## 使用方法

### 📝 文字生成视频

直接告诉助手你想要什么视频：

```
帮我生成一个咖啡冲泡过程的视频，温馨风格
```

```
Make me a 30-second video about ocean waves at sunset
```

```
做一个产品介绍视频，主题是新款运动鞋发布
```

### 🖼️ 图片 + 文字生成视频

发一张图片（或图片链接），然后说明你想怎么用它：

```
用这张图生成一个产品宣传视频
[直接发送图片]
```

```
帮我用这张照片做个视频 https://example.com/photo.jpg
```

助手会自动上传你的图片，确保视频中使用的就是你提供的素材。

### 🎞️ 竖版短视频

想要抖音 / TikTok 竖版？直接说：

```
做一个竖版短视频，主题是日落延时
```

---

## 更多功能

| 你说的话 | 效果 |
|---------|------|
| "帮我做个 XX 视频" | 自动生成视频 |
| "用这张图做视频" + 发图 | 用你的图片生成 |
| "做竖版的" / "9:16 比例" | 竖版短视频 |
| "有哪些视频模板？" | 浏览预设模板 |
| "上次视频好了吗？" | 查看最近任务状态 |
| "我的视频历史" | 查看历史生成记录 |

---

## 常见问题

### 生成需要多久？

通常 5-15 分钟。复杂脚本可能需要更长。生成过程是后台异步的，完成后助手会自动把视频发给你。

### 支持哪些图片格式？

`.jpg`、`.png`、`.webp`、`.mp4`、`.mov`、`.gif`

### 积分用完了怎么办？

助手会提示你充值链接。充完值后说"充好了，重新试一下"即可。

### 支持哪些聊天平台？

Feishu（飞书）、Telegram、Discord、WhatsApp、Signal 等 OpenClaw 支持的所有平台均可使用。视频会直接发送到你的聊天窗口。

---

## 技术信息

- **依赖**：Python 3.6+（纯标准库，无需额外安装）
- **数据存储**：`~/.openclaw/workspace/medeo-video/`（API 配置 + 历史记录）
- **API 文档**：https://docs.prd.medeo.app/

---

## 链接

- [Medeo 平台](https://medeo.app)
- [OpenClaw](https://github.com/openclaw/openclaw)
- [ClawhHub 技能市场](https://clawhub.com)

---

MIT License
