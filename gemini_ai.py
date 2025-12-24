import streamlit as st
import requests

def get_ai_analysis(user_name, results_summary):
    # שליפת המפתח הראשון בלבד לבדיקה
    api_key = st.secrets.get("GEMINI_KEY_1", "").strip()
    
    if not api_key:
        return "שגיאה: GEMINI_KEY_1 לא נמצא ב-Secrets."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "Say 'System Active' in Hebrew"}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_data = response.json()
        
        if response.status_code == 200:
            return res_data['candidates'][0]['content']['parts'][0]['text']
        else:
            # זה הקטע הכי חשוב: מה גוגל אומרת?
            error_msg = res_data.get('error', {}).get('message', 'שגיאה לא ידועה')
            return f"גוגל דחתה את הבקשה. קוד: {response.status_code}. הודעה: {error_msg}"
    except Exception as e:
        return f"שגיאת תקשורת: {str(e)}"
