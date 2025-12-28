import streamlit as st
import requests
import json
import plotly.graph_objects as go
import time

# מילון תרגום והגדרות בסיס
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

# הגדרת טווחים קריטיים לכל תכונה
TRAIT_RANGES = {
    "Honesty-Humility": {"critical_low": 3.5, "optimal_low": 4.2, "optimal_high": 4.9, "critical_high": 5.0},
    "Emotionality": {"critical_low": 2.8, "optimal_low": 3.6, "optimal_high": 4.1, "critical_high": 4.5},
    "Extraversion": {"critical_low": 2.5, "optimal_low": 3.6, "optimal_high": 4.2, "critical_high": 4.8},
    "Agreeableness": {"critical_low": 3.2, "optimal_low": 4.0, "optimal_high": 4.6, "critical_high": 5.0},
    "Conscientiousness": {"critical_low": 3.8, "optimal_low": 4.3, "optimal_high": 4.8, "critical_high": 5.0},
    "Openness to Experience": {"critical_low": 2.8, "optimal_low": 3.5, "optimal_high": 4.1, "critical_high": 4.7}
}

class HEXACO_Analyzer:
    def __init__(self):
        # טעינת המפתחות מה-Secrets
        self.gemini_keys = [
            st.secrets.get("GEMINI_KEY_1", "").strip(),
            st.secrets.get("GEMINI_KEY_2", "").strip(),
            st.secrets.get("GEMINI_KEY_3", "").strip()  # תמיכה במפתח נוסף
        ]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        self.claude_key = st.secrets.get("CLAUDE_KEY", "").strip()

    def _discover_gemini_model(self, api_key):
        """גילוי אוטומטי של מודל Gemini הטוב ביותר"""
        default_model = "models/gemini-1.5-flash-latest"
        if not api_key: return default_model
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            res = requests.get(list_url, timeout=7)
            if res.status_code == 200:
                models_data = res.json().get("models", [])
                # חיפוש Pro תחילה, אחר כך Flash
                pro_models = [str(m["name"]) for m in models_data if isinstance(m.get("name"), str) and "pro" in m["name"].lower()]
                if pro_models: return pro_models[-1]
                flash_models = [str(m["name"]) for m in models_data if isinstance(m.get("name"), str) and "flash" in m["name"].lower()]
                if flash_models: return flash_models[-1]
        except Exception as e:
            st.warning(f"⚠️ גילוי מודל Gemini נכשל: {str(e)}")
        return default_model

    def _discover_claude_model(self):
        """גילוי אוטומטי של מודל Claude העדכני"""
        default_model = "claude-3-5-sonnet-20241022"
        if not self.claude_key: return default_model
        try:
            url = "https://api.anthropic.com/v1/models"
            headers = {"x-api-key": self.claude_key, "anthropic-version": "2023-06-01"}
            res = requests.get(url, headers=headers, timeout=7)
            if res.status_code == 200:
                sonnet_models = [m["id"] for m in res.json().get("data", []) if "sonnet" in m["id"].lower()]
                if sonnet_models: return sorted(sonnet_models)[-1]
        except Exception as e:
            st.warning(f"⚠️ גילוי מודל Claude נכשל: {str(e)}")
        return default_model

    def _build_enhanced_prompt(self, user_name, current_results, history, provider="gemini"):
        """בניית פרומפט מתקדם ומפורט לניתוח פסיכולוגי עמוק"""
        
        # ניתוח מגמות והיסטוריה
        history_analysis = ""
        if history and isinstance(history, list) and len(history) > 0:
            history_analysis = "\n### 📊 ניתוח מגמות היסטוריות:\n"
            for idx, h in enumerate(history[:3], 1):
                results_data = h.get('results', {})
                test_date = h.get('test_date', 'לא ידוע')
                history_analysis += f"\n**מבחן #{idx} ({test_date}):**\n"
                for trait, score in results_data.items():
                    history_analysis += f"  - {trait}: {score}\n"
            
            # חישוב שינויים
            if len(history) >= 2:
                history_analysis += "\n**שינויים מהמבחן הקודם:**\n"
                prev_results = history[0].get('results', {})
                for trait in current_results:
                    if trait in prev_results:
                        change = current_results[trait] - prev_results[trait]
                        direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                        history_analysis += f"  {direction} {trait}: {change:+.2f}\n"

        # ניתוח פערים קריטיים
        gap_analysis = "\n### ⚠️ ניתוח פערים ואזורי סיכון:\n"
        for trait, score in current_results.items():
            if trait in TRAIT_RANGES:
                ranges = TRAIT_RANGES[trait]
                ideal = IDEAL_DOCTOR[trait]
                gap = score - ideal
                
                if score < ranges["critical_low"]:
                    gap_analysis += f"🔴 **{trait}**: ציון קריטי נמוך ({score:.2f}) - פער של {abs(gap):.2f} מהאידיאל!\n"
                elif score < ranges["optimal_low"]:
                    gap_analysis += f"🟡 **{trait}**: מתחת לטווח ({score:.2f}) - צריך שיפור של {abs(gap):.2f}\n"
                elif score > ranges["critical_high"]:
                    gap_analysis += f"🔴 **{trait}**: ציון גבוה חשוד ({score:.2f}) - חשד לריצוי חברתי!\n"
                elif score > ranges["optimal_high"]:
                    gap_analysis += f"🟡 **{trait}**: מעל הטווח ({score:.2f}) - יתרון של {gap:.2f} אך צריך איזון\n"
                else:
                    gap_analysis += f"✅ **{trait}**: בטווח אידיאלי ({score:.2f})\n"

        # בניית הפרומפט המלא
        if provider == "gemini":
            prompt = f"""
# 🎯 ניתוח פסיכולוגי מקצועי - מועמד לרפואה

## פרטי המועמד
- **שם**: {user_name}
- **תאריך ניתוח**: {time.strftime('%d/%m/%Y %H:%M')}

## 📈 תוצאות מבחן נוכחי:
{json.dumps(current_results, indent=2, ensure_ascii=False)}

{history_analysis}

{gap_analysis}

## 🎓 הנחיות לניתוח מקצועי:

אתה פסיכולוג ארגוני בכיר במרכז הערכה לרפואה (מס"ר). תפקידך לכתוב דוח מעמיק ומפורט.

### מבנה הדוח הנדרש (לפחות 1200 מילים):

#### 1. **סיכום ראשוני** (2-3 פסקאות)
   - תמונה כוללת של פרופיל המועמד
   - נקודות חוזקה מרכזיות
   - אזורי דאגה עיקריים

#### 2. **ניתוח תכונה-תכונה** (פסקה לכל תכונה):
   לכל אחת מ-6 התכונות:
   - השוואה לפרופיל האידיאלי של רופא
   - משמעות הציון בהקשר רפואי
   - השלכות על עבודה קלינית
   - דוגמאות קונקרטיות לסיטואציות רפואיות
   - אם יש מגמה מההיסטוריה - הסבר את המשמעות

#### 3. **ניתוח אינטגרטיבי** (3-4 פסקאות):
   - איך התכונות משפיעות זו על זו
   - סינרגיות או סתירות פנימיות
   - פרופיל האישיות הכולל
   - התאמה לתפקידים רפואיים שונים (רופא משפחה, מנתח, פסיכיאטר וכו')

#### 4. **זיהוי דפוסי תגובה חשודים**:
   - חשד לריצוי חברתי (Social Desirability)
   - עקביות התשובות
   - ציונים קיצוניים חשודים
   - דפוסי תגובה לא טיפוסיים

#### 5. **מגמות לאורך זמן** (אם יש היסטוריה):
   - שינויים משמעותיים
   - יציבות או תנודתיות
   - פרשנות למגמות

#### 6. **המלצות מפורטות לשיפור** (5-7 המלצות):
   - אסטרטגיות קונקרטיות לכל נקודת חולשה
   - תרגילים ופעילויות ספציפיות
   - ספרים/משאבים מומלצים
   - דרכי הכנה לראיון הסימולציה

#### 7. **עצות לראיון עם שחקן** (3-4 פסקאות):
   - תרחישים צפויים
   - מלכודות להימנע מהן
   - איך להדגיש חוזקות
   - איך לנטרל חולשות

#### 8. **תחזית והמלצה סופית**:
   - סיכויי הצלחה בקבלה (באחוזים)
   - סיכויי הצלחה ברפואה (ארוך טווח)
   - תחומי רפואה מומלצים
   - המלצה אישית סופית

**סגנון כתיבה**: 
- עברית רהוטה וברורה
- משפטים מורכבים אך קריאים
- שימוש במונחים פסיכולוגיים מקצועיים (עם הסבר)
- טון אמפתי אך ישיר
- דוגמאות קונקרטיות מהעולם הרפואי

**אורך מינימלי**: 1200 מילים בעברית (לא כולל כותרות)

התחל בכתיבת הדוח המלא עכשיו:
"""
        else:  # Claude
            prompt = f"""
You are Dr. Rachel Goldstein, a senior clinical psychologist and personality assessment expert specializing in medical school admissions in Israel. You have 20 years of experience evaluating candidates for Israeli medical schools.

## Candidate Profile
- **Name**: {user_name}
- **Assessment Date**: {time.strftime('%d/%m/%Y %H:%M')}

## Current HEXACO Results:
{json.dumps(current_results, indent=2, ensure_ascii=False)}

{history_analysis}

{gap_analysis}

## Your Mission:
Write an exceptionally detailed, clinically rigorous psychological assessment report in Hebrew. This will be used by medical school admissions committees.

## Report Structure (Minimum 1500 words in Hebrew):

### 1. Executive Summary (3 paragraphs)
- Overall personality profile
- Key strengths for medical practice
- Critical areas of concern
- Prediction of interview performance

### 2. Six-Factor Deep Dive (250+ words per trait)
For each HEXACO dimension, provide:

**A. Quantitative Analysis:**
- Current score vs. ideal physician benchmark
- Percentile ranking compared to medical students
- Statistical significance of gaps
- Trend analysis from historical data (if available)

**B. Clinical Interpretation:**
- What this score reveals about cognitive-emotional patterns
- Behavioral manifestations in clinical settings
- Impact on doctor-patient relationships
- Influence on medical decision-making
- Effect on team collaboration

**C. Real-World Scenarios:**
Describe 2-3 specific medical situations where this trait level would:
- Be an asset or liability
- Create challenges
- Require compensation strategies

**D. Developmental Insights:**
- Is this trait stable or malleable?
- Evidence of growth from past assessments
- Realistic potential for improvement

### 3. Integrative Personality Synthesis (400+ words)
- **Configuration Analysis**: How traits interact dynamically
- **Compensatory Mechanisms**: How high scores balance low ones
- **Internal Conflicts**: Contradictions that create stress
- **Specialty Fit**: 
  - Primary Care: [detailed analysis]
  - Surgery: [detailed analysis]
  - Psychiatry: [detailed analysis]
  - Emergency Medicine: [detailed analysis]
  - Pediatrics: [detailed analysis]

### 4. Validity and Response Pattern Analysis (200+ words)
- **Social Desirability Detection**: Evidence of impression management
- **Response Consistency**: Internal contradictions
- **Extreme Responding**: Tendency toward poles
- **Acquiescence Bias**: Agreement tendency
- **Confidence Level**: How much to trust these results (%)

### 5. Longitudinal Trajectory Analysis (if history exists, 200+ words)
- Meaningful changes over time
- Stability vs. volatility
- Context of changes (stress, preparation, authentic growth?)
- Predictions for future development

### 6. Evidence-Based Development Plan (500+ words)

For each weakness identified, provide:
- **Specific Intervention**: Concrete exercises/practices
- **Timeline**: How long will improvement take
- **Measurability**: How to track progress
- **Resources**: Books, courses, apps, therapy approaches
- **Quick Wins**: What can be improved before interview
- **Long-term Strategy**: Sustainable personality development

### 7. Interview Simulation Preparation (300+ words)
- **High-Probability Scenarios**: 5 situations they'll face
- **Your Weak Points Will Be Tested On**: Specific provocations
- **Optimal Responses**: Word-for-word examples
- **Red Flags to Avoid**: Statements that reveal weaknesses
- **Authenticity vs. Strategy**: How to be genuine while strategic

### 8. Psychiatric/Psychological Risk Assessment
- Any indicators of burnout risk
- Potential for compassion fatigue
- Stress resilience capacity
- Need for ongoing psychological support

### 9. Final Recommendation with Percentages
- **Admission Probability**: X% (based on personality fit)
- **Success in Medical School**: X%
- **Success as Practicing Physician**: X%
- **Recommended Specialties** (ranked 1-5 with rationale)
- **Go/No-Go Decision**: Clear recommendation with caveats

### 10. Personal Letter to Candidate (100+ words)
A compassionate, honest paragraph speaking directly to {user_name} about their journey.

## Critical Requirements:
- Write ENTIRELY in Hebrew (עברית)
- Use professional psychological terminology with explanations
- Cite specific research when relevant (e.g., "מחקרים מראים כי...")
- Be brutally honest but constructive
- Every claim must be evidence-based from the scores
- Think like an admissions gatekeeper, not a cheerleader
- MINIMUM 1500 words

Begin the full report now in Hebrew:
"""

        return prompt

    def generate_multi_report(self, user_name, current_results, history):
        """יצירת דוח כפול עם Gemini ו-Claude"""
        gemini_prompt = self._build_enhanced_prompt(user_name, current_results, history, "gemini")
        claude_prompt = self._build_enhanced_prompt(user_name, current_results, history, "claude")
        
        gemini_report = self._call_gemini_with_failover(gemini_prompt)
        claude_report = self._call_claude_with_detailed_errors(claude_prompt)
        
        return gemini_report, claude_report

    def _call_gemini_with_failover(self, prompt):
        """קריאה ל-Gemini עם Failover מתקדם"""
        if not self.gemini_keys: 
            return "❌ שגיאה: לא הוגדרו מפתחות Gemini ב-Secrets. אנא הוסף GEMINI_KEY_1"
        
        for i, key in enumerate(self.gemini_keys, 1):
            try:
                model = self._discover_gemini_model(key)
                url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={key}"
                
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 8192  # מקסימום לפלאש
                    }
                }
                
                res = requests.post(url, json=payload, timeout=60)
                
                if res.status_code == 200:
                    data = res.json()
                    if 'candidates' in data and len(data['candidates']) > 0:
                        text = data['candidates'][0]['content']['parts'][0]['text']
                        return text
                    else:
                        st.warning(f"⚠️ Gemini key #{i}: תגובה ריקה")
                else:
                    error_detail = res.text[:200]
                    st.warning(f"⚠️ Gemini key #{i} החזיר קוד {res.status_code}: {error_detail}")
                    
            except requests.Timeout:
                st.warning(f"⏱️ Gemini key #{i}: תם הזמן (timeout)")
            except Exception as e:
                st.warning(f"⚠️ Gemini key #{i} נכשל: {str(e)[:100]}")
                continue
        
        return "❌ כל ניסיונות Gemini נכשלו. אנא בדוק:\n1. המפתחות תקינים ב-Secrets\n2. יש קרדיט במפתחות\n3. אין חסימת API"

    def _call_claude_with_detailed_errors(self, prompt):
        """קריאה ל-Claude עם טיפול שגיאות מתקדם"""
        if not self.claude_key: 
            return "❌ שגיאה: לא הוגדר מפתח Claude ב-Secrets. אנא הוסף CLAUDE_KEY"
        
        try:
            model_id = self._discover_claude_model()
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.claude_key, 
                "anthropic-version": "2023-06-01", 
                "content-type": "application/json"
            }
            payload = {
                "model": model_id, 
                "max_tokens": 8192,  # הגדלה ל-8K לדוח מפורט
                "temperature": 0.7,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            res = requests.post(url, headers=headers, json=payload, timeout=90)
            
            if res.status_code == 200:
                data = res.json()
                if 'content' in data and len(data['content']) > 0:
                    return data['content'][0]['text']
                else:
                    return "⚠️ Claude החזיר תגובה ריקה"
            
            # טיפול מפורט בשגיאות
            error_msg = self._parse_api_error('Claude', res)
            return f"❌ שגיאת Claude API:\n{error_msg}\n\nקוד שגיאה: {res.status_code}\nמודל: {model_id}"
            
        except requests.Timeout:
            return "⏱️ תקלה: Claude לא הגיב תוך 90 שניות. ייתכן שהדוח ארוך מדי."
        except requests.ConnectionError:
            return "🌐 תקלת רשת: לא ניתן להתחבר ל-API של Claude. בדוק את החיבור לאינטרנט."
        except Exception as e:
            return f"⚠️ שגיאה לא צפויה בחיבור ל-Claude:\n{str(e)}\n\nסוג שגיאה: {type(e).__name__}"

    def _parse_api_error(self, provider, response):
        """ניתוח מפורט של שגיאות API"""
        status = response.status_code
        try:
            detail = response.json()
            if provider == "Claude":
                msg = detail.get('error', {}).get('message', str(detail))
            else:
                msg = str(detail)
        except: 
            msg = response.text[:300]
        
        # שגיאות נפוצות
        error_map = {
            400: "בקשה שגויה - הפרומפט עלול להכיל תוכן לא תקין",
            401: "מפתח API לא תקין או פג תוקפו",
            403: "גישה נדחתה - ייתכן שהמפתח אינו מורשה לשירות זה",
            404: "המודל לא נמצא - יתכן שהוא הוסר או השם שגוי",
            429: "חרגת ממכסת השימוש. פתרונות:\n   - המתן מספר דקות\n   - שדרג את החבילה\n   - בדוק קרדיט",
            500: "שגיאת שרת פנימית - נסה שוב בעוד מספר דקות",
            503: "השירות אינו זמין כרגע - תחזוקה או עומס"
        }
        
        error_desc = error_map.get(status, f"שגיאה {status}")
        return f"{error_desc}\n\nפרטים טכניים: {msg}"

    def create_radar_chart(self, results):
        """יצירת תרשים רדאר משופר"""
        categories = [TRAIT_DICT[k] for k in results.keys()]
        user_vals = list(results.values())
        ideal_vals = [IDEAL_DOCTOR[k] for k in results.keys()]
        
        fig = go.Figure()
        
        # קו האידיאל
        fig.add_trace(go.Scatterpolar(
            r=ideal_vals + [ideal_vals[0]], 
            theta=categories + [categories[0]], 
            fill='toself', 
            name='🎯 פרופיל רופא אידיאלי',
            line=dict(color='#2ECC71', width=3),
            fillcolor='rgba(46, 204, 113, 0.2)',
            opacity=0.8
        ))
        
        # קו המועמד
        fig.add_trace(go.Scatterpolar(
            r=user_vals + [user_vals[0]], 
            theta=categories + [categories[0]], 
            fill='toself', 
            name='📊 הפרופיל שלך',
            line=dict(color='#3498DB', width=4),
            fillcolor='rgba(52, 152, 219, 0.3)',
            marker=dict(size=8, color='#3498DB')
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True, 
                    range=[1, 5],
                    tickmode='linear',
                    tick0=1,
                    dtick=0.5,
                    gridcolor='rgba(200, 200, 200, 0.3)'
                ),
                angularaxis=dict(
                    direction='clockwise',
                    rotation=90
                )
            ),
            showlegend=True,
            title={
                'text': "מפת אישיות HEXACO - השוואה ליעד",
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2C3E50')
            },
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            height=500
        )
        
        return fig

    def create_comparison_chart(self, results):
        """יצירת תרשים עמודות משופר עם צבעים דינמיים"""
        categories = [TRAIT_DICT[k] for k in results.keys()]
        user_scores = list(results.values())
        ideal_scores = [IDEAL_DOCTOR[k] for k in results.keys()]
        
        # צביעה דינמית לפי פערים
        colors = []
        for trait, score in results.items():
            if trait in TRAIT_RANGES:
                ranges = TRAIT_RANGES[trait]
                if ranges["optimal_low"] <= score <= ranges["optimal_high"]:
                    colors.append('#2ECC71')  # ירוק - מצוין
                elif score < ranges["critical_low"] or score > ranges["critical_high"]:
                    colors.append('#E74C3C')  # אדום - בעייתי
                else:
                    colors.append('#F39C12')  # כתום - דורש שיפור
            else:
                colors.append('#3498DB')  # כחול - ברירת מחדל
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='📊 הציון שלך',
            x=categories,
            y=user_scores,
            marker_color=colors,
            text=[f'{s:.2f}' for s in user_scores],
            textposition='outside',
            textfont=dict(size=12, color='#2C3E50'),
            hovertemplate='<b>%{x}</b><br>ציון: %{y:.2f}<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='🎯 יעד רופא',
            x=categories,
            y=ideal_scores,
            marker_color='rgba(46, 204, 113, 0.6)',
            text=[f'{s:.2f}' for s in ideal_scores],
            textposition='outside',
            textfont=dict(size=12, color='#27AE60'),
            hovertemplate='<b>%{x}</b><br>יעד: %{y:.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            barmode='group',
            yaxis=dict(
                range=[1, 5.5],
                title='ציון',
                gridcolor='rgba(200, 200, 200, 0.3)'
            ),
            xaxis=dict(
                title='',
                tickangle=-15
            ),
            title={
                'text': "השוואה כמותית - אתה מול היעד",
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2C3E50')
            },
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            height=500,
            hovermode='x unified'
        )
        
        return fig

# פונקציות עזר לשעון טוקנים
def create_token_gauge(text_content):
    """יוצר שעון ויזואלי משופר המראה ניצול טוקנים"""
    if not text_content or not isinstance(text_content, str):
        estimated_tokens = 0
    else:
        # הערכה משופרת: עברית + פיסוק
        words = len(text_content.split())
        estimated_tokens = int(words * 1.6)
    
    max_cap = 8192  # עודכן למקסימום החדש
    percentage = (estimated_tokens / max_cap) * 100
    
    # צבע דינמי לפי ניצול
    if percentage < 30:
        bar_color = "#95A5A6"  # אפור - ניצול נמוך
    elif percentage < 60:
        bar_color = "#3498DB"  # כחול - ניצול בינוני
    elif percentage < 85:
        bar_color = "#2ECC71"  # ירוק - ניצול טוב
    else:
        bar_color = "#E74C3C"  # אדום - כמעט מלא
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=estimated_tokens,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={
            'text': "ניצול טוקנים (עומק ואיכות הדוח)",
            'font': {'size': 16, 'color': '#2C3E50'}
        },
        delta={
            'reference': max_cap * 0.6,  # יעד 60%
            'increasing': {'color': "#2ECC71"},
            'decreasing': {'color': "#E74C3C"}
        },
        number={
            'suffix': f" / {max_cap}",
            'font': {'size': 24, 'color': '#2C3E50'}
        },
        gauge={
            'axis': {
                'range': [None, max_cap],
                'tickwidth': 2,
                'tickcolor': "#2C3E50"
            },
            'bar': {'color': bar_color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#BDC3C7",
            'steps': [
                {'range': [0, max_cap * 0.3], 'color': "#ECF0F1"},
                {'range': [max_cap * 0.3, max_cap * 0.6], 'color': "#D6EAF8"},
                {'range': [max_cap * 0.6, max_cap * 0.85], 'color': "#A9DFBF"},
                {'range': [max_cap * 0.85, max_cap], 'color': "#F5B7B1"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_cap * 0.9  # אזהרה ב-90%
            }
        }
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "#2C3E50", 'family': "Arial"}
    )
    
    return fig

def calculate_compatibility_score(results):
    """חישוב מדד התאמה מתקדם לרפואה"""
    if not results:
        return 0, "אין נתונים"
    
    total_score = 0
    max_score = 0
    details = []
    
    for trait, score in results.items():
        if trait in TRAIT_RANGES and trait in IDEAL_DOCTOR:
            ranges = TRAIT_RANGES[trait]
            ideal = IDEAL_DOCTOR[trait]
            
            # ניקוד לפי קרבה לאידיאל
            if ranges["optimal_low"] <= score <= ranges["optimal_high"]:
                points = 100  # ציון מושלם
                status = "✅ מצוין"
            elif ranges["critical_low"] <= score < ranges["optimal_low"]:
                # ניקוד ליניארי בטווח התחתון
                gap = ranges["optimal_low"] - score
                max_gap = ranges["optimal_low"] - ranges["critical_low"]
                points = 100 - (gap / max_gap * 30)  # עד 30 נקודות קנס
                status = "🟡 בסדר"
            elif ranges["optimal_high"] < score <= ranges["critical_high"]:
                # ניקוד ליניארי בטווח העליון
                gap = score - ranges["optimal_high"]
                max_gap = ranges["critical_high"] - ranges["optimal_high"]
                points = 100 - (gap / max_gap * 25)  # עד 25 נקודות קנס
                status = "🟡 גבוה מעט"
            else:
                points = 50  # ציון קריטי
                status = "🔴 בעייתי"
            
            total_score += points
            max_score += 100
            details.append(f"{TRAIT_DICT[trait]}: {status} ({points:.0f}/100)")
    
    if max_score == 0:
        return 0, "שגיאה בחישוב"
    
    final_percentage = int((total_score / max_score) * 100)
    details_str = "\n".join(details)
    
    return final_percentage, details_str

# פונקציות ממשק ציבוריות
def get_multi_ai_analysis(user_name, results, history):
    """ממשק ראשי ליצירת ניתוח AI כפול"""
    return HEXACO_Analyzer().generate_multi_report(user_name, results, history)

def get_radar_chart(results):
    """ממשק ליצירת תרשים רדאר"""
    return HEXACO_Analyzer().create_radar_chart(results)

def get_comparison_chart(results):
    """ממשק ליצירת תרשים עמודות"""
    return HEXACO_Analyzer().create_comparison_chart(results)

def get_compatibility_metrics(results):
    """ממשק לחישוב מדדי התאמה"""
    return calculate_compatibility_score(results)