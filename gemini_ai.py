import streamlit as st
import requests
import json
import plotly.graph_objects as go
import time

TRAIT_DICT = {
    "Honesty-Humility": "כנות וענווה (Honesty-Humility)",
    "Emotionality": "רגשיות וחוסן (Emotionality)",
    "Extraversion": "מוחצנות (Extraversion)",
    "Agreeableness": "נעימות ושיתוף פעולה (Agreeableness)",
    "Conscientiousness": "מצפוניות ואחריות (Conscientiousness)",
    "Openness to Experience": "פתיחות מחשבתית (Openness to Experience)"
}

IDEAL_DOCTOR = {
    "Honesty-Humility": 4.2, "Emotionality": 2.8, "Extraversion": 3.5,
    "Agreeableness": 4.0, "Conscientiousness": 4.5, "Openness to Experience": 3.8
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

    def _discover_model(self):
        """חוקר את השרת כדי למצוא מודל זמין שתומך ביצירת תוכן"""
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            res = requests.get(list_url, timeout=10)
            if res.status_code == 200:
                models = res.json().get("models", [])
                # מחפש מודל שתומך ב-generateContent ומעדיף את flash
                for m in models:
                    if "generateContent" in m.get("supportedGenerationMethods", []):
                        if "flash" in m["name"]:
                            return m["name"] # מחזיר משהו כמו "models/gemini-1.5-flash"
                
                # אם לא מצא פלאש, קח את הראשון שזמין
                if models:
                    return models[0]["name"]
        except:
            pass
        return "models/gemini-1.5-flash" # ברירת מחדל בטוחה

    def generate_report(self, user_name, current_results, history):
        if not self.api_key: 
            return "❌ חסר מפתח API ב-Secrets"
        
        # 1. שלב החקירה - מציאת המודל הנכון
        target_model = self._discover_model()
        
        # 2. בניית ה-URL הדינמי
        url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
        
        # 3. הכנת ההקשר (Context)
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- נתוני עבר לניתוח מגמות ---\n"
            for i, h in enumerate(history[:3]):
                history_context += f"מבחן {i+1}: {h.get('results')}\n"

        prompt = f"""
        פעל כמאמן מומחה למבחני מס"ר לרפואה.
        שם המועמד: {user_name}
        תוצאות נוכחיות: {current_results}
        פרופיל יעד: {IDEAL_DOCTOR}
        {history_context}
        
        נתח פערים מול פרופיל הרופא, התייחס למגמות מהעבר, ותן הנחיות פרקטיות לסימולציה.
        כתוב בעברית רהוטה ומקצועית.
        """
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {'Content-Type': 'application/json'}

        # 4. ביצוע השאילתה עם ניסיונות חוזרים
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
                elif response.status_code == 404:
                    # אם המודל שחקרנו פתאום מחזיר 404, ננסה שוב עם מודל גנרי
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                    continue
                else:
                    return f"⚠️ שגיאת AI ({response.status_code})"
            except:
                time.sleep(1)
        
        return "⚠️ שרת ה-AI אינו זמין כרגע."

def get_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_report(user_name, results, history)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)
