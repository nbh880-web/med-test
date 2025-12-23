import streamlit as st
import google.generativeai as genai

def get_ai_analysis(results_summary):
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets"
    
    genai.configure(api_key=st.secrets["GEMINI_KEY_1"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    אתה מומחה לניתוח מבחני אישיות HEXACO לקבלה לרפואה. 
    נתח את התוצאות הבאות וספק המלצות לשיפור ושימור:
    {results_summary}
    כתוב בעברית, בצורה מקצועית ומעודדת.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"שגיאה בתקשורת עם ה-AI: {e}"
