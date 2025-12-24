import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime

class DB_Manager:
    def __init__(self):
        self.db = self._init_firebase()

    def _init_firebase(self):
        try:
            if "firebase" not in st.secrets: return None
            fb_info = dict(st.secrets["firebase"])
            if "\\n" in fb_info["private_key"]:
                fb_info["private_key"] = fb_info["private_key"].replace("\\n", "\n")
            creds = service_account.Credentials.from_service_account_info(fb_info)
            return firestore.Client(credentials=creds, project=fb_info["project_id"])
        except: return None

    def save_test(self, user_name, results, report):
        if not self.db: return
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

    def fetch_history(self, user_name):
        if not self.db: return []
        user_id = user_name.strip().lower()
        try:
            docs = self.db.collection("hexaco_results")\
                          .where("user_id", "==", user_id)\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .limit(10).stream()
            return [doc.to_dict() for doc in docs]
        except: return []

def save_to_db(name, res, rep): DB_Manager().save_test(name, res, rep)
def get_db_history(name): return DB_Manager().fetch_history(name)
