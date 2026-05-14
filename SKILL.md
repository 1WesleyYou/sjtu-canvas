---
name: sjtu-canvas
description: |
  SJTU Canvas LMS 课程助手（Claude Code Edition）。管理上海交通大学 Canvas (oc.sjtu.edu.cn) 课程数据。
  也适用于其他基于 Canvas LMS 的高校，修改 base_url 即可。
  Fork of xhh678876/sjtu-canvas with Claude Code adaptation by 1WesleyYou.
  触发场景:
  (1) 跨课程近期动向摘要(公告/新作业/讨论/评分变化, activity_stream)
  (2) 查看/下载课程文件(PPT/PDF)、批量下载课件
  (3) 近 N 天 slides 更新筛选
  (4) Syllabus 自动定位(适配 SJTU JI 习惯, 搜索 *syllabus*.pdf)
  (5) 查看作业列表、DDL、提交状态、提交作业
  (6) 同步作业DDL到Apple日历(Mac+iPhone)
  (7) PPT/PDF内容提取和AI总结、课件学习
  (8) 作业辅导(提取作业要求+课件内容→给思路)
  (9) 查看成绩、计算均分
  (10) 课程讨论区摘要
  (11) DDL预警提醒
  (12) 期末复习包生成(所有课件→Markdown)
  (13) 一键提交作业
  触发词: Canvas, 课程, 作业, DDL, 截止, 成绩, 课件, slides, PPT, syllabus, 大纲, 动向, 近期, 最近, 总结, 复习, 提交作业, 讨论区, course, assignment, grade, activity, recent
---

# SJTU Canvas 课程助手 (Claude Code Edition)

Canvas LMS 课程管理技能，默认配置为上海交通大学 (oc.sjtu.edu.cn)，也兼容其他 Canvas LMS 实例。

