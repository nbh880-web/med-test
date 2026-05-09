"""
Mednitai — Database Layer
=========================
Firebase Firestore: save, fetch, admin.
"""

import streamlit as st
from datetime import datetime
import json
import threading


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
    """Returns (is_connected: bool, error_message: str or None) — for debugging."""
    return (_db_client is not None, _db_init_error)


@st.cache_resource
def _init_firebase():
    """Initialize Firebase — cached so it runs once."""
    return _init_firebase_safe()


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

        try:
            now = datetime.now()
            doc = {
                'user_name': str(user_name),
                'user_id': str(user_name).lower().replace(' ', '_'),
                'test_type': collection.replace('_results', ''),
                'results': self._safe_serialize(results),
                'ai_report': self._safe_serialize(report),
                'hesitation_count': int(hesitation_count),
                'test_date': now.strftime('%Y-%m-%d'),
                'test_time': now.strftime('%H:%M:%S'),
                'timestamp': now,
            }

            if extra_data and isinstance(extra_data, dict):
                for k, v in extra_data.items():
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
        """Fetch up to 20 records. NO order_by — to avoid Firestore index requirements."""
        db = self._get_db()
        if not db:
            return []

        user_id = str(user_name).lower().replace(' ', '_')

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
        """Fetch all records for admin view."""
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
            return {k: self._safe_serialize(v) for k, v in data.items()}
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


def save_haifa_test_to_db(name, results, report, hesitation=0, video_count=0):
    """שמירה של תרגול חיפה — קטגוריה נפרדת."""
    return _db.save_test(name, results, report, 'haifa_results', hesitation,
                         extra_data={'video_count': video_count})


def get_db_history(name):
    """Merge history from all 4 collections."""
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
    return all_history


def get_integrity_history(name):
    return _db.fetch_history(name, 'integrity_results')


def get_combined_history(name):
    return _db.fetch_history(name, 'combined_results')


def get_haifa_history(name):
    return _db.fetch_history(name, 'haifa_results')


def get_all_tests():
    """Admin: fetch all tests from all collections."""
    all_tests = []
    for collection in ['hexaco_results', 'integrity_results', 'combined_results', 'haifa_results']:
        try:
            tests = _db.fetch_all_tests_admin(collection)
            all_tests.extend(tests)
        except Exception:
            continue
    return all_tests