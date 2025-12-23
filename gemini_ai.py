import streamlit as st
import google.generativeai as genai
from google.generativeai.types import RequestOptions

def get_ai_analysis(user_name, results_summary):
    # רשימת המפתחות שיש לך ב-Secrets
    keys = [st.secrets.get("GEMINI_KEY_1"), st.secrets.get("GEMINI_KEY_2")]
    keys = [k for k in keys if k] # סינון מפתחות ריקים

    if not keys:
        return "שגיאה: לא הוגדרו מפתחות API ב-Secrets."

    last_error = ""
    
    for api_key in keys:
        try:
            # הגדרה עם המפתח הנוכחי
            genai.configure(api_key=api_key, transport='rest')
            
            # שימוש במודל בגרסה יציבה
            model = genai.GenerativeModel(model_name='gemini-1.5-flash')
            
            prompt = f"""
            ניתוח HEXACO למועמד לרפואה (מס"ר): {user_name}
            נתונים: {results_summary}
            
            כתוב ניתוח בעברית הכולל: סיכום פרופיל, דגש על יושרה-ענווה, וטיפ למבחני מס"ר.
            כתוב בטקסט פשוט ללא עיצוב מורכב.
            """
            
            # הכרחת שימוש בגרסה v1 כדי למנוע 404
            response = model.generate_content(
                prompt,
                request_options=RequestOptions(api_version='v1')
            )
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            last_error = str(e)
            continue # ניסיון עם המפתח הבא ברשימה

    return f"שגיאה בחיבור ל-AI (נוסו כל המפתחות): {last_error}"
