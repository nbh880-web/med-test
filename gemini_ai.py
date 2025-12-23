import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    """
    מפיק ניתוח ממוקד למבחני מס"ר (קבלה לרפואה) על בסיס שאלון HEXACO.
    """
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets של המערכת."
    
    try:
        # הגדרת ה-API
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"])
        
        # שימוש במודל יציב ומהיר
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        המערכת מנתחת את תוצאות שאלון ה-HEXACO של המועמד/ת לרפואה: {user_name}.
        המטרה: הכנה למבחני מס"ר (מרכז הערכה לרפואה בישראל).
        
        נתוני התוצאות:
        {results_summary}
        
        כתוב דו"ח ניתוח בעברית הכולל:
        1. פתיחה: התייחסות למועמד בשמו וסיכום כללי של הפרופיל שהתקבל.
        2. התאמה למבחני מס"ר: ניתוח של התכונות הקריטיות (כמו 'יושרה-ענווה' ו'נעימות') והאם הן בטווח המצופה מרופא.
        3. בקרת אמינות: התייחסות לעקביות התשובות (האם המועמד ענה בצורה אותנטית או ניסה "לרצות" את השאלון).
        4. דגשים לשיפור: נקודות שהמועמד צריך לשים אליהן לב לקראת יום המבחן האמיתי.
        
        הנחיות חשובות: 
        - אל תשתמש בכוכביות, סולמיות או עיצוב Markdown מורכב. 
        - כתוב בטון מקצועי, אנליטי ומכוון מטרה.
        - זכור: המטרה היא מעבר מוצלח של שלב השאלונים בדרך לבית הספר לרפואה.
        """
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "לא ניתן היה להפיק ניתוח. נסה שוב בעוד מספר דקות."
            
    except Exception as e:
        return f"שגיאה בחיבור ל-AI: {str(e)}"
