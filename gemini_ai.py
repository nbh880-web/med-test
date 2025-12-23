import streamlit as st
import google.generativeai as genai

def get_ai_analysis(results_summary):
    # בדיקת קיום מפתחות
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets"
    
    try:
        # הגדרת המפתח והמודל (שימוש ב-gemini-pro היציב)
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"])
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        אתה מומחה לניתוח מבחני אישיות HEXACO לקבלה לרפואה בישראל.
        נתח את התוצאות הבאות עבור המועמד:
        {results_summary}
        
        דגשים לכתיבה:
        1. האם הציונים בטווח המצופה לרופא (3.5-4.5)?
        2. התייחס לעקביות וזמני תגובה.
        3. ספק המלצות פרקטיות לשיפור לקראת המבחן האמיתי.
        כתוב בעברית רהוטה ומקצועית.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"שגיאה בתקשורת עם ה-AI: {str(e)}"
