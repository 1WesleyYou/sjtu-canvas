---
name: sjtu-canvas
description: |
  SJTU Canvas LMS 课程助手（Claude Code Edition）。管理上海交通大学 Canvas (oc.sjtu.edu.cn) 课程数据。
  也适用于其他基于 Canvas LMS 的高校，修改 base_url 即可。
  Fork of xhh678876/sjtu-canvas with Claude Code adaptation by 1WesleyYou.
  ⚠️ 摘要原则: 所有"汇总/总结/看看最近"类请求必须按 DDL 时序输出，
  最紧急的放最前；每条必须写"要做什么+什么时候+链接"，而不是只贴标题；
  详见 SKILL.md 的"🎯 摘要原则"段落。
  触发场景:
  (1) 跨课程近期动向摘要(公告/新作业/讨论/评分变化, activity_stream)
  (1b) 跨课程公告汇总(all_announcements, 支持按时间窗筛选)
  (1c) Agent Memory: 本地追踪作业/公告状态(sync/pending/mark, state/memory.json)
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
  触发词: Canvas, 课程, 作业, DDL, 截止, 成绩, 课件, slides, PPT, syllabus, 大纲, 动向, 近期, 最近, 公告, announcement, 通知, 总结, 复习, 提交作业, 讨论区, course, assignment, grade, activity, recent
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

# 跨课程公告汇总（本 fork 新增）
python3 scripts/canvas_api.py announcements     # 全部
python3 scripts/canvas_api.py announcements 7   # 近 7 天
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
list_announcements(course_id)           # 单门课公告列表
all_announcements(since_days=7)         # 跨课程公告汇总
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

## 🎯 摘要原则（重要 — 所有总结类输出必须遵守）

当用户问"看看最近 Canvas 上有什么"、"汇总公告"、"看一下动向"、"这周要做什么"等类似问题时，**必须按以下规则组织输出**：

### 1. 时序优先：最紧急的放最前

按"距离 DDL/到期时间的远近"排序，**越早需要做的越在前面**。具体优先级：

```
🚨 P0 - 24 小时内截止 / 已逾期
🔴 P1 - 本周内截止（1-7 天）
🟡 P2 - 下周到下个月（8-30 天）
🟢 P3 - 一个月以上 / 仅信息性公告
ℹ️  P4 - 学院行政类 / 与个人无关的通知
```

### 2. 行动导向：突出"要做什么"而非"发生了什么"

每条不要只是标题，要写清：
- **要做的动作**（提交 / 报名 / 查看 / 选课组 / 参加考试 ...）
- **截止时间**（精确到日期 + 时间）
- **链接 / 课程 ID**（方便用户立即点进去）

❌ 不好的输出：
```
ECE4500: Step 1 Project preference form by 11:59am, May 15
```

✅ 好的输出：
```
🚨 明天 (5/15) 11:59am 截止
   ECE4500 | 提交 Project Preference Form (Step 1)
   ⚠️ 注意：使用 Updated 版项目信息，不是最初版
   → https://oc.sjtu.edu.cn/courses/92381/...
```

### 3. 分组结构

输出格式遵循以下结构：

```
🚨 紧急 (24h / 逾期)        ← 用户首先看到这块
    └─ [每条都明确写 "做什么" + "什么时候" + "链接"]

🔴 本周到期 (1-7 天)
    └─ ...

🟡 短期内 (8-30 天)
    └─ ...

🟢 信息性 / 长期
    └─ ...

ℹ️ 学院行政 (折叠或单独一段, 不与课程混在一起)
    └─ ...
```

### 4. 数据源整合

做"近期动向摘要"时要整合至少 3 个数据源，**按优先级排序后再展示**：

1. `get_all_upcoming_ddls()` — 真正的截止时间，权重最高
2. `all_announcements(since_days=N)` — 公告（提取里面的时间敏感词）
3. `recent_activity(per_page=N)` — activity_stream 兜底（含评分变化、新作业创建等）

合并时去重（同一个事件可能在多个源都出现），用 `posted_at` / `due_at` 做时间比较。

### 5. 同时给"建议"

摘要末尾可以加一句"我建议你最先做 X、然后 Y"，但不要超过 3 条，且必须对应上面列出的 P0/P1 项。

---

## 工作流

### 1. 每日 / 每周课程动向摘要（本 fork 主要场景）

**目标**：让用户在 30 秒内知道"我现在最该做什么"。

执行步骤：
1. `get_all_upcoming_ddls()` — 拿到带 due_at 的硬截止时间列表（最高权威）
2. `all_announcements(since_days=7)` — 公告流，提取时间敏感词（"by"、"due"、"截止"、"deadline"）
3. `recent_activity(per_page=30)` — 兜底，捕捉评分变化、新发布的作业等
4. **合并 + 去重 + 按时序排序**（见上面"摘要原则"）
5. 用 P0/P1/P2/P3/P4 分组输出
6. 末尾给 1-3 条"建议优先做"

