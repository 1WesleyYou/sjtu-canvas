#!/usr/bin/env python3
"""SJTU Canvas API 核心模块 - 课程/文件/作业/成绩/讨论区"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ_SHANGHAI = timezone(timedelta(hours=8))

# Search for config.json across common Claude Code skill / repo locations.
def _find_config():
    candidates = [
        os.environ.get("SJTU_CANVAS_CONFIG"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),
        os.path.expanduser("~/.claude/skills/sjtu-canvas/config.json"),
        os.path.expanduser("~/Desktop/sjtu-canvas/config.json"),
    ]
    for p in candidates:
        if not p:
            continue
        p = os.path.normpath(p)
        if os.path.exists(p):
            return p
    return None

def load_config():
    path = _find_config()
    if path:
        with open(path) as f:
            return json.load(f)
    return {}

def get_token():
    config = load_config()
    token = config.get("canvas_token", "")
    if not token:
        print("ERROR: Canvas token not configured. Set it in config.json")
        sys.exit(1)
    return token

def get_base_url():
    config = load_config()
    return config.get("base_url", "https://oc.sjtu.edu.cn")

def headers():
    return {"Authorization": f"Bearer {get_token()}"}

def api_get(path, params=None):
    url = f"{get_base_url()}{path}"
    items = []
    while url:
        r = requests.get(url, headers=headers(), params=params)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            items.extend(data)
        else:
            return data
        # 分页
        links = r.headers.get("Link", "")
        url = None
        for link in links.split(","):
            if 'rel="next"' in link:
                url = link.split("<")[1].split(">")[0]
        params = None  # 后续页面 URL 已包含参数
    return items

# ===== 用户 =====
def get_me():
    return api_get("/api/v1/users/self")

# ===== 课程 =====
def list_courses():
    return api_get("/api/v1/courses", {"enrollment_state": "active", "per_page": 50})

# ===== 文件 =====
def list_course_files(course_id, search_term=None):
    params = {"per_page": 100}
    if search_term:
        params["search_term"] = search_term
    return api_get(f"/api/v1/courses/{course_id}/files", params)

def list_course_folders(course_id):
    return api_get(f"/api/v1/courses/{course_id}/folders", {"per_page": 100})

def download_file(file_url, save_path):
    r = requests.get(file_url, headers=headers(), stream=True)
    r.raise_for_status()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return save_path

def download_course_files(course_id, course_name, save_dir, extensions=None):
    """批量下载课程文件，可按扩展名过滤"""
    files = list_course_files(course_id)
    downloaded = []
    for f in files:
        name = f.get("display_name", "")
        if extensions:
            ext = os.path.splitext(name)[1].lower()
            if ext not in extensions:
                continue
        save_path = os.path.join(save_dir, course_name, name)
        if os.path.exists(save_path):
            downloaded.append(save_path)
            continue
        try:
            download_file(f["url"], save_path)
            downloaded.append(save_path)
            print(f"  ✅ {name}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    return downloaded

def recent_files(course_id, since_days=7):
    """近 N 天更新的课程文件（按 updated_at 倒序）。
    适合 'slides 更新' 类查询。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    files = api_get(
        f"/api/v1/courses/{course_id}/files",
        {"per_page": 50, "sort": "updated_at", "order": "desc"},
    )
    recent = []
    for f in files:
        upd = f.get("updated_at")
        if not upd:
            continue
        upd_dt = datetime.fromisoformat(upd.replace("Z", "+00:00"))
        if upd_dt >= cutoff:
            recent.append(f)
    return recent

def find_syllabus(course_id):
    """搜索课程内文件名含 'syllabus' 的 PDF。
    适配 SJTU JI 习惯：syllabus 以 PDF 形式上传，而非 Canvas syllabus_body 字段。"""
    files = list_course_files(course_id, search_term="syllabus")
    return [
        f for f in files
        if f.get("display_name", "").lower().endswith(".pdf")
    ]

