import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    # שליפת המפתחות בצורה בטוחה
    keys = [st.secrets.get("GEMINI_KEY_1"), st.secrets.get("GEMINI_KEY_2")]
    keys = [k for k in keys if k]

    if not keys:
        return "שגיאה: מפתח API לא נמצא ב-Secrets."

    for api_key in keys:
        try:
            # התיקון הקריטי: transport='rest'
            genai.configure(api_key=api_key, transport='rest')
            
            # הגדרת המודל
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            ניתוח HEXACO עבור {user_name} לקראת מבחני מס"ר.
            תוצאות: {results_summary}
            
            כתוב חוות דעת מקצועית בעברית:
            1. התאמה לרפואה.
            2. דגש על יושרה-ענווה (Honesty-Humility).
            3. טיפ למבחן.
            (ללא כוכביות או סולמיות).
            """
            
            response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            if api_key == keys[-1]:
                return f"שגיאה בחיבור ל-AI: {str(e)}"
            continue

    return "לא ניתן היה להפיק ניתוח."
