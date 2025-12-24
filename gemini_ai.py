import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    # 1. שליפת מפתחות וניקוי
    key1 = st.secrets.get("GEMINI_KEY_1")
    key2 = st.secrets.get("GEMINI_KEY_2")
    api_keys = [k.strip() for k in [key1, key2] if k]

    if not api_keys:
        return "שגיאה: מפתח API חסר ב-Secrets."

    prompt_text = f"נתח תוצאות HEXACO עבור המועמד {user_name}: {results_summary}. כתוב בעברית חוות דעת על התאמה לרפואה ויושרה."

    for api_key in api_keys:
        # התיקון הקריטי: הוספת 'models/' בתוך ה-URL עצמו לפני שם המודל
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            res_data = response.json()

            if response.status_code == 200:
                return res_data['candidates'][0]['content']['parts'][0]['text']
            
            # אם v1 נכשל, ננסה "כוח גס" - פנייה לכתובת ללא מספר גרסה
            url_alt = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            response = requests.post(url_alt, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
                
            last_error = res_data.get('error', {}).get('message', 'Unknown Error')
        except Exception as e:
            last_error = str(e)
            continue

    return f"מערכת ה-AI לא זמינה. שגיאה: {last_error}"
