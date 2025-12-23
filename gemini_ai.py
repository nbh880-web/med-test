import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets."
    
    try:
        # הגדרה בסיסית - הגרסאות החדשות של הספרייה מטפלות בזה אוטומטית
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"])
        
        # בחירת המודל
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        ניתוח HEXACO עבור מועמד למבחני מסר: {user_name}.
        תוצאות: {results_summary}
        
        כתוב דו"ח בעברית (ללא עיצוב מורכב) הכולל:
        1. סיכום הפרופיל של {user_name}.
        2. ניתוח עקביות ויושרה בהקשר של קבלה לרפואה.
        3. דגשים ליום המבחן.
        """
        
        # הוספת safety_settings למניעת חסימת הניתוח על ידי גוגל
        response = model.generate_content(
            prompt,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        
        if response and response.text:
            return response.text
        return "המערכת לא החזירה טקסט."
            
    except Exception as e:
        return f"שגיאה בחיבור ל-AI: {str(e)}"
