import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets."
    
    try:
        # הגדרת המפתח עם פרוטוקול rest למניעת שגיאות גרסה
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"], transport='rest')
        
        # שימוש בשם המודל המלא כולל הגדרת v1 (הגרסה היציבה)
        # זה מונע מהספרייה לנסות לגשת ל-v1beta הבעייתי
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        
        prompt = f"""
        ניתוח תוצאות שאלון HEXACO עבור המועמד/ת לרפואה: {user_name}.
        הקשר: הכנה למבחני מס"ר (מרכז הערכה לרפואה בישראל).
        
        נתוני התוצאות:
        {results_summary}
        
        כתוב חוות דעת מקצועית בעברית (טקסט בלבד, ללא כוכביות) הכוללת:
        1. סיכום הפרופיל של {user_name} כרופא/ה לעתיד.
        2. דגש על מדד היושרה (Honesty-Humility) והתאמתו לאתיקה הרפואית.
        3. האם התשובות עקביות או שיש חשד לניסיון "לרצות" את המבחן?
        4. טיפ פרקטי אחד ליום המבחן האמיתי.
        """
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        return "המערכת לא החזירה טקסט, נסה שוב בעוד רגע."
            
    except Exception as e:
        # טיפול בשגיאת 404 ספציפית בתוך הקוד
        if "404" in str(e):
            return "שגיאה טכנית: ה-API של גוגל לא מזהה את המודל בגרסה זו. וודא שביצעת Reboot לאפליקציה."
        return f"שגיאה בחיבור ל-AI: {str(e)}"
