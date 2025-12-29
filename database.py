import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime

class DB_Manager:
    _instance = None

    def __init__(self):
        # אתחול ה-Client רק אם הוא לא קיים כדי לחסוך בביצועים
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
            # אנחנו לא רוצים שהאפליקציה תתרסק אם אין חיבור לבסיס הנתונים
            print(f"❌ חיבור ל-Firebase נכשל: {e}")
            return None

    def save_test(self, user_name, results, report):
        """שמירת תוצאות מבדק חדש"""
        if not self.db or not user_name: 
            return
        try:
            now = datetime.now()
            user_id = user_name.strip().lower()
            
            self.db.collection("hexaco_results").add({
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

    def fetch_history(self, user_name):
        """שליפת היסטוריה עבור משתמש ספציפי (עד 10 מבדקים)"""
        if not self.db or not user_name: 
            return []
        
        user_id = user_name.strip().lower()
        try:
            # ניסיון שליפה עם מיון (דורש Index ב-Firestore)
            docs = self.db.collection("hexaco_results")\
                          .where("user_id", "==", user_id)\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .limit(10).stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            # Fallback למקרה שאין Index או שיש שגיאת מיון - שליפה ומיון מקומי
            try:
                docs = self.db.collection("hexaco_results")\
                              .where("user_id", "==", user_id)\
                              .limit(20).stream()
                raw = [doc.to_dict() for doc in docs]
                return sorted(raw, key=lambda x: str(x.get('timestamp', '')), reverse=True)
            except:
                return []

    def fetch_all_tests_admin(self):
        """שליפת כל המבדקים הקיימים עבור ממשק הניהול"""
        if not self.db: 
            return []
        try:
            docs = self.db.collection("hexaco_results")\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            try:
                docs = self.db.collection("hexaco_results").stream()
                raw = [doc.to_dict() for doc in docs]
                return sorted(raw, key=lambda x: str(x.get('timestamp', '')), reverse=True)
            except:
                return []

# --- פונקציות גשר (Interface) עבור app.py ---

def save_to_db(name, res, rep):
    """קריאה ישירה לשמירה מהאפליקציה"""
    manager = DB_Manager()
    manager.save_test(name, res, rep)

def get_db_history(name):
    """קריאה ישירה להיסטוריה מהאפליקציה"""
    return DB_Manager().fetch_history(name)

def get_all_tests():
    """קריאה עבור דף ה-Admin"""
    return DB_Manager().fetch_all_tests_admin()
