import streamlit as st
import requests
import json
import plotly.graph_objects as go
import time

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

    def create_radar_chart(self, user_results):
        if not user_results: return None
        categories = [TRAIT_DICT.get(k, k)[::-1] for k in user_results.keys()]
        user_vals = list(user_results.values())
        ideal_vals = [IDEAL_DOCTOR.get(k, 3.5) for k in user_results.keys()]
        
        categories.append(categories[0])
        user_vals.append(user_vals[0])
        ideal_vals.append(ideal_vals[0])
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=ideal_vals, theta=categories, fill='toself', name='יעד רופא',
            line_color='rgba(46, 204, 113, 0.6)', fillcolor='rgba(46, 204, 113, 0.2)'
        ))
        fig.add_trace(go.Scatterpolar(
            r=user_vals, theta=categories, fill='toself', name='הפרופיל שלך',
            line_color='#1E90FF', fillcolor='rgba(30, 144, 255, 0.3)'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
            showlegend=True, legend=dict(orientation="h", y=-0.2),
            margin=dict(t=30, b=30, l=60, r=60)
        )
        return fig

    def create_comparison_chart(self, user_results):
        if not user_results: return None
        labels = [TRAIT_DICT.get(k, k) for k in user_results.keys()]
        fig = go.Figure(data=[
            go.Bar(name='הציון שלך', x=labels, y=list(user_results.values()), marker_color='#1E90FF'),
            go.Bar(name='ציון יעד', x=labels, y=[IDEAL_DOCTOR.get(k) for k in user_results.keys()], marker_color='#2ECC71')
        ])
        fig.update_layout(barmode='group', yaxis=dict(range=[1, 5]))
        return fig

    def _get_gemini_report(self, prompt):
        """בוחן 1: Gemini"""
        if not self.gemini_key: return "⚠️ מפתח Gemini חסר"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
        except: pass
        return "⚠️ שרת Gemini אינו זמין."

    def _get_claude_report(self, prompt):
        """בוחן 2: Claude"""
        if not self.claude_key: return "⚠️ מפתח Claude חסר"
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
        except: pass
        return "⚠️ שרת Claude אינו זמין."

    def generate_multi_report(self, user_name, current_results, history):
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- היסטוריית ציונים ---\n"
            for i, h in enumerate(history[:3]):
                history_context += f"מבחן {i+1}: {h.get('results')}\n"

        prompt = f"""
        תפקיד: פסיכולוג מאבחן מומחה למיוני רפואה (מס"ר).
        שם המועמד: {user_name}
        תוצאות HEXACO נוכחיות: {current_results}
        
        טווחים אידיאליים:
        C (מצפוניות): 4.3-4.8 | H (יושר): 4.2-4.9 | A (נעימות): 4.0-4.6 
        E (רגשיות): 3.6-4.1 | X (מוחצנות): 3.6-4.2
        
        {history_context}
        
        משימה:
        1. נתח פערים מול הטווחים.
        2. זהה נטייה לריצוי חברתי (Social Desirability) אם הציונים גבוהים מדי (4.9-5).
        3. תן 3 המלצות התנהגותיות לסימולציה מול שחקן.
        כתוב בעברית מקצועית, בגוף שני, בנקודות.
        """
        
        gemini_res = self._get_gemini_report(prompt)
        claude_res = self._get_claude_report(prompt)
        
        return gemini_res, claude_res

def get_multi_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_multi_report(user_name, results, history)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)

def get_radar_chart(results):
    return HEXACO_Analyzer().create_radar_chart(results)