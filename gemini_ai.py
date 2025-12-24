 import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    # איסוף מפתחות
    key1 = st.secrets.get("GEMINI_KEY_1")
    key2 = st.secrets.get("GEMINI_KEY_2")
    api_keys = [k for k in [key1, key2] if k]

    if not api_keys:
        return "שגיאה: מפתח API לא נמצא ב-Secrets."

    # הגדרת הפרומפט
    prompt_text = f"""
    תפקיד: פסיכולוג תעסוקתי מומחה למיוני רפואה (מס"ר).
    משימה: ניתוח תוצאות שאלון HEXACO עבור המועמד {user_name}.
    נתונים: {results_summary}
    כתוב חוות דעת מקצועית בעברית (טקסט בלבד) על התאמה לרפואה, יושרה וטיפ למבחן.
    """

    # נסיון דרך כל המפתחות ודרך ה-API הישיר (v1 היציב)
    for api_key in api_keys:
        # אנחנו פונים ל-v1 (לא v1beta!) כדי למנוע את ה-404
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            res_data = response.json()

            if response.status_code == 200:
                # חילוץ הטקסט מהמבנה של גוגל
                return res_data['candidates'][0]['content']['parts'][0]['text']
            else:
                error_msg = res_data.get('error', {}).get('message', 'Unknown Error')
                continue # נסה מפתח הבא אם יש שגיאה (כמו Quota)
        except Exception as e:
            continue

    return "מערכת ה-AI לא זמינה כרגע. וודא שמפתח ה-API תקין ב-Google AI Studio."
