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

    def save_test(self, user_name, results, report, collection="hexaco_results", hesitation_count=0):
        """שמירת תוצאות מבדק חדש עם תווית סוג מבדק ומדד היסוס"""
        if not self.db or not user_name: 
            return
        try:
            now = datetime.now()
            user_id = user_name.strip().lower()
            
            # זיהוי סוג המבחן לפי שם ה-Collection
            test_type_map = {
                "hexaco_results": "hexaco",
                "integrity_results": "integrity",
                "combined_results": "combined"
            }
            test_type = test_type_map.get(collection, "unknown")

            self.db.collection(collection).add({
                "user_name": user_name,
                "user_id": user_id,
                "test_type": test_type,
                "results": results,
                "ai_report": report,
                "hesitation_count": hesitation_count,
                "test_date": now.strftime("%d/%m/%Y"),
                "test_time": now.strftime("%H:%M"),
                "timestamp": firestore.SERVER_TIMESTAMP,
                "copyright": "© זכויות יוצרים לניתאי מלכה"
            })
        except Exception as e:
            st.error(f"⚠️ שגיאה בשמירת נתונים: {e}")

    def fetch_history(self, user_name, collection):
        """שליפת היסטוריה עבור משתמש ספציפי מ-Collection מסוים"""
        if not self.db or not user_name: 
            return []
        
        user_id = user_name.strip().lower()
        try:
            docs = self.db.collection(collection)\
                          .where("user_id", "==", user_id)\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .limit(20).stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            # Fallback למקרה שאין אינדקס ב-Firestore
            try:
                docs = self.db.collection(collection).where("user_id", "==", user_id).limit(30).stream()
                raw = [doc.to_dict() for doc in docs]
                return sorted(raw, key=lambda x: str(x.get('timestamp', '')), reverse=True)
            except:
                return []

    def fetch_all_tests_admin(self, collection):
        """שליפת כל המבדקים מ-Collection מסוים עבור האדמין"""
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

# --- פונקציות גשר (Interface) המאוחדות ---

def save_to_db(name, res, rep, hesitation=0):
    """שמירת מבדק HEXACO"""
    DB_Manager().save_test(name, res, rep, "hexaco_results", hesitation)

def save_integrity_test_to_db(name, res, rep, hesitation=0):
    """שמירת מבדק אמינות"""
    DB_Manager().save_test(name, res, rep, "integrity_results", hesitation)

def save_combined_test_to_db(name, res, rep, hesitation=0):
    """שמירת מבדק משולב"""
    DB_Manager().save_test(name, res, rep, "combined_results", hesitation)

def get_db_history(name):
    """
    פונקציה מאוחדת: מושכת את כל ההיסטוריה של המשתמש מכל הטבלאות.
    כך המשתמש רואה את כל המבחנים שלו במקום אחד.
    """
    manager = DB_Manager()
    collections = ["hexaco_results", "integrity_results", "combined_results"]
    full_history = []
    
    for col in collections:
        res = manager.fetch_history(name, col)
        for doc in res:
            if 'test_type' not in doc:
                doc['test_type'] = col.replace("_results", "")
        full_history.extend(res)
        
    return sorted(full_history, key=lambda x: str(x.get('timestamp', '')), reverse=True)

def get_all_tests():
    """
    פונקציה מאוחדת לאדמין: מושכת את כל המבדקים מכל הטבלאות.
    מאפשרת לממשק האדמין להציג 'תיק מועמד' עם כל המבחנים שלו.
    """
    manager = DB_Manager()
    collections = ["hexaco_results", "integrity_results", "combined_results"]
    all_data = []
    
    for col in collections:
        res = manager.fetch_all_tests_admin(col)
        for doc in res:
            if 'test_type' not in doc:
                doc['test_type'] = col.replace("_results", "")
        all_data.extend(res)
        
    return sorted(all_data, key=lambda x: str(x.get('timestamp', '')), reverse=True)
