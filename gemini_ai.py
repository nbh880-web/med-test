import streamlit as st
import requests
import json

def get_ai_analysis(user_name, results_summary):
    # 1. איסוף וניקוי מפתחות
    key1 = st.secrets.get("GEMINI_KEY_1")
    key2 = st.secrets.get("GEMINI_KEY_2")
    # ניקוי רווחים נסתרים שעלולים לגרום לשגיאת אימות
    api_keys = [k.strip() for k in [key1, key2] if k]

    if not api_keys:
        return "שגיאה: מפתח API לא נמצא ב-Secrets. וודא שהגדרת GEMINI_KEY_1."

    # 2. הכנת הפרומפט
    prompt_text = f"""
    תפקיד: פסיכולוג תעסוקתי מומחה למיוני רפואה (מס"ר).
    משימה: ניתוח תוצאות שאלון HEXACO עבור המועמד {user_name}.
    נתונים: {results_summary}
    כתוב חוות דעת מקצועית בעברית (טקסט בלבד) על התאמה לרפואה, יושרה וטיפ למבחן.
    """

    last_error = "לא ידוע"

    # 3. לולאת ניסיונות
    for api_key in api_keys:
        # פנייה ל-v1 היציב כדי למנוע שגיאות 404 של גרסאות בטא
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        # שימוש ב-UTF-8 כדי שהעברית לא תישבר
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload).encode('utf-8'), 
                timeout=30
            )
            res_data = response.json()

            if response.status_code == 200:
                return res_data['candidates'][0]['content']['parts'][0]['text']
            else:
                # שמירת השגיאה המדויקת מגוגל לצורך ניפוי באגים
                last_error = res_data.get('error', {}).get('message', 'Unknown Google Error')
                continue 
        except Exception as e:
            last_error = str(e)
            continue

    return f"מערכת ה-AI לא זמינה. שגיאה אחרונה: {last_error}"
