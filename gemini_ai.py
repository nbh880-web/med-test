import streamlit as st
import requests
import json
import plotly.graph_objects as go
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

class HEXACO_Analyzer:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_KEY_1", "").strip()

    def create_comparison_chart(self, user_results):
        if not user_results: return None
        labels = [TRAIT_DICT.get(k, k) for k in user_results.keys()]
        user_vals = list(user_results.values())
        ideal_vals = [IDEAL_DOCTOR.get(k, 3.5) for k in user_results.keys()]

        fig = go.Figure(data=[
            go.Bar(name='הציון שלך', x=labels, y=user_vals, marker_color='#1E90FF'),
            go.Bar(name='פרופיל יעד', x=labels, y=ideal_vals, marker_color='#2ECC71')
        ])
        fig.update_layout(
            barmode='group', 
            yaxis=dict(range=[1, 5], title="ציון (1-5)"),
            title=dict(text="השוואת פרופיל אישי מול יעד רפואי", x=0.5, xanchor='center'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            margin=dict(t=100, b=50)
        )
        return fig

    def generate_report(self, user_name, current_results, history):
        if not self.api_key: 
            return "❌ שגיאה: מפתח API לא מוגדר ב-Secrets."
        
        # בניית הקשר היסטורי מהנתונים שהגיעו מה-App
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- נתוני התקדמות (מבחנים קודמים מהארכיון) ---\n"
            for i, h in enumerate(history[:3]):
                prev_results = h.get('results', 'אין נתונים')
                date = h.get('test_date', 'תאריך לא ידוע')
                history_context += f"מבחן עבר מ-{date}: {prev_results}\n"

        # הגדרת המודל והכתובת (לפי הלוגיקה שעבדה)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        prompt = f"""
        פעל כמאמן בכיר להכנה למבחני מס"ר לרפואה.
        שם המועמד: {user_name}
        תוצאות נוכחיות: {current_results}
        פרופיל רופא יעד אידיאלי: {IDEAL_DOCTOR}
        
        {history_context}

        משימות הדוח (כתוב בעברית מקצועית):
        1. ניתוח פערים: השווה את התוצאות הנוכחיות לפרופיל היעד.
        2. ניתוח התקדמות: השווה לתוצאות העבר (אם צורפו). האם יש שיפור?
        3. דגשים לסימולציה: איך להתנהג בתחנות מס"ר בהתבסס על הפרופיל.
        4. אזהרות: נקודות שעלולות להכשיל אותו.
        """
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        # לוגיקת ה-Retry (ניסיונות חוזרים) שהוכיחה את עצמה
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=45)
                if response.status_code == 200:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
                elif response.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    return f"⚠️ שגיאת שרת AI ({response.status_code})"
            except Exception as e:
                if attempt == 2: return f"🆘 שגיאת תקשורת: {str(e)}"
                time.sleep(1)
        
        return "⚠️ לא ניתן להפיק דוח AI כרגע."

# פונקציות גשר לשימוש ב-App.py
def get_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_report(user_name, results, history)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)
