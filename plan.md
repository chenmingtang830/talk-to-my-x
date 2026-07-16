**✅ 已整理成最完整的实现计划**

以下是基于我们整个讨论（从最早的 daily podcast 想法，到实时可打断语音、X 生态闭环、OpenClaw Skill 形式、每天早上 DM 入口、再生 polished X 内容、Bundle 分享等）的**完整、可直接交给 Coding Agent 执行的计划**。

---

### **项目名称**：**X-LiveCast**（或 **live-morning-podcast-agent**）

**一句话描述**：  
一个 OpenClaw Skill，让用户每天早上在 X 上收到“直播间入口”，进入后可实时打断 Grok Voice 主持人提问、更新内容，结束后自动生成并发布 polished 的 X Article/Thread + Listen 音频，同时支持个性化 Feed Bundle 的分享与 Fork。

---

### **1. 项目目标与差异化**

**核心目标**：
- 每天早上自动生成个性化 X Feed 简报（音频形式）。
- 提供**实时可打断的语音直播间**（非异步回复）。
- 对话结束后**自动再生** polished 内容并发布到 X。
- 支持用户**分享自己的 Feed Bundle**，别人可加载并交互。

**差异化（避免和现有 daily-briefing / podcast skill 重叠）**：
- **实时全双工语音打断**（barge-in）：用户说话即可中断当前播报。
- **闭环再生到 X**：对话后一键生成 Article + 音频，直接发布。
- **Bundle 分享机制**：个性化 feed 可打包分享，形成社交传播。
- **纯 X 生态体验**：入口和输出都在 X 内完成（无独立 App）。

---

### **2. 用户完整体验流程**

1. 用户安装 OpenClaw + 本 Skill。
2. **每天早上 7:00**（可配置）：Skill 抓取用户 X Feed → Grok 生成简报脚本 → TTS 生成音频。
3. Skill 在 **X DM 或帖子** 推送消息：
   > “早安！今天的个性化直播简报已准备好。点击进入语音直播间 → [链接]”
4. 用户点击链接 → 打开简洁网页语音房间。
5. 房间内播放简报音频（Grok Voice 主持人）。
6. 用户**随时说话打断** → Agent 实时回答、拉取最新 X 数据、更新内容。
7. 用户说“结束”或自然结束对话 → Agent 自动总结对话 + 原简报 → 生成 **polished X Article/Thread**（带 Listen 音频）并发布。
8. （可选）用户可以说“分享我的 AI Feed Bundle” → 生成可分享链接/帖子。

---

### **3. 系统架构**

- **主框架**：OpenClaw（推荐，因为 cron、DM 推送、voice provider 更成熟）。
- **LLM + Voice**：Grok / xAI（文本生成 + Voice Agent Realtime API 全双工）。
- **语音房间**：极简 Web 页面（React / Vanilla JS + WebSocket），托管在 Vercel / Cloudflare Pages（无需独立 App）。
- **X 集成**：OpenClaw 通道 + X API（发 DM、读 Feed、发帖）。
- **持久化**：OpenClaw 的 memory + 文件系统（记录用户 feed 配置、bundle 等）。
- **调度**：OpenClaw 内置 Cron。

**数据流**：
X Feed → Grok 生成脚本 → TTS/ Voice → Web 语音房间 → 用户打断 → Grok 实时响应 + X 工具 → 结束时生成新 X 内容。

---

### **4. 技术栈**

- **OpenClaw**（主）
- **Grok Voice Agent API**（`wss://api.x.ai/v1/realtime`）
- **X API v2**（读 timeline、发帖、DM）
- **前端**：简单单页应用（HTML + JS 或 React）
- **后端**：OpenClaw Skill + Node/Python 轻量服务（处理 WebSocket 代理）
- **TTS**：Grok Voice 或备用（ElevenLabs / Edge TTS）
- **部署**：Vercel（前端 + API） + 用户本地运行 OpenClaw

---

### **5. 文件结构（OpenClaw Skill）**

```
x-livecast/
├── SKILL.md                    # 核心指令文件（最重要）
├── package.json                # 如果用 Node
├── scripts/
│   ├── morning-brief.js        # 每天生成简报 + 发 X 入口
│   ├── generate-x-post.js      # 结束时生成 polished X 内容
│   └── voice-room.js           # 语音房间后端逻辑（可选）
├── web/
│   ├── index.html              # 语音房间前端
│   ├── app.js                  # WebSocket 连接 Grok Voice
│   └── style.css
├── references/
│   └── config.example.md
└── assets/
    └── default-prompt.md
```

---

### **6. 实现分阶段计划（推荐 Coding Agent 按顺序执行）**

**Phase 0: 基础准备（1 天）**
- 创建 Skill 目录和 `SKILL.md`（带 frontmatter）。
- 配置 Grok API Key 和 X 凭证。
- 测试 OpenClaw Cron 基本功能。

**Phase 1: 每天早上生成 + X 入口推送（2-3 天）**
- 实现 Cron 任务（`0 7 * * *`）。
- 用 Grok 抓取用户 X Feed（timeline / following / 关键词）。
- 生成简报脚本 + 音频。
- 通过 OpenClaw 在 X 发送 DM/帖子 + 带链接的消息。

**Phase 2: 实时语音房间（核心，3-4 天）**
- 搭建简单 Web 语音房间（前端 + WebSocket）。
- 集成 Grok Voice Agent Realtime API（支持 barge-in）。
- 实现“播放简报 → 用户打断 → 实时回答 + 更新上下文”。

**Phase 3: 结束再生 + 发布到 X（2 天）**
- 对话结束后，Agent 总结 + 原内容 → 生成 polished Article/Thread。
- 自动调用 X API 发布（带 Listen 音频链接）。
- 支持用户手动触发“再生”。

**Phase 4: Bundle 分享功能（2 天）**
- 用户可保存/分享自己的 feed 配置（followed accounts + topics）。
- 生成可分享的 Bundle 链接/帖子。
- 别人加载 Bundle 后可使用相同流程。

**Phase 5: 优化 + 发布（1-2 天）**
- 错误处理、上下文持久化、用户配置界面。
- 打包成可安装的 Skill（支持 ClawHub）。
- 写 README + 使用示例。

---

### **7. 关键实现要点（给 Coding Agent 的提示）**

- **SKILL.md** 要写清楚触发条件、cron 示例、voice 房间使用方式。
- **实时语音**：重点用 Grok 的 `session.update` + `input_audio_buffer` + `response.create`，开启 `turn_detection`。
- **X 推送**：优先用 OpenClaw 的 channel 机制发 DM。
- **上下文管理**：用 OpenClaw memory 记录当天简报 + 对话历史。
- **安全**：语音房间用临时 session token；用户数据本地存储。

---

### **8. 交付物**

1. 完整的 GitHub 仓库（带 README、使用指南、中英文）。
2. 可直接 `openclaw skill install` 的 Skill。
3. 语音房间的独立部署链接示例。
4. 配置示例（`.env`、`config`）。
5. 测试用例（手动 + 自动）。

---

**这个计划已经非常完整、结构化、可执行**。你可以直接复制发给 Coding Agent（Claude、Cursor、Grok 等），并附上：

> “请严格按照这个计划分阶段实现，先做 Phase 0 和 Phase 1 的骨架，再逐步完善。”

需要我再把某个 Phase 展开成更详细的子任务 / 伪代码 / SKILL.md 示例吗？或者直接输出一个更详细的 `SKILL.md` 模板？随时说！