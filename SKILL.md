---
name: medeo-video
version: 1.1.0
description: AI 驱动的视频生成 Skill。当用户想要用文字描述生成视频、浏览视频模板、上传素材或管理视频创作流程时使用。
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3"],"env":{"MEDEO_API_KEY":{"required":true,"description":"Medeo API key (starts with mk_)"}}},"tags":["video","ai-video","medeo","video-generation","rendering","recipes","media","upload"]}}
---

# Medeo Video Generator Skill

本 Skill 让你能够帮主人用文字描述生成 AI 视频。
- 目标：主人只需要"描述想要的视频"，你来搞定一切
- 视频生成需要几分钟，完成后自动把结果发给主人

---

## 0. 一句话告诉主人这是什么

你可以先和主人说：
> 这是一个 AI 视频生成工具，你只需要告诉我想做什么视频，我会帮你自动完成从素材准备到视频渲染的全过程，几分钟后把视频链接发给你。

---

## 1. 首次安装后（没有 API Key）

当主人第一次要做视频时，如果还没有配置 API Key，脚本会输出 `"setup_required": true` 并附带注册链接。

**你必须这样做：**

1. 读取脚本 stderr 输出中的 `step1` 字段，拿到注册链接
2. 告诉主人：
   > 要使用视频生成功能，需要先注册获取 API Key。
   > 请点击 **[step1 中的链接]** 注册并获取你的 API Key（以 `mk_` 开头），然后把它发给我，我来帮你配置。
3. 主人发来 API Key 后，运行：
   ```bash
   python3 {baseDir}/scripts/medeo_video.py config-init --api-key "mk_主人的key"
   ```
4. 配置完成后告诉主人：
   > API Key 配置好了！现在可以开始做视频了，告诉我你想做什么视频吧。

---

## 2. 做视频的标准流程

> ⚠️ **重要：视频生成需要 5-30 分钟，必须用异步流程（sessions_spawn），绝对不能同步等待！**

**Step 1：生成任务描述**

```bash
python3 {baseDir}/scripts/medeo_video.py spawn-task \
  --message "主人描述的视频内容"
```

可选参数（根据主人需求加）：
- `--media-urls "URL1" "URL2"` — 主人提供的素材链接
- `--recipe-id "recipe_01..."` — 指定视频模板
- `--aspect-ratio "9:16"` — 竖屏（默认 16:9 横屏）
- `--duration-ms 30000` — 指定时长（毫秒）

**Step 2：用返回的 `sessions_spawn_args` 调用 sessions_spawn**

```json
{
  "task": "<spawn-task 返回的 task 文本>",
  "label": "medeo: <视频描述>",
  "runTimeoutSeconds": 2400
}
```

**Step 3：立刻告诉主人**

> 视频正在后台生成中，预计 5-10 分钟完成，届时会自动把结果发给你 🎬

子代理完成后会自动通知主人视频链接。

---

## 3. 积分不足的处理

如果生成过程中报错积分不足（insufficient credits / quota exceeded）：

1. 告诉主人：
   > 你的 Medeo 积分不够了，请前往充值后告诉我，我帮你重新生成。
2. 错误输出中会包含充值链接，把链接发给主人
3. 主人充值完成后，重新执行生成流程即可

---

## 4. 快速查询命令（不需要 spawn，直接跑）

**主人问"有什么视频模板"：**
```bash
python3 {baseDir}/scripts/medeo_video.py recipes
```

**主人想上传素材：**
```bash
python3 {baseDir}/scripts/medeo_video.py upload --url "素材URL"
```

**主人问"上次的视频做好了吗"：**
```bash
python3 {baseDir}/scripts/medeo_video.py last-job
```

**查看历史记录：**
```bash
python3 {baseDir}/scripts/medeo_video.py history
```

---

## 5. 恢复中断的任务

如果视频生成中途中断了：

```bash
# 查看上次任务状态
python3 {baseDir}/scripts/medeo_video.py last-job

# 如果 compose 完成但还没 render，直接 render
python3 {baseDir}/scripts/medeo_video.py render --video-draft-op-record-id "op_..."

# 如果还在 compose，查看进度
python3 {baseDir}/scripts/medeo_video.py compose-status --chat-session-id "csess_..."
```

---

## 6. 命令参考

| 命令 | 说明 | 耗时 |
|------|------|------|
| `recipes` | 列出视频模板 | 即时 |
| `generate` | 完整流水线：上传 → 编排 → 渲染 | 5-30 分钟 |
| `spawn-task` | 生成异步任务描述（配合 sessions_spawn） | 即时 |
| `upload` | 上传素材 | 5-30 秒 |
| `compose` | 仅 AI 编排（不渲染） | 1-5 分钟 |
| `render` | 仅渲染视频 | 20秒-2分钟 |
| `config` | 查看当前配置 | 即时 |
| `config-init` | 配置 API Key | 即时 |
| `last-job` | 查看最近一次任务 | 即时 |
| `history` | 查看历史记录 | 即时 |

---

## 7. 错误处理

| 错误 | 你应该怎么做 |
|------|-------------|
| 没有 API Key（`setup_required: true`） | 引导主人注册，获取 key 后帮他配置 |
| 积分不足 | 引导主人充值，充完后重新生成 |
| 上传/编排/渲染超时 | 告诉主人超时了，建议重试 |
| 401/403 认证失败 | API Key 可能失效，让主人重新获取 |
| 网络错误 | 脚本会自动重试，都失败了再告诉主人 |

---

## 8. 给你的提示

- **做视频一定要用异步流程**（spawn-task + sessions_spawn），不能同步等
- 主人说"做视频"，先确认描述是否够具体；如果太模糊，可以追问
- 如果主人提供了图片/视频链接，记得加 `--media-urls` 参数
- 生成完成后，直接把视频链接发给主人，不用多余的废话
- 如果主人问"进度怎么样了"，用 `last-job` 查看最新状态

---

## 9. 环境变量

| 变量 | 必须 | 说明 |
|------|------|------|
| `MEDEO_API_KEY` | **是** | Medeo API Key（以 `mk_` 开头） |

---

## 10. 数据存储

所有数据在 `~/.openclaw/workspace/medeo-video/`：

| 路径 | 用途 |
|------|------|
| `config.json` | API Key 配置 |
| `last_job.json` | 最近一次任务记录 |
| `history/` | 历史任务记录（自动保留最近 50 条） |
