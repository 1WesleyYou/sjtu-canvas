# report（auto-hw 子流程）

## 索引匹配

- **report 要求** — 作业基础
- **课程大纲** — 课程内容简介
- **作业涉及的全部 slide，以及序号最大的所涉及 slide 之前的所有 slide** — 知识储备；公式和知识应当基于课堂内容，而非互联网或大模型自身知识
- **实验数据** — 撰写报告的数据依据
- **之前的报告** — 了解写作规范、表达方式和相关知识

## 流程

### 1. 准备

- 看 instruction：报告分几个 section、是否要求 subsection、字数 / 页数、TeX 模板
- 数据处理 / 实验复现：在输出文件夹写最小可复现 python 脚本，跑完收齐数值、图、表

### 2. 报告结构

instruction 指定结构 → **严格按 instruction 走**。

没有默认结构，结构不明确就询问用户。

### 3. 逐 section 撰写（loop，不一次性写完）

**禁止一次性写完整份报告**。按 section 顺序逐个完成：

1. 取下一个未完成的 section
2. 判断该 section 是否需要 subsection——**依据作业 instruction**
   - 需要 subsection → 在该 section 内按 subsection 顺序**逐个**写（subsection 同样不一次性写完，写完一个再下一个）
   - 不需要 subsection → 直接写完整个 section
3. 当前 section 完整后再进入下一个
4. 所有 section 写完后进 Review

### 4. 命名落盘

- **先看作业所在目录里有没有既有 report 文件，有就沿用它的命名规则**
- 没先例 → `report<序号>.tex`
- 再按 `~/.claude/skills/auto-hw/tex-standard.md` 编译同名 PDF 与 `.tex` 同目录共存（含 `\ref{}` / TOC 时跑两遍）

### 5. Review

- 是否按 instruction 的格式 / 字数 / section 要求
- 数据来源和处理步骤清晰
- 图表必须有编号 + caption；TeX 里 `\ref{}` 引用对得上
- 代码能跑、数值 / 图来自实际验证
- TeX 能编译通过、PDF 正常生成
- 删 AI 味

## 风格

- **用 TeX**（不是 Markdown）
- 公式：行内 `$...$`，单独成行用 `\begin{equation}`
- 图：`\begin{figure}` + `\label{}` + `\caption{}`；引用用 `\ref{}`
- 表：`\begin{table}` + `\label{}` + `\caption{}`；引用用 `\ref{}`
- 短标题、紧凑表格
- 朴素客观语气（少用第一人称、不堆形容词）
