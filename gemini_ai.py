import streamlit as st
import requests
import json
import plotly.graph_objects as go
import time
from datetime import datetime

# --- הגדרות ליבה ומילוני תרגום ---
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

class HEXACO_System:
    def __init__(self):
        # טעינת מפתחות
        self.gemini_keys = [st.secrets.get(f"GEMINI_KEY_{i}", "").strip() for i in range(1, 4)]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        self.claude_key = st.secrets.get("CLAUDE_KEY", "").strip()
        self.error_log = []

    # --- פונקציית Discovery למציאת מודל Gemini פנוי ---
    def _get_available_gemini_model(self, api_key):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                models = [m['name'] for m in res.json().get('models', []) if 'generateContent' in m['supportedGenerationMethods']]
                # עדיפות ל-Pro, אם לא אז Flash
                for m in models: 
                    if "1.5-pro" in m: return m
                return models[0] if models else None
        except: return None

    # --- פונקציית קריאה ל-Claude ---
    def _call_claude(self, prompt):
        if not self.claude_key: return "⚠️ מפתח Claude חסר."
        try:
            headers = {"x-api-key": self.claude_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            payload = {"model": "claude-3-5-sonnet-20240620", "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}]}
            res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=150)
            return res.json()['content'][0]['text'] if res.status_code == 200 else f"Error Claude: {res.status_code}"
        except Exception as e: return f"Claude Exception: {str(e)}"

    # --- פונקציית Gemini עם Discovery ו-Failover ---
    def _call_gemini_with_failover(self, prompt):
        for i, key in enumerate(self.gemini_keys, 1):
            model = self._get_available_gemini_model(key)
            if not model: continue
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.85, "maxOutputTokens": 8192}}
                res = requests.post(url, json=payload, timeout=120)
                if res.status_code == 200:
                    return res.json()['candidates'][0]['content']['parts'][0]['text']
            except: continue
        return "❌ כל ניסיונות הפנייה ל-AI נכשלו."

    # --- ויזואליזציה (Plotly) ---
    def create_radar_chart(self, results):
        categories = [TRAIT_DICT[k] for k in results.keys()]
        user_vals = list(results.values())
        ideal_vals = [IDEAL_DOCTOR[k] for k in results.keys()]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=ideal_vals + [ideal_vals[0]], theta=categories + [categories[0]], fill='toself', name='🎯 יעד מס"ר', line=dict(color='rgba(46, 204, 113, 0.8)')))
        fig.add_trace(go.Scatterpolar(r=user_vals + [user_vals[0]], theta=categories + [categories[0]], fill='toself', name='📊 הפרופיל שלך', line=dict(color='#3498DB', width=4)))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 5])), title="מפת אישיות HEXACO")
        return fig

    def create_token_gauge(self, text_content):
        tokens = int(len(text_content.split()) * 1.5) if text_content else 0
        fig = go.Figure(go.Indicator(mode="gauge+number", value=tokens, title={'text': "עומק ניתוח (Tokens)"}, gauge={'axis': {'range': [0, 8000]}, 'bar': {'color': "#2ECC71"}}))
        fig.update_layout(height=250)
        return fig

    # --- לוגיקה חישובית ---
    def calculate_compatibility(self, results):
        total_points = 0
        details = []
        for trait, score in results.items():
            ranges = TRAIT_RANGES[trait]
            if ranges["optimal_low"] <= score <= ranges["optimal_high"]: points = 100
            elif score < ranges["critical_low"] or score > ranges["critical_high"]: points = 40
            else: points = 75
            total_points += points
            details.append(f"{TRAIT_DICT[trait]}: {points}/100")
        return int(total_points / 6), "\n".join(details)

    # --- יצירת דוח AI משולב (Gemini + Claude + History) ---
    def generate_reports(self, user_name, current_results, history=[]):
        # 1. ניתוח פערים אוטומטי
        gap_analysis = ""
        for trait, score in current_results.items():
            ideal = IDEAL_DOCTOR[trait]
            diff = score - ideal
            status = "🔴" if abs(diff) > 0.6 else "🟡" if abs(diff) > 0.3 else "✅"
            gap_analysis += f"{status} {TRAIT_DICT[trait]}: {score:.2f} (פער: {diff:+.2f})\n"

        # 2. ניתוח מגמות היסטורי
        trends = "אין היסטוריה קודמת."
        if history:
            trends = "שינויים מהמבחן האחרון:\n"
            last_res = history[-1]['results']
            for trait, score in current_results.items():
                change = score - last_res.get(trait, score)
                icon = "📈" if change > 0.05 else "📉" if change < -0.05 else "➡️"
                trends += f"{icon} {TRAIT_DICT[trait]}: {change:+.2f}\n"

        # 3. בניית הפרומפטים (לפי ההוראות שלך)
        base_context = f"מועמד: {user_name}\nנתונים:\n{gap_analysis}\n\n{trends}"
        
        gemini_prompt = f"אתה פסיכולוג מס\"ר. כתוב דוח מעשי (1200 מילים) הכולל סיכום, ניתוח אינטגרטיבי, זיהוי ריצוי חברתי, והכנה לראיון.\n\n{base_context}"
        claude_prompt = f"You are Dr. Rachel Goldstein, clinical psychologist. Write a deep 1500-word Hebrew report: Executive Summary, Six-Factor Deep Dive (250+ words per trait), Risk Assessment and Development Plan.\n\n{base_context}"

        return self._call_gemini_with_failover(gemini_prompt), self._call_claude(claude_prompt)

# --- ממשק Streamlit ---
def main():
    st.set_page_config(page_title="HEXACO Expert - Dual AI", layout="wide")
    system = HEXACO_System()

    if 'results' not in st.session_state:
        st.session_state.results = {"Honesty-Humility": 4.1, "Emotionality": 3.2, "Extraversion": 3.7, "Agreeableness": 4.0, "Conscientiousness": 4.6, "Openness to Experience": 3.9}
    if 'history' not in st.session_state:
        st.session_state.history = [] # כאן ניתן להוסיף מבחני עבר

    st.title("🩺 מערכת הערכה פסיכולוגית - ניתוח מומחים משולב")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(system.create_radar_chart(st.session_state.results), use_container_width=True)
    with col2:
        score, details = system.calculate_compatibility(st.session_state.results)
        st.metric("מדד התאמה לרפואה", f"{score}%")
        with st.expander("פירוט ניקוד"): st.text(details)

    if st.button("🚀 הפעל מעריך פסיכולוגי (Gemini + Claude)"):
        with st.spinner("המומחים מנתחים..."):
            gemini_rep, claude_rep = system.generate_reports("מועמד בדיקה", st.session_state.results, st.session_state.history)
            
            t1, t2 = st.tabs(["🤖 דוח Gemini (מעשי)", "🧠 דוח Claude (עמוק)"])
            with t1:
                st.markdown(gemini_rep)
                st.plotly_chart(system.create_token_gauge(gemini_rep))
            with t2:
                st.markdown(claude_rep)
                st.plotly_chart(system.create_token_gauge(claude_rep))

if __name__ == "__main__":
    main()