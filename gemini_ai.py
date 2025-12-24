import streamlit as st
import requests
import json
from google.cloud import firestore
from google.oauth2 import service_account

class HEXACO_AI_Engine:
    def __init__(self):
        # שליפת מפתח Gemini
        self.api_key = st.secrets.get("GEMINI_KEY_1", "").strip()
        # אתחול Firebase
        self.db = self._init_firebase()

    def _init_firebase(self):
        """חיבור למסד הנתונים של Firebase באמצעות ה-Secrets"""
        try:
            if "firebase" not in st.secrets:
                return None
            
            fb_info = dict(st.secrets["firebase"])
            # תיקון תקלות נפוצות בפורמט ה-Private Key
            if "\\n" in fb_info["private_key"]:
                fb_info["private_key"] = fb_info["private_key"].replace("\\n", "\n")
            
            creds = service_account.Credentials.from_service_account_info(fb_info)
            return firestore.Client(credentials=creds, project=fb_info["project_id"])
        except Exception as e:
            st.error(f"שגיאת התחברות ל-Firebase: {e}")
            return None

    def get_user_history(self, user_name):
        """שליפת היסטוריית המבחנים של המשתמש מהארכיון"""
        if not self.db:
            return []
        try:
            # מחפש מסמכים שבהם שם המשתמש זהה, וממיין לפי זמן
            docs = self.db.collection("hexaco_results")\
                          .where("user_name", "==", user_name)\
                          .order_by("timestamp", direction=firestore.Query.ASCENDING)\
                          .stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []

    def save_to_archive(self, user_name, results, report):
        """שמירת המבחן הנוכחי לארכיון ב-Firebase"""
        if not self.db:
            return
        try:
            self.db.collection("hexaco_results").add({
                "user_name": user_name,
                "results": results,
                "ai_report": report,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            st.warning(f"התוצאות לא נשמרו בארכיון: {e}")

    def generate_professional_report(self, user_name, results):
        if not self.api_key:
            return "שגיאה: מפתח API חסר ב-Secrets."

        # --- שלב א: שליפת היסטוריה לצורך ניתוח מצטבר ---
        history = self.get_user_history(user_name)
        history_context = ""
        if history:
            history_context = "\nשים לב: זו אינה הפעם הראשונה של המועמד. הנה היסטוריית הציונים הקודמת שלו:\n"
            for i, entry in enumerate(history):
                history_context += f"מבחן {i+1}: {entry.get('results')}\n"
            history_context += "\nבצע ניתוח מצטבר: האם יש מגמת שיפור, עקביות או שינוי קיצוני שדורש התייחסות?"

        # --- שלב ב: חקירת מודל Gemini זמין ---
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            models_res = requests.get(list_url, timeout=10)
            if models_res.status_code == 200:
                models_list = models_res.json().get("models", [])
                available = [m["name"] for m in models_list if "generateContent" in m.get("supportedGenerationMethods", [])]
                target_model = next((m for m in available if "flash" in m), available[0] if available else "models/gemini-1.5-flash")
            else:
                target_model = "models/gemini-1.5-flash"
        except:
            target_model = "models/gemini-1.5-flash"

        # --- שלב ג: בניית הפרומפט המורכב (מס"ר + ניתוח מצטבר) ---
        url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
        
        prompt = f"""
        פעל כמעריך בכיר במרכז מס"ר (מרכז סימולציה רפואית) בשיטת ה-MSR למיון מועמדים לרפואה.
        נתח את תוצאות ה-HEXACO של המועמד {user_name}.
        ציונים נוכחיים: {results}
        {history_context}

        דרישות הדוח (בעברית רהוטה ומקצועית):
        1. הערכת יושרה וצניעות: אמינות המועמד כרופא.
        2. תקשורת ונעימות: עבודה בצוות וניהול קונפליקטים.
        3. חוסן נפשי: עמידה בלחץ ושחיקה במערכת הבריאות.
        4. ניתוח מצטבר: השוואה למבחנים קודמים (אם קיימים) וזיהוי מגמות.
        5. המלצה סופית לבוחני מס"ר.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                report_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                
                # שמירה לארכיון לאחר יצירת הדוח בהצלחה
                self.save_to_archive(user_name, results, report_text)
                
                return report_text
            return f"שגיאה (Status {response.status_code}): {response.json().get('error', {}).get('message', 'Unknown')}"
        except Exception as e:
            return f"שגיאת תקשורת: {str(e)}"

def get_ai_analysis(user_name, results_summary):
    engine = HEXACO_AI_Engine()
    return engine.generate_professional_report(user_name, results_summary)
