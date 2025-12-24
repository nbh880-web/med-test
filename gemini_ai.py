import streamlit as st
import google.generativeai as genai
import time

def get_ai_analysis(user_name, results_summary):
    # 1. איסוף מפתחות מה-Secrets
    key1 = st.secrets.get("GEMINI_KEY_1")
    key2 = st.secrets.get("GEMINI_KEY_2")
    api_keys = [k for k in [key1, key2] if k]

    if not api_keys:
        return "שגיאה: לא נמצאו מפתחות API ב-Secrets. וודא שהגדרת GEMINI_KEY_1."

    # 2. הגדרת סדר המודלים לניסיון (Pro קודם כי הוא איכותי יותר)
    # שימוש בשמות מפורשים כדי למנוע שגיאות 404
    models_to_try = [
        'models/gemini-1.5-pro', 
        'models/gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-1.5-flash'
    ]
    
    last_error = ""

    # 3. לולאת הגנות - עוברת על כל המפתחות
    for api_key in api_keys:
        try:
            # הגדרה עם transport='rest' לעקיפת בעיות פרוטוקול בענן
            genai.configure(api_key=api_key, transport='rest')
            
            # 4. לולאה פנימית - מנסה כל מודל אפשרי עבור המפתח הנוכחי
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    prompt = f"""
                    תפקיד: פסיכולוג תעסוקתי מומחה למיוני רפואה (מס"ר).
                    משימה: ניתוח תוצאות שאלון HEXACO עבור המועמד {user_name}.
                    
                    נתונים:
                    {results_summary}
                    
                    כתוב חוות דעת מקצועית בעברית (טקסט בלבד, ללא כוכביות/סמלים):
                    1. סיכום פרופיל המועמד והתאמתו לערכי הרפואה.
                    2. דגש על מדד היושרה (Honesty-Humility).
                    3. האם יש חשד לחוסר עקביות או ניסיון "לרצות" את המבחן?
                    4. טיפ פרקטי אחד ליום המבחן.
                    """
                    
                    # ניסיון הפקת תוכן
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        return response.text
                        
                except Exception as e:
                    last_error = f"נכשל במודל {model_name}: {str(e)}"
                    continue # עובר למודל הבא
                    
        except Exception as e:
            last_error = f"שגיאה במפתח API: {str(e)}"
            continue # עובר למפתח הבא

    # 5. אם הגענו לכאן - הכל נכשל
    return f"מערכת ה-AI לא זמינה כרגע. (שגיאה אחרונה: {last_error})"
