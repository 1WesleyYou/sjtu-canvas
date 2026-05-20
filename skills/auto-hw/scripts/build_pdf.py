#!/usr/bin/env python3
"""
build_pdf.py — Compile a Markdown answer/report into a PDF via xelatex.

Workflow:
  1. Read <input>.md
  2. Apply MD → TeX substitutions per ~/.claude/skills/auto-hw/tex-standard.md
  3. Write <input>.tex (sibling of .md)
  4. Run xelatex with aux files in ~/.claude/tmp/auto-hw-compile/
  5. Move the produced PDF next to the .md (overwriting if exists)
  6. Print the result path + size

Usage:
  python3 build_pdf.py <path-to-answer.md>
  python3 build_pdf.py <path-to-answer.md> --preamble report   # for report.md sub-flow

Exit codes:
  0  PDF written successfully
  1  xelatex failed (log surfaced on stdout)
  2  bad arguments / missing input file
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Minimal preamble for answer.md sub-flow. tex-standard.md says:
# "答题用" → minimal article + ctex + amsmath + amssymb + enumitem + hyperref.
PREAMBLE_ANSWER = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{ctex}
\usepackage{amsmath,amssymb}
\usepackage{enumitem}
\usepackage{hyperref}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\begin{document}
"""

# Report sub-flow needs the same baseline + graphics + tables + units.
PREAMBLE_REPORT = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{ctex}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{siunitx}
\usepackage{subcaption}
\usepackage{float}
\usepackage{enumitem}
\usepackage{hyperref}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\begin{document}
"""

PREAMBLES = {"answer": PREAMBLE_ANSWER, "report": PREAMBLE_REPORT}


def md_to_tex_body(text: str) -> str:
    """Apply the MD → TeX substitutions from tex-standard.md.

    Order matters:
      - $$ ... $$ first (greedy multiline) so subsequent heading regexes do
        not accidentally chew text inside a math block.
      - Then headings, deepest first to avoid # eating ## etc. (using anchored
        ^ regexes per line, so order is actually safe — but we still do deepest
        first for clarity).
    """
    # Display math: $$ ... $$  →  \[ ... \]
    text = re.sub(r"\$\$(.+?)\$\$", r"\\[\1\\]", text, flags=re.DOTALL)
    # Headings
    text = re.sub(r"^### (.+)$", r"\\subsubsection*{\1}", text, flags=re.M)
    text = re.sub(r"^## (.+)$", r"\\subsection*{\1}", text, flags=re.M)
    text = re.sub(r"^# (.+)$", r"\\section*{\1}", text, flags=re.M)
    return text


def compile_pdf(md_path: Path, preamble_name: str = "answer") -> Path:
    """Compile md_path to <stem>.pdf next to it; return PDF path."""
    if not md_path.is_file():
        sys.exit(f"❌ Input not found: {md_path}")
    if preamble_name not in PREAMBLES:
        sys.exit(f"❌ Unknown preamble '{preamble_name}'. Use one of: {list(PREAMBLES)}")

    tex_path = md_path.with_suffix(".tex")
    pdf_path = md_path.with_suffix(".pdf")
    aux_dir = Path.home() / ".claude" / "tmp" / "auto-hw-compile"
    aux_dir.mkdir(parents=True, exist_ok=True)

    body = md_to_tex_body(md_path.read_text(encoding="utf-8"))
    tex_path.write_text(
        PREAMBLES[preamble_name] + body + "\n\\end{document}\n",
        encoding="utf-8",
    )
    print(f"📝 wrote {tex_path}")

    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-output-directory",
        str(aux_dir),
        str(tex_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Report.md sub-flow asks for double-pass when \ref{} / TOC present.
    # Cheap heuristic: if the .tex contains \ref or \tableofcontents, re-run.
    tex_src = tex_path.read_text(encoding="utf-8")
    if r"\ref{" in tex_src or r"\tableofcontents" in tex_src:
        print("🔁 \\ref or \\tableofcontents detected — running xelatex twice")
        result = subprocess.run(cmd, capture_output=True, text=True)

    generated_pdf = aux_dir / pdf_path.name
    if not generated_pdf.exists():
        log_path = aux_dir / (md_path.stem + ".log")
        print("❌ xelatex did not produce a PDF.")
        if log_path.exists():
            log = log_path.read_text(encoding="utf-8", errors="replace")
            print("--- xelatex log (last 1500 chars) ---")
            print(log[-1500:])
        else:
            print("--- xelatex stdout tail ---")
            print(result.stdout[-1500:])
        sys.exit(1)

    generated_pdf.replace(pdf_path)
    print(f"✅ {pdf_path}  ({pdf_path.stat().st_size // 1024} KB)")
    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("md_path", help="Path to the .md source")
    parser.add_argument(
        "--preamble",
        default="answer",
        choices=sorted(PREAMBLES.keys()),
        help="Which preamble to use (default: answer)",
    )
    args = parser.parse_args()
    compile_pdf(Path(args.md_path).expanduser().resolve(), args.preamble)


if __name__ == "__main__":
    main()
