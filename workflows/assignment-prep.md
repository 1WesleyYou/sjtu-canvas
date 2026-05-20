# 作业准备工作流 (Assignment Prep Workflow)

> 让 Claude Code 在用户说「帮我准备 X 课的 Assignment N」之类的话时,自动完成
> **下载 + 提取 + 题目-课件 映射 + 难点分析 + 建议入手顺序** 的全流程。

## 🎯 触发场景

用户消息匹配下列模式之一:

- "帮我准备 / 完成 / 做 \<课程\> 的 \<作业\>"
- "用 \<课程\> 的资料完成 \<作业\>"
- "把 \<作业\> 的相关课件下载下来"
- "为 \<作业\> 做好准备工作"
- 类似自然语言变体

## 📥 输入参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `course_keyword` | 课程名子串(case-insensitive 匹配 `list_courses()`) | 用户指定,如 `ME335` |
| `assignment_keyword` | 作业名子串(匹配 `list_assignments(course_id)`) | 用户指定,如 `Assignment 1` |
| `workspace` | 工作区根目录 | `~/Desktop/senior_su` |

## 🔄 工作流(两阶段:确定性 + LLM 判断)

### Phase 1: 确定性部分(用 prep_assignment.py 一键完成)

```bash
cd ~/.claude/skills/sjtu-canvas
python3 scripts/prep_assignment.py <course> "<assignment>" [--workspace DIR]
```

脚本会:

1. **定位课程**: `list_courses()` 找 keyword 匹配,多匹配 / 无匹配则报错退出
2. **定位作业**: `list_assignments(course_id)` 找 keyword 匹配
3. **记录提交状态**: 读 `has_submitted_submissions`,如果 `True` 提示用户(可能需要重做)
4. **列文件 + 分类**:
   - `syllabus`(文件名含 syllabus)
   - `assignment`(含 assignment/homework/hw)
   - `lecture`(含 lecture/lec/slide/vm/ch/chapter)
   - `other`(默认不下,加 `--include-other` 启用)
5. **建目录**: `<workspace>/<course_short>/` 和 `_md/` 子目录
6. **下载所有相关文件**
7. **批量提取 PDF → markdown** 到 `_md/`
8. **生成 auto-hw 兼容的 `index.md`** —— ASCII 管道树 + 每文件启发式摘要(取首条 >=30 字、非 metadata、非日期/页脚的内容行)
9. **输出 JSON summary**(供 LLM 链式消费,含 `index_md` 字段)

> Phase 1 完成后工作区结构就是 [auto-hw](~/.claude/skills/auto-hw/SKILL.md) 期望的标准 KB root 布局,可直接被 auto-hw 接管做题。

### Phase 2: LLM 判断部分(Claude 读取 markdown 后产出)

读 Phase 1 输出的 `extracted_md` 列表:

#### Step A: 解析 assignment.md

对每个题目提取:
- **题号**(1, 2, 3, ...)
- **主题**(变 k 导热 / 对流 / 辐射 / 综合能量平衡 ...)
- **核心公式 / 概念**(Fourier 定律、Newton 冷却、Stefan-Boltzmann ...)
- **已知量**(几何尺寸、温度、系数)
- **求解目标**

#### Step B: 解析每个 lecture.md

扫每节 lecture 的 page 标题(`## Page N` 后面的内容),建立**主题词表**:
- L1 含哪些概念?
- L2 含哪些例题?
- ...

#### Step C: 题目 → Lecture 映射表

输出标准模板:

```markdown
| # | 题目主题 | 核心公式 / 概念 | 主要 Lecture | 辅助 |
|---|---|---|---|---|
| **P1** | <主题> | <公式名> | **L_?** (<对应内容>) | <secondary> |
```

匹配启发式:
- 题目核心公式名 → 出现该公式名/概念的 lecture
- 题目计算类型(如"两物体辐射")→ lecture 中有同类例题的章节
- 优先匹配**含 Example 的 lecture**,因为例题最贴近作业难度

#### Step D: 建议入手顺序

写 1-3 段简短建议,包含:
- 先读哪些 lecture(从基础到综合)
- 从哪道题入手(选数学最纯/最像例题的)
- 哪几道题是综合题(留到后面)

#### Step E: 难点提示

对每道题写 1 行"易错点",优先来自:
- 题目中容易被忽略的边界条件(如"忽略两端散热"、"假设大腔体")
- 单位陷阱(kcal vs kJ, mm vs m)
- 公式适用条件(如恒定 k vs 变 k)

#### Step F: 写 NOTES.md

在 `<workspace>/<course_short>/NOTES.md` 写入完整笔记(模板见下方)。

#### Step G: 给用户简报

回复格式:
1. **文件结构树**(`tree` 样式)
2. **关键信息卡片**(DDL / 提交状态 / 文件总大小)
3. **题目 → 课件映射表**(精简版,详细的在 NOTES.md)
4. **建议入手顺序**(2-3 条)
5. **下一步可选动作**(读 NOTES、看某题对应 lecture、查上次提交内容...)

## 📋 NOTES.md 模板

```markdown
# {COURSE_NAME} {ASSIGNMENT_NAME} — 作业准备笔记

> 📅 Assigned: {ASSIGNED_DATE} · **Due: {DUE_DATE}**
> 📚 课本: {TEXTBOOK}(从 lecture 1 提取)
> 👨‍🏫 Instructor: {INSTRUCTOR}(从 lecture 1 提取)
> ⚠️ Canvas {SUBMISSION_STATUS}(如果 has_submitted=True 才写)

---

## 题目 → 课件 映射

| # | 题目主题 | 核心公式 / 概念 | 主要 Lecture | 辅助 |
|---|---|---|---|---|
| **P1** | ... | ... | **L_?** | ... |

---

## 建议入手顺序

1. **先读 Lecture _** —— 原因
2. ...
3. **从 P_ 开始做** —— 原因

---

## 题目难点提示

| 题 | 易错点 |
|---|---|
| P1 | ... |

---

## 文件位置

```
{TREE_OUTPUT}
```

---

## 评分相关(from Syllabus)

- 作业占总成绩 ...
- 提交格式 ...
- 迟交规则 ...
- Exams 日程 ...
```

## 🚨 边界情况

| 情况 | 处理 |
|---|---|
| 课程关键词匹配多门课 | 报错列出所有候选,让用户更具体 |
| 作业关键词匹配多个 | 同上 |
| Assignment 显示 `has_submitted=True` | 仍然下载并准备,但在简报中**显著标注**,问用户是否重做 |
| 课程文件 > 30 个(大型课) | 默认只下含 syllabus/assignment/lecture 关键词的,提示用户可加 `--include-other` |
| PDF 提取失败 | file_extractor 返回 `[提取失败: ...]`,但不阻塞流程;在简报中标注哪些 md 不可用 |
| 没找到 syllabus 文件 | 跳过教学大纲分析,NOTES.md 的"评分相关"部分留空 |
| 课程只有 1-2 个 lecture | 全下,不做相关性筛选(因为信息量太少) |

## 🔗 与其他工作流的关系

- **比"作业辅导"工作流(SKILL.md §4)更早一步** —— 本工作流是"读题 + 找资料",作业辅导是"看完资料给解题思路"
- **可以接 calendar_sync** —— 准备完成后,用户可能想把 DDL 同步到日历
- **可以接 state.py** —— 完成后用 `mark_status(slug, "in_progress")` 标记到 agent memory

## ⚙️ 调用示例

```bash
# 基础用法
python3 scripts/prep_assignment.py ME335 "Assignment 1"

# 自定义工作区
python3 scripts/prep_assignment.py ECE4500 "HW 3" --workspace ~/Desktop/coursework

# 包含其他类型文件(项目模板、参考代码等)
python3 scripts/prep_assignment.py ME4950 "Project 2" --include-other
```
