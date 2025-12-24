import streamlit as st
import requests

def get_ai_analysis(user_name, results_summary):
    api_key = st.secrets.get("GEMINI_KEY_1", "").strip()
    if not api_key:
        return "שגיאה: GEMINI_KEY_1 חסר."

    # שימוש בנתיב הכי בסיסי שיש לגוגל
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    prompt_text = f"נתח תוצאות HEXACO עבור {user_name}: {results_summary}. כתוב בעברית חוות דעת מקצועית."
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"שגיאה חוזרת (Status {response.status_code}). מומלץ ליצור מפתח חדש ב-AI Studio."
    except Exception as e:
        return f"שגיאה: {str(e)}"
