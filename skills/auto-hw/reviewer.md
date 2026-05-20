# reviewer（auto-hw 子流程）

> 解题完成 + LaTeX 编译完之后的严格质检层。
> 三个 reviewer sub-agent 并行跑各自的独立维度,主 controller 聚合后产出 `hw<N>_review.md` 并给用户简报。

## 触发场景

- `answer.md` Phase 4 (review 步骤) 自动触发
- `report.md` 同理可调用(报告类作业)
- 用户显式说 "review 一下作业 / 检查 hw / 校对一下"

## 三个 reviewer 的分工

| Reviewer | 必读输入 | 检查维度 | **不**碰 |
|---|---|---|---|
| **R1 — Logic** | `hw_answer.md` + `_md/Assignment N.md` | 解题逻辑链是否合理: 假设 → 调用的物理定律 → 代数推导 → 最终答案。每一步推理是否站得住 | 算术、单位、公式是否来自课件 |
| **R2 — Formula + Symbol provenance** | `hw_answer.md` + `_md/Lecture *.md`(全部相关 slide) | (1) 每条公式 / 方法是否能在课件里找到出处;(2) **学生使用的符号是否与 lecture 一致**(如 $T_{sur}$ vs $T_{surr}$, $q$ vs $q''$, $G_S$ vs $G$ 这种细节);(3) 有没有用了模型自己记忆的或互联网的公式 | 算术对错、最终格式 |
| **R3 — Calc/Unit/Format** | `hw_answer.md` + `hw_answer.tex` | (a) 数值重算每一步;(b) 量纲 / 单位一致性;(c) 每个小问最终答案是否用 `\boxed{...}` 框出 | 公式来源、推理逻辑 |

> 这种分工是为了**让每个 reviewer 责任收敛、不互相补丁**。比如 R1 不应该批评单位写错(那是 R3 的工作),R3 不应该说"这公式来历不明"(那是 R2)。

## 调度

并行调度,跟 `answer.md` 解题阶段一样:

```
Agent 工具
  subagent_type: general-purpose
  model: opus
  ×3 并发
```

每个 reviewer 输出结构化 Markdown,模板:

```markdown
# Review Report — <Reviewer Name>

## P1
- **Verdict**: ✅ OK / ⚠️ Issue / ❌ Fatal
- **Findings**:
  - 引用具体位置 (题号/小问号/公式行)
  - 简述问题
  - 建议修正

## P2
...

(每题独立 section, 即便 ✅ OK 也要写出来,便于后面聚合)
```

## 主 controller 聚合

把 3 份 review 合成单一文件 `hw<N>_review.md`,放在作业目录(跟 hw_answer.md 同目录):

```markdown
# Review Report — <Course> Assignment <N>

> Overall Verdict: ✅ APPROVED / ⚠️ MINOR ISSUES / ❌ MAJOR ISSUES
> 跑时间: <timestamp>

## Summary matrix

| # | Logic (R1) | Formula (R2) | Calc/Unit/Box (R3) |
|---|---|---|---|
| P1 | ✅ | ✅ | ⚠️ box missing on (b) |
| P2 | ✅ | ✅ | ✅ |
| ...

## Detailed findings

### P1 — <题目主题>
**Logic (R1)**: ...
**Formula (R2)**: ...
**Calc/Unit/Box (R3)**: ...

### P2 — ...

(按题分组合并, 同题三个 reviewer 的输出放一起方便修)

## Suggested actions

- R1 / R2 issues 优先级最高(推理或物理错误)
- R3 issues 是机械修正(改单位 / 加 box / 改算术)
- 给出 3 个用户选项见下文
```

## Verdict 规则

- **❌ MAJOR**: R1 或 R2 标出任何 ❌ Fatal,或 ≥3 个 ⚠️ Issue
- **⚠️ MINOR**: R1/R2 只有 ⚠️ Issue ≤ 2 个 **或** R3 只是格式 / 单位修正
- **✅ APPROVED**: 三个 reviewer 全部 ✅

## Loop-back

