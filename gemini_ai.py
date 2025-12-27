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
        # שליכת מפתחות מ-Secrets
        self.gemini_key = st.secrets.get("GEMINI_KEY_1", "").strip()
        self.claude_key = st.secrets.get("CLAUDE_KEY", "").strip()

    # --- מנגנון Discovery ל-Gemini ---
    def _discover_gemini_model(self):
        """מוצא את מודל ה-Flash העדכני ביותר הזמין"""
        default_model = "models/gemini-1.5-flash"
        if not self.gemini_key: return default_model
        
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_key}"
        try:
            res = requests.get(list_url, timeout=5)
            if res.status_code == 200:
                models = res.json().get("models", [])
                # מחפש מודל שתומך בייצור תוכן ומכיל את המילה flash
                flash_models = [m["name"] for m in models if "flash" in m["name"] and "generateContent" in m["supportedGenerationMethods"]]
                if flash_models:
                    return flash_models[0] # מחזיר את הראשון שנמצא (בדרך כלל החדש ביותר)
        except:
            pass
        return default_model

    # --- שליפת דוח מ-Gemini ---
    def _get_gemini_report(self, prompt):
        if not self.gemini_key: return "❌ מפתח API של Gemini חסר בהגדרות."
        
        model_name = self._discover_gemini_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={self.gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            return f"⚠️ שגיאת Gemini: {res.status_code}"
        except Exception as e:
            return f"⚠️ שגיאה בתקשורת עם Gemini: {str(e)}"

    # --- שליפת דוח מ-Claude ---
    def _get_claude_report(self, prompt):
        if not self.claude_key: return "❌ מפתח API של Claude חסר בהגדרות."
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.claude_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()['content'][0]['text']
            return f"⚠️ שגיאת Claude: {res.status_code}"
        except Exception as e:
            return f"⚠️ שגיאה בתקשורת עם Claude: {str(e)}"

    # --- ניתוח משולב (הפונקציה הראשית) ---
    def generate_multi_report(self, user_name, current_results, history):
        # הכנת הקשר היסטורי (אם קיים)
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- מגמות עבר (מבחנים קודמים) ---\n"
            for i, h in enumerate(history[:3]):
                res_str = h.get('results', '{}')
                history_context += f"מבחן מיום {h.get('date', 'לא ידוע')}: {res_str}\n"

        prompt = f"""
        תפקיד: פסיכולוג תעסוקתי מומחה למיון רפואי (מרק"ם/שאלון ביוגרפי).
        שם המועמד: {user_name}
        
        נתונים נוכחיים (HEXACO): {current_results}
        {history_context}
        
        משימה:
        1. השווה את התוצאות לפרופיל הרופא האידיאלי (דגש על מצפוניות גבוהה C וכנות H).
        2. זהה נקודת חוזק אחת ונקודה אחת לשיפור בסימולציות.
        3. תן 3 טיפים קונקרטיים להתנהלות בתחנות הערכה.
        
        הוראות כתיבה: עברית רהוטה, גוף שני, פורמט של נקודות (Bullet points).
        """
        
        return self._get_gemini_report(prompt), self._get_claude_report(prompt)

    # --- גרפים ---
    def create_radar_chart(self, results):
        categories = [TRAIT_DICT[k] for k in results.keys()]
        values = list(results.values())
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name='הפרופיל שלך',
            line_color='#1E90FF'
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
            showlegend=False,
            title="מפת אישיות HEXACO"
        )
        return fig

    def create_comparison_chart(self, results):
        categories = [TRAIT_DICT[k] for k in results.keys()]
        user_vals = list(results.values())
        ideal_vals = [IDEAL_DOCTOR[k] for k in results.keys()]

        fig = go.Figure()
        fig.add_trace(go.Bar(name='הציון שלך', x=categories, y=user_vals, marker_color='#1E90FF'))
        fig.add_trace(go.Bar(name='פרופיל רופא אידיאלי', x=categories, y=ideal_vals, marker_color='#E0E0E0'))

        fig.update_layout(
            barmode='group',
            yaxis=dict(range=[1, 5], title="ציון (1-5)"),
            title="השוואה לפרופיל המקצועי הנדרש"
        )
        return fig

# פונקציות עזר לקריאה נוחה מה-App
def get_multi_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_multi_report(user_name, results, history)

def get_radar_chart(results):
    return HEXACO_Analyzer().create_radar_chart(results)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)