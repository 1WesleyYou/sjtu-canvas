# 📚 SJTU Canvas Agent Skill — Claude Code Edition

> 🍴 **Fork notice**: 此仓库 fork 自 [xhh678876/sjtu-canvas](https://github.com/xhh678876/sjtu-canvas)，由 [@1WesleyYou](https://github.com/1WesleyYou) 在保留原作者所有功能基础上，做了**面向 Claude Code 的适配**和若干 bug 修复。原版基于 OpenClaw，本 fork 同时兼容 Claude Code Skill 加载机制。

一个 **AI Agent 技能（Skill）**，赋予你的 AI Agent（Claude Code / OpenClaw / Claude Desktop）管理 Canvas LMS 课程的能力——不只是查数据，更能帮你理解课件、辅导作业、定位知识点。默认适配 **上海交通大学** Canvas (oc.sjtu.edu.cn)，修改一行配置即可兼容任何 Canvas LMS 实例。

## 🆚 Fork 与原版差异

| 项 | 原版 (xhh678876) | 本 fork (1WesleyYou) |
|---|---|---|
| **Agent 平台** | OpenClaw | Claude Code + OpenClaw 双兼容 |
| **配置查找路径** | `~/.openclaw/workspace/...` 单一路径 | 多路径搜索（含 `~/.claude/skills/`、`~/Desktop/`、`SJTU_CANVAS_CONFIG` 环境变量） |
| **`submit_assignment()`** | 含 f-string `SyntaxError`，模块无法 import | ✅ 已修复 |
| **近期动向摘要** | 无 | ✅ 新增 `recent_activity()` 包装 Canvas activity_stream |
| **Syllabus 拉取** | 仅查 Canvas `syllabus_body` 字段（SJTU JI 不用此字段） | ✅ 新增 `find_syllabus()`：搜索文件名含 "syllabus" 的 PDF |
| **近期文件过滤** | 无 | ✅ 新增 `recent_files(course_id, since_days)`：按更新时间窗过滤 |
| **CLI 子命令** | `courses` `ddls` `grades` `me` | + `activity` `syllabus` `recent` |

## ✨ 功能一览

| 功能 | 说明 |
|---|---|
| 🌊 **近期动向流** | 跨所有课程的 activity_stream（公告/新作业/讨论/评分变化），一眼看完最近发生了什么 |
| 📢 **跨课程公告汇总** | 拉所有 active 课程的 announcements，支持按时间窗筛选（近 N 天），含作者/链接/HTML body |
| 📂 **课件管理** | 查看、下载、批量下载课程文件（PPT/PDF/DOCX）；按时间窗筛选近期更新 |
| 📄 **Syllabus 智能定位** | 自动搜索 `*syllabus*.pdf` 文件（适配 SJTU JI 习惯） |
| 🧠 **AI 课件总结** | 提取课件内容为 Markdown，配合 AI 生成学习笔记 |
| 🎯 **作业辅导** | 自动提取作业要求，匹配相关课件，定位对应知识点，给出解题思路 |
| 📝 **DDL 追踪** | 一键查看所有课程的未来截止时间 |
| ⏰ **日历同步** | 将 DDL 同步到 Apple 日历，iCloud 自动推送到 iPhone（仅 macOS） |
| 📊 **成绩查询** | 查看各科已出成绩，计算均分 |
| 💬 **讨论区** | 获取课程讨论区内容和摘要 |
| 🚀 **提交作业** | 直接从命令行提交作业文件（已修复 upstream 的 SyntaxError） |
| 📦 **复习包** | 批量导出所有课件为 Markdown，导入 NotebookLM 复习 |

## 🚀 安装

### 方式 A：Claude Code Skill（本 fork 推荐）

```bash
git clone https://github.com/1WesleyYou/sjtu-canvas.git ~/.claude/skills/sjtu-canvas
cd ~/.claude/skills/sjtu-canvas
cp config.example.json config.json
# 编辑 config.json 填入 token
pip3 install python-pptx pdfplumber requests
```

Claude Code 会自动识别 `SKILL.md` 的 frontmatter 触发器，对话中说"看一下我 Canvas 这周的动向"即可激活。

### 方式 B：放任意目录 + 环境变量

```bash
git clone https://github.com/1WesleyYou/sjtu-canvas.git ~/Desktop/sjtu-canvas
cd ~/Desktop/sjtu-canvas
cp config.example.json config.json
# 编辑 config.json
export SJTU_CANVAS_CONFIG=~/Desktop/sjtu-canvas/config.json
```

### 方式 C：原版 OpenClaw（保留兼容）

```bash
clawhub install sjtu-canvas
# 或手动 clone 到 ~/.openclaw/workspace/skills/sjtu-canvas
```

## ⚙️ 获取 Canvas API Token

1. 浏览器登录 `https://oc.sjtu.edu.cn`（校外需 SJTU VPN）
2. 右上头像 → **Account** → **Settings**
3. 滚动到 **Approved Integrations** → **+ New Access Token**
4. Purpose 填随便（如 `claude-code-canvas`），Expires 留空 = 永不过期
5. 点 **Generate Token**，**立刻复制**（只显示一次）
6. 粘贴到 `config.json` 的 `canvas_token` 字段

```json
{
  "canvas_token": "你的Token",
  "base_url": "https://oc.sjtu.edu.cn",
  "save_dir": "~/Downloads/Canvas课件",
  "calendar_name": "Canvas作业"
}
```

> 💡 非 SJTU 用户只需修改 `base_url` 为你学校的 Canvas 地址。
> 🔒 `config.json` 已在 `.gitignore` 中，不会被 commit。

## 💬 使用方式

### 自然语言（Claude Code / OpenClaw）

```
"看一下我这周 Canvas 上发生了什么"     ← 触发 recent_activity
"最近的 DDL 有哪些？"                ← 触发 get_all_upcoming_ddls
"拉一下 ECE2150 的 syllabus"        ← 触发 find_syllabus
"哪些课最近更新了 slides？"           ← 触发 recent_files
"下载 ME4950 的课件"
"帮我总结这个 PPT 的重点"
"这次作业考的是哪些知识点？"
"查看成绩"
"把 DDL 同步到日历"
```

### CLI 子命令

```bash
python3 scripts/canvas_api.py courses          # 课程列表
python3 scripts/canvas_api.py me               # 当前用户
python3 scripts/canvas_api.py ddls             # 所有未来 DDL
python3 scripts/canvas_api.py grades           # 已出成绩

# 本 fork 新增 ↓
python3 scripts/canvas_api.py activity         # 近期动向（默认 30 条）
python3 scripts/canvas_api.py activity 50      # 近期动向（指定条数）
python3 scripts/canvas_api.py syllabus         # 各课 syllabus PDF
python3 scripts/canvas_api.py recent           # 近 7 天更新的课件
python3 scripts/canvas_api.py recent 3         # 近 3 天更新的课件

# 课件提取
python3 scripts/file_extractor.py path/to/lecture.pptx

# DDL → Apple Calendar
python3 scripts/calendar_sync.py
```

### Python API

```python
import sys; sys.path.insert(0, "scripts")
from canvas_api import *

list_courses()                          # 课程列表
list_assignments(course_id)             # 作业列表
get_all_upcoming_ddls()                 # 所有未来 DDL
get_course_grades(course_id)            # 成绩
list_course_files(course_id)            # 课程文件
download_course_files(cid, name, dir)   # 批量下载
list_discussions(course_id)             # 讨论区
submit_assignment(cid, aid, [paths])    # 提交作业

# 本 fork 新增 ↓
recent_activity(per_page=30)            # 跨课程动向流
recent_files(course_id, since_days=7)   # 近 N 天更新的文件
find_syllabus(course_id)                # 搜索 syllabus PDF
list_announcements(course_id)           # 单门课公告
all_announcements(since_days=7)         # 跨课程公告汇总
```

## 🏗️ 项目结构

```
sjtu-canvas/
├── SKILL.md              # Agent Skill 触发定义（Claude Code / OpenClaw 通用）
├── README.md             # 本文件
├── config.example.json   # 配置模板
├── config.json           # 你的实际配置（gitignored）
├── LICENSE
└── scripts/
    ├── canvas_api.py     # Canvas API 核心 + 新增 activity/syllabus/recent 函数
    ├── file_extractor.py # 课件提取器（PPT/PDF/DOCX → Markdown）
    └── calendar_sync.py  # DDL → Apple Calendar 同步（macOS）
```

## 🎓 兼容性

- ✅ **Canvas LMS** — 适配任何 Canvas 实例，不限于 SJTU
- ✅ **Claude Code / Claude Desktop** — 本 fork 原生支持
- ✅ **OpenClaw** — 保留 upstream 兼容
- ✅ **macOS** — Apple 日历同步（iCloud → iPhone）
- ⚠️ 日历同步功能仅限 macOS

## 🔁 与上游同步

```bash
# 本仓库已配好 upstream 指向原作者，可随时拉新功能
git fetch upstream
git merge upstream/main
```

## 🙏 致谢

- [xhh678876/sjtu-canvas](https://github.com/xhh678876/sjtu-canvas) — 本 fork 的上游，原始实现
- [SJTU-Canvas-Helper](https://github.com/Okabe-Rintarou-0/SJTU-Canvas-Helper) — 上游灵感来源
- [OpenClaw](https://github.com/openclaw/openclaw) — AI Agent 运行时

## 📄 License

[MIT](LICENSE)

---

Original by [小灰灰大人](https://github.com/xhh678876) · Claude Code adaptation by [@1WesleyYou](https://github.com/1WesleyYou)
