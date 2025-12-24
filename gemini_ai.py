import streamlit as st
import requests
import json
import pandas as pd
import plotly.graph_objects as go
from google.cloud import firestore
from google.oauth2 import service_account
import time

# מילון תרגום ותצוגה
TRAIT_DICT = {
    "Honesty-Humility": "כנות וענווה (Honesty-Humility)",
    "Emotionality": "רגשיות וחוסן (Emotionality)",
    "Extraversion": "מוחצנות (Extraversion)",
    "Agreeableness": "נעימות ושיתוף פעולה (Agreeableness)",
    "Conscientiousness": "מצפוניות ואחריות (Conscientiousness)",
    "Openness to Experience": "פתיחות מחשבתית (Openness to Experience)"
}

# פרופיל יעד - רופא אופטימלי
IDEAL_DOCTOR = {
    "Honesty-Humility": 4.2,
    "Emotionality": 2.8,
    "Extraversion": 3.5,
    "Agreeableness": 4.0,
    "Conscientiousness": 4.5,
    "Openness to Experience": 3.8
}

class HEXACO_AI_Engine:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_KEY_1", "").strip()
        self.db = self._init_firebase()

    def _init_firebase(self):
        try:
            if "firebase" not in st.secrets: return None
            fb_info = dict(st.secrets["firebase"])
            if "\\n" in fb_info["private_key"]:
                fb_info["private_key"] = fb_info["private_key"].replace("\\n", "\n")
            creds = service_account.Credentials.from_service_account_info(fb_info)
            return firestore.Client(credentials=creds, project=fb_info["project_id"])
        except Exception as e:
            st.error(f"שגיאת התחברות ל-Firebase: {e}")
            return None

    def create_comparison_chart(self, user_results):
        """יצירת גרף עמודות השוואתי - ללא שגיאת RTL"""
        if not user_results: return None
            
        labels = [TRAIT_DICT.get(k, k) for k in user_results.keys()]
        user_vals = list(user_results.values())
        ideal_vals = [IDEAL_DOCTOR.get(k, 3.5) for k in user_results.keys()]

        fig = go.Figure(data=[
            go.Bar(name='הציון שלך', x=labels, y=user_vals, marker_color='#1E90FF'),
            go.Bar(name='פרופיל רופא יעד', x=labels, y=ideal_vals, marker_color='#2ECC71')
        ])
        
        fig.update_layout(
            barmode='group', 
            yaxis=dict(range=[1, 5], title="ציון (1-5)"),
            title=dict(text="השוואת פרופיל אישי מול יעד רפואי", x=0.5, xanchor='center'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            font=dict(size=12),
            margin=dict(t=100, b=50)
        )
        return fig

    def get_user_history(self, user_name):
        """שליפת היסטוריה לפי מזהה אחיד (Case-Insensitive)"""
        if not self.db or not user_name: return []
        try:
            # יצירת מזהה אחיד לחיפוש (ללא רווחים ובאותיות קטנות)
            user_id = user_name.strip().lower()
            docs = self.db.collection("hexaco_results")\
                          .where("user_id", "==", user_id)\
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                          .limit(10)\
                          .stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            return []

    def save_to_archive(self, user_name, results, report):
        """שמירה עם שדה user_id לחיפוש עתידי אמין"""
        if not self.db or not user_name: return
        try:
            user_id = user_name.strip().lower()
            self.db.collection("hexaco_results").add({
                "user_name": user_name,  # השם המקורי לתצוגה
                "user_id": user_id,      # המזהה לחיפוש
                "results": results,
                "ai_report": report,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
        except: pass

    def generate_professional_report(self, user_name, results):
        if not self.api_key: 
            return "❌ שגיאה: מפתח API לא מוגדר ב-Secrets."
        
        # שליפת היסטוריה לצורך הכללה בפרומפט
        history = self.get_user_history(user_name)
        history_context = ""
        if history:
            history_context = "\n--- נתוני התקדמות (מבחנים קודמים) ---\n"
            for i, h in enumerate(history[:3]):
                history_context += f"מבחן עבר {i+1}: {h.get('results')}\n"

        # בחירת מודל
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            res = requests.get(list_url, timeout=10)
            available = [m["name"] for m in res.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
            target_model = next((m for m in available if "flash" in m), "models/gemini-1.5-flash")
        except: target_model = "models/gemini-1.5-flash"

        url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
        
        # פרומפט מפורט המנחה את ה-AI להתייחס להתקדמות
        prompt = f"""
        פעל כמאמן בכיר להכנה למבחני מס"ר.
        שם המועמד: {user_name}
        תוצאות נוכחיות: {results}
        פרופיל רופא יעד אידיאלי: {IDEAL_DOCTOR}
        
        {history_context}

        משימות הדוח (כתוב בעברית מקצועית):
        1. ניתוח פערים: השווה את התוצאות הנוכחיות לפרופיל היעד.
        2. ניתוח התקדמות: השווה לתוצאות העבר (אם קיימות). האם המועמד משתפר? האם הוא עקבי יותר? ציין מגמות ספציפיות.
        3. דגשים לסימולציה: איך המועמד צריך להתנהג בתחנות מס"ר בהתבסס על הפרופיל שלו.
        4. אזהרות: נקודות שעלולות להכשיל אותו במבחן האמיתי.
        """
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 200:
                    report = response.json()['candidates'][0]['content']['parts'][0]['text']
                    self.save_to_archive(user_name, results, report)
                    return report
                elif response.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    return f"❌ שגיאת שרת ({response.status_code})."
            except requests.exceptions.Timeout:
                if attempt < 2: continue
                return "⏳ שגיאת זמן (Timeout): השרת לא ענה."
            except Exception as e:
                return f"🆘 שגיאה: {str(e)}"
        
        return "שגיאת תקשורת לאחר מספר ניסיונות."

# פונקציות גשר
def get_ai_analysis(user_name, results_summary):
    engine = HEXACO_AI_Engine()
    return engine.generate_professional_report(user_name, results_summary)

def get_comparison_chart(results):
    engine = HEXACO_AI_Engine()
    return engine.create_comparison_chart(results)

def get_history(user_name):
    engine = HEXACO_AI_Engine()
    return engine.get_user_history(user_name)
