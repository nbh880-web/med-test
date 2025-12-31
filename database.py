import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime

class DB_Manager:
    def __init__(self):
        # אתחול ה-Client
        self.db = self._init_firebase()

    def _init_firebase(self):
        try:
            if "firebase" not in st.secrets: 
                return None
            
            fb_info = dict(st.secrets["firebase"])
            
            # תיקון תווים מיוחדים במפתח הפרטי
            if "private_key" in fb_info and "\\n" in fb_info["private_key"]:
                fb_info["private_key"] = fb_info["private_key"].replace("\\n", "\n")
            
            creds = service_account.Credentials.from_service_account_info(fb_info)
            return firestore.Client(credentials=creds, project=fb_info["project_id"])
        except Exception as e:
            print(f"❌ חיבור ל-Firebase נכשל: {e}")
            return None

    def save_test(self, user_name, results, report, collection="hexaco_results"):
        """שמירת תוצאות מבדק חדש (תומך בכל סוגי המבדקים)"""
        if not self.db or not user_name: 
            return
        try:
            now = datetime.now()
            user_id = user_name.strip().lower()
            
            self.db.collection(collection).add({
                "user_name": user_name,
                "user_id": user_id,
                "results": results,
                "ai_report": report,
                "test_date": now.strftime("%d/%m/%Y"),
                "test_time": now.strftime("%H:%M"),
                "timestamp": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            st.error(f"⚠️ שגיאה בשמירת נתונים: {e}")

    def fetch_history(self, user_name, collection="hexaco_results"):
        """שליפת היסטוריה עבור משתמש ספציפי עם מנגנון Fallback לשגיאות אינדקס"""
        if not self.db or not user_name: 
            return []
        
        user_id = user_name.strip().lower()
        try:
            # ניסיון שליפה עם מיון (דורש Index ב-Firestore)
            docs = self.db.collection(collection)\
                          .where("user_id", "==", user_id)\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .limit(10).stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            # Fallback: שליפה ללא מיון בשרת ומיון מקומי ב-Python
            try:
                docs = self.db.collection(collection)\
                              .where("user_id", "==", user_id)\
                              .limit(20).stream()
                raw = [doc.to_dict() for doc in docs]
                return sorted(raw, key=lambda x: str(x.get('timestamp', '')), reverse=True)
            except:
                return []

    def fetch_all_tests_admin(self, collection="hexaco_results"):
        """שליפת כל המבדקים עבור ממשק הניהול"""
        if not self.db: 
            return []
        try:
            docs = self.db.collection(collection)\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            try:
                docs = self.db.collection(collection).stream()
                raw = [doc.to_dict() for doc in docs]
                return sorted(raw, key=lambda x: str(x.get('timestamp', '')), reverse=True)
            except:
                return []

# --- פונקציות גשר (Interface) עבור app.py ---

def save_to_db(name, res, rep):
    """שמירת מבדק HEXACO"""
    DB_Manager().save_test(name, res, rep, "hexaco_results")

def save_integrity_test_to_db(name, res, rep):
    """שמירת מבדק אמינות"""
    DB_Manager().save_test(name, res, rep, "integrity_results")

def save_combined_test_to_db(name, res, rep):
    """שמירת מבדק משולב"""
    DB_Manager().save_test(name, res, rep, "combined_results")

def get_db_history(name, test_type="hexaco"):
    """קבלת היסטוריה לפי סוג מבחן"""
    collections = {
        "hexaco": "hexaco_results",
        "integrity": "integrity_results",
        "combined": "combined_results"
    }
    col = collections.get(test_type, "hexaco_results")
    return DB_Manager().fetch_history(name, col)

def get_all_tests(test_type="hexaco"):
    """קריאה עבור דף ה-Admin לפי סוג מבחן"""
    collections = {
        "hexaco": "hexaco_results",
        "integrity": "integrity_results",
        "combined": "combined_results"
    }
    col = collections.get(test_type, "hexaco_results")
    return DB_Manager().fetch_all_tests_admin(col)