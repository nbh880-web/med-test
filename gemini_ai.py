import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    # שליפת המפתח החדש שהחלפת
    api_key = st.secrets.get("GEMINI_KEY_1", "").strip()
    if not api_key:
        return "שגיאה: GEMINI_KEY_1 לא נמצא ב-Secrets."

    # שינוי ה-URL למבנה הפרוטוקול המלא
    # שים לב לשימוש ב-v1 (היציב) ובנתיב models/gemini-1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt_text = f"Analyze HEXACO results for {user_name}: {results_summary}. Write a professional feedback in Hebrew about medical suitability and integrity. Output only the Hebrew text."
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        
        if response.status_code == 200:
            res_data = response.json()
            return res_data['candidates'][0]['content']['parts'][0]['text']
        else:
            # אם v1 נכשל, ננסה v1beta עם אותו מבנה
            url_beta = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            response_beta = requests.post(url_beta, headers=headers, json=payload, timeout=20)
            
            if response_beta.status_code == 200:
                return response_beta.json()['candidates'][0]['content']['parts'][0]['text']
            
            # הצגת השגיאה המפורטת מגוגל כדי להבין מה חסר
            error_info = response_beta.json().get('error', {}).get('message', 'Unknown Error')
            return f"שגיאה (Status {response_beta.status_code}): {error_info}"
            
    except Exception as e:
        return f"שגיאת תקשורת: {str(e)}"
