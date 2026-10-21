#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
قاعدة بيانات البوت واليوزربوت (SQLite Database Layer)
Multi-User Sessions, Campaigns, Sources, and Anti-Duplicate Storage
================================================================================
الوظيفة:
- تخزين مستخدمي البوت وجلساتهم الخاصة (Session Strings) بشكل آمن ومستقل.
- تخزين الحملات (Campaigns) والقنوات المصدرية والقنوات الهدف لكل مستخدم.
- تتبع آخر رسالة تمت معالجتها (last_processed_id) والهاشات لمنع التكرار نهائياً.
- تسجيل سجل العمليات والأخطاء (Activity Logs & Statistics).
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_database.db")


def get_connection():
    """الحصول على اتصال بقاعدة بيانات SQLite مع دعم القواميس"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """تهيئة جداول قاعدة البيانات والفهارس اللازمة"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. جدول المستخدمين والجلسات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                phone TEXT,
                session_string TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. جدول الحملات (كل مستخدم يملك حملة أو أكثر)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_channel TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                keywords TEXT DEFAULT '[]',
                blacklist TEXT DEFAULT '[]',
                custom_instruction TEXT,
                custom_ad TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)

        # 3. جدول القنوات المصدرية
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

        # 4. جدول سجل النشاط
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

        # 5. جدول منع تكرار المحتوى والهاشات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_hashes (
                content_hash TEXT PRIMARY KEY,
                user_id INTEGER,
                source_channel TEXT,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # إنشاء فهارس لتسريع البحث
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_campaign ON sources(campaign_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_user ON sources(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at DESC)")

        conn.commit()


# ==========================================
# عمليات المستخدمين والجلسات (Users & Sessions)
# ==========================================

def add_or_update_user(user_id: int, username: str = None, first_name: str = None, phone: str = None, session_string: str = None) -> Dict[str, Any]:
    """إضافة أو تحديث بيانات المستخدم"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        now = datetime.utcnow().isoformat()
        if existing:
            query = "UPDATE users SET last_active = ?"
            params = [now]
            if username is not None:
                query += ", username = ?"
                params.append(username)
            if first_name is not None:
                query += ", first_name = ?"
                params.append(first_name)
            if phone is not None:
                query += ", phone = ?"
                params.append(phone)
            if session_string is not None:
                query += ", session_string = ?"
                params.append(session_string)
            query += " WHERE user_id = ?"
            params.append(user_id)
            cursor.execute(query, tuple(params))
        else:
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, phone, session_string, is_active, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """, (user_id, username or "", first_name or "", phone or "", session_string or "", now, now))

        conn.commit()
    return get_user(user_id)


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """جلب بيانات مستخدم محدد"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_users(active_only: bool = True) -> List[Dict[str, Any]]:
    """جلب جميع المستخدمين المسجلين"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_user_session(user_id: int, session_string: str, phone: str = None):
    """تحديث الجلسة النصية الخاصة بالمستخدم"""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        if phone:
            cursor.execute("UPDATE users SET session_string = ?, phone = ?, last_active = ? WHERE user_id = ?",
                           (session_string, phone, now, user_id))
        else:
            cursor.execute("UPDATE users SET session_string = ?, last_active = ? WHERE user_id = ?",
                           (session_string, now, user_id))
        conn.commit()


def delete_user_session(user_id: int):
    """حذف جلسة المستخدم (تسجيل الخروج)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET session_string = '', last_active = ? WHERE user_id = ?",
                       (datetime.utcnow().isoformat(), user_id))
        conn.commit()


# ==========================================
# عمليات الحملات (Campaigns)
# ==========================================

def create_campaign(user_id: int, name: str, target_channel: str,
                    keywords: List[str] = None, blacklist: List[str] = None,
                    custom_instruction: str = None, custom_ad: str = None) -> str:
    """إنشاء حملة جديدة للمستخدم"""
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
    """جلب جميع حملات مستخدم محدد مع مصادرها"""
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
    """جلب جميع الحملات النشطة لكل المستخدمين النشطين الذين يملكون جلسة صالحة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, u.session_string, u.phone, u.username as user_name
            FROM campaigns c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.enabled = 1 AND u.is_active = 1 AND u.session_string IS NOT NULL AND length(u.session_string) > 10
        """)
        campaigns = [dict(r) for r in cursor.fetchall()]

    for c in campaigns:
        c["keywords"] = json.loads(c.get("keywords") or "[]")
        c["blacklist"] = json.loads(c.get("blacklist") or "[]")
        c["sources"] = get_campaign_sources(c["id"])
    return campaigns


def update_campaign(campaign_id: str, **kwargs) -> bool:
    """تعديل بيانات حملة"""
    allowed_fields = ["name", "target_channel", "enabled", "keywords", "blacklist", "custom_instruction", "custom_ad"]
    updates = []
    params = []

    for k, v in kwargs.items():
        if k in allowed_fields:
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
    """حذف حملة وكافة مصادرها"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        conn.commit()
    return True


