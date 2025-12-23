import streamlit as st
import google.generativeai as genai

def get_ai_analysis(results_summary):
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets"
    
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"])
        
        # שימוש במודל העדכני והנתמך ביותר
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        prompt = f"""
        נתח את תוצאות מבחן ה-HEXACO הבאות עבור מועמד לרפואה:
        {results_summary}
        כתוב חוות דעת מקצועית בעברית. אל תשתמש בכוכביות, סולמיות או סימני עיצוב מיוחדים.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"שגיאה בתקשורת עם ה-AI: {str(e)}"
