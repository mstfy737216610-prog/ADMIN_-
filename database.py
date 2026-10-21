#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
قاعدة بيانات SQLite (Database Layer)
================================================================================
تخزين الجلسات (Users & Sessions)، الحملات (Campaigns)،
المصادر (Sources)، وسجلات النشر ومنع التكرار.
قاعدة البيانات: database/data.db
================================================================================
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "data.db")


def get_connection():
    """الحصول على اتصال بقاعدة بيانات SQLite"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """تهيئة جداول قاعدة البيانات والفهارس اللازمة"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. جدول المستخدمين والجلسات (مطابق لطلب المستخدم)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                phone TEXT,
                session TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. جدول الحملات وقنوات النشر
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_channel TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                keywords TEXT DEFAULT '[]',
                blacklist TEXT DEFAULT '[]',
                custom_instruction TEXT DEFAULT '',
                custom_ad TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)

        # 3. جدول القنوات والمصادر المراقبة
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                target TEXT NOT NULL,
                title TEXT,
                last_processed_id INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)

        # 4. جدول منع تكرار الرسائل (Message IDs & SHA-256 Hashes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_hashes (
                content_hash TEXT PRIMARY KEY,
                user_id INTEGER,
                source_channel TEXT,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. جدول سجل العمليات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                campaign_id TEXT,
                source_channel TEXT,
                target_channel TEXT,
                message_id INTEGER,
                original_text TEXT,
                processed_text TEXT,
                status TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # الفهارس لتسريع الاستعلامات
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_camp ON sources(campaign_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_user ON sources(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hashes_user ON processed_hashes(user_id)")

        conn.commit()


# ==============================================================================
# 1. دالة حفظ الجلسة في قاعدة البيانات (الكود الأساسي المطلوب بدقة)
# ==============================================================================
def save_session_to_db(user_id: int, phone: str, session_string: str):
    """
    حفظ أو تحديث جلسة المستخدم في قاعدة البيانات database/data.db
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # إنشاء الجدول إذا لم يكن موجوداً
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            phone TEXT,
            session TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    now = datetime.utcnow().isoformat()
    # حفظ أو تحديث بيانات المستخدم
    cursor.execute("""
        INSERT INTO users (user_id, phone, session, is_active, last_active)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            phone = excluded.phone,
            session = excluded.session,
            is_active = 1,
            last_active = excluded.last_active
    """, (user_id, phone, session_string, now))
    conn.commit()
    conn.close()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """جلب بيانات مستخدم محدد"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_active_users() -> List[Dict[str, Any]]:
    """جلب جميع المستخدمين أصحاب الجلسات الصالحة والنشطة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM users
            WHERE is_active = 1 AND session IS NOT NULL AND length(session) > 15
            ORDER BY last_active DESC
        """)
        return [dict(r) for r in cursor.fetchall()]


def delete_user_session(user_id: int):
    """تسجيل خروج المستخدم وحذف جلسته"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET session = '', last_active = ? WHERE user_id = ?",
                       (datetime.utcnow().isoformat(), user_id))
        conn.commit()


# ==============================================================================
# 2. إدارة الحملات وقنوات النشر (Campaigns & Channels)
# ==============================================================================
def create_campaign(user_id: int, name: str, target_channel: str,
                    keywords: List[str] = None, blacklist: List[str] = None,
                    custom_instruction: str = None, custom_ad: str = None) -> str:
    """إنشاء حملة نشر جديدة للمستخدم"""
    camp_id = f"camp_{user_id}_{int(datetime.utcnow().timestamp())}"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO campaigns (id, user_id, name, target_channel, enabled, keywords, blacklist, custom_instruction, custom_ad)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            camp_id,
            user_id,
            name,
            target_channel,
            json.dumps(keywords or [], ensure_ascii=False),
            json.dumps(blacklist or [], ensure_ascii=False),
            custom_instruction or "",
            custom_ad or ""
        ))
        conn.commit()
    return camp_id


def get_user_campaigns(user_id: int) -> List[Dict[str, Any]]:
    """جلب حملات مستخدم معين مع مصادرها"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = [dict(r) for r in cursor.fetchall()]

    for r in rows:
        r["keywords"] = json.loads(r.get("keywords") or "[]")
        r["blacklist"] = json.loads(r.get("blacklist") or "[]")
        r["sources"] = get_campaign_sources(r["id"])
    return rows


def get_all_active_campaigns() -> List[Dict[str, Any]]:
    """جلب جميع الحملات النشطة للمستخدمين الذين يملكون جلسة صالحة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, u.session, u.phone, u.username as user_name
            FROM campaigns c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.enabled = 1 AND u.is_active = 1 AND u.session IS NOT NULL AND length(u.session) > 15
        """)
        rows = [dict(r) for r in cursor.fetchall()]

    for r in rows:
        r["keywords"] = json.loads(r.get("keywords") or "[]")
        r["blacklist"] = json.loads(r.get("blacklist") or "[]")
        r["sources"] = get_campaign_sources(r["id"])
    return rows


def update_campaign(campaign_id: str, **kwargs) -> bool:
    """تعديل بيانات حملة"""
    allowed = ["name", "target_channel", "enabled", "keywords", "blacklist", "custom_instruction", "custom_ad"]
    updates = []
    params = []
    for k, v in kwargs.items():
        if k in allowed:
            updates.append(f"{k} = ?")
            if k in ["keywords", "blacklist"] and isinstance(v, list):
                params.append(json.dumps(v, ensure_ascii=False))
            else:
                params.append(v)
    if not updates:
        return False
    params.append(campaign_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE campaigns SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()
    return True


def delete_campaign(campaign_id: str) -> bool:
    """حذف حملة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        conn.commit()
    return True


# ==============================================================================
# 3. إدارة القنوات المصدرية (Sources)
# ==============================================================================
def add_source(campaign_id: str, user_id: int, target: str, title: str = None) -> str:
    """إضافة قناة مصدرية لحملة"""
    source_id = f"src_{int(datetime.utcnow().timestamp())}_{hashlib.md5(target.encode()).hexdigest()[:6]}"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sources (id, campaign_id, user_id, target, title, last_processed_id, enabled)
            VALUES (?, ?, ?, ?, ?, 0, 1)
        """, (source_id, campaign_id, user_id, target, title or target))
        conn.commit()
    return source_id


def remove_source(source_id: str) -> bool:
    """حذف مصدر"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        conn.commit()
    return True


def get_campaign_sources(campaign_id: str) -> List[Dict[str, Any]]:
    """جلب قنوات مصدرية لحملة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sources WHERE campaign_id = ? ORDER BY created_at ASC", (campaign_id,))
        return [dict(r) for r in cursor.fetchall()]


def update_source_last_id(source_id: str, last_processed_id: int):
    """تحديث آخر معرّف رسالة تم جلبه لهذا المصدر"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE sources SET last_processed_id = ? WHERE id = ?", (last_processed_id, source_id))
        conn.commit()


# ==============================================================================
# 4. منع التكرار وتتبع الهاشات (Anti-Duplication)
# ==============================================================================
def is_message_processed(user_id: int, source_channel: str, message_id: int, text_content: str = None) -> bool:
    """التحقق من عدم تكرار الرسالة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM logs
            WHERE user_id = ? AND source_channel = ? AND message_id = ? AND status = 'forwarded'
            LIMIT 1
        """, (user_id, source_channel, message_id))
        if cursor.fetchone():
            return True

        if text_content and len(text_content.strip()) > 20:
            content_hash = hashlib.sha256(text_content.strip()[:150].encode("utf-8")).hexdigest()
            cursor.execute("SELECT 1 FROM processed_hashes WHERE content_hash = ? LIMIT 1", (content_hash,))
            if cursor.fetchone():
                return True

    return False


def mark_message_processed(user_id: int, source_channel: str, message_id: int, text_content: str = None):
    """حفظ بصمة الرسالة"""
    if text_content and len(text_content.strip()) > 20:
        content_hash = hashlib.sha256(text_content.strip()[:150].encode("utf-8")).hexdigest()
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO processed_hashes (content_hash, user_id, source_channel, message_id)
                    VALUES (?, ?, ?, ?)
                """, (content_hash, user_id, source_channel, message_id))
                conn.commit()
        except Exception:
            pass


# ==============================================================================
# 5. السجلات والإحصائيات (Logs & Stats)
# ==============================================================================
def add_log(user_id: int, campaign_id: str, source_channel: str, target_channel: str,
            message_id: int, original_text: str, processed_text: str, status: str, details: str = None):
    """إضافة سجل عملية"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (user_id, campaign_id, source_channel, target_channel, message_id,
                             original_text, processed_text, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, campaign_id, source_channel, target_channel, message_id,
              original_text[:1000] if original_text else "",
              processed_text[:1000] if processed_text else "",
              status, details or ""))
        conn.commit()


def get_stats(user_id: int = None) -> Dict[str, Any]:
    """جلب إحصائيات الأداء"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT count(*) FROM campaigns WHERE user_id = ?", (user_id,))
            c_cnt = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM sources WHERE user_id = ?", (user_id,))
            s_cnt = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM logs WHERE user_id = ? AND status = 'forwarded'", (user_id,))
            fwd = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM logs WHERE user_id = ? AND status = 'ad_replaced'", (user_id,))
            ad_rep = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM logs WHERE user_id = ? AND status = 'skipped'", (user_id,))
            skp = cursor.fetchone()[0]
            return {
                "campaigns": c_cnt,
                "sources": s_cnt,
                "forwarded": fwd,
                "ad_replaced": ad_rep,
                "skipped": skp
            }
        else:
            cursor.execute("SELECT count(*) FROM users WHERE session IS NOT NULL AND length(session) > 15")
            active_users = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM campaigns WHERE enabled = 1")
            active_camps = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM sources WHERE enabled = 1")
            active_srcs = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM logs WHERE status = 'forwarded'")
            fwd = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM logs WHERE status = 'ad_replaced'")
            ad_rep = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM logs WHERE status = 'skipped'")
            skp = cursor.fetchone()[0]
            return {
                "active_users": active_users,
                "active_campaigns": active_camps,
                "active_sources": active_srcs,
                "total_forwarded": fwd,
                "total_ad_replaced": ad_rep,
                "total_skipped": skp
            }


# التهيئة التلقائية
init_db()

if __name__ == "__main__":
    print("✅ تم فحص وتهيئة قاعدة بيانات SQLite بنجاح:", DB_FILE)
    print("الإحصائيات:", get_stats())
