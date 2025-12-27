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
        # טעינת המפתחות מה-Secrets
        self.gemini_keys = [
            st.secrets.get("GEMINI_KEY_1", "").strip(),
            st.secrets.get("GEMINI_KEY_2", "").strip()
        ]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        self.claude_key = st.secrets.get("CLAUDE_KEY", "").strip()

    def _discover_gemini_model(self, api_key):
        default_model = "models/gemini-1.5-flash"
        if not api_key: return default_model
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            res = requests.get(list_url, timeout=7)
            if res.status_code == 200:
                models_data = res.json().get("models", [])
                flash_models = [
                    str(m["name"]) for m in models_data 
                    if isinstance(m.get("name"), str) and "flash" in m["name"].lower()
                ]
                if flash_models: return flash_models[-1]
        except: pass
        return default_model

    def _discover_claude_model(self):
        default_model = "claude-3-5-sonnet-20241022"
        if not self.claude_key: return default_model
        try:
            url = "https://api.anthropic.com/v1/models"
            headers = {"x-api-key": self.claude_key, "anthropic-version": "2023-06-01"}
            res = requests.get(url, headers=headers, timeout=7)
            if res.status_code == 200:
                sonnet_models = [m["id"] for m in res.json().get("data", []) if "sonnet" in m["id"].lower()]
                if sonnet_models: return sorted(sonnet_models)[-1]
        except: pass
        return default_model

    def generate_multi_report(self, user_name, current_results, history):
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- מגמות עבר (מבחנים קודמים) ---\n"
            for h in history[:3]: # הגדלנו ל-3 מבחנים לניתוח מגמה עמוק
                results_data = h.get('results', '{}')
                history_context += f"מבחן קודם: {results_data}\n"

        prompt = f"""
        תפקיד: פסיכולוג בכיר במרכז הערכה לרפואה (מס"ר/מרק"ם).
        משימה: ניתוח עומק נוקב ומפורט של אישיות המועמד {user_name}.
        נתונים נוכחיים: {current_results}
        {history_context}
        
        דרישות הדוח:
        1. ניתוח כל תכונה מול יעד הרופא עם התייחסות למגמת העלייה/ירידה מהעבר.
        2. זיהוי 'פער סיכון' (למשל נפילה במצפוניות).
        3. ניתוח חשד לריצוי חברתי (Social Desirability).
        4. 3 עצות מעשיות לסימולציה מול שחקן המבוססות על חולשות המועמד.
        
        הוראות: עברית רהוטה, דוח ארוך ומפורט מאוד (לפחות 800 מילים).
        """
        return self._call_gemini_with_failover(prompt), self._call_claude_with_detailed_errors(prompt)

    def _call_gemini_with_failover(self, prompt):
        if not self.gemini_keys: return "❌ חסר מפתח Gemini"
        for i, key in enumerate(self.gemini_keys):
            try:
                model = self._discover_gemini_model(key)
                url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={key}"
                res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
                if res.status_code == 200:
                    return res.json()['candidates'][0]['content']['parts'][0]['text']
            except: continue
        return "❌ כל נסיונות Gemini נכשלו"

    def _call_claude_with_detailed_errors(self, prompt):
        if not self.claude_key: return "❌ חסר מפתח Claude"
        try:
            model_id = self._discover_claude_model()
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.claude_key, 
                "anthropic-version": "2023-06-01", 
                "content-type": "application/json"
            }
            payload = {
                "model": model_id, 
                "max_tokens": 4096, # תיקון: הגדלה למקסימום כדי שלא יחתך
                "messages": [{"role": "user", "content": prompt}]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=45)
            if res.status_code == 200:
                return res.json()['content'][0]['text']
            
            error_msg = self._parse_api_error('Claude', res)
            return f"❌ שגיאת Claude: {error_msg}"
        except Exception as e:
            return f"⚠️ תקלה בחיבור ל-Claude: {str(e)}"

    def _parse_api_error(self, provider, response):
        status = response.status_code
        try:
            detail = response.json()
            msg = detail.get('error', {}).get('message', str(detail)) if provider == "Claude" else str(detail)
        except: msg = response.text
        if status == 429: return "חריגה ממכסת שימוש או חוסר בקרדיט."
        elif status == 401: return "מפתח API לא תקין."
        return f"שגיאה {status}: {msg[:100]}"

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

# פונקציות עזר לשעון טוקנים
def create_token_gauge(text_content):
    """
    יוצר שעון ויזואלי המראה כמה טוקנים נוצלו מתוך הקיבולת
    """
    # הערכה גסה: בעברית כל מילה היא בערך 1.5 טוקנים
    estimated_tokens = int(len(text_content.split()) * 1.6)
    max_cap = 4096
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = estimated_tokens,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "ניצול טוקנים (עומק דוח)", 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [None, max_cap], 'tickwidth': 1},
            'bar': {'color': "#1E90FF"},
            'steps': [
                {'range': [0, 1000], 'color': "#E8F4F8"},
                {'range': [1000, 3000], 'color': "#D1EAF0"},
                {'range': [3000, 4096], 'color': "#A9D6E5"}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 3900}}))
    
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# פונקציות ממשק
def get_multi_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_multi_report(user_name, results, history)

def get_radar_chart(results):
    return HEXACO_Analyzer().create_radar_chart(results)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)