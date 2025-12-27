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
        # סינון מפתחות שלא הוכנסו
        self.gemini_keys = [k for k in self.gemini_keys if k]
        self.claude_key = st.secrets.get("CLAUDE_KEY", "").strip()

    def _discover_gemini_model(self, api_key):
        """
        מנגנון Discovering דינמי: מחפש את מודל ה-Flash הזמין ביותר עבור המפתח הנוכחי.
        """
        default_model = "models/gemini-1.5-flash"
        if not api_key: return default_model
        
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            res = requests.get(list_url, timeout=7)
            if res.status_code == 200:
                models = res.json().get("models", [])
                # סינון מודלים שתומכים ב-GenerateContent וכוללים 'flash'
                flash_models = [
                    m["name"] for m in models 
                    if "flash" in m["name"].lower() and "generateContent" in m["supportedGenerationMethods"]
                ]
                if flash_models:
                    # מחזיר את המודל האחרון ברשימה (לרוב הגרסה החדשה ביותר)
                    return flash_models[-1]
        except Exception:
            pass 
        return default_model

    def generate_multi_report(self, user_name, current_results, history):
        history_context = ""
        if history and isinstance(history, list):
            history_context = "\n--- מגמות עבר (מבחנים קודמים) ---\n"
            for h in history[:2]:
                history_context += f"מבחן קודם: {h.get('results', '{}')}\n"

        prompt = f"""
        תפקיד: פסיכולוג בכיר במרכז הערכה לרפואה (מס"ר/מרק"ם).
        שם המועמד: {user_name}
        נתונים נוכחיים: {current_results}
        {history_context}
        
        טווחים מצופים מרופא: 
        C (מצפוניות): 4.4-4.8, H (כנות): 4.3-4.9, A (נעימות): 4.1-4.6.

        משימה:
        1. ניתוח התאמה מפורט לכל תכונה.
        2. זיהוי 'פער סיכון' או ניסיונות 'ריצוי חברתי'.
        3. עצה מעשית לסימולציה מול שחקן (תקשורת בין-אישית).
        4. שורת סיכום על בשלות למקצוע.
        
        הוראות: עברית רהוטה, נקודות קצרות, גוף שני.
        """
        
        return self._call_gemini_with_failover(prompt), self._call_claude_with_detailed_errors(prompt)

    def _call_gemini_with_failover(self, prompt):
        """
        מנסה את המפתח הראשון. אם נכשל בגלל Quota או שגיאה, עובר אוטומטית למפתח השני.
        """
        if not self.gemini_keys:
            return "❌ שגיאה: לא הוגדרו מפתחות Gemini ב-Secrets."

        attempts_log = []
        for i, key in enumerate(self.gemini_keys):
            try:
                model_name = self._discover_gemini_model(key)
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                
                res = requests.post(url, json=payload, timeout=30)
                
                if res.status_code == 200:
                    return res.json()['candidates'][0]['content']['parts'][0]['text']
                
                # ניתוח שגיאה לפי קוד תגובה
                error_info = self._parse_api_error("Gemini", res)
                attempts_log.append(f"מפתח {i+1}: {error_info}")
                
            except Exception as e:
                attempts_log.append(f"מפתח {i+1}: תקלה טכנית ({str(e)})")
        
        return "❌ כל נסיונות ה-Gemini נכשלו:\n" + "\n".join(attempts_log)

    def _call_claude_with_detailed_errors(self, prompt):
        """
        קריאה ל-Claude עם ניתוח שגיאות מפורט.
        """
        if not self.claude_key:
            return "❌ שגיאה: מפתח Claude חסר ב-Secrets."
        
        try:
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
            res = requests.post(url, headers=headers, json=payload, timeout=35)
            
            if res.status_code == 200:
                return res.json()['content'][0]['text']
            
            return f"❌ שגיאת Claude: {self._parse_api_error('Claude', res)}"
            
        except requests.exceptions.Timeout:
            return "❌ שגיאת Claude: פג זמן ההמתנה לשרת (Timeout)."
        except Exception as e:
            return f"⚠️ תקלה בחיבור ל-Claude: {str(e)}"

    def _parse_api_error(self, provider, response):
        """
        פונקציה מרכזית לניתוח ופירוט שגיאות API.
        """
        status = response.status_code
        try:
            detail = response.json()
        except:
            detail = response.text

        if status == 429:
            return "חריגה ממכסת שימוש (Quota/Rate Limit). נסה שוב מאוחר יותר."
        elif status == 401:
            return "מפתח API לא תקין או פג תוקף (Unauthorized)."
        elif status == 403:
            return "גישה חסומה (Forbidden) - ייתכן מגבלה גאוגרפית או הרשאת מפתח."
        elif status == 400:
            return f"בקשה לא תקינה. ייתכן וסינון התוכן חסם את התשובה."
        elif status >= 500:
            return "שגיאת שרת פנימית אצל הספק (Google/Anthropic)."
        
        return f"שגיאה {status}: {str(detail)[:100]}"

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

# פונקציות ממשק ל-app.py
def get_multi_ai_analysis(user_name, results, history):
    return HEXACO_Analyzer().generate_multi_report(user_name, results, history)

def get_radar_chart(results):
    return HEXACO_Analyzer().create_radar_chart(results)

def get_comparison_chart(results):
    return HEXACO_Analyzer().create_comparison_chart(results)