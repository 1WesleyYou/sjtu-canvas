#!/usr/bin/env python3
"""轻量级 agent memory — Canvas 数据 + 本地状态 overlay。

单 JSON 文件存储，原子写（.tmp + rename），按 slug 索引。
Canvas 数据为 source of truth（_canvas 字段），sync 时整块覆盖；
local 字段为用户/agent 标注，sync 永远不动它。
"""

import json
import os
import re
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ===== 路径 =====
def get_state_path() -> Path:
    """默认: 项目根目录/state/memory.json，可被环境变量覆盖。"""
    env = os.environ.get("SJTU_CANVAS_STATE")
    if env:
        return Path(env).expanduser()
    here = Path(__file__).resolve().parent
    return here.parent / "state" / "memory.json"


def empty_state() -> dict:
    return {
        "_meta": {"version": 1, "last_full_sync": None},
        "assignments": {},
        "announcements": {},
    }


# ===== 读写 =====
def load_state() -> dict:
    path = get_state_path()
    if not path.exists():
        return empty_state()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    """原子写：tmpfile 同目录 + os.replace。"""
    path = get_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".memory.", suffix=".json.tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=False)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ===== Slug 生成 =====
def make_slug(course_name: str, title: str, max_len: int = 80) -> str:
    """生成人读 slug, e.g. 'ECE4500_step1_project_preference_form'。"""
    m = re.match(r"^[A-Z]+\d+", course_name)
    course_short = m.group(0) if m else re.sub(r"[^\w]", "", course_name)[:10]
    body = re.sub(r"[^\w一-鿿\s-]", "", title)
    body = re.sub(r"\s+", "_", body).strip("_").lower()
    full = f"{course_short}_{body}" if body else course_short
    if len(full) > max_len:
        full = full[:max_len].rstrip("_")
    return full


# ===== Priority 推导 =====
def derive_assignment_priority(due_at_iso) -> str:
    """P0 < 24h, P1 1-7d, P2 7-30d, P3 > 30d / no DDL。"""
    if not due_at_iso:
        return "P3"
    try:
        due = datetime.fromisoformat(due_at_iso.replace("Z", "+00:00"))
    except Exception:
        return "P3"
    hours = (due - datetime.now(timezone.utc)).total_seconds() / 3600
    if hours < 24:
        return "P0"
    if hours < 24 * 7:
        return "P1"
    if hours < 24 * 30:
        return "P2"
    return "P3"


ACTION_KEYWORDS = [
    "by ", "due ", "deadline", "submit", "register", "sign up", "sign-up",
    "complete by", "deliver", "rsvp", "form",
    "截止", "提交", "报名", "选课", "签到", "选组", "请假", "确认", "登录"
]


def derive_announcement_action(title: str, message: str = "") -> bool:
    """轻量判断公告是否含 action item（标题或正文前 500 字含关键词）。"""
    hay = (title + " " + (message or ""))[:500].lower()
    return any(k in hay for k in ACTION_KEYWORDS)


# ===== Merge =====
def merge_assignment(state: dict, canvas_a: dict, course_name: str) -> str:
    """合并一个作业到 state；保留 local 字段。返回 slug。"""
    slug = make_slug(course_name, canvas_a.get("name", "") or "")
    now_iso = datetime.now(timezone.utc).isoformat()
    sub = canvas_a.get("submission") or {}
    workflow = sub.get("workflow_state", "")

    existing = state["assignments"].get(slug) or {}
    local = existing.get("local") or {
        "status": "pending",
        "completed_at": None,
        "intent": "",
        "notes": "",
        "blockers": [],
    }
    # Canvas 显示已交 → 本地一次性升级（不覆盖已是 completed/skipped 的状态）
    if workflow in ("submitted", "graded") and local["status"] in ("pending", "in_progress"):
        local["status"] = "completed"
        local["completed_at"] = local.get("completed_at") or now_iso

    state["assignments"][slug] = {
        "_canvas": {
            "id": canvas_a.get("id"),
            "course_id": canvas_a.get("course_id"),
            "course_name": course_name,
            "title": canvas_a.get("name", ""),
            "due_at": canvas_a.get("due_at"),
            "html_url": canvas_a.get("html_url"),
            "submission_types": canvas_a.get("submission_types", []),
            "points_possible": canvas_a.get("points_possible"),
            "workflow_state": workflow,
        },
        "derived": {
            "priority": derive_assignment_priority(canvas_a.get("due_at")),
        },
        "local": local,
        "last_synced": now_iso,
    }
    return slug


