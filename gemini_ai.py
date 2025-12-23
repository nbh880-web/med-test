import streamlit as st
import google.generativeai as genai

def get_ai_analysis(results_summary):
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets"
    
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"])
        
        # שימוש במודל gemini-pro (ללא גרסאות בטא)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        אתה מומחה לניתוח מבחני אישיות HEXACO לקבלה לרפואה.
        נתח את התוצאות הבאות עבור מועמד:
        {results_summary}
        כתוב חוות דעת מקצועית בעברית, התייחס לציונים (טווח 3.5-4.5) ולזמני תגובה.
        """
        
        # הוספת הגדרת בטיחות בסיסית כדי למנוע חסימות מיותרות
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # ניסיון אחרון עם שם מודל חלופי אם הראשון נכשל
        try:
            model = genai.GenerativeModel('models/gemini-1.0-pro')
            response = model.generate_content(prompt)
            return response.text
        except:
            return f"שגיאה בתקשורת עם ה-AI: {str(e)}"
