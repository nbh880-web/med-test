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

# פרופיל יעד מעודכן - ממוצע הטווחים האידיאליים לרפואה
IDEAL_DOCTOR = {
    "Honesty-Humility": 4.55,      # מרכז הטווח 4.2-4.9
    "Emotionality": 3.85,         # מרכז הטווח 3.6-4.1
    "Extraversion": 3.9,          # מרכז הטווח 3.6-4.2
    "Agreeableness": 4.3,         # מרכז הטווח 4.0-4.6
    "Conscientiousness": 4.55,    # מרכז הטווח 4.3-4.8
    "Openness to Experience": 3.8  # מרכז הטווח 3.5-4.1
}

class HEXACO_Analyzer:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_KEY_1", "").strip()

    def create_radar_chart(self, user_results):
        """יוצר גרף מכ"ם היקפי להשוואה מול יעד הרופא"""
        if not user_results: return None
        
        categories = [TRAIT_DICT.get(k, k)[::-1] for k in user_results.keys()]
        user_vals = list(user_results.values())
        ideal_vals = [IDEAL_DOCTOR.get(k, 3.5) for k in user_results.keys()]
        
        # סגירת מעגל הגרף
        categories.append(categories[0])
        user_vals.append(user_vals[0])
        ideal_vals.append(ideal_vals[0])
        
        fig = go.Figure()
        
        # שכבת היעד
        fig.add_trace(go.Scatterpolar(
            r=ideal_vals,
            theta=categories,
            fill='toself',
            name='יעד רופא אידיאלי',
            line_color='rgba(46, 204, 113, 0.6)',
            fillcolor='rgba(46, 204, 113, 0.2)'
        ))
        
        # שכבת המשתמש
        fig.add_trace(go.Scatterpolar(
            r=user_vals,
            theta=categories,
            fill='toself',
            name='הפרופיל שלך',
            line_color='#1E90FF',
            fillcolor='rgba(30, 144, 255, 0.3)'
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
            showlegend=True,
            legend=dict(orientation="h", y=-0.2),
            margin=dict(t=30, b=30, l=60, r=60)
        )
        return fig

    def create_comparison_chart(self, user_results):
        """גרף עמודות להשוואת ציונים ישירה"""
        if not user_results: return None
        labels = [TRAIT_DICT.get(k, k) for k in user_results.keys()]
        user_vals = list(user_results.values())
        ideal_vals = [IDEAL_DOCTOR.get(k, 3.5) for k in user_results.keys()]

        fig = go.Figure(data=[
            go.Bar(name='הציון שלך', x=labels, y=user_vals, marker_color='#1E90FF'),
            go.Bar(name='ציון יעד', x=labels, y=ideal_vals, marker_color='#2ECC71')
        ])
        fig.update_layout(
            barmode='group', 
            yaxis=dict(range=[1, 5], title="ציון (1-5)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )
        return fig

    def _discover_model(self):
        target_model = "models/gemini-1.5-flash"
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            res = requests.get(list_url, timeout=10)
            if res.status_code == 200:
                models = res.json().get("models", [])
                for m in models:
                    if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]:
                        return m["name"]
        except: pass
        return target_model

    def generate_report(self, user_name, current_results, history):
        if not self.api_key: return "❌ חסר מפתח API"
        
        target_model = self._discover_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
        
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- היסטוריית ציונים (לניתוח מגמה) ---\n"
            for i, h in enumerate(history[:3]):
                history_context += f"מבחן {i+1}: {h.get('results')}\n"

        prompt = f"""
        תפקיד: פסיכולוג מאבחן ומומחה למיוני רפואה (מס"ר/מרק"ם).
        שם המועמד: {user_name}
        תוצאות נוכחיות: {current_results}
        
        הטווחים המבוקשים בקבלה לרפואה:
        - מצפוניות (C): 4.3 עד 4.8 (אחריות ודיוק)
        - יושר-ענווה (H): 4.2 עד 4.9 (אתיקה והיעדר אגו)
        - נעימות (A): 4.0 עד 4.6 (עבודת צוות וסבלנות)
        - רגשיות (E): 3.6 עד 4.1 (אמפתיה מיוצבת ללא שחיקה)
        - מוחצנות (X): 3.6 עד 4.2 (תקשורת תפקודית רגיעה)
        
        {history_context}
        
        משימות הניתוח:
        1. השווה כל מדד לטווח האידיאלי. אם המועמד בתוך הטווח, ציין זאת לחיוב.
        2. התרע על "Social Desirability" אם יש ריבוי ציונים של 4.9-5.0.
        3. אם המצפוניות מתחת ל-3.8, הדגש שזה "דגל אדום" קריטי למקצוע הרפואה.
        4. נתח מגמות: האם המועמד משתפר או נסוג בויסות הרגשי (E) ובנעימות (A)?
        5. סיכום: 3 דגשים קונקרטיים להתנהלות בסימולציה מול שחקן.
        
        כתוב בעברית רהוטה, בגוף שני, בפורמט של נקודות ברורות.
        """
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {'Content-Type': 'application/json'}

        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
            except: time.sleep(1)
        
        return "⚠️ שרת ה-AI אינו זמין כרגע."

def get_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_report(user_name, results, history)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)

def get_radar_chart(results):
    return HEXACO_Analyzer().create_radar_chart(results)