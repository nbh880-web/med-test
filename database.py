"""
Mednitai — Database Layer
=========================
Firebase Firestore: save, fetch, admin.
"""

import streamlit as st
from datetime import datetime
import json


# ============================================================
# Firebase Init — Cached
# ============================================================
@st.cache_resource
def _init_firebase():
    """Initialize Firebase — cached so it runs once."""
    try:
        from google.cloud import firestore
        from google.oauth2 import service_account

        firebase_config = dict(st.secrets["firebase"])

        # Fix private key newlines
        if 'private_key' in firebase_config:
            firebase_config['private_key'] = firebase_config['private_key'].replace('\\n', '\n')

        credentials = service_account.Credentials.from_service_account_info(firebase_config)
        db = firestore.Client(credentials=credentials, project=firebase_config.get('project_id'))
        return db
    except Exception as e:
        st.warning(f"Firebase לא זמין: {e}")
        return None


# ============================================================
# DB Manager
# ============================================================
class DB_Manager:

    def _get_db(self):
        return _init_firebase()

    def save_test(self, user_name, results, report, collection,
                  hesitation_count=0, extra_data=None):
        """Save test results to Firestore."""
        db = self._get_db()
        if not db:
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

            db.collection(collection).add(doc)
            return True
        except Exception as e:
            st.warning(f"שגיאה בשמירה: {e}")
            return False

    def fetch_history(self, user_name, collection):
        """Fetch up to 20 records, sorted by timestamp. Fallback without order_by."""
        db = self._get_db()
        if not db:
            return []

        user_id = str(user_name).lower().replace(' ', '_')

        try:
            # Try with order_by (requires Firestore index)
            query = (db.collection(collection)
                     .where('user_id', '==', user_id)
                     .order_by('timestamp')
                     .limit(20))
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            try:
                # Fallback without order_by
                query = (db.collection(collection)
                         .where('user_id', '==', user_id)
                         .limit(20))
                docs = query.stream()
                return [doc.to_dict() for doc in docs]
            except Exception:
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


def get_db_history(name):
    """Merge history from all 3 collections."""
    all_history = []
    for collection in ['hexaco_results', 'integrity_results', 'combined_results']:
        try:
            history = _db.fetch_history(name, collection)
            all_history.extend(history)
        except Exception:
            continue
    # Sort by timestamp if available
    try:
        all_history.sort(key=lambda x: x.get('timestamp', ''), reverse=False)
    except Exception:
        pass
    return all_history


def get_integrity_history(name):
    return _db.fetch_history(name, 'integrity_results')


def get_combined_history(name):
    return _db.fetch_history(name, 'combined_results')


def get_all_tests():
    """Admin: fetch all tests from all collections."""
    all_tests = []
    for collection in ['hexaco_results', 'integrity_results', 'combined_results']:
        try:
            tests = _db.fetch_all_tests_admin(collection)
            all_tests.extend(tests)
        except Exception:
            continue
    return all_tests
