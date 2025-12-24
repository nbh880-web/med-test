import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    # 1. שליפת מפתחות וניקוי
    keys = [st.secrets.get("GEMINI_KEY_1"), st.secrets.get("GEMINI_KEY_2")]
    api_keys = [k.strip() for k in keys if k]

    if not api_keys:
        return "שגיאה: מפתח API חסר ב-Secrets."

    # 2. הגדרת הפרומפט
    prompt_text = f"נתח תוצאות HEXACO עבור המועמד לרפואה {user_name}: {results_summary}. כתוב בעברית חוות דעת על התאמה ויושרה (טקסט בלבד)."
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    # 3. רשימת האפשרויות לסריקה (מודלים וגרסאות)
    versions = ["v1", "v1beta"]
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
    
    last_error = ""

    # לולאת "הגנה מוחלטת"
    for api_key in api_keys:
        for version in versions:
            for model_name in models:
                try:
                    # בניית ה-URL לפי הקומבינציה הנוכחית
                    url = f"https://generativelanguage.googleapis.com/{version}/models/{model_name}:generateContent?key={api_key}"
                    
                    response = requests.post(url, json=payload, timeout=20)
                    res_data = response.json()

                    if response.status_code == 200:
                        # הצלחה! מחזירים את התשובה מהמודל הראשון שענה
                        return res_data['candidates'][0]['content']['parts'][0]['text']
                    
                    # אם נכשל, שומרים את השגיאה וממשיכים לניסיון הבא
                    last_error = f"[{version}/{model_name}] {res_data.get('error', {}).get('message', 'Error')}"
                
                except Exception as e:
                    last_error = str(e)
                    continue

    return f"כל המודלים נכשלו. שגיאה אחרונה: {last_error}"