聚合完成后,主 controller 给用户三个选项:

| 选项 | 说明 |
|---|---|
| **A. 自动 fix** | 把每个 ⚠️/❌ issue 作为 constraint,重新派对应题目的 answer sub-agent(只重做有问题的题,不全做),完成后再走一次 reviewer 直到 ✅ |
| **B. 手动 fix** | 用户自己读 `hw_review.md` 改,改完后说 "再 review 一遍" 触发新一轮 |
| **C. 接受现状** | 把 review 报告留作记录,不改作业 |

如果初始就是 ✅ APPROVED,跳过 loop-back,直接告诉用户"通过"。

## 风格 / 规范

- Reviewer 输出**用中文**(便于用户阅读)
- 引用具体位置必须**精确到小问号**,不能"P2 那里好像有问题"这种模糊表述
- Reviewer 不重写答案,只指出问题 + 给方向(具体重写由 loop-back 的 answer sub-agent 做)
- **不删 AI 味的话术**(reviewer 输出本身就是报告类文本,允许严肃语气)

## 与其他子流程的关系

- 答题 (`answer.md`) → 默认走完后调本流程
- 报告 (`report.md`) → 同样可调,但 R2 的检查范围可能要扩到 instruction / 数据;R3 检查 \ref / \label 而不是 \boxed
- 读后感 (`reflection.md`) → **不走** reviewer(文本类作业靠人工判断更合适)

---

## Sub-agent prompt 模板

每个 reviewer / fix sub-agent 用对应模板填空发出(`Agent` 工具,`subagent_type: general-purpose`,`model: opus`)。

### R1 — Logic Reviewer

````
You are R1 (Logic Reviewer) for {COURSE_CODE} {ASSIGNMENT_NAME}. Strict TA mode, no rubber-stamping.

