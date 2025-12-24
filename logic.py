import streamlit as st
import google.generativeai as genai

def get_ai_analysis(user_name, results_summary):
    api_key = st.secrets.get("GEMINI_KEY_1")
    if not api_key:
        return "שגיאה: מפתח API חסר."

    try:
        genai.configure(api_key=api_key, transport='rest')
        
        # מעבר למודל ה-Pro (עדיין בתוך ה-Free Tier)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        prompt = f"""
        אתה פסיכולוג תעסוקתי מומחה למיוני רפואה בישראל.
        נתח את תוצאות ה-HEXACO של המועמד {user_name}.
        התייחס להתאמתו לערכי מקצוע הרפואה ולמדד היושרה.
        נתונים: {results_summary}
        כתוב בעברית, טקסט נקי בלבד.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"שגיאה: {str(e)}"