# ===== 作业 =====
def list_assignments(course_id):
    return api_get(f"/api/v1/courses/{course_id}/assignments", {"per_page": 50, "order_by": "due_at"})

def get_assignment(course_id, assignment_id):
    return api_get(f"/api/v1/courses/{course_id}/assignments/{assignment_id}")

def get_my_submission(course_id, assignment_id):
    return api_get(f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self")

def submit_assignment(course_id, assignment_id, file_paths):
    """上传文件并提交作业"""
    token = get_token()
    h = headers()
    uploaded_ids = []
    for fp in file_paths:
        fname = os.path.basename(fp)
        fsize = os.path.getsize(fp)
        # Step 1: 请求上传
        r = requests.post(
            f"{get_base_url()}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self/files",
            headers=h,
            data={"name": fname, "size": fsize}
        )
        r.raise_for_status()
        upload_info = r.json()
        # Step 2: 上传文件
        with open(fp, "rb") as f:
            r2 = requests.post(
                upload_info["upload_url"],
                data=upload_info.get("upload_params", {}),
                files={"file": (fname, f)}
            )
            r2.raise_for_status()
            uploaded_ids.append(r2.json()["id"])
    # Step 3: 提交
    r3 = requests.post(
        f"{get_base_url()}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions",
        headers=h,
        data={
            "submission[submission_type]": "online_upload",
            **{f"submission[file_ids][{i}]": fid for i, fid in enumerate(uploaded_ids)}
        }
    )
    r3.raise_for_status()
    return r3.json()

# ===== 成绩 =====
def get_course_grades(course_id):
    assignments = list_assignments(course_id)
    results = []
    for a in assignments:
        sub = a.get("submission", {})
        results.append({
            "name": a["name"],
            "points_possible": a.get("points_possible"),
            "score": sub.get("score") if sub else None,
            "grade": sub.get("grade") if sub else None,
            "workflow_state": sub.get("workflow_state", "") if sub else "",
            "due_at": a.get("due_at"),
        })
    return results

# ===== 公告 / Announcements =====
def list_announcements(course_id):
    """单门课的公告列表（按 posted_at 倒序，含作者、HTML body）。
    走 discussion_topics?only_announcements=true，
    比 /api/v1/announcements 端点更稳定（后者多课查询在某些 Canvas 实例会 500）。"""
    return api_get(
        f"/api/v1/courses/{course_id}/discussion_topics",
        {"only_announcements": "true", "per_page": 50},
    )

def all_announcements(since_days=None):
    """跨所有 active 课程的公告汇总。
    返回扁平 list，每项含 course_name / course_id / title / posted_at / author / message / url。
    since_days=None 拉全部，否则只保留最近 N 天的。"""
    cutoff = None
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    out = []
    for c in list_courses():
        cid = c["id"]
        cname = c.get("name", "?")
        try:
            anns = list_announcements(cid)
        except Exception:
            continue
        for a in anns:
            posted = a.get("posted_at") or a.get("created_at")
            if cutoff and posted:
                try:
                    if datetime.fromisoformat(posted.replace("Z", "+00:00")) < cutoff:
                        continue
                except Exception:
                    pass
            out.append({
                "course_id": cid,
                "course_name": cname,
                "title": a.get("title", ""),
                "posted_at": posted,
                "author": (a.get("author") or {}).get("display_name", "?"),
                "message": a.get("message", ""),
                "url": a.get("html_url", ""),
            })
    out.sort(key=lambda x: x.get("posted_at") or "", reverse=True)
    return out

# ===== 讨论区 =====
def list_discussions(course_id):
    return api_get(f"/api/v1/courses/{course_id}/discussion_topics", {"per_page": 50})

def get_full_discussion(course_id, topic_id):
    return api_get(f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/view")

# ===== DDL 汇总 =====
def get_all_upcoming_ddls():
    """获取所有课程的未来DDL"""
    now = datetime.now(TZ_SHANGHAI)
    courses = list_courses()
    ddls = []
    for c in courses:
        try:
            assignments = list_assignments(c["id"])
        except:
            continue
        for a in assignments:
            due = a.get("due_at")
            if not due:
                continue
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")).astimezone(TZ_SHANGHAI)
            if due_dt > now:
                sub = a.get("submission", {})
                workflow = sub.get("workflow_state", "") if sub else ""
                ddls.append({
                    "course": c.get("name", ""),
                    "course_id": c["id"],
                    "assignment": a["name"],
                    "assignment_id": a["id"],
                    "due_at": due,
                    "due_local": due_dt.strftime("%Y-%m-%d %H:%M"),
                    "submitted": workflow in ["submitted", "graded"],
                    "points": a.get("points_possible"),
                })
    ddls.sort(key=lambda x: x["due_at"])
    return ddls

# ===== Agent Memory 同步 =====
def sync_state():
    """从 Canvas 拉所有作业 + 公告，合并到本地 state/memory.json。
    Canvas → _canvas 字段（整块覆盖），local 字段永远不动。"""
    import state as _state

    s = _state.load_state()
    a_count = 0
    n_count = 0
    courses = list_courses()
    for c in courses:
        cid = c["id"]
        cname = c.get("name", f"course_{cid}")
        # 作业（"Undergraduate Students" 行政频道无作业，跳过）
        if cname != "Undergraduate Students":
            try:
                for a in list_assignments(cid):
                    a["course_id"] = cid
                    _state.merge_assignment(s, a, cname)
                    a_count += 1
            except Exception as e:
                print(f"  ⚠️  {cname} assignments: {e}")
        # 公告
        try:
            for ann in list_announcements(cid):
                ann["course_id"] = cid
                _state.merge_announcement(s, ann, cname)
                n_count += 1
        except Exception as e:
            print(f"  ⚠️  {cname} announcements: {e}")

    s["_meta"]["last_full_sync"] = datetime.now(timezone.utc).isoformat()
    _state.save_state(s)
    return {"assignments": a_count, "announcements": n_count, "path": str(_state.get_state_path())}


# ===== 动向流 =====
def recent_activity(per_page=30):
    """跨所有课程的近期动向流（公告 / 新作业 / 讨论 / 评分变化等）。
    返回 Canvas activity_stream 原始事件列表，按时间倒序。"""
    return api_get("/api/v1/users/self/activity_stream", {"per_page": per_page})

# ===== 日历事件 =====
def list_calendar_events(course_ids, start_date, end_date):
    context_codes = [f"course_{cid}" for cid in course_ids]
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "per_page": 100,
    }
    for i, cc in enumerate(context_codes):
        params[f"context_codes[{i}]"] = cc
    return api_get("/api/v1/calendar_events", params)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "courses"

    if cmd == "courses":
        for c in list_courses():
            print(f"[{c['id']}] {c['name']}")
    elif cmd == "ddls":
        for d in get_all_upcoming_ddls():
            status = "✅" if d["submitted"] else "❌"
            print(f"{status} [{d['course']}] {d['assignment']} → {d['due_local']}")
    elif cmd == "grades":
        for c in list_courses():
            grades = get_course_grades(c["id"])
            scored = [g for g in grades if g["score"] is not None]
            if scored:
                print(f"\n📚 {c['name']}:")
                for g in scored:
                    print(f"  {g['name']}: {g['score']}/{g['points_possible']}")
    elif cmd == "me":
        me = get_me()
        print(f"用户: {me['name']} (ID: {me['id']})")
    elif cmd == "activity":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        for ev in recent_activity(per_page=n):
            t = ev.get("type", "?")
            title = (ev.get("title") or "")[:60]
            upd = (ev.get("updated_at") or "")[:10]
            print(f"[{upd}] {t:15s} {title}")
    elif cmd == "syllabus":
        for c in list_courses():
            hits = find_syllabus(c["id"])
            if hits:
                print(f"\n📚 {c['name']}:")
                for f in hits:
                    print(f"  📄 {f['display_name']} → {f.get('url', '')[:80]}")
    elif cmd == "recent":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        for c in list_courses():
            files = recent_files(c["id"], since_days=days)
            if files:
                print(f"\n📚 {c['name']} (近 {days} 天 {len(files)} 个更新):")
                for f in files:
                    upd = (f.get("updated_at") or "")[:10]
                    print(f"  [{upd}] {f.get('display_name', '?')}")
    elif cmd == "announcements":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else None
        anns = all_announcements(since_days=days)
        scope = f"近 {days} 天" if days else "全部"
        print(f"=== {scope} announcement 共 {len(anns)} 条 ===\n")
        last_course = None
        for a in anns:
            if a["course_name"] != last_course:
                print(f"\n📚 {a['course_name']}")
                last_course = a["course_name"]
            date = (a["posted_at"] or "")[:10]
            print(f"  [{date}] [{a['author'][:18]:18s}] {a['title'][:60]}")
    elif cmd == "sync":
        import state as _state
        print("=== 从 Canvas 同步到本地 memory ===")
        stats = sync_state()
        print(f"  ✅ 作业: {stats['assignments']} 条")
        print(f"  ✅ 公告: {stats['announcements']} 条")
        print(f"  📂 文件: {stats['path']}")
    elif cmd == "pending":
        import state as _state
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        # 公告窗口默认放宽到作业窗口 × 4，但至少 30 天
        ann_days = max(days * 4, 30)
        s = _state.load_state()
        a_list = _state.list_pending_assignments(s, days_window=days)
        n_list = _state.list_pending_announcements(s, since_days=ann_days)
        print(f"=== 近 {days} 天未完成作业 ({len(a_list)} 条) ===")
        for slug, item, due in a_list:
            prio = item["derived"]["priority"]
            course = item["_canvas"]["course_name"]
            title = item["_canvas"]["title"]
            wfs = item["_canvas"].get("workflow_state", "")
            print(f"  {prio} [{course}] {title}")
            print(f"      due: {due.strftime('%Y-%m-%d %H:%M')}  canvas_state: {wfs or '-'}")
            print(f"      slug: {slug}")
        print(f"\n=== 待处理公告 ({len(n_list)} 条) ===")
        for slug, item in n_list:
            course = item["_canvas"]["course_name"]
            title = item["_canvas"]["title"]
            author = item["_canvas"]["author"]
            posted = (item["_canvas"].get("posted_at") or "")[:10]
            print(f"  [{posted}] [{course}] {title}  (by {author})")
            print(f"      slug: {slug}")
    elif cmd == "mark":
        if len(sys.argv) < 4:
            print("Usage: canvas_api.py mark <slug> <status> [notes]")
            print("  assignment status: pending|in_progress|completed|skipped|blocked")
            print("  announcement status: unseen|seen|pending|acted_on|dismissed")
            sys.exit(1)
        import state as _state
        slug = sys.argv[2]
        status = sys.argv[3]
        notes = sys.argv[4] if len(sys.argv) > 4 else ""
        r = _state.mark_status(slug, status, notes)
        if r:
            print(f"✅ {r['kind']} {slug} → {status}")
        else:
            print(f"❌ slug not found: {slug}")
            sys.exit(1)
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: canvas_api.py <command> [args]")
        print("  courses              课程列表")
        print("  me                   当前用户")
        print("  ddls                 所有未来 DDL")
        print("  grades               已出成绩")
        print("  activity [N]         近期动向流（默认 30 条）")
        print("  syllabus             各课 syllabus PDF")
        print("  recent [DAYS]        近 N 天更新的课件（默认 7）")
        print("  announcements [DAYS] 跨课公告汇总（不带参数 = 全部）")
        print("  sync                 拉 Canvas 数据到本地 memory")
        print("  pending [DAYS]       看 memory 里未完成的事（默认 7）")
        print("  mark <slug> <status> 改一条 item 的本地状态")
        sys.exit(1)
