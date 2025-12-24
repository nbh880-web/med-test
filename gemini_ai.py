import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    # 1. שליפת מפתחות (הם צריכים להיות מלאים ב-Secrets)
    key1 = st.secrets.get("GEMINI_KEY_1")
    key2 = st.secrets.get("GEMINI_KEY_2")
    api_keys = [k.strip() for k in [key1, key2] if k]

    if not api_keys:
        return "שגיאה: מפתח API לא נמצא ב-Secrets."

    # 2. פרומפט נקי
    prompt_text = f"נתח תוצאות HEXACO עבור המועמד {user_name}: {results_summary}. כתוב בעברית חוות דעת מקצועית."
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    # 3. רשימת ה-URLs המדויקים ביותר (בלי ניחושים)
    # גוגל עברה לפורמט שבו השם חייב להיות מלא
    for api_key in api_keys:
        endpoints = [
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
            f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        ]
        
        for url in endpoints:
            try:
                response = requests.post(url, json=payload, timeout=20)
                if response.status_code == 200:
                    res_data = response.json()
                    return res_data['candidates'][0]['content']['parts'][0]['text']
            except:
                continue

    return "לא ניתן היה להתחבר ל-AI. וודא שהמפתח ב-Secrets הוא המפתח המלא שהעתקת מ-Google AI Studio."
