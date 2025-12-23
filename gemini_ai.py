import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    """
    מפיק ניתוח ממוקד למבחני מס"ר על בסיס שאלון HEXACO.
    """
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets."
    
    try:
        # הגדרה מפורשת של גרסה v1 כדי למנוע שגיאת 404 של v1beta
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"], transport='rest')
        
        # בחירת מודל Flash יציב
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash'
        )
        
        prompt = f"""
        ניתוח תוצאות HEXACO עבור המועמד/ת לרפואה: {user_name}.
        הקשר: הכנה למבחני מס"ר (מרכז הערכה לרפואה בישראל).
        
        נתוני התוצאות:
        {results_summary}
        
        משימה:
        כתוב דו"ח ניתוח בעברית (ללא כוכביות או סולמיות) הכולל:
        1. סיכום הפרופיל האישי של {user_name}.
        2. ניתוח רמת העקביות והיושרה (Honesty-Humility) בהקשר של אתיקה רפואית.
        3. האם הציונים משקפים פרופיל מאוזן המתאים לעבודה עם מטופלים?
        4. המלצות פרקטיות למבחן האמיתי ביום המיון.
        """
        
        # יצירת תוכן
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "המערכת לא החזירה טקסט, נסה שוב."
            
    except Exception as e:
        # טיפול בשגיאות נפוצות
        error_msg = str(e)
        if "404" in error_msg:
            return "שגיאה טכנית: המודל לא נמצא בגרסה זו. וודא שחבילת google-generativeai מעודכנת."
        return f"שגיאה בחיבור ל-AI: {error_msg}"
