"""
Mednitai — Database Layer
=========================
Firebase Firestore: save, fetch, admin.
"""

import streamlit as st
from datetime import datetime
import json
import threading
import re
import hashlib


# ============================================================
# Firebase Init — Module-level cache (works from threads too!)
# ============================================================

_db_client = None
_db_init_lock = threading.Lock()
_db_init_attempted = False
_db_init_error = None


def _init_firebase_safe():
    """Initialize Firebase — thread-safe, works from background threads."""
    global _db_client, _db_init_attempted, _db_init_error
    
    if _db_client is not None:
        return _db_client
    
    if _db_init_attempted and _db_client is None:
        return None
    
    with _db_init_lock:
        if _db_client is not None:
            return _db_client
        if _db_init_attempted:
            return None
        
        _db_init_attempted = True
        
        try:
            from google.cloud import firestore
            from google.oauth2 import service_account
            
            try:
                firebase_config = dict(st.secrets["firebase"])
            except Exception as e:
                _db_init_error = f"Cannot read st.secrets: {e}"
                return None
            
            if 'private_key' in firebase_config:
                firebase_config['private_key'] = firebase_config['private_key'].replace('\\n', '\n')
            
            credentials = service_account.Credentials.from_service_account_info(firebase_config)
            _db_client = firestore.Client(credentials=credentials, project=firebase_config.get('project_id'))
            return _db_client
        except Exception as e:
            _db_init_error = str(e)
            return None


def get_db_status():
    """Returns (is_connected: bool, error_message: str or None)."""
    return (_db_client is not None, _db_init_error)


@st.cache_resource
def _init_firebase():
    return _init_firebase_safe()


# ============================================================
# User ID Sanitization — תיקון ValueError של Firestore
# ============================================================
def _make_safe_user_id(user_name):
    """
    יוצר user_id ASCII-only ל-Firestore.
    Firestore לא תמיד מטפל טוב בתווי עברית כ-IDs.
    הפתרון: hash של השם → תמיד ASCII-only, תמיד ייחודי, לא ריק.
    """
    if not user_name:
        return "anonymous_user"
    
    raw = str(user_name).strip()
    if not raw:
        return "anonymous_user"
    
    # יוצר hash מהשם המקורי (כך ש"דוד כהן" תמיד יקבל את אותו ID)
    name_hash = hashlib.md5(raw.encode('utf-8')).hexdigest()[:16]
    
    # מנסה גם להוציא חלק קריא מהשם (אנגלית/מספרים בלבד)
    readable = re.sub(r'[^a-zA-Z0-9]+', '', raw)[:20].lower()
    
    if readable:
        return f"u_{readable}_{name_hash[:8]}"
    else:
        # רק עברית/תווים מיוחדים — נשתמש ב-hash בלבד
        return f"user_{name_hash}"


# ============================================================
# DB Manager
# ============================================================
class DB_Manager:

    def _get_db(self):
        client = _init_firebase_safe()
        if client is not None:
            return client
        try:
            return _init_firebase()
        except Exception:
            return None

    def save_test(self, user_name, results, report, collection,
                  hesitation_count=0, extra_data=None):
        """Save test results to Firestore."""
        db = self._get_db()
        if not db:
            try:
                st.warning("⚠️ Firebase לא זמין — בדוק את ה-secrets")
            except Exception:
                pass
            return False

        # ולידציה של שם משתמש
        if not user_name or not str(user_name).strip():
            try:
                st.warning("⚠️ שם משתמש ריק — לא ניתן לשמור")
            except Exception:
                pass
            return False

        # ולידציה של שם הקולקציה
        if not collection or not isinstance(collection, str) or not collection.strip():
            return False

        try:
            now = datetime.now()
            safe_name = str(user_name).strip()
            safe_user_id = _make_safe_user_id(safe_name)
            
            # ולידציה אחרונה — וודא ש-user_id הוא string לא ריק (ASCII)
            if not safe_user_id or not isinstance(safe_user_id, str):
                safe_user_id = "anonymous_user"
            
            doc = {
                'user_name': safe_name,
                'user_id': safe_user_id,
                'test_type': str(collection).replace('_results', ''),
                'results': self._safe_serialize(results),
                'ai_report': self._safe_serialize(report),
                'hesitation_count': int(hesitation_count) if hesitation_count is not None else 0,
                'test_date': now.strftime('%Y-%m-%d'),
                'test_time': now.strftime('%H:%M:%S'),
                'timestamp': now,
            }

            if extra_data and isinstance(extra_data, dict):
                for k, v in extra_data.items():
                    if k and isinstance(k, str):
                        doc[k] = self._safe_serialize(v)

            doc_ref = db.collection(collection).add(doc)
            if doc_ref:
                return True
            return False
        except Exception as e:
            global _db_init_error
            _db_init_error = f"Save failed: {type(e).__name__}: {e}"
            try:
                st.warning(f"⚠️ שגיאה בשמירה ל-DB: {type(e).__name__}: {e}")
            except Exception:
                pass
            return False

    def fetch_history(self, user_name, collection):
        """Fetch up to 20 records — without order_by."""
        db = self._get_db()
        if not db:
            return []
        
        if not user_name or not str(user_name).strip():
            return []

        user_id = _make_safe_user_id(str(user_name).strip())

        try:
            query = (db.collection(collection)
                     .where('user_id', '==', user_id)
                     .limit(20))
            docs = list(query.stream())
            results = [doc.to_dict() for doc in docs]
            
            try:
                results.sort(key=lambda x: x.get('timestamp', ''), reverse=False)
            except Exception:
                pass
            
            return results
        except Exception as e:
            try:
                st.warning(f"⚠️ שגיאה בטעינת היסטוריה ({collection}): {type(e).__name__}: {e}")
            except Exception:
                pass
            return []

    def fetch_all_tests_admin(self, collection):
        db = self._get_db()
        if not db:
            return []
        try:
            docs = db.collection(collection).stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            return []

    def _safe_serialize(self, data):
        """Make data JSON-safe for Firestore."""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if hasattr(data, 'to_dict'):
            return data.to_dict()
        if isinstance(data, dict):
            return {str(k): self._safe_serialize(v) for k, v in data.items() if k is not None}
        if isinstance(data, list):
            return [self._safe_serialize(item) for item in data]
        try:
            return json.loads(json.dumps(data, default=str))
        except Exception:
            return str(data)


# ============================================================
# Public Interface Functions
# ============================================================
_db = DB_Manager()


def save_to_db(name, res, rep, hesitation=0):
    return _db.save_test(name, res, rep, 'hexaco_results', hesitation)


def save_integrity_test_to_db(name, int_scores, reliability_score, rep, hesitation=0):
    return _db.save_test(name, int_scores, rep, 'integrity_results', hesitation,
                         extra_data={'reliability_score': reliability_score})


def save_combined_test_to_db(name, trait_scores, int_scores, reliability_score, rep, hesitation=0):
    return _db.save_test(name, trait_scores, rep, 'combined_results', hesitation,
                         extra_data={
                             'int_scores': int_scores,
                             'reliability_score': reliability_score
                         })


def save_haifa_test_to_db(name, results, report, hesitation=0, video_count=0, video_data=None):
    """שמירה של תרגול חיפה — קטגוריה נפרדת, כולל תשובות הווידאו."""
    extra = {'video_count': video_count}
    if video_data:
        extra['video_responses'] = video_data
    return _db.save_test(name, results, report, 'haifa_results', hesitation,
                         extra_data=extra)


def _dedupe_tests(tests):
    """
    מסיר רשומות כפולות — מבחנים שנשמרו פעמיים בטעות.
    כפילות = אותו משתמש + אותו תאריך + אותה שעה (עד הדקה) + אותו סוג.
    """
    seen = set()
    unique = []
    for t in tests:
        # מפתח ייחודי: סוג + תאריך + שעה (עד דקה) + ציון אמינות
        test_time = str(t.get('test_time', ''))[:5]  # HH:MM (בלי שניות)
        key = (
            t.get('test_type', ''),
            t.get('test_date', ''),
            test_time,
            str(t.get('reliability_score', '')),
            str(t.get('hesitation_count', '')),
        )
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def get_db_history(name):
    """Merge history from all 4 collections — with deduplication."""
    all_history = []
    for collection in ['hexaco_results', 'integrity_results', 'combined_results', 'haifa_results']:
        try:
            history = _db.fetch_history(name, collection)
            all_history.extend(history)
        except Exception:
            continue
    try:
        all_history.sort(key=lambda x: x.get('timestamp', ''), reverse=False)
    except Exception:
        pass
    return _dedupe_tests(all_history)


def get_integrity_history(name):
    return _db.fetch_history(name, 'integrity_results')


def get_combined_history(name):
    return _db.fetch_history(name, 'combined_results')


def get_haifa_history(name):
    return _db.fetch_history(name, 'haifa_results')


def get_all_tests():
    """Admin: fetch all tests from all collections — with deduplication."""
    all_tests = []
    for collection in ['hexaco_results', 'integrity_results', 'combined_results', 'haifa_results']:
        try:
            tests = _db.fetch_all_tests_admin(collection)
            all_tests.extend(tests)
        except Exception:
            continue
    
    # dedup — כולל שם משתמש במפתח (כי אדמין רואה את כולם)
    seen = set()
    unique = []
    for t in all_tests:
        test_time = str(t.get('test_time', ''))[:5]
        key = (
            t.get('user_name', ''),
            t.get('test_type', ''),
            t.get('test_date', ''),
            test_time,
            str(t.get('reliability_score', '')),
        )
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique