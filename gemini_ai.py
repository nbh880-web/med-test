import streamlit as st
import requests
import json
import plotly.graph_objects as go
import time
from datetime import datetime

# --- הגדרות ליבה ומילוני תרגום ---
TRAIT_DICT = {
    "Honesty-Humility": "כנות וענווה (H)",
    "Emotionality": "רגשיות (E)",
    "Extraversion": "מוחצנות (X)",
    "Agreeableness": "נעימות (A)",
    "Conscientiousness": "מצפוניות (C)",
    "Openness to Experience": "פתיחות (O)"
}

IDEAL_DOCTOR = {
    "Honesty-Humility": 4.55, 
    "Emotionality": 3.85, 
    "Extraversion": 3.9,
    "Agreeableness": 4.3, 
    "Conscientiousness": 4.55, 
    "Openness to Experience": 3.8
}

TRAIT_RANGES = {
    "Honesty-Humility": {"critical_low": 3.5, "optimal_low": 4.2, "optimal_high": 4.9, "critical_high": 5.0},
    "Emotionality": {"critical_low": 2.8, "optimal_low": 3.6, "optimal_high": 4.1, "critical_high": 4.5},
    "Extraversion": {"critical_low": 2.5, "optimal_low": 3.6, "optimal_high": 4.2, "critical_high": 4.8},
    "Agreeableness": {"critical_low": 3.2, "optimal_low": 4.0, "optimal_high": 4.6, "critical_high": 5.0},
    "Conscientiousness": {"critical_low": 3.8, "optimal_low": 4.3, "optimal_high": 4.8, "critical_high": 5.0},
    "Openness to Experience": {"critical_low": 2.8, "optimal_low": 3.5, "optimal_high": 4.1, "critical_high": 4.7}
}

class HEXACO_System:
    def __init__(self):
        # טעינת המפתחות מה-Secrets של Streamlit
        self.gemini_keys = [
            st.secrets.get("GEMINI_KEY_1", "").strip(),
            st.secrets.get("GEMINI_KEY_2", "").strip(),
            st.secrets.get("GEMINI_KEY_3", "").strip()
        ]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        self.claude_key = st.secrets.get("CLAUDE_KEY", "").strip()

    # --- פונקציות API (Gemini & Claude) ---
    def _call_gemini_with_failover(self, prompt):
        if not self.gemini_keys:
            return "❌ שגיאה: לא הוגדרו מפתחות API ב-Secrets."

        for i, key in enumerate(self.gemini_keys, 1):
            try:
                # שימוש ב-1.5 Pro לטובת ניתוח טקסט ארוך ומעמיק
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={key}"
                
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.85,
                        "maxOutputTokens": 8192,
                        "topP": 0.95
                    },
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ]
                }

                res = requests.post(url, json=payload, timeout=120)
                if res.status_code == 200:
                    data = res.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
                elif res.status_code == 429:
                    st.warning(f"⚠️ מפתח #{i} חרג מהמכסה, מנסה את הבא...")
                    continue
            except Exception as e:
                st.error(f"❌ תקלה במפתח #{i}: {str(e)}")
                continue
        return "❌ כל ניסיונות הפנייה ל-AI נכשלו."

    # --- פונקציות ויזואליזציה (Plotly) ---
    def create_radar_chart(self, results):
        categories = [TRAIT_DICT[k] for k in results.keys()]
        user_vals = list(results.values())
        ideal_vals = [IDEAL_DOCTOR[k] for k in results.keys()]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=ideal_vals + [ideal_vals[0]], 
            theta=categories + [categories[0]], 
            fill='toself', name='🎯 יעד רופא אידיאלי (מס"ר)', 
            line=dict(color='rgba(46, 204, 113, 0.8)', width=2)
        ))
        fig.add_trace(go.Scatterpolar(
            r=user_vals + [user_vals[0]], 
            theta=categories + [categories[0]], 
            fill='toself', name='📊 הפרופיל שלך', 
            line=dict(color='#3498DB', width=4)
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
            showlegend=True,
            title="מפת אישיות HEXACO - השוואה לנורמות מס\"ר"
        )
        return fig

    def create_token_gauge(self, text_content):
        words = len(text_content.split()) if text_content else 0
        tokens = int(words * 1.5)
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=tokens,
            title={'text': "עומק ואיכות הניתוח (Tokens)"},
            gauge={'axis': {'range': [0, 8000]},
                   'bar': {'color': "#2ECC71"},
                   'steps': [{'range': [0, 3000], 'color': "#E74C3C"},
                             {'range': [3000, 6000], 'color': "#F1C40F"}]}
        ))
        fig.update_layout(height=250)
        return fig

    # --- לוגיקה חישובית ---
    def calculate_compatibility(self, results):
        total_points = 0
        details = []
        for trait, score in results.items():
            ranges = TRAIT_RANGES[trait]
            if ranges["optimal_low"] <= score <= ranges["optimal_high"]:
                points = 100
            elif score < ranges["critical_low"] or score > ranges["critical_high"]:
                points = 40
            else:
                points = 75
            total_points += points
            details.append(f"{TRAIT_DICT[trait]}: {points}/100")
        
        final_score = int(total_points / 6)
        return final_score, "\n".join(details)

    # --- יצירת דוח AI מעודכן ---
    def generate_report(self, user_name, current_results, history=[]):
        # בניית ניתוח הפערים עבור הפרומפט
        gap_analysis = ""
        for trait, score in current_results.items():
            ideal = IDEAL_DOCTOR[trait]
            diff = score - ideal
            gap_analysis += f"- {TRAIT_DICT[trait]}: ציון {score:.2f} (יעד מס\"ר: {ideal}, פער: {diff:+.2f})\n"

        prompt = f"""
        זהות: אתה מעריך פסיכולוגי בכיר ומומחה במרכז מס"ר (המרכז הארצי לסימולציות רפואיות). תפקידך הוא למיין מועמדים לרפואה.
        מועמד: {user_name}
        
        נתונים כמותיים משאלון HEXACO:
        {gap_analysis}
        
        משימה: כתוב דוח פסיכולוגי מקצועי, נוקב ומעמיק (לפחות 1500 מילים) בעברית.
        
        מבנה הדוח הנדרש:
        1. סיכום התאמה למקצוע הרפואה: האם הפרופיל מתאים לסטנדרטים הנוקשים של מרכז מס"ר?
        2. ניתוח תכונות מעמיק: איך הציונים משפיעים על האמפתיה, קבלת ההחלטות והיציבות הרגשית של המועמד.
        3. איתור ניסיונות הטיה (Impression Management): האם יש חשד שהמועמד ניסה להציג תמונה "מושלמת" מדי (למשל כנות נמוכה מול מצפוניות קיצונית)?
        4. חיזוי ביצועים בסימולציות: תאר 5 תחנות מס"ר ספציפיות (מסירת בשורה מרה, דילמה אתית, חולה תוקפני, עבודה עם איש צוות קשה) ונתח איך המועמד יתפקד בהן.
        5. חוות דעת סופית והמלצות לשיפור: מה המועמד חייב לשנות בהתנהלותו כדי לעבור את יום המיון בהצלחה.
        
        טון: מקצועי, קליני, לא מתנחמד. אתה כותב עבור ועדת הקבלה.
        """
        return self._call_gemini_with_failover(prompt)

# --- ממשק Streamlit ---
def main():
    st.set_page_config(page_title="HEXACO Medical Expert - מס\"ר Edition", layout="wide")
    system = HEXACO_System()

    st.title("🩺 מערכת הערכה פסיכולוגית - תקן מס\"ר")
    st.markdown("---")

    # בדיקת נתונים ב-Session
    if 'results' not in st.session_state:
        # נתוני דוגמה התחלתיים
        st.session_state.results = {
            "Honesty-Humility": 4.1, "Emotionality": 3.2, "Extraversion": 3.7,
            "Agreeableness": 4.0, "Conscientiousness": 4.6, "Openness to Experience": 3.9
        }

    col1, col2 = st.columns([1, 1])

    with col1:
        st.plotly_chart(system.create_radar_chart(st.session_state.results), use_container_width=True)

    with col2:
        score, details = system.calculate_compatibility(st.session_state.results)
        st.subheader("מדד התאמה לרפואה")
        st.metric("ציון סופי", f"{score}%")
        with st.expander("ראה פירוט ניקוד לפי תכונות"):
            st.text(details)

    st.markdown("---")
    
    if st.button("🚀 הפעל מעריך פסיכולוגי של מס\"ר (ייצור דוח מלא)"):
        with st.spinner("מעריך מס\"ר מנתח את הנתונים... נא להמתין"):
            report = system.generate_report("מועמד בדיקה", st.session_state.results)
            
            st.markdown("### 📄 דוח הערכה פסיכולוגי רשמי - תקן מס\"ר")
            st.info("הדוח להלן נוצר על ידי בינה מלאכותית המדמה פסיכולוג מעריך. יש להתייחס לממצאים בזהירות.")
            st.markdown(report)
            
            st.markdown("---")
            st.plotly_chart(system.create_token_gauge(report))

if __name__ == "__main__":
    main()