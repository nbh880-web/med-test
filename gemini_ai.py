import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    keys = [st.secrets.get("GEMINI_KEY_1"), st.secrets.get("GEMINI_KEY_2")]
    api_keys = [k.strip() for k in keys if k]

    if not api_keys:
        return "שגיאה: מפתח API חסר ב-Secrets."

    prompt_text = f"נתח תוצאות HEXACO עבור המועמד {user_name}: {results_summary}. כתוב בעברית חוות דעת על התאמה ויושרה (טקסט בלבד)."
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    # רשימת השמות המדויקים והעדכניים ביותר שגוגל דורשת עכשיו
    models_to_scan = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-1.0-pro"
    ]
    
    # ננסה גם v1 וגם v1beta
    versions = ["v1", "v1beta"]
    
    last_error = ""

    for api_key in api_keys:
        for model_id in models_to_scan:
            for ver in versions:
                try:
                    url = f"https://generativelanguage.googleapis.com/{ver}/models/{model_id}:generateContent?key={api_key}"
                    response = requests.post(url, json=payload, timeout=15)
                    
                    if response.status_code == 200:
                        res_data = response.json()
                        return res_data['candidates'][0]['content']['parts'][0]['text']
                    
                    # אם קיבלנו שגיאה ספציפית על המודל, נמשיך לבא
                    res_data = response.json()
                    last_error = f"Model: {model_id}, Ver: {ver}, Msg: {res_data.get('error', {}).get('message', 'Unknown')}"
                except:
                    continue

    return f"ניסינו את כל המודלים והם נכשלו. שגיאה אחרונה: {last_error}"