Files to read (Read tool):
- {ABS_PATH_TO}/hw{N}_answer.md (student's solution)
- {ABS_PATH_TO}/_md/{ASSIGNMENT_NAME}.md (original problem statements)

Your role: For each of the {NUM_PROBLEMS} problems, audit ONLY the solving logic chain:
- Are stated assumptions reasonable and complete? (e.g. "1D steady, no source, vacuum, large enclosure")
- Is the correct physical law invoked? (Fourier / Newton / Stefan-Boltzmann / energy balance / ...)
- Does the chain "assumption → law → equation → algebra → final answer" hold without unjustified leaps?
- Are boundary conditions / special cases (limits, edge conditions) handled rigorously?
- Are missing terms flagged?

You DO NOT check (other reviewers handle these):
- Arithmetic (R3)
- Unit consistency (R3)
- Whether formulas are sourced from lectures (R2)
- \boxed{} formatting (R3)

Output format (Markdown, all problems get a section even if OK):

# Review Report — R1 Logic

## P1
- Verdict: ✅ OK | ⚠️ Issue | ❌ Fatal
- Findings:
  - <具体位置 + 引用学生原文 + 解释问题>
  - 建议: <修正方向>

## P2 ... (continue for all problems)

Output ONLY this report, no preamble or epilogue. Chinese prose, English/math for technical terms.
````

### R2 — Formula + Symbol Provenance Reviewer

````
You are R2 (Formula + Symbol Provenance) for {COURSE_CODE} {ASSIGNMENT_NAME}.

Files to read:
- {ABS_PATH_TO}/hw{N}_answer.md
- {ABS_PATH_TO}/_md/{LECTURE_1}.md
- {ABS_PATH_TO}/_md/{LECTURE_2}.md
- {ABS_PATH_TO}/_md/{LECTURE_3}.md
... (all lectures covered up to this assignment)

Course philosophy: "公式和知识应当基于课堂内容,而非互联网或大模型自身知识"

Two-part check for each problem:

**Part A — Formula provenance**:
List every formula / method used; cite where it appears in lectures (Lecture N + page if identifiable). Flag external formulas (textbook not in lectures, model memory, internet).

Acceptable: stated in a lecture, derivable from lecture content, standard constants (σ, π).
NOT acceptable: textbook formula not introduced, method requiring concept not yet taught.

**Part B — Symbol consistency**:
For each symbol used, verify it matches lecture notation:
- Temperature subscripts ($T_{surr}$ vs $T_{sur}$, $T_s$ vs $T_w$ — match what lecture writes)
- Heat: $q$ (rate, W) vs $q''$ (flux, W/m²)
- Greek letters: $\varepsilon$ vs $\epsilon$, $\sigma$, $\alpha$
- Latent heat: $h_{fg}$ (vaporization, NOT in most thermo-only lectures!) vs $h_{sf}$ (fusion)
- Solar / radiation: $G$ vs $G_S$, $T_{sur}$ vs $T_{sky}$
- Subscripts that collide across problems (e.g. $T_c$ for "cell" vs "cover")

When flagging a symbol issue: state what student wrote, what lecture uses, and severity (⚠️ minor cosmetic / ❌ confusing).

You DO NOT check arithmetic, units, or \boxed formatting (R3's job) — only formula sources + symbol matching.

Output format:

# Review Report — R2 Formula + Symbol

## P1
- Verdict: ✅ | ⚠️ | ❌
- Formulas used + sources:
  - `<formula>` — L? page ? (description)
- Symbol consistency:
  - $X$ — matches L? ✓ | conflicts with L? Example ? (different meaning)
- Issues: <if any>

## P2 ... (continue)

## Cross-problem symbol audit
(Table listing every symbol used across problems vs lecture usage)

Output ONLY this report.
````

### R3 — Calculation / Unit / Format Reviewer

````
You are R3 (Calculation / Unit / Format) for {COURSE_CODE} {ASSIGNMENT_NAME}. Mechanical audit, no physics judgment.

Files to read:
- {ABS_PATH_TO}/hw{N}_answer.md (Markdown source)
- {ABS_PATH_TO}/hw{N}_answer.tex (compiled LaTeX — used to verify \boxed sync)

Three independent checks for every sub-part:

(a) **Arithmetic recomputation**: Redo each numerical line independently from scratch.
  - σ = 5.67 × 10⁻⁸ W/(m²·K⁴), π ≈ 3.14159265
  - Maintain full precision in intermediate steps; round only at display
  - Flag mismatches; tolerance ±1 in the last significant figure quoted by student

(b) **Unit / dimensional consistency**: For each equation, check LHS units match RHS.
  - W vs kW, J vs kJ, m vs mm
  - K vs °C (especially Stefan-Boltzmann needs K!)
  - Dimensional consistency in final answer; explicit unit on every \boxed result

(c) **\boxed{} format**: {NUM_SUBPARTS} final answers expected.
  - Each sub-part must have exactly one \boxed{...} on its FINAL result
  - Cross-check .tex actually has \boxed where .md does (md is source, .tex is what compiled)
  - Intermediate equations must NOT be boxed
  - Qualitative-conclusion sub-parts (Yes/No without numeric final) don't need \boxed

You DO NOT check logic correctness (R1) or formula provenance (R2).

Output format:

# Review Report — R3 Calc/Unit/Format

## P1
- Verdict: ✅ | ⚠️ | ❌
- Arithmetic: <recomputed value vs student's, OK or mismatch>
- Units: <verdict + any mismatches>
- \boxed:
  - (a): ✅ has \boxed on final | ⚠️ missing | ⚠️ boxed wrong thing
  - (b): ...
- Issues:
  - <具体行号 / 引用 / 建议>

## P2 ... (continue)

Output ONLY this report.
````

### Fix sub-agent (loop-back)

派 fix agent 重做被 flag 的题(option A 自动 fix)。每题一个 agent,并行调度。

````
You are fixing Problem {N} ({BRIEF_DESCRIPTION}) in {COURSE_CODE} {ASSIGNMENT_NAME} based on reviewer feedback.

Files to read:
- {ABS_PATH_TO}/hw{N}_answer.md (your current `## {N}` section)
- {ABS_PATH_TO}/_md/{ASSIGNMENT_NAME}.md (original problem)
- {ABS_PATH_TO}/_md/{relevant LECTURE files}

Issues to fix (verbatim from review):
1. (R{?}) {description of issue + suggested fix}
2. (R{?}) {description}
...

PRESERVE these numerical results (don't recompute, don't change):
- {sub-part}: {value with unit}
- ...

(If R3 flagged an arithmetic fix, then DO change that number and follow the new value through to the final \boxed.)

Style rules (STRICT, same as initial solving):
- ENGLISH ONLY
- Markdown + LaTeX math
- NO bold/italic
- Lecture-consistent symbols (define non-lecture symbols inline)
- Start with `## {N}`. Sub-parts `### (a)`, `### (b)`, ...
- Final of each sub-part wrapped `\boxed{...}`
- Don't rewrite parts that the reviewers didn't flag — minimal targeted changes

Output ONLY the new `## {N}` section, no preamble. Main controller will paste it into hw{N}_answer.md replacing the old section.
````

---

## 符号陷阱清单(R2 重点查的"小恶魔")

历史教训汇总,R2 每次都查一遍这些:

| 符号 | 常见误用 | 课件标准 | 严重度 |
|---|---|---|---|
| $T_{sur}$ vs $T_{surr}$ | 学生写双 r | Incropera 系列课件多用单 r `T_{sur}` | ⚠️ minor 但要 catch |
| $T_c$ | 同符号在 P3 (cell) 和 P5 (cover) 不同物理 | 任一课件 Example 用过即占位 | ❌ 必须 inline 定义 |
| $h_{fg}$ vs $h_{sf}$ | 学生用 $h_{fg}$ (vaporization) | 课件只引入 $h_{sf}$ (fusion) | ⚠️ inline 定义即可 |
| $G_S$ vs $G$ | "S" 表示 solar 是 Incropera 习惯 | 课件用 bare $G$ for irradiation | ⚠️ inline 定义 |
| $T_{sky}$ | solar collector 题特有 | 课件用 $T_{sur}$ for surroundings | ⚠️ inline 定义 |
| $q$ vs $q''$ | 学生用 $q_{conv}$ 而 $q$ 应是 rate (W) | 课件 surface energy balance 用 flux $q''_{conv}$ (W/m²) | ⚠️ 量纲对就 OK,但应保持一致 |
| $\varepsilon$ vs $\epsilon$ | 两种 LaTeX 命令都渲染 | 课件用 `\varepsilon` (双 e 形) | ⚠️ 视觉上能区分即可 |
| $T_{wall}$ vs $T_\infty$ | 辐射 surroundings 默认等于 ambient | 显式假设要声明 | ⚠️ 隐式假设要 flag |

---

## Verdict 双轨评估(经验)

按规则给的 verdict 有时跟实际严重程度不一致,**报告里同时给两个**:

| 维度 | 触发条件 | 含义 |
|---|---|---|
| **严格 Verdict (按规则)** | R1/R2 任一 ❌ Fatal 或 ≥3 个 ⚠️ Issue → MAJOR | reviewer.md 规则口径 |
| **实际严重程度 (经验)** | 最终数值正确 + 假设未声明 + 推理跳步 → 实际 MINOR | 真正影响成绩 / 物理意义的口径 |

**典型 case**:
- R1 抓出 3 个"假设没声明"⚠️ → 规则触发 MAJOR,但物理答案全对 → **practical MINOR**
- R3 抓出 1 处算术 ~2% 偏差导致最终值差 0.1 °C → 规则 minor,但**临界** → 提醒用户复核
- R2 抓出 ❌ 符号冲突($T_c$ 双义) → 规则 MAJOR,**实际**也 MAJOR(读者真会读错)

Verdict 双轨写法:
```
> 严格 Verdict: ⚠️ MAJOR (R1 ≥3 ⚠️)
> 实际严重程度: ⚠️ MINOR — 数值全对,只是假设声明不充分
```

让用户自己判断要不要花 token loop-back fix。
