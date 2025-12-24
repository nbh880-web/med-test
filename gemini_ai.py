import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    # שליפת המפתחות
    api_keys = [st.secrets.get("GEMINI_KEY_1"), st.secrets.get("GEMINI_KEY_2")]
    api_keys = [k for k in api_keys if k]

    if not api_keys:
        return "שגיאה: מפתח API לא מוגדר ב-Secrets."

    # סדר עדיפויות: Pro לניתוח איכותי, Flash לגיבוי מהיר
    models = ['gemini-1.5-pro', 'gemini-1.5-flash']

    for api_key in api_keys:
        genai.configure(api_key=api_key, transport='rest')
        for model_name in models:
            try:
                model = genai.GenerativeModel(model_name)
                prompt = f"""
                פעל כפסיכולוג מומחה למבחני מס"ר. 
                נתח את תוצאות ה-HEXACO של המועמד {user_name}.
                נתונים: {results_summary}
                כתוב חוות דעת מקצועית בעברית על התאמה לאתיקה רפואית ויושרה. 
                אל תשתמש בכוכביות או סמלים.
                """
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text
            except:
                continue
    return "שגיאה: המערכת לא הצליחה להתחבר למודלים של Gemini. בדוק את מפתחות ה-API."