> 🍴 Fork of [xhh678876/sjtu-canvas](https://github.com/xhh678876/sjtu-canvas) by [@1WesleyYou](https://github.com/1WesleyYou)，做了面向 Claude Code 的适配和 bug 修复。

## 首次配置

1. 复制配置模板并填入你的 Canvas API Token：

```bash
# Claude Code 路径（推荐）
cp ~/.claude/skills/sjtu-canvas/config.example.json ~/.claude/skills/sjtu-canvas/config.json

# 或任意位置 + 环境变量
export SJTU_CANVAS_CONFIG=/path/to/config.json
```

2. 编辑 `config.json`，填入：
   - `canvas_token`: 从 Canvas → Account → Settings → New Access Token 获取
   - `base_url`: 你的 Canvas 地址（默认 `https://oc.sjtu.edu.cn`）
   - `save_dir`: 课件下载目录（默认 `~/Downloads/Canvas课件`）
   - `calendar_name`: Apple 日历分类名（默认 `Canvas作业`）

3. 安装依赖：

```bash
pip3 install python-pptx pdfplumber requests
```

## 核心脚本

所有脚本位于 `scripts/`，用 python3 执行。配置文件按以下顺序自动查找：
1. `SJTU_CANVAS_CONFIG` 环境变量
2. 脚本同级 `../config.json`
3. 脚本同级 `config.json`
4. `~/.claude/skills/sjtu-canvas/config.json`
5. `~/Desktop/sjtu-canvas/config.json`
6. `~/.openclaw/workspace/skills/sjtu-canvas/config.json`

### canvas_api.py — Canvas API 交互

```bash
# 课程列表
python3 scripts/canvas_api.py courses

# 当前用户
python3 scripts/canvas_api.py me

# 所有未来 DDL
python3 scripts/canvas_api.py ddls

# 已出成绩
python3 scripts/canvas_api.py grades

# 跨课程近期动向流（本 fork 新增）
python3 scripts/canvas_api.py activity        # 默认 30 条
python3 scripts/canvas_api.py activity 50     # 指定条数

# 各课 syllabus PDF（本 fork 新增）
python3 scripts/canvas_api.py syllabus

# 近 N 天更新的课件（本 fork 新增）
python3 scripts/canvas_api.py recent          # 默认 7 天
python3 scripts/canvas_api.py recent 3        # 指定天数
```

Python 中调用：

```python
import sys; sys.path.insert(0, "scripts")
from canvas_api import *

# 基础（upstream 原有）
list_courses()                          # 课程列表
list_assignments(course_id)             # 作业列表
get_all_upcoming_ddls()                 # 所有未来 DDL
get_course_grades(course_id)            # 成绩
list_course_files(course_id)            # 课程文件
download_course_files(cid, name, dir)   # 批量下载
list_discussions(course_id)             # 讨论区
get_full_discussion(cid, topic_id)      # 讨论详情
submit_assignment(cid, aid, [paths])    # 提交作业（已修复 upstream SyntaxError）

# 本 fork 新增
recent_activity(per_page=30)            # 跨课程动向流
recent_files(course_id, since_days=7)   # 近 N 天更新的文件
find_syllabus(course_id)                # 搜索 syllabus PDF
```

### file_extractor.py — 课件内容提取

```bash
# 提取单个文件
python3 scripts/file_extractor.py path/to/file.pptx

# 批量提取目录 → Markdown
python3 scripts/file_extractor.py ~/Downloads/Canvas课件/传热学 ~/Downloads/Canvas课件/传热学_md
```

支持格式: `.pptx` `.pdf` `.docx` `.txt` `.md`

### calendar_sync.py — DDL → Apple 日历 (macOS)

```bash
cd ~/.claude/skills/sjtu-canvas && python3 scripts/calendar_sync.py
```

自动创建日历分类，已存在的事件不会重复创建。通过 iCloud 同步到 iPhone。

## 工作流

### 1. 每日 / 每周课程动向摘要（本 fork 主要场景）

1. `recent_activity()` 拉跨课程动向流
2. `get_all_upcoming_ddls()` 列出未来 DDL + 提交状态
3. `recent_files(cid, since_days=7)` 列出近期 slides 更新
4. LLM 整合为 Markdown 摘要

### 2. Syllabus 智能定位

1. `find_syllabus(course_id)` 搜索 `*syllabus*.pdf`
2. `download_file(file["url"], save_path)` 下载
3. `file_extractor.extract_pdf()` 提取为 Markdown
4. LLM 总结教学大纲

### 3. 课件下载 + 总结

1. `download_course_files()` 下载课程 PPT/PDF
2. `file_extractor.extract_file()` 提取文本
3. 用 LLM 总结要点

### 4. 作业辅导

1. `get_assignment()` 获取作业要求
2. 下载相关课件并提取内容
3. 结合作业要求和课件，给出解题思路

### 5. DDL 管理

1. `get_all_upcoming_ddls()` 获取所有未来 DDL
2. `calendar_sync.sync_ddls()` 同步到 Apple 日历
3. 可设置 cron 定时巡检

### 6. 成绩追踪

1. `get_course_grades()` 获取各科成绩
2. 计算加权均分

### 7. 期末复习包

1. `download_course_files()` 批量下载课件
2. `file_extractor.batch_extract()` 批量提取为 Markdown
3. 导入 NotebookLM 或其他工具复习

### 8. 提交作业

1. 确认课程 ID、作业 ID、本地文件
2. `submit_assignment()` 提交
3. **提交前必须向用户确认**

## 注意事项

- 提交作业前**必须**向用户确认
- Canvas Token 有效期可能有限，失效时需重新生成
- Token 泄露后立刻去 Canvas Settings 删除并重新生成
- Apple 日历同步仅支持 macOS
- 非 SJTU 用户需修改 `config.json` 中的 `base_url`
- 校外访问 SJTU Canvas 需 SJTU VPN
- SJTU JI 老师习惯把 syllabus 作为 PDF 上传，不用 Canvas 内置 syllabus_body 字段，因此 `find_syllabus()` 走文件搜索路线
