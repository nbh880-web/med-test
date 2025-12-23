import streamlit as st
import google.generativeai as genai
from google.generativeai.types import RequestOptions

def get_ai_analysis(user_name, results_summary):
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets."
    
    try:
        # הגדרה עם transport='rest' ושימוש בגרסת API v1 באופן מפורש
        genai.configure(
            api_key=st.secrets["GEMINI_KEY_1"],
            transport='rest'
        )
        
        # יצירת המודל עם הגדרת timeout למניעת תקיעות
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        
        prompt = f"""
        משימה: ניתוח תוצאות שאלון HEXACO למועמד לרפואה (מס"ר).
        שם המועמד: {user_name}
        
        תוצאות גולמיות:
        {results_summary}
        
        כתוב חוות דעת מקצועית בעברית (טקסט בלבד):
        1. סיכום התאמה אישיותית לעולם הרפואה.
        2. דגש על מדד היושרה (Honesty-Humility).
        3. אזהרות לגבי חוסר עקביות (אם יש).
        4. טיפ ליום המיון במרכז מס"ר.
        """
        
        # שימוש ב-RequestOptions כדי להכריח את הגרסה היציבה
        response = model.generate_content(
            prompt,
            request_options=RequestOptions(api_version='v1')
        )
        
        if response and response.text:
            return response.text
        return "המערכת לא החזירה תוכן מילולי."
            
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return "שגיאה 404: השרת לא מזהה את המודל. וודא שביצעת 'Clear Cache' ב-Streamlit Cloud."
        return f"שגיאה בחיבור ל-AI: {error_msg}"
