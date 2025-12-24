import streamlit as st
import requests
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
        fig = go.Figure(data=[
            go.Bar(name='הציון שלך', x=labels, y=list(user_results.values()), marker_color='#1E90FF'),
            go.Bar(name='פרופיל יעד', x=labels, y=[IDEAL_DOCTOR.get(k) for k in user_results.keys()], marker_color='#2ECC71')
        ])
        fig.update_layout(barmode='group', yaxis=dict(range=[1, 5]),
                          title=dict(text="ניתוח השוואתי מול פרופיל יעד", x=0.5))
        return fig

    def generate_report(self, user_name, current_results, history):
        if not self.api_key: return "❌ חסר מפתח API"
        
        # בניית הקשר היסטורי מהנתונים שה-App שלח
        history_context = ""
        if history:
            history_context = "\nמגמות ממבחנים קודמים:\n"
            for i, h in enumerate(history[:3]):
                history_context += f"- מבחן מ-{h.get('test_date', 'לא ידוע')}: {h.get('results')}\n"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        prompt = f"""
        פעל כמאמן הכנה למבחני מס"ר לרפואה.
        מועמד: {user_name}
        תוצאות נוכחיות: {current_results}
        פרופיל יעד: {IDEAL_DOCTOR}
        {history_context}
        
        נתח את הפערים, התייחס לשיפור או נסיגה מול העבר, ותן טיפים להתנהגות בסימולציות. כתוב בעברית מקצועית.
        """
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
        except: pass
        return "⚠️ לא ניתן להפיק דוח AI כרגע."

def get_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_report(user_name, results, history)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)
