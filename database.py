import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime

class DB_Manager:
    def __init__(self):
        self.db = self._init_firebase()

    def _init_firebase(self):
        try:
            if "firebase" not in st.secrets: 
                return None
            fb_info = dict(st.secrets["firebase"])
            if "\\n" in fb_info["private_key"]:
                fb_info["private_key"] = fb_info["private_key"].replace("\\n", "\n")
            creds = service_account.Credentials.from_service_account_info(fb_info)
            return firestore.Client(credentials=creds, project=fb_info["project_id"])
        except Exception as e:
            # כאן אנחנו לא בולעים את השגיאה במידה והחיבור נכשל לגמרי
            st.error(f"חיבור ל-Firebase נכשל: {e}")
            return None

    def save_test(self, user_name, results, report):
        if not self.db or not user_name: return
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
            st.error(f"שגיאה בשמירת נתונים: {e}")

    def fetch_history(self, user_name):
        if not self.db or not user_name: return []
        user_id = user_name.strip().lower()
        
        try:
            # ניסיון ראשון: שאילתה מסודרת (דורשת אינדקס ב-Firebase)
            docs = self.db.collection("hexaco_results")\
                          .where("user_id", "==", user_id)\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .limit(10).stream()
            
            results = [doc.to_dict() for doc in docs]
            if results: return results
        except Exception as e:
            # Fallback: אם חסר אינדקס, נשלוף ללא מיון ונמיין ב-Python כדי שהאפליקציה לא תיתקע
            try:
                docs = self.db.collection("hexaco_results")\
                              .where("user_id", "==", user_id)\
                              .limit(20).stream()
                raw_list = [doc.to_dict() for doc in docs]
                # מיון ידני לפי תאריך בתוך הקוד
                return sorted(raw_list, key=lambda x: str(x.get('timestamp')), reverse=True)
            except:
                return []
        return []

# פונקציות גשר התואמות ל-app.py
def save_to_db(name, res, rep):
    DB_Manager().save_test(name, res, rep)

def get_db_history(name):
    return DB_Manager().fetch_history(name)
