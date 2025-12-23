import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    """
    מפיק ניתוח ממוקד למבחני מס"ר על בסיס שאלון HEXACO.
    """
    if "GEMINI_KEY_1" not in st.secrets:
        return "שגיאה: מפתח API לא הוגדר ב-Secrets."
    
    try:
        # הגדרה הכרחית למניעת שגיאת 404 בשרתים של Streamlit
        genai.configure(api_key=st.secrets["GEMINI_KEY_1"], transport='rest')
        
        # אתחול המודל - גרסת פלאש 1.5 היא היציבה והמהירה ביותר
        model = genai.GenerativeModel('gemini-1.5-flash')
        
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
        return "לא התקבל טקסט מה-AI."
            
    except Exception as e:
        return f"שגיאה בחיבור ל-AI: {str(e)}"
