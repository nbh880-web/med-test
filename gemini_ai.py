import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    # ניסיון לקחת את המפתחות מה-Secrets
    key1 = st.secrets.get("GEMINI_KEY_1")
    key2 = st.secrets.get("GEMINI_KEY_2")
    keys = [k for k in [key1, key2] if k]

    if not keys:
        return "שגיאה: לא הוגדרו מפתחות API ב-Secrets."

    for api_key in keys:
        try:
            genai.configure(api_key=api_key)
            
            # שימוש בשם המודל הבסיסי ביותר - עובד בכל הגרסאות
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            נתח את תוצאות שאלון HEXACO עבור מועמד לרפואה (מס"ר): {user_name}
            תוצאות: {results_summary}
            
            כתוב חוות דעת מקצועית בעברית הכוללת:
            1. ניתוח התאמה למקצוע הרפואה.
            2. דגש על יושרה-ענווה (Honesty-Humility).
            3. טיפ ליום המבחן במס"ר.
            (כתוב בטקסט פשוט, ללא כוכביות או סולמיות).
            """
            
            response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            # אם זה המפתח האחרון וזה נכשל, נציג את השגיאה
            if api_key == keys[-1]:
                return f"שגיאה בחיבור ל-AI: {str(e)}"
            continue # נסה את המפתח הבא

    return "לא ניתן היה להפיק ניתוח."
