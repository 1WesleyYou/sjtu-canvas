#!/usr/bin/env python3
"""Canvas 每日摘要 + 自动下载新课件"""

import os
import sys
import re
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 让 import canvas_api 能找到同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canvas_api as cv

TZ_SHANGHAI = cv.TZ_SHANGHAI

STATE_FILE = Path.home() / ".canvas_digest_state.json"

DIGEST_DIR = Path.home() / "Downloads" / "26SU" / "daily_digests"
SAVE_DIR_DEFAULT = Path.home() / "Downloads" / "26SU" / "canvas"

COURSE_SHORTNAME = {
    "ECE4500JSU2026": "ECE4500J",
    "ME3350JSU2026":  "ME3350J",
    "ME3600JSU2026":  "ME3600J",
    "ME3820JSU2026":  "ME3820J",
    "ME4950JSU2026":  "ME4950J",
}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_file_ids": {}, "seen_announcement_ids": {}, "last_run": None}


def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False))


def days_left_str(due_at_str):
    due = datetime.fromisoformat(due_at_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = due - now
    total_secs = delta.total_seconds()
    days = delta.days
    hours = int((total_secs % 86400) / 3600)
    local_due = due.astimezone(TZ_SHANGHAI)
    date_str = local_due.strftime("%m/%d %H:%M")
    if total_secs < 0:
        return date_str, "~~已过期~~", "⚫"
    elif days == 0:
        return date_str, f"今天 还剩{hours}h ⚠️", "🔴"
    elif days == 1:
        return date_str, "明天到期 ⚠️", "🔴"
    elif days <= 3:
        return date_str, f"还剩{days}天 ⚠️", "🟠"
    elif days <= 7:
        return date_str, f"还剩{days}天", "🟡"
    else:
        return date_str, f"还剩{days}天", "🟢"


def safe_dirname(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip()


def download_new_files(courses, save_dir, state, since_days=3):
    """下载近 since_days 天更新的新课件，保留 Canvas 文件夹层级，跳过已下载的"""
    new_downloads = {}
    for c in courses:
        cid = str(c["id"])
        cname = c.get("name", cid)
        if cname == "Undergraduate Students":
            continue
        short = COURSE_SHORTNAME.get(cname, safe_dirname(cname))

        seen = state["seen_file_ids"].setdefault(cid, [])
        try:
            files = cv.recent_files(c["id"], since_days=since_days)
        except Exception:
            continue
        if not files:
            continue

        # Build folder map once per course (only if needed)
        try:
            folder_map = cv.build_folder_map(int(cid))
        except Exception:
            folder_map = {}

        downloaded_this = []
        for f in files:
            fid = str(f.get("id"))
            if fid in seen:
                continue
            fname = f.get("display_name", fid)
            rel_folder = folder_map.get(f.get("folder_id"), "")
            dest = save_dir / short / rel_folder / fname if rel_folder else save_dir / short / fname
            if dest.exists():
                seen.append(fid)
                continue
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                cv.download_file(f["url"], str(dest))
                seen.append(fid)
                display = f"{rel_folder}/{fname}" if rel_folder else fname
                downloaded_this.append(display)
                print(f"  ⬇️  [{short}] {display}")
            except Exception as e:
                print(f"  ❌  [{short}] {fname}: {e}")

        if downloaded_this:
            new_downloads[short] = downloaded_this

    return new_downloads


def run():
    cfg = cv.load_config()
    save_dir = Path(cfg.get("save_dir", str(SAVE_DIR_DEFAULT))).expanduser()
    save_dir.mkdir(parents=True, exist_ok=True)
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    now_str = datetime.now(TZ_SHANGHAI).strftime("%H:%M")

    print(f"[{today} {now_str}] Canvas 每日同步开始...")

    # ── 1. 课程列表 ──────────────────────────────────────────────
    courses = cv.list_courses()
    real_courses = [c for c in courses if c.get("name") != "Undergraduate Students"]

    # ── 2. DDL ───────────────────────────────────────────────────
    print("拉取作业截止时间...")
    ddls = cv.get_all_upcoming_ddls()

    # ── 3. 公告（只取今天新增，首次运行取近7天）──────────────────
    last_run = state.get("last_run")
    ann_days = 1 if last_run else 7
    print(f"拉取近 {ann_days} 天公告...")
    raw_anns = cv.all_announcements(since_days=ann_days)
    seen_ann_ids = state["seen_announcement_ids"]
    new_anns = []
    for a in raw_anns:
        aid = str(a.get("course_id", "")) + "_" + str(a.get("title", ""))
        if aid not in seen_ann_ids:
            new_anns.append(a)
            seen_ann_ids[aid] = today

    # ── 4. 下载新课件 ─────────────────────────────────────────────
    print("检查并下载新课件...")
    new_files = download_new_files(real_courses, save_dir, state, since_days=ann_days)

    # ── 5. 生成摘要 Markdown ──────────────────────────────────────
    lines = [
        f"# 📚 Canvas 每日摘要 — {today}",
        f"> 生成时间: {now_str} | 下次同步: 明天早上 8:00",
        "",
    ]

    # DDL 表格
    lines += ["## 📝 待完成作业", ""]
    if ddls:
        lines.append("| 状态 | 课程 | 作业 | 截止时间 | 倒计时 |")
        lines.append("|:---:|------|------|----------|--------|")
        for d in ddls:
            cname = d["course"]
            short = COURSE_SHORTNAME.get(cname, cname)
            date_s, countdown, icon = days_left_str(d["due_at"])
            submitted = "✅" if d.get("submitted") else "❌"
            pts = f" ({int(d['points'])}分)" if d.get("points") else ""
            aname = d["assignment"].strip()
            lines.append(f"| {icon} | {short} | {aname}{pts} | {date_s} | {countdown} |")
    else:
        lines.append("*暂无待完成作业* ✅")
    lines.append("")

    # 新公告
    lines += ["## 📢 新公告", ""]
    ann_courses = [c for c in real_courses if c.get("name") != "Undergraduate Students"]
    school_anns = [a for a in new_anns if a["course_name"] == "Undergraduate Students"]
    course_anns = [a for a in new_anns if a["course_name"] != "Undergraduate Students"]

    if course_anns:
        lines.append("### 课程公告")
        for a in course_anns:
            short = COURSE_SHORTNAME.get(a["course_name"], a["course_name"])
            posted = (a.get("posted_at") or "")[:10]
            title = a["title"]
            url = a.get("url", "")
            author = a.get("author", "").strip()
            link = f"[{title}]({url})" if url else title
            lines.append(f"- **[{short}]** {link} — *{author}* ({posted})")
        lines.append("")

    if school_anns:
        lines.append("<details><summary>📌 学院通知（点击展开）</summary>\n")
        for a in school_anns:
            posted = (a.get("posted_at") or "")[:10]
            title = a["title"]
            url = a.get("url", "")
            link = f"[{title}]({url})" if url else title
            lines.append(f"- {link} ({posted})")
        lines.append("\n</details>\n")

    if not new_anns:
        lines.append("*今天暂无新公告*")
        lines.append("")

    # 新课件
    lines += ["## 📁 新课件下载", ""]
    if new_files:
        for course_short, fnames in new_files.items():
            lines.append(f"**{course_short}** ({len(fnames)} 个)")
            for fn in fnames:
                lines.append(f"  - {fn}")
        lines.append(f"\n已保存到: `{save_dir}`")
    else:
        lines.append("*今天暂无新课件*")
    lines.append("")

    # 文件夹提示
    lines += [
        "---",
        f"**文件存储路径:** `{save_dir}/{{课程代号}}/`",
        f"**历史摘要:** `{DIGEST_DIR}/`",
    ]

    digest_text = "\n".join(lines)
    digest_file = DIGEST_DIR / f"{today}.md"
    digest_file.write_text(digest_text, encoding="utf-8")

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    print(f"\n✅ 摘要已生成: {digest_file}")
    print("\n" + "─" * 60)
    print(digest_text)

    return digest_file


if __name__ == "__main__":
    run()