def merge_announcement(state: dict, canvas_t: dict, course_name: str) -> str:
    """合并一个公告到 state；保留 local 字段。返回 slug。"""
    slug = make_slug(course_name, canvas_t.get("title", "") or "")
    now_iso = datetime.now(timezone.utc).isoformat()

    existing = state["announcements"].get(slug) or {}
    local = existing.get("local") or {
        "status": "unseen",
        "acted_at": None,
        "action_taken": "",
        "notes": "",
    }

    has_action = derive_announcement_action(
        canvas_t.get("title", "") or "",
        canvas_t.get("message", "") or "",
    )

    state["announcements"][slug] = {
        "_canvas": {
            "id": canvas_t.get("id"),
            "course_id": canvas_t.get("course_id"),
            "course_name": course_name,
            "title": canvas_t.get("title", ""),
            "posted_at": canvas_t.get("posted_at") or canvas_t.get("created_at"),
            "author": (canvas_t.get("author") or {}).get("display_name", "?"),
            "html_url": canvas_t.get("html_url"),
            "read_state": canvas_t.get("read_state", "unread"),
        },
        "derived": {
            "has_action": has_action,
        },
        "local": local,
        "last_synced": now_iso,
    }
    return slug


# ===== 查询 =====
def list_pending_assignments(state: dict, days_window: int = 7):
    """返回 (slug, item, due_dt) 列表，按 due_at 升序，仅含未完成 + 在窗口内的。"""
    out = []
    cutoff = datetime.now(timezone.utc) + timedelta(days=days_window)
    for slug, item in state["assignments"].items():
        if item["local"]["status"] in ("completed", "skipped"):
            continue
        due_at = item["_canvas"].get("due_at")
        if not due_at:
            continue
        try:
            due_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        except Exception:
            continue
        if due_dt > cutoff:
            continue
        out.append((slug, item, due_dt))
    out.sort(key=lambda x: x[2])
    return out


def list_pending_announcements(state: dict, since_days: int = 30):
    """返回 (slug, item) 列表，仅含:
    1) derived.has_action == True
    2) local.status 还未 acted_on/dismissed/seen
    3) 发布时间在近 since_days 天内（默认 30 天，避免老公告堆积）
    按 posted_at 倒序。"""
    out = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    for slug, item in state["announcements"].items():
        if item["local"]["status"] in ("acted_on", "dismissed", "seen"):
            continue
        if not item["derived"].get("has_action"):
            continue
        posted = item["_canvas"].get("posted_at")
        if posted:
            try:
                if datetime.fromisoformat(posted.replace("Z", "+00:00")) < cutoff:
                    continue
            except Exception:
                pass
        out.append((slug, item))
    out.sort(
        key=lambda x: x[1]["_canvas"].get("posted_at") or "",
        reverse=True,
    )
    return out


# ===== 状态修改 =====
def mark_status(slug: str, status: str, notes: str = "") -> dict:
    """改 local.status；返回 (kind, item) 或 None。"""
    state = load_state()
    now_iso = datetime.now(timezone.utc).isoformat()
    if slug in state["assignments"]:
        item = state["assignments"][slug]
        item["local"]["status"] = status
        if status == "completed":
            item["local"]["completed_at"] = item["local"].get("completed_at") or now_iso
        if notes:
            item["local"]["notes"] = notes
        save_state(state)
        return {"kind": "assignment", "slug": slug, "item": item}
    if slug in state["announcements"]:
        item = state["announcements"][slug]
        item["local"]["status"] = status
        if status == "acted_on":
            item["local"]["acted_at"] = item["local"].get("acted_at") or now_iso
        if notes:
            item["local"]["notes"] = notes
        save_state(state)
        return {"kind": "announcement", "slug": slug, "item": item}
    return None