### 2. Syllabus 智能定位

1. `find_syllabus(course_id)` 搜索 `*syllabus*.pdf`
2. `download_file(file["url"], save_path)` 下载
3. `file_extractor.extract_pdf()` 提取为 Markdown
4. LLM 总结教学大纲

### 3. 课件下载 + 总结

1. `download_course_files()` 下载课程 PPT/PDF
2. `file_extractor.extract_file()` 提取文本
3. 用 LLM 总结要点

### 4. 作业辅导 / 准备工作流

**触发场景**: 用户说"帮我准备 X 课的 Assignment N"、"用 Canvas 资料完成这次作业"、"把 X 作业相关课件下载下来"等。

**两阶段**:

#### Phase 1 — 确定性下载 + 提取(用脚本一键完成)

```bash
python3 scripts/prep_assignment.py <course_keyword> "<assignment_keyword>" [--workspace DIR]

# 例:
python3 scripts/prep_assignment.py ME335 "Assignment 1"
```

脚本会:定位课程 → 定位作业 → 列文件并按 syllabus/assignment/lecture/other 分类 → 建 `<workspace>/<course_short>/` → 下载相关文件 → 批量提取 PDF 到 `_md/` → **生成 auto-hw 兼容的 `index.md`**(ASCII 树 + 一句话摘要) → 输出 JSON summary。

#### 🔗 接力到 auto-hw 真正做作业

Phase 1 跑完后,工作区已经是 [auto-hw](~/.claude/skills/auto-hw/SKILL.md) 期望的标准布局(KB root + index.md)。用户接着说"完成 Assignment 1"或 `/auto-hw`,会自动触发 auto-hw skill,它读 `index.md` 摘要 → 路由到 reflection / answer / report 子流程 → 解题 + 编译 PDF。

#### Phase 2 — LLM 分析(读 markdown 后产出)

1. 解析 `_md/Assignment N.md` 拆解每道题(主题 / 公式 / 已知 / 求解)
2. 解析每个 `_md/Lecture X.md` 建主题词表
3. 输出**题目 → Lecture 映射表**
4. 给**建议入手顺序**(从基础到综合)
5. 写**题目难点提示**(易错点 / 单位陷阱 / 适用条件)
6. 在工作区写 `NOTES.md` 留存
7. 给用户简报(目录树 + 关键信息 + 映射表 + 建议)

> 完整 workflow 文档: [workflows/assignment-prep.md](workflows/assignment-prep.md)
> NOTES.md 模板、边界情况处理、与其他工作流的关系都在那里。

**注意**: 如果作业已 `submitted=True`,**不要静默继续**,在简报中显著标注让用户确认是重做还是核对。

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

## Agent Memory (state/memory.json)

本 fork 新增的轻量级状态层，三层结构：

```
_canvas  ← Canvas 拉来的真实数据（sync 时整块覆盖）
derived  ← 自动算出的字段（priority, has_action）每次 sync 重算
local    ← 用户/agent 标注（status, notes, blockers）sync 永远不动它
```

工作流：
1. `python3 scripts/canvas_api.py sync` — 把所有作业/公告同步到本地
2. `python3 scripts/canvas_api.py pending [DAYS]` — 看未完成的事（按 P0/P1/P2 排序）
3. `python3 scripts/canvas_api.py mark <slug> <status>` — 改本地状态
   - 作业: pending / in_progress / completed / skipped / blocked
   - 公告: unseen / seen / pending / acted_on / dismissed

Python API：

```python
import state
s = state.load_state()
a_list = state.list_pending_assignments(s, days_window=7)
n_list = state.list_pending_announcements(s, since_days=30)
state.mark_status("ECE4500_step_1_...", "acted_on", "已提交")
```

slug 命名规则: `<COURSE_SHORT>_<TITLE_KEBAB>`, e.g. `ME4950_2_individual_report`。

## 注意事项

- 提交作业前**必须**向用户确认
- Canvas Token 有效期可能有限，失效时需重新生成
- Token 泄露后立刻去 Canvas Settings 删除并重新生成
- Apple 日历同步仅支持 macOS
- 非 SJTU 用户需修改 `config.json` 中的 `base_url`
- 校外访问 SJTU Canvas 需 SJTU VPN
- SJTU JI 老师习惯把 syllabus 作为 PDF 上传，不用 Canvas 内置 syllabus_body 字段，因此 `find_syllabus()` 走文件搜索路线
