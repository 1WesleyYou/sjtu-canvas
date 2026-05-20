# answer（auto-hw 子流程）

## 索引匹配

- **作业文件** — 作业基础
- **课程大纲** — 课程内容简介
- **作业涉及的全部 slide，以及序号最大的所涉及 slide 之前的所有 slide** — 知识储备；公式和知识应当基于课堂内容，而非互联网或大模型自身知识
- **之前的作业和答题文件** — 了解答题规范、表达方式和相关知识

## 流程

### 1. 拆题 + 调度

- 题目相互耦合或不确定多 → 单 agent
- 题目能按独立小问清楚解耦 → 并行（不设置 sub-agent 数量上限，`Agent` 工具，`subagent_type: general-purpose`，使用 opus）
- 主 controller 统一收口、去重、定稿，不让多个 sub-agent 改同一份最终文件

### 2. 解题

- **计算或公式推导题**：手算推导，过程写进 Markdown
- **数值 / 绘图 / 模型题**：在输出文件夹写最小可复现 python 脚本，跑完把数值、图写回 Markdown。代码保持短小，只服务于本题结果

### 3. 落盘

- **先看作业所在目录里有没有既有答题文件，有就沿用它的命名规则**
- 没先例 → `hw<数字>_answer.md`
- 再按 `~/.claude/skills/auto-hw/tex-standard.md` 编译同名 PDF 与 `.md` 同目录共存

### 4. Review

落盘 + 编译完成后,**必须调用** `~/.claude/skills/auto-hw/reviewer.md` 子流程,派三个并行 reviewer sub-agent (R1 Logic / R2 Formula provenance / R3 Calc-Unit-Box) 做严格质检,聚合输出到 `hw<N>_review.md`。

主 controller 在 reviewer 跑完之前还要快速自查:
- 每个小问是否答完
- 删 AI 味("本文将"、"综上所述"、"作为 AI"、空泛背景、装饰性总结)
- PDF 真编译出来了、公式渲染正常无溢出

reviewer 流程会处理: 逻辑链、公式出处、算术 / 单位 / `\boxed{}`、loop-back fix。

## 风格

- Markdown + LaTeX 公式
- 短标题和必要中间步骤
- 不过度解释常规定义
- 朴素学生语气
- **全文用英文**: prose / 单位 / 推理说明都用英文。例外:课程材料本身是中文时(如某些 SJTU 课程的中文 lecture),按 lecture 主语言走。判断标准是 `_md/Lecture *.md` 的主语言。

## 规范

- 文档标题：`<课程名> - Assignment <序号>`（如 `ME3350J - Assignment 1`），全文只此一个标题
- 题号 / 小问号只写编号本身，不带概括式描述
- 题目之间不加横线或分隔符
- 正文不使用着重，禁用 `**X**` / `*X*` / `\textbf{}` / `\emph{}`
- **最终答案用 `\boxed{...}` 框出**(格式约定,不算"着重")。每个小问的最终结果要框,中间步骤不框。
  - 数值类: `\boxed{T_s = 34.1\ ^\circ\text{C}}`
  - 符号表达式: `\boxed{T(x) = T_1 - \frac{q''}{a}\ln\!\left(\frac{ax+b}{b}\right)}`
  - 定性结论: 用一行清楚陈述,不必 \boxed

## Sub-agent prompt 模板(解题)

每道题派一个 sub-agent (`Agent` 工具,`subagent_type: general-purpose`,`model: opus`) 时,prompt 用以下模板填空:

````
You are solving Problem {N} of {COURSE_CODE} {ASSIGNMENT_NAME}. Just this one problem.

Problem statement:
> {VERBATIM_PROBLEM_TEXT_INCLUDING_GIVEN_QUANTITIES}

Reference materials (read with Read tool as needed; **base your physics on these lectures only**, not internet/model knowledge):
- {ABS_PATH_TO}/_md/{ASSIGNMENT_NAME}.md  (full assignment)
- {ABS_PATH_TO}/_md/{LECTURE_1}.md  ({1-line topic hint})
- {ABS_PATH_TO}/_md/{LECTURE_2}.md  ({1-line topic hint})
- {ABS_PATH_TO}/_md/{LECTURE_3}.md  ({1-line topic hint})

Key physics (optional — write 2-4 bullets to scaffold, don't give away answers):
- {hint about which conservation law / which formula category}
- {hint about typical pitfall, e.g. "use K not °C for Stefan-Boltzmann"}

Strict style rules:
- ENGLISH ONLY (no Chinese in prose; lecture-language exceptions per answer.md)
- Markdown with LaTeX math ($...$ inline, $$...$$ display)
- NO bold (no **X**), NO italic emphasis (no *X*), NO horizontal rules
- Start with `## {N}` heading. Sub-parts: `### (a)`, `### (b)`, … NO descriptive titles after the number.
- Short steps. No "本文将...", "Based on the formula above...", "In summary...", or decorative summaries.
- Use lecture-consistent symbols (e.g. $T_{sur}$ single 'r', $q$ rate vs $q''$ flux, $\varepsilon$ not $\epsilon$). If you introduce a non-lecture symbol, define it inline.
- Final answer of each sub-part wrapped in `\boxed{...}` (intermediate steps NOT boxed).
- Compute numerics to a sensible significant-figure count; show key intermediate values for traceability.

Output ONLY the markdown solution starting with `## {N}` — main controller will assemble all problems into one document. No preamble, no explanation of what you did, just the solution.
````

**填空原则**:
- `{VERBATIM_PROBLEM_TEXT}` 直接从 `_md/Assignment N.md` 抄,不要改写或简化(防止 sub-agent 误解题目)
- `{LECTURE_N}` 只列**该题相关**的 lecture;不是所有 lecture 都喂给每个 agent(节省 token)
- `Key physics` 写 1-2 句**方向性提示**,不写解答;留给 sub-agent 自己推
- 5 道独立题 → 5 个并发 Agent 调用一次性发出(一条 assistant message 里 5 个 Agent tool use,parallel 跑)
