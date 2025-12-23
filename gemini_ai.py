import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    """
    מפיק ניתוח ממוקד למבחני מס"ר על בסיס שאלון HEXACO.
    """
    # 1. בדיקת מפתח API
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets."
    
    try:
        # 2. הגדרת המפתח ושימוש ב-transport='rest' כדי לעקוף שגיאות גרסה
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"], transport='rest')
        
        # 3. אתחול מודל Flash בגרסה היציבה
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 4. הכנת ה-Prompt (ממוקד מס"ר)
        prompt = f"""
        ניתוח תוצאות שאלון HEXACO עבור המועמד/ת לרפואה: {user_name}.
        הקשר: הכנה למבחני מס"ר (מרכז הערכה לרפואה בישראל).
        
        נתוני התוצאות (ממוצעים):
        {results_summary}
        
        משימה:
        כתוב חוות דעת מקצועית בעברית (טקסט נקי, ללא כוכביות או סולמיות) הכוללת:
        1. סיכום קצר של הפרופיל האישי של {user_name}.
        2. דגש מיוחד על מדד ה'יושרה-ענווה' (Honesty-Humility) כפי שנמדד ב-HEXACO - האם הוא בטווח המצופה מרופא?
        3. ניתוח רמת העקביות של המועמד (האם הוא ענה בצורה אותנטית).
        4. המלצה אחת מרכזית לשיפור ביום המבחן האמיתי.
        """
        
        # 5. יצירת התוכן
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "המערכת לא החזירה תשובה. נסה שוב."
            
    except Exception as e:
        # הדפסת שגיאה מפורטת במידת הצורך
        return f"שגיאה בחיבור ל-AI: {str(e)}"
