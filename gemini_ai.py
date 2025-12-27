import streamlit as st
import requests
import json
import plotly.graph_objects as go
import time

# מילון תרגום והגדרות בסיס
TRAIT_DICT = {
    "Honesty-Humility": "כנות וענווה (H)",
    "Emotionality": "רגשיות (E)",
    "Extraversion": "מוחצנות (X)",
    "Agreeableness": "נעימות (A)",
    "Conscientiousness": "מצפוניות (C)",
    "Openness to Experience": "פתיחות (O)"
}

IDEAL_DOCTOR = {
    "Honesty-Humility": 4.55, 
    "Emotionality": 3.85, 
    "Extraversion": 3.9,
    "Agreeableness": 4.3, 
    "Conscientiousness": 4.55, 
    "Openness to Experience": 3.8
}

class HEXACO_Analyzer:
    def __init__(self):
        self.gemini_key = st.secrets.get("GEMINI_KEY_1", "").strip()
        self.claude_key = st.secrets.get("CLAUDE_KEY", "").strip()

    def _discover_gemini_model(self):
        default_model = "models/gemini-1.5-flash"
        if not self.gemini_key: return default_model
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_key}"
        try:
            res = requests.get(list_url, timeout=5)
            if res.status_code == 200:
                models = res.json().get("models", [])
                flash_models = [m["name"] for m in models if "flash" in m["name"] and "generateContent" in m["supportedGenerationMethods"]]
                if flash_models: return flash_models[0]
        except: pass
        return default_model

    def generate_multi_report(self, user_name, current_results, history):
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- מגמות עבר (מבחנים קודמים) ---\n"
            for i, h in enumerate(history[:2]):
                history_context += f"מבחן קודם: {h.get('results', '{}')}\n"

        # פרומפט מקצועי מעודכן למס"ר
        prompt = f"""
        תפקיד: פסיכולוג בכיר במרכז הערכה לרפואה (מס"ר/מרק"ם).
        שם המועמד: {user_name}
        נתונים נוכחיים: {current_results}
        {history_context}
        
        טווחים מצופים מרופא: 
        C (מצפוניות): 4.4-4.8, H (כנות): 4.3-4.9, A (נעימות): 4.1-4.6.

        משימה:
        1. ניתוח התאמה: השווה כל תכונה ליעד הרופא. ציין היכן יש 'פער סיכון' (ציון נמוך מדי).
        2. דגלים אדומים: התייחס לניסיונות 'ריצוי חברתי' (Social Desirability) אם כל הציונים מעל 4.8.
        3. טיפ לסימולציה: תן עצה ספציפית אחת לשיפור התקשורת מול שחקן כועס על בסיס הציון ב-A ו-E.
        4. סיכום: האם המועמד מפגין בשלות למקצוע הרפואה?
        
        הוראות: עברית רהוטה, נקודות קצרות, גוף שני.
        """
        return self._call_ai(prompt, "gemini"), self._call_ai(prompt, "claude")

    def _call_ai(self, prompt, provider):
        try:
            if provider == "gemini":
                model_name = self._discover_gemini_model()
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={self.gemini_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                res = requests.post(url, json=payload, timeout=30)
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                url = "https://api.anthropic.com/v1/messages"
                headers = {"x-api-key": self.claude_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                payload = {"model": "claude-3-5-sonnet-20240620", "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]}
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                return res.json()['content'][0]['text']
        except: return f"⚠️ שירות {provider} לא זמין כרגע."

    def create_radar_chart(self, results):
        categories = [TRAIT_DICT[k] for k in results.keys()]
        user_vals = list(results.values())
        ideal_vals = [IDEAL_DOCTOR[k] for k in results.keys()]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=ideal_vals + [ideal_vals[0]], theta=categories + [categories[0]], fill='toself', name='יעד רופא', line_color='#2ECC71', opacity=0.3))
        fig.add_trace(go.Scatterpolar(r=user_vals + [user_vals[0]], theta=categories + [categories[0]], fill='toself', name='הפרופיל שלך', line_color='#1E90FF'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 5])), showlegend=True, title="מפת אישיות מול יעד")
        return fig

    def create_comparison_chart(self, results):
        categories = [TRAIT_DICT[k] for k in results.keys()]
        fig = go.Figure()
        fig.add_trace(go.Bar(name='הציון שלך', x=categories, y=list(results.values()), marker_color='#1E90FF'))
        fig.add_trace(go.Bar(name='יעד רופא', x=categories, y=[IDEAL_DOCTOR[k] for k in results.keys()], marker_color='#2ECC71'))
        fig.update_layout(barmode='group', yaxis=dict(range=[1, 5]), title="השוואה כמותית")
        return fig

# פונקציות עזר
def get_multi_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_multi_report(user_name, results, history)

def get_radar_chart(results):
    return HEXACO_Analyzer().create_radar_chart(results)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)