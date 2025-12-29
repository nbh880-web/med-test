import streamlit as st
import requests
import json
import plotly.graph_objects as go
import time
from datetime import datetime

# --- 1. הגדרות ליבה וטווחים פסיכומטריים (ניתוח פערים) ---
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

TRAIT_RANGES = {
    "Honesty-Humility": {"critical_low": 3.5, "optimal_low": 4.2, "optimal_high": 4.9, "critical_high": 5.0},
    "Emotionality": {"critical_low": 2.8, "optimal_low": 3.6, "optimal_high": 4.1, "critical_high": 4.5},
    "Extraversion": {"critical_low": 2.5, "optimal_low": 3.6, "optimal_high": 4.2, "critical_high": 4.8},
    "Agreeableness": {"critical_low": 3.2, "optimal_low": 4.0, "optimal_high": 4.6, "critical_high": 5.0},
    "Conscientiousness": {"critical_low": 3.8, "optimal_low": 4.3, "optimal_high": 4.8, "critical_high": 5.0},
    "Openness to Experience": {"critical_low": 2.8, "optimal_low": 3.5, "optimal_high": 4.1, "critical_high": 4.7}
}

class HEXACO_Expert_System:
    def __init__(self):
        # Failover ל-3 מפתחות Gemini
        self.gemini_keys = [
            st.secrets.get("GEMINI_KEY_1", "").strip(),
            st.secrets.get("GEMINI_KEY_2", "").strip(),
            st.secrets.get("GEMINI_KEY_3", "").strip()
        ]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        # שים לב: כאן השתמשתי ב-CLAUDE_KEY וגם ב-ANTHROPIC_API_KEY ליתר ביטחון
        self.claude_key = st.secrets.get("CLAUDE_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "").strip()

    # --- מנגנוני API ו-Failover ---
    def _get_model_discovery(self, api_key):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                models = [m['name'] for m in res.json().get('models', []) if 'generateContent' in m['supportedGenerationMethods']]
                for m in models:
                    if "1.5-flash" in m: return m
                return models[0] if models else "models/gemini-1.5-flash"
        except: pass
        return "models/gemini-1.5-flash"

    def _call_gemini_safe(self, prompt):
        if not self.gemini_keys: return "❌ מפתחות Gemini חסרים."
        for i, key in enumerate(self.gemini_keys, 1):
            model = self._get_model_discovery(key)
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={key}"
                res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
                if res.status_code == 200:
                    data = res.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
                elif res.status_code == 429:
                    st.warning(f"מפתח #{i} חרג מהמכסה, עובר למפתח הבא...")
                    continue
            except: continue
        return "❌ כל ניסיונות ה-Gemini נכשלו."

    def _call_claude(self, prompt):
        if not self.claude_key: return "⚠️ מפתח Claude חסר."
        
        # רשימת מודלים לניסיון לפי סדר עדיפות - כדי למנוע 404
        models_to_try = [
            "claude-sonnet-4-20250514",      # המודל החדש והמומלץ
            "claude-3-5-sonnet-20241022",    # גיבוי יציב
            "claude-3-5-sonnet-latest"       # גיבוי כללי
        ]
        
        headers = {
            "x-api-key": self.claude_key, 
            "anthropic-version": "2023-06-01", 
            "content-type": "application/json"
        }

        for model_name in models_to_try:
            try:
                payload = {
                    "model": model_name, 
                    "max_tokens": 4096, 
                    "messages": [{"role": "user", "content": prompt}]
                }
                res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)
                
                if res.status_code == 200:
                    return res.json()['content'][0]['text']
                elif res.status_code == 404:
                    continue # מנסה את המודל הבא אם הנוכחי לא נמצא ב-Tier שלך
                else:
                    return f"❌ שגיאת Claude ({model_name}): {res.status_code} - {res.text}"
            except Exception as e: 
                return f"❌ שגיאה ב-Claude: {str(e)}"
        
        return "❌ שגיאת 404: המודל לא זמין בחשבון זה."

    # --- לוגיקה פסיכומטרית ---
    def calculate_compatibility_score(self, results):
        if not results: return 0
        total = 0
        for trait, score in results.items():
            r = TRAIT_RANGES.get(trait, {})
            if r.get("optimal_low", 0) <= score <= r.get("optimal_high", 5): total += 100
            elif score < r.get("critical_low", 0) or score > r.get("critical_high", 5): total += 30
            else: total += 70
        return int(total / 6)

    # --- הפקת דוחות משולבת (עם היסטוריה) ---
    def generate_expert_reports(self, name, results, history=[]):
        # ניתוח פערים לטקסט
        gaps = "\n".join([f"{TRAIT_DICT.get(t, t)}: {s:.2f} (יעד: {IDEAL_DOCTOR.get(t, 'N/A')})" for t, s in results.items()])
        
        # ניתוח מגמות (3 מבחנים אחרונים)
        trend_text = "אין היסטוריה קודמת"
        if history:
            last_3 = history[-3:]
            trend_text = "\n".join([f"מבחן מ-{h.get('test_date', 'unknown')}: {h.get('results', '{}')}" for h in last_3])

        gemini_prompt = f"""
        אתה פסיכולוג ארגוני בכיר במיוני רפואה (מס"ר).
        מועמד: {name}
        תוצאות נוכחיות: {json.dumps(results)}
        ניתוח פערים: {gaps}
        היסטוריית מגמות: {trend_text}
        
        כתוב דוח מפורט (לפחות 1200 מילים) בעברית הכולל:
        1. סיכום מנהלים על התאמת המועמד.
        2. ניתוח עומק של כל תכונה HEXACO והשפעתה על תפקוד כרופא.
        3. זיהוי סתירות או דפוסי התנהגות חריגים.
        4. הכנה ממוקדת לסימולציות ולראיון האישי.
        """
        
        claude_prompt = f"""
        אתה ד"ר רחל גולדשטיין, פסיכולוגית קלינית בכירה המומחית למיון מועמדים לרפואה.
        מועמד: {name}
        תוצאות: {json.dumps(results)}
        נתח את הסיכונים הקליניים והתאמת המועמד למצבי לחץ .
        ניתוח עומק של כל תכונה HEXACO והשפעתה על תפקוד כרופא.
        זיהוי סתירות או דפוסי התנהגות חריגים.
        הכנה ממוקדת לסימולציות ולראיון האישי.
        כתוב דוח של 1500 מילים בעברית.
        """
        
        return self._call_gemini_safe(gemini_prompt), self._call_claude(claude_prompt)

    # --- גרפים ---
    def create_radar_chart(self, results):
        if not results: return go.Figure()
        fig = go.Figure()
        cat = [TRAIT_DICT.get(k, k) for k in results.keys()]
        val = list(results.values())
        ideal = [IDEAL_DOCTOR.get(k, 3) for k in results.keys()]
        
        fig.add_trace(go.Scatterpolar(r=ideal+[ideal[0]], theta=cat+[cat[0]], fill='toself', name='🎯 יעד', line=dict(color='rgba(46,204,113,0.5)')))
        fig.add_trace(go.Scatterpolar(r=val+[val[0]], theta=cat+[cat[0]], fill='toself', name='📊 אתה', line=dict(color='#1e3a8a', width=4)))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 5])), paper_bgcolor='rgba(0,0,0,0)')
        return fig

    def create_comparison_bar_chart(self, results):
        if not results: return go.Figure()
        cat = [TRAIT_DICT.get(k, k) for k in results.keys()]
        val = list(results.values())
        ideal = [IDEAL_DOCTOR.get(k, 3) for k in results.keys()]

        fig = go.Figure(data=[
            go.Bar(name='אתה', x=cat, y=val, marker_color='#1e3a8a'),
            go.Bar(name='יעד רפואי', x=cat, y=ideal, marker_color='rgba(46,204,113,0.5)')
        ])
        fig.update_layout(barmode='group', yaxis=dict(range=[1, 5]), paper_bgcolor='rgba(0,0,0,0)')
        return fig

    def create_token_gauge(self, text):
        tokens = int(len(str(text).split()) * 1.5) if text else 0
        fig = go.Figure(go.Indicator(mode="gauge+number", value=tokens, title={'text': "Tokens"},
                                     gauge={'axis': {'range': [0, 8000]}, 'bar': {'color': "#2ECC71"}}))
        fig.update_layout(height=250)
        return fig

# פונקציות גלובליות לשימוש ב-app.py
def get_multi_ai_analysis(name, results, history=[]):
    return HEXACO_Expert_System().generate_expert_reports(name, results, history)

def get_radar_chart(results):
    return HEXACO_Expert_System().create_radar_chart(results)

def get_comparison_chart(results):
    return HEXACO_Expert_System().create_comparison_bar_chart(results)

def create_token_gauge(text):
    return HEXACO_Expert_System().create_token_gauge(text)
