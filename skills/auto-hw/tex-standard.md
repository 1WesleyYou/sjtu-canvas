# tex-standard（tex 规范）

> 答题 / 报告子流程的落盘 PDF 都按这里走。

## 最小 preamble

按需增删，不要堆。答题用：

```latex
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{ctex}              % 中文兜底，正文是英文也保留
\usepackage{amsmath,amssymb}
\usepackage{enumitem}
\usepackage{hyperref}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\begin{document}
% ... 正文 ...
\end{document}
```

报告若 instruction 自带模板就沿用，否则在以上基础上按需加 `graphicx`、`booktabs`、`siunitx`、`subcaption`、`float` 等。

## MD → TeX 简单替换

其余文本与 `$...$` 原样保留。`\boxed{}` / `\frac{}` / `\times` / 希腊字母等已经是合法 TeX。

| Markdown | TeX |
|---|---|
| `# X` | `\section*{X}` |
| `## X` | `\subsection*{X}` |
| `### X` | `\subsubsection*{X}` |
| `**X**` | `\textbf{X}` |
| `*X*` | `\emph{X}` |
| `` `X` `` | `\texttt{X}` |
| `$$...$$` | `\[ ... \]` |
| `- ` 列表 | `itemize` + `\item` |
| `1. ` 列表 | `enumerate` + `\item` |
| `---` 分隔 | `\hrulefill` |
| 表格 (`\|...\|`) | `tabular`（只几行直接写） |

## 编译命令

**优先用打包好的脚本**(一行搞定 MD→TeX→PDF,自动处理 aux dir + double-pass):

```bash
python3 ~/.claude/skills/auto-hw/scripts/build_pdf.py <path-to-answer.md>
# 报告子流程:
python3 ~/.claude/skills/auto-hw/scripts/build_pdf.py <path-to-report.md> --preamble report
```

脚本会:
1. 读 .md,按本文件的 MD→TeX 替换表生成 .tex(同目录同名)
2. xelatex 编译到 `~/.claude/tmp/auto-hw-compile/`(aux 文件不污染工作目录)
3. 含 `\ref{}` / `\tableofcontents` 自动跑两遍
4. 把 .pdf 移到工作目录跟 .md 并排

**手动编译命令(脚本背后做的事)**:

```bash
xelatex -interaction=nonstopmode -output-directory=~/.claude/tmp/auto-hw-compile <file>.tex
```

报告含 `\ref{}` / TOC 时跑两遍让引用收敛。

完成后把生成的 `.pdf` 移到作业目录，源文件（`.md` / `.tex`）保留作可读源。

## 常见报错

先看 `.log`：

- 未转义 `&` / `%` / `_` / `#` / `$` → 加反斜杠
- 未匹配 `$` 或 `$$` → 检查公式块
- `itemize`/`enumerate` 外裸 `\item` → 包进对应环境
- 中文字体缺 → `ctex` 改 `CJKutf8` fallback，或装字体
- `Undefined control sequence` → 缺包，preamble 补 `\usepackage{...}`
