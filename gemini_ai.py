import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    # שליפת המפתח (חייב להיות המלא)
    api_key = st.secrets.get("GEMINI_KEY_1", "").strip()
    
    if not api_key:
        return "שגיאה: GEMINI_KEY_1 לא נמצא ב-Secrets."

    # שים לב לשינוי ב-URL: עברנו ל-v1 (גרסה יציבה)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt_text = f"נתח תוצאות HEXACO עבור {user_name}: {results_summary}. כתוב בעברית חוות דעת מקצועית על התאמה לרפואה."
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        res_data = response.json()
        
        if response.status_code == 200:
            return res_data['candidates'][0]['content']['parts'][0]['text']
        else:
            # אם v1 נכשל, ננסה את מודל ה-Pro הישן והיציב כגיבוי אחרון
            backup_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
            res_backup = requests.post(backup_url, json=payload, timeout=20)
            if res_backup.status_code == 200:
                return res_backup.json()['candidates'][0]['content']['parts'][0]['text']
            
            error_msg = res_data.get('error', {}).get('message', 'Unknown error')
            return f"שגיאה סופית מגוגל (Status {response.status_code}): {error_msg}"
            
    except Exception as e:
        return f"שגיאת תקשורת: {str(e)}"
