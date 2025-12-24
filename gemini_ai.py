import streamlit as st
import requests
import json

class HEXACO_AI_Engine:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_KEY_1", "").strip()

    def generate_professional_report(self, user_name, results):
        if not self.api_key:
            return "שגיאה: מפתח API חסר ב-Secrets."

        # שלב 1: חקירה - איזה מודל זמין למפתח הזה?
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            models_res = requests.get(list_url, timeout=10)
            if models_res.status_code == 200:
                models_list = models_res.json().get("models", [])
                # מחפש מודל שתומך ביצירת תוכן
                available = [m["name"] for m in models_list if "generateContent" in m.get("supportedGenerationMethods", [])]
                # עדיפות ל-flash, אם אין - מה שיש
                target_model = next((m for m in available if "flash" in m), available[0] if available else None)
            else:
                target_model = "models/gemini-1.5-flash" # ברירת מחדל אם הרשימה נכשלה
        except:
            target_model = "models/gemini-1.5-flash"

        # שלב 2: שליחת הפרומפט למודל שנמצא
        url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
        
        prompt = f"""
        פעל כמעריך בכיר במרכז מס"ר (מרכז סימולציה רפואית) בשיטת ה-MSR למיון מועמדים לרפואה.
        נתח את תוצאות ה-HEXACO של המועמד {user_name} על פי המדדים הבאים: {results}.
        
        דרישות הדוח (בעברית רהוטה):
        1. הערכת יושרה וצניעות: אמינות המועמד כרופא.
        2. תקשורת ונעימות: עבודה בצוות וקונפליקטים.
        3. חוסן נפשי: עמידה בלחץ ושחיקה.
        4. פוטנציאל מנהיגות רפואית.
        5. המלצה סופית לבוחני מס"ר.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            return f"שגיאה (Status {response.status_code}): {response.json().get('error', {}).get('message', 'Unknown')}"
        except Exception as e:
            return f"שגיאת תקשורת: {str(e)}"

def get_ai_analysis(user_name, results_summary):
    engine = HEXACO_AI_Engine()
    return engine.generate_professional_report(user_name, results_summary)
