---
name: auto-hw
description: 完成大学课程作业。KB root = 以课程编号命名的最高层目录（如 `HIS281/`、`CS230/`、`me335/`），下面放一个 `index.md`，按目录树结构列出 KB 内每个文件的一句话摘要。skill 把作业内容匹配到 index 摘要 → 挑相关文件读 → 完成作业 → 落盘至作业所在文件夹。识别三类作业并按类型分流到子流程：读后感（`reflection.md`）/ 答题（`answer.md`）/ 报告（`report.md`）。用户说"完成作业 / 写读后感 / 做 hw / 写 report"或 `/auto-hw` 时触发；用户说"生成/建/扫/重建 索引"时触发，按 `make-index.md` 子流程走。回复使用中文，落盘文件使用英文。
---

# auto-hw

> 📦 Forked from [FishfishCai/claude-config](https://github.com/FishfishCai/claude-config) `skills/auto-hw/`。
> 本地适配:与 `sjtu-canvas/prep_assignment.py` 衔接 —— 前者负责从 Canvas 拉资料 + 建 KB root + 生成兼容的 `index.md`,本 skill 负责接管做题 + LaTeX 编译。

## 流程

### 1. 找 KB root

先检查目前是否就在 KB root；不然从 cwd 向上递归找第一个目录名匹配 `^[A-Z]{2,4}\d{2,4}[A-Za-z]?$`（如 HIS281、CS230、MATH301A）的目录。找不到就问用户。

**本地约定**: `sjtu-canvas/prep_assignment.py` 默认把 KB root 建在 `~/Desktop/senior_su/<course_short>/`,正则同样能匹配大小写形式。

### 2. 读 `index.md`

`index.md` 放在 KB root，**只有一行 `# <文件夹名>` 标题**，下面用 ASCII 管道树（`├──` / `└──` / `│   `）列出每个文件 + 一句话摘要。

格式示例：
```markdown
# AB123

├── file1.pdf — ...
└── subdir/
    ├── file2.pdf — ...
    └── file3.pdf — ...
```

`index.md` 缺失 / 用户要求重建 / 有遗漏文件 → 走子流程 `~/.claude/skills/auto-hw/make-index.md`。如果用户只想生成索引、没要做作业，跑完 make-index 就停。

### 3. 定位并读取作业文件

识别用户消息里给的路径或指定的文件。没给就问。

按如下方式读取：

| 格式 | 方法 |
|------|------|
| PDF 文字层 | `pdftotext -layout` |
| PDF 扫描件 | Read tool 多模态读图 |
| DOCX/DOC | `pandoc` 转 MD |
| MD / HTML / Notebook / 纯文本 | Read tool 直读 |
| 图片题 | Read tool 多模态识别 |

公式、表格、版面有歧义问用户。

### 4. 分类 + 路由

判定作业类型，确认子流程文件位置：

| 类型 | 判定 | 子流程 |
|------|------|------|
| **读后感** | "reflection" / "读后感" / "读完……谈感想" | `~/.claude/skills/auto-hw/reflection.md` |
| **答题** | Q1, Q2, Q3 / "回答以下问题" / "based on the lecture" | `~/.claude/skills/auto-hw/answer.md` |
| **报告** | "report" / "撰写报告" / 涉及数据分析 / 有实验数据 | `~/.claude/skills/auto-hw/report.md` |

不明确就问。不存在混合任务。

### 5. 子流程

进入第 4 步路由到的子流程文件，依次执行其中的索引匹配、作业流程和落盘。

聊天回复使用中文，落盘文件使用英文。

### 6. 追加输出

answer / report 子流程除源文件外要编译同名 PDF 同目录共存:

```bash
python3 ~/.claude/skills/auto-hw/scripts/build_pdf.py <path-to-hw_answer.md>
```

详细规则见 `~/.claude/skills/auto-hw/tex-standard.md`。完成后把新输出追加进 `index.md`。

### 7. 质检 (answer / report 必跑)

调用 `~/.claude/skills/auto-hw/reviewer.md` 派三个 reviewer sub-agent 并行检查:
- **R1**: 解题逻辑链
- **R2**: 公式是否来自课件 slides
- **R3**: 算术 / 单位 / 最终答案 `\boxed{}` 格式

聚合后写 `hw<N>_review.md`,有问题给用户 3 个选项(自动 fix / 手动 fix / 接受现状)。

## 约束

- **位置**：默认输出到作业文件所在文件夹，用户指定除外
- **Python 环境**：按 `~/.claude/CLAUDE.md`
- **诚信边界**：本 skill 是辅助工具,**不替代用户思考**。带学术诚信声明的考核(take-home exam / 期末)禁用