# ==========================================
# عمليات المصادر (Sources)
# ==========================================

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
    """حذف مصدر محدد"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        conn.commit()
    return True


def get_campaign_sources(campaign_id: str) -> List[Dict[str, Any]]:
    """جلب مصادر حملة معينة"""
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


# ==========================================
# منع التكرار (Anti-Duplication Tracking)
# ==========================================

def is_message_processed(user_id: int, source_channel: str, message_id: int, text_content: str = None) -> bool:
    """التحقق مما إذا كانت الرسالة أو محتواها قد عولج مسبقاً"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # تحقق من رقم الرسالة
        cursor.execute("""
            SELECT 1 FROM logs
            WHERE user_id = ? AND source_channel = ? AND message_id = ? AND status = 'forwarded'
            LIMIT 1
        """, (user_id, source_channel, message_id))
        if cursor.fetchone():
            return True

        # تحقق من بصمة النص إن وجدت
        if text_content and len(text_content.strip()) > 20:
            content_hash = hashlib.sha256(text_content.strip()[:150].encode("utf-8")).hexdigest()
            cursor.execute("SELECT 1 FROM processed_hashes WHERE content_hash = ? LIMIT 1", (content_hash,))
            if cursor.fetchone():
                return True

    return False


def mark_message_processed(user_id: int, source_channel: str, message_id: int, text_content: str = None):
    """تسجيل بصمة الرسالة في جدول الهاشات لمنع تكرارها"""
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


# ==========================================
# السجلات والإحصائيات (Logs & Stats)
# ==========================================

def add_log(user_id: int, campaign_id: str, source_channel: str, target_channel: str,
            message_id: int, original_text: str, processed_text: str, status: str, details: str = None):
    """إضافة عملية لسجل النشاط"""
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


def get_recent_logs(limit: int = 50, user_id: int = None) -> List[Dict[str, Any]]:
    """جلب أحدث العمليات المسجلة"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        else:
            cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]


def get_stats(user_id: int = None) -> Dict[str, Any]:
    """إحصائيات إجمالية للأداء"""
    with get_connection() as conn:
        cursor = conn.cursor()

        if user_id:
            cursor.execute("SELECT count(*) FROM campaigns WHERE user_id = ?", (user_id,))
            total_campaigns = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM sources WHERE user_id = ?", (user_id,))
            total_sources = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs WHERE user_id = ? AND status = 'forwarded'", (user_id,))
            forwarded = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs WHERE user_id = ? AND status = 'ad_replaced'", (user_id,))
            ad_replaced = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs WHERE user_id = ? AND status = 'skipped'", (user_id,))
            skipped = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs WHERE user_id = ?", (user_id,))
            total_processed = cursor.fetchone()[0]

            return {
                "total_users": 1,
                "total_campaigns": total_campaigns,
                "total_sources": total_sources,
                "total_processed": total_processed,
                "total_forwarded": forwarded,
                "total_ad_replaced": ad_replaced,
                "total_skipped": skipped
            }
        else:
            cursor.execute("SELECT count(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM users WHERE length(session_string) > 10")
            logged_in_users = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM campaigns WHERE enabled = 1")
            active_campaigns = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM sources WHERE enabled = 1")
            active_sources = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs WHERE status = 'forwarded'")
            forwarded = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs WHERE status = 'ad_replaced'")
            ad_replaced = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs WHERE status = 'skipped'")
            skipped = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM logs")
            total_processed = cursor.fetchone()[0]

            return {
                "total_users": total_users,
                "logged_in_users": logged_in_users,
                "active_campaigns": active_campaigns,
                "active_sources": active_sources,
                "total_processed": total_processed,
                "total_forwarded": forwarded,
                "total_ad_replaced": ad_replaced,
                "total_skipped": skipped
            }


# التهيئة التلقائية عند استيراد الملف
init_db()

if __name__ == "__main__":
    print("✅ تم فحص وتهيئة قاعدة بيانات SQLite بنجاح:", DB_FILE)
    print("الإحصائيات الحالية:", json.dumps(get_stats(), indent=2, ensure_ascii=False))
