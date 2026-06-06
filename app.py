"""
Mednitai HEXACO System — Main Application (v2.0)
==================================================
שיפורים מרכזיים:
- שאלון "נכון/לא נכון" מהיר (HEXACO + תרחישים)
- מצב אימון ממוקד לתכונה ספציפית
- רענון חכם (רק כשצריך) — ביצועים טובים יותר
- טיפים מיידיים אחרי כל תשובה במצב תרגול
- סיכום מסכם בסוף כל מבחן
- תיקון נתיבי CSV
- ממשק נקי וידידותי יותר
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import html
import uuid
import time
import random
import math
import threading
import os
from streamlit.runtime.scriptrunner import add_script_run_ctx

from logic import (
    process_results, calculate_medical_fit, calculate_reliability_index,
    get_inconsistent_questions, analyze_consistency, create_pdf_report,
    create_excel_download, get_balanced_questions, calculate_fatigue_index,
    calculate_dynamic_wpm_threshold
)
from integrity_logic import (
    get_integrity_questions, process_integrity_results,
    detect_contradictions, calculate_reliability_score,
    get_integrity_interpretation, get_category_risk_level
)
from gemini_ai import (
    get_multi_ai_analysis, get_integrity_ai_analysis,
    get_combined_ai_analysis, get_radar_chart,
    get_comparison_chart, create_token_gauge
)
from database import (
    save_to_db, save_integrity_test_to_db, save_combined_test_to_db,
    save_haifa_test_to_db, get_haifa_history,
    get_db_history, get_integrity_history, get_combined_history,
    get_all_tests, get_db_status
)

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="Mednitai — מבדק HEXACO",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CSS (כמו שהיה — לא נגענו)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap');

/* ===== Color Palette =====
   Primary: Teal #0d9488
   Accent: Mango #f97316
   Background: Cream #fef9f3
   Card: White #ffffff
   Text: Slate-Dark #1e293b
*/

html, body, [class*="css"] {
    font-family: 'Assistant', 'Rubik', sans-serif;
    direction: rtl;
}

.stApp {
    background: linear-gradient(180deg, #fef9f3 0%, #fff7ed 100%);
}

.main .block-container {
    max-width: 900px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
#MainMenu, footer, header { visibility: hidden; }

h1 {
    font-family: 'Rubik', sans-serif;
    font-weight: 700;
    background: linear-gradient(135deg, #0f766e 0%, #0d9488 50%, #f97316 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    font-size: 2.4rem !important;
}
h2, h3 {
    font-family: 'Rubik', sans-serif;
    color: #0f766e;
}

/* === Primary Buttons === */
button[kind="primary"] {
    background: linear-gradient(135deg, #0d9488 0%, #14b8a6 50%, #f97316 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.7rem 2.2rem !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    font-family: 'Assistant', sans-serif !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(13, 148, 136, 0.25) !important;
}
button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 25px rgba(249, 115, 22, 0.35) !important;
}

/* === Secondary Buttons === */
button[kind="secondary"] {
    background: #ffffff !important;
    color: #0f766e !important;
    border: 2px solid #5eead4 !important;
    border-radius: 14px !important;
    padding: 0.7rem 1rem !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    font-family: 'Assistant', sans-serif !important;
    transition: all 0.2s ease !important;
}
button[kind="secondary"]:hover, button[kind="secondary"]:active, button[kind="secondary"]:focus {
    background: linear-gradient(135deg, #0d9488 0%, #f97316 100%) !important;
    color: white !important;
    border: 2px solid transparent !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(249, 115, 22, 0.25);
}

.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #0d9488, #14b8a6, #f97316);
    border-radius: 10px;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Assistant', sans-serif;
    font-weight: 600;
    border-radius: 10px 10px 0 0;
    padding: 10px 24px;
    color: #0f766e;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #ccfbf1 0%, #fed7aa 100%) !important;
    color: #0f766e !important;
}
[data-testid="stMetricValue"] {
    font-size: 2rem; font-weight: 700; color: #0d9488;
}

/* ===== STRESS SCREEN — נשאר מפחיד אבל בעזיבה ===== */
.stress-screen {
    background: linear-gradient(180deg, #1c1917 0%, #44403c 50%, #1c1917 100%);
    color: #fb923c;
    text-align: center;
    padding: 60px 20px;
    border-radius: 20px;
    min-height: 450px;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    border: 2px solid rgba(249, 115, 22, 0.4);
    box-shadow: 0 0 60px rgba(249, 115, 22, 0.2);
}
.stress-icon {
    font-size: 4rem;
    margin-bottom: 15px;
    animation: pulse 1.5s infinite;
}
.stress-title {
    font-size: 1.8rem;
    font-weight: 800;
    font-family: 'Rubik', sans-serif;
    color: #fb923c;
    text-shadow: 0 0 20px rgba(249, 115, 22, 0.5);
    margin-bottom: 15px;
    letter-spacing: 1px;
}
.stress-detail {
    font-size: 1.1rem;
    color: #fed7aa;
    margin: 8px 0;
    max-width: 500px;
    line-height: 1.6;
}
.stress-timer {
    font-size: 5rem;
    font-weight: 800;
    font-family: 'Rubik', sans-serif;
    color: #fb923c;
    text-shadow: 0 0 40px rgba(249, 115, 22, 0.7);
    margin: 20px 0;
    animation: timerPulse 1s infinite;
}
.stress-warning-bar {
    background: rgba(249, 115, 22, 0.15);
    border: 1px solid rgba(249, 115, 22, 0.3);
    border-radius: 10px;
    padding: 12px 24px;
    margin-top: 20px;
    font-size: 0.9rem;
    color: #fed7aa;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.15); opacity: 0.8; }
}
@keyframes timerPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

/* ===== Question Card ===== */
.question-card {
    background: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 16px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 4px 20px rgba(13, 148, 136, 0.08);
    animation: fadeIn 0.4s ease;
    text-align: right;
    direction: rtl;
}
.question-text {
    font-size: 1.25rem;
    font-weight: 600;
    color: #1e293b;
    line-height: 1.8;
    text-align: right;
}
.question-category {
    font-size: 0.85rem;
    color: #0d9488;
    margin-bottom: 8px;
    text-align: right;
    font-weight: 600;
}

.hero-section {
    text-align: center;
    padding: 20px 20px 10px;
    background: transparent;
    margin-bottom: 20px;
    animation: fadeIn 0.5s ease;
}
.hero-section h1 {
    font-size: 2rem !important;
    margin-bottom: 8px;
}
.hero-subtitle { font-size: 1rem; color: #6b7280; margin-top: 6px; font-weight: 500; }

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.learning-tip {
    background: linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%);
    border-right: 4px solid #14b8a6;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 10px 0;
    color: #134e4a;
}
.learning-warning {
    background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%);
    border-right: 4px solid #f97316;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 10px 0;
    color: #9a3412;
}

.instant-tip {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border-right: 4px solid #f59e0b;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 12px 0;
    font-size: 0.95rem;
    line-height: 1.6;
    color: #78350f;
}

.summary-card {
    background: linear-gradient(135deg, #ffffff 0%, #fef9f3 100%);
    border-radius: 16px;
    padding: 24px;
    margin: 20px 0;
    border-right: 5px solid #0d9488;
    box-shadow: 0 4px 14px rgba(13, 148, 136, 0.08);
}
.summary-card h4 { color: #0f766e; margin-bottom: 10px; }

.admin-stat-card {
    background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    color: white;
    box-shadow: 0 4px 14px rgba(13, 148, 136, 0.25);
}
.admin-stat-value {
    font-size: 2.2rem;
    font-weight: 800;
    font-family: 'Rubik', sans-serif;
    color: #fb923c;
}
.admin-stat-label {
    font-size: 0.9rem;
    color: #ccfbf1;
    margin-top: 5px;
}

/* ===== Hourglass Timer ===== */
.hourglass-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
    padding: 16px;
    border-radius: 14px;
    margin: 12px 0;
    transition: background 0.5s ease;
}
.hourglass-container svg { flex-shrink: 0; }
.hourglass-info {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
}
.hourglass-num {
    font-size: 2rem;
    font-weight: 800;
    font-family: 'Rubik', sans-serif;
}
.hourglass-num-unit {
    font-size: 1rem;
    font-weight: 500;
}
.hourglass-status {
    font-size: 0.95rem;
    font-weight: 600;
}
@keyframes hourglass-shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-3px); }
    75% { transform: translateX(3px); }
}
.shake-animation {
    animation: hourglass-shake 0.4s ease-in-out infinite;
}
.timer-warning-box {
    background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
    border: 2px solid #dc2626;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 10px 0;
    text-align: center;
    font-weight: 700;
    color: #991b1b;
    animation: pulse-warning 1s ease-in-out infinite;
}
@keyframes pulse-warning {
    0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
    50% { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0); }
}

/* ===== Inputs & Forms ===== */
.stTextInput input, .stTextArea textarea {
    border-radius: 12px !important;
    border: 2px solid #e7e5e4 !important;
    background: #ffffff !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #0d9488 !important;
    box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.15) !important;
}
.stRadio > div { gap: 10px; }
.stSelectbox > div > div {
    border-radius: 12px !important;
}

/* ===== Alerts === */
[data-testid="stAlert"] {
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)



# ============================================================
# Constants
# ============================================================
STRESS_MESSAGES = [
    {'icon': '⚠️', 'title': 'זוהה חוסר עקביות בתשובות',
     'detail': 'המערכת זיהתה פערים משמעותיים בין תשובותיך. מתבצע ניתוח מעמיק של דפוסי התגובה...',
     'bar': 'מודול אימות אמינות פעיל — אנא המתן'},
    {'icon': '🔍', 'title': 'נדרשת בדיקת אימות נוספת',
     'detail': 'דפוס התשובות שלך חורג מהנורמה הסטטיסטית. המערכת בודקת את מדד העקביות הפנימי...',
     'bar': 'סריקת Integrity פעילה — אנא המתן'},
    {'icon': '🛡️', 'title': 'התקבלה התראת מערכת',
     'detail': 'אלגוריתם הבקרה זיהה חריגה בזמני התגובה שלך. מתבצע ניתוח סטטיסטי מורחב...',
     'bar': 'מנגנון Anti-Fake פעיל — אנא המתן'},
    {'icon': '📊', 'title': 'ניתוח דפוסים חריג',
     'detail': 'המערכת זיהתה שינוי מגמה חד בתשובותיך. מתבצעת השוואה מול מאגר נורמטיבי...',
     'bar': 'מודול Cross-Validation פעיל — בודק עקביות'},
    {'icon': '🔐', 'title': 'נדרש אימות פרופיל',
     'detail': 'ציון האמינות הנוכחי שלך ירד מתחת לסף הקריטי. המערכת מבצעת בדיקה מחודשת...',
     'bar': 'פרוטוקול אימות — סורק תשובות אחרונות'},
]

TRAIT_EXPLANATIONS = {
    'Conscientiousness': {
        'name': 'מצפוניות',
        'desc': 'מודדת ארגון, משמעת, תכנון ונחישות.',
        'medical': 'חיונית ברפואה — רופאים צריכים להיות מדויקים, שיטתיים ואמינים.',
        'tip_low': 'הדגש בראיון דוגמאות של תכנון, עמידה בזמנים ומחויבות לפרטים.',
        'tip_high': 'ציון מצוין! הראה שאתה גם גמיש ולא רק נוקשה.'
    },
    'Honesty-Humility': {
        'name': 'כנות-ענווה',
        'desc': 'מודדת כנות, הגינות, צניעות ואי-תחמון.',
        'medical': 'ערך מרכזי — יושרה מקצועית, שקיפות עם מטופלים ועמיתים.',
        'tip_low': 'הכן דוגמאות של מצבים שבחרת לפעול בהגינות גם כשזה היה קשה.',
        'tip_high': 'מצוין! הביא דוגמאות שבהן עמדת על עקרונות.'
    },
    'Agreeableness': {
        'name': 'נעימות',
        'desc': 'מודדת סלחנות, גמישות, סבלנות ונכונות לשתף פעולה.',
        'medical': 'עבודת צוות היא בסיס ברפואה — שיתוף פעולה עם כל הגורמים.',
        'tip_low': 'הדגש בראיון יכולת עבודה בצוות וסיפורים על פשרות.',
        'tip_high': 'וודא שאתה גם מסוגל לעמוד על דעתך כשצריך.'
    },
    'Emotionality': {
        'name': 'רגשנות',
        'desc': 'מודדת חרדתיות, רגישות ומודעות רגשית.',
        'medical': 'רפואה דורשת איזון — אמפתיה אבל גם תפקוד תחת לחץ.',
        'tip_low': 'הראה שיש לך אמפתיה ויכולת להתחבר רגשית למטופלים.',
        'tip_high': 'הדגש יכולת לנהל רגשות קשים ולהישאר מקצועי.'
    },
    'Extraversion': {
        'name': 'מוחצנות',
        'desc': 'מודדת חברותיות, ביטחון עצמי, חיות ואומץ.',
        'medical': 'חשובה לתקשורת עם מטופלים, צוות, והנהגה קלינית.',
        'tip_low': 'הקשבה זה גם חוזק — הראה יכולות תקשורת בדרך שלך.',
        'tip_high': 'שלב הובלה והשפעה חברתית עם הקשבה ורגישות.'
    },
    'Openness to Experience': {
        'name': 'פתיחות לחוויות',
        'desc': 'מודדת יצירתיות, סקרנות אינטלקטואלית ודמיון.',
        'medical': 'מאפשרת חשיבה יצירתית באבחון ועדכון מתמיד בידע.',
        'tip_low': 'הראה סקרנות ועניין בלמידה — ערך חשוב ברפואה.',
        'tip_high': 'הביא דוגמאות של סקרנות, קריאת מאמרים, חקירת נושאים חדשים.'
    }
}

IDEAL_RANGES = {
    'Conscientiousness': (4.3, 4.8),
    'Honesty-Humility': (4.2, 4.9),
    'Agreeableness': (4.0, 4.6),
    'Emotionality': (3.6, 4.1),
    'Extraversion': (3.6, 4.2),
    'Openness to Experience': (3.5, 4.1)
}

TRAIT_DICT = {
    "Honesty-Humility": "כנות וענווה (H)",
    "Emotionality": "רגשיות (E)",
    "Extraversion": "מוחצנות (X)",
    "Agreeableness": "נעימות (A)",
    "Conscientiousness": "מצפוניות (C)",
    "Openness to Experience": "פתיחות (O)"
}


# ============================================================
# B: Trait Direction Metadata (לפי מתודולוגיית מכון נועם)
# ============================================================
# לכל תכונה: האם היא חיובית/שלילית/מאוזנת לרפואה
# וגם אילו תכונות-משנה נחשבות חיוביות/שליליות
TRAIT_DIRECTIONS = {
    'Conscientiousness': {
        'direction': 'positive',  # תכונה חיובית מובהקת לרפואה
        'label': '✅ חיובית מובהקת',
        'subtraits_positive': ['סדר', 'ארגון', 'דייקנות', 'תכנון', 'משמעת', 'אמינות',
                               'התמדה', 'יסודיות', 'אחריות'],
        'subtraits_negative': ['פזיזות', 'שכחנות', 'דחיינות', 'בלגן', 'רשלנות'],
        'why_medical': 'רופא חייב להיות מדויק, שיטתי ואמין — טעות אחת = חיים. זו התכונה הקריטית ביותר.',
        'how_to_answer': 'תכונה זו תמיד חיובית — סמן "נכון" להיגדים שמתחייבים אותה, "לא נכון" להיגדים ששוללים אותה.'
    },
    'Honesty-Humility': {
        'direction': 'positive',
        'label': '✅ חיובית מובהקת',
        'subtraits_positive': ['כנות', 'יושרה', 'הגינות', 'צניעות', 'ענווה'],
        'subtraits_negative': ['חמדנות', 'תחמון', 'יוהרה', 'שקרנות', 'חוסר יושר'],
        'why_medical': 'יושרה מקצועית, שקיפות עם מטופלים, הימנעות מניצול מעמד — אבני יסוד באתיקה רפואית.',
        'how_to_answer': 'תכונה זו תמיד חיובית — אבל היזהר! אל תהיה "מושלם מדי" — סמן "לא נכון" רק להיגדים שאומרים דברים בעייתיים מובהקים.'
    },
    'Agreeableness': {
        'direction': 'positive',
        'label': '✅ חיובית',
        'subtraits_positive': ['שיתוף פעולה', 'סלחנות', 'סבלנות', 'גמישות', 'אמפתיה'],
        'subtraits_negative': ['ביקורתיות יתר', 'קשיחות', 'נקמנות', 'ויכוחנות'],
        'why_medical': 'עבודת צוות עם רופאים, אחיות, מטופלים ומשפחות — הבסיס לרפואה מודרנית.',
        'how_to_answer': 'תכונה חיובית — אך זכור שגם יכולת לעמוד על דעה זה ערך. אל תיתן את כל ה"כן" באופן שמשתמע כניעה.'
    },
    'Extraversion': {
        'direction': 'balanced',  # מאוזנת — לא קיצוני
        'label': '⚖️ מאוזנת',
        'subtraits_positive': ['ביטחון עצמי', 'אופטימיות', 'חברותיות', 'אנרגטיות',
                               'מנהיגות', 'חיוביות', 'יוזמה', 'אקטיביות'],
        'subtraits_negative': ['ביישנות יתר', 'הסתגרות', 'פסיביות', 'דכדוך'],
        'why_medical': 'תקשורת עם מטופלים וצוות חשובה, אבל גם יכולת הקשבה. רופא לא צריך להיות "כוכב מסיבות".',
        'how_to_answer': 'בדוק את המהות: היגדים על אקטיביות/אופטימיות/ביטחון = "נכון". היגדים על ביישנות מוגזמת/דכדוך = "לא נכון". היגדים נייטרליים על "אהבת מסיבות גדולות" — אפשר לפי האמת שלך.'
    },
    'Emotionality': {
        'direction': 'balanced',
        'label': '⚖️ מאוזנת — זהירות!',
        'subtraits_positive': ['אמפתיה', 'רגישות למטופלים', 'מודעות רגשית'],
        'subtraits_negative': ['חרדתיות', 'דאגנות יתר', 'רגזנות', 'איבוד שליטה',
                               'קריסה תחת לחץ', 'חוסר יציבות'],
        'why_medical': 'רופא חייב אמפתיה — אבל לא יכול לקרוס תחת לחץ. זה איזון עדין מאוד.',
        'how_to_answer': '⚠️ זהירות! היגדים על אמפתיה/רגישות לאחרים = "נכון". היגדים על חרדה/דאגה מוגזמת/קריסה = "לא נכון" חד משמעית.'
    },
    'Openness to Experience': {
        'direction': 'positive',
        'label': '✅ חיובית',
        'subtraits_positive': ['סקרנות', 'אהבת למידה', 'יצירתיות', 'פתיחות לרעיונות',
                               'חשיבה ביקורתית'],
        'subtraits_negative': ['שמרנות יתר', 'דוגמטיות', 'חוסר עניין'],
        'why_medical': 'הרפואה מתעדכנת מהר — נדרשת אהבת למידה תמידית, סקרנות אינטלקטואלית, יצירתיות באבחון.',
        'how_to_answer': 'תכונה חיובית למיון לרפואה. סמן "נכון" להיגדים על סקרנות/למידה. "לא נכון" להיגדים על שמרנות מוגזמת.'
    },
}


# מילון מילות-מפתח שמרמזות על "מתחייב" או "נשלל" בהיגד
NEGATION_HINTS = ['לא ', 'אין ', 'אינני', 'אינו ', 'אינה ', 'נמנע', 'מתקשה',
                  'מתרחק', 'מסרב', 'בורח', 'אסור']


# ============================================================
# Haifa Simulation — תרגול חיפה
# ============================================================

# בנק שאלות וידאו — מבוסס על נושאים שעלו במבחני חיפה האחרונים
HAIFA_VIDEO_QUESTIONS = [
    {
        'category': 'procedures',
        'q': 'ספר על מקרה שבו לא עמדת בנוהל או הוראה בעבודה או בלימודים. מה קרה? איך זה הסתיים?',
        'duration_sec': 180,  # 3 דקות
        'tips_for_practice': [
            'התחל במקרה ספציפי — מתי, איפה, מי היה מעורב',
            'הסבר למה הפרת את הנוהל (אבל אל תצדיק יתר על המידה)',
            'קח אחריות, גם אם הסיבה הייתה טובה',
            'סיים בלקח שלמדת',
        ]
    },
    {
        'category': 'conflict',
        'q': 'ספר על קונפליקט שהיה לך עם עמית, מנהל או חבר בעבודה. איך התמודדת איתו?',
        'duration_sec': 180,
        'tips_for_practice': [
            'בחר מקרה אמיתי, לא מומצא',
            'הצג את שתי הצדדים — לא רק את שלך',
            'הסבר מה ניסית לעשות כדי לפתור',
            'גם אם הקונפליקט לא נפתר — מה למדת ממנו'
        ]
    },
    {
        'category': 'population_groups',
        'q': 'תאר מצב שבו הרגשת אי-נוחות בעבודה או בלמידה מול קבוצת אוכלוסייה שונה ממך. איך התמודדת?',
        'duration_sec': 180,
        'tips_for_practice': [
            'היה כן — כולנו מרגישים אי-נוחות לפעמים, וזה בסדר',
            'אל תתחמק מהשאלה — לאמר "אף פעם לא הרגשתי" זה דגל אדום',
            'הראה מודעות עצמית והתפתחות',
            'בסוף הצג שיש לך כלים להתמודד עם זה כרופא'
        ]
    },
    {
        'category': 'mistake',
        'q': 'ספר על טעות משמעותית שעשית, איך זיהית אותה ומה עשית בעקבותיה.',
        'duration_sec': 180,
        'tips_for_practice': [
            'בחר טעות אמיתית, לא קלה מדי ("עיכבתי כמה דקות")',
            'הראה איך זיהית אותה בעצמך (לא שאחרים תפסו אותך)',
            'הראה אחריות מלאה — בלי תירוצים',
            'סיים בשיפור או שינוי בעקבות הטעות'
        ]
    },
    {
        'category': 'pressure',
        'q': 'תאר מצב שבו עבדת תחת לחץ זמן או עומס. איך הסתדרת?',
        'duration_sec': 180,
        'tips_for_practice': [
            'בחר מצב מקצועי או לימודי, לא אישי',
            'תאר אסטרטגיות ספציפיות (תעדוף, ביקוש עזרה, פירוק משימות)',
            'הראה שאתה מסוגל גם לבקש עזרה — לא רק "אני סובל לבד"',
            'סיים עם תוצאה חיובית או למידה'
        ]
    },
    {
        'category': 'ethics',
        'q': 'תאר מצב שראית מישהו עושה משהו לא אתי. איך הגבת?',
        'duration_sec': 180,
        'tips_for_practice': [
            'בחר מקרה אמיתי — גם אם קטן',
            'הראה שלא התעלמת',
            'הסבר את שיקול הדעת שלך — למי פנית, איך',
            'הראה שאתה מבין את החשיבות של דיווח מבלי להפוך למלשין'
        ]
    },
    {
        'category': 'feedback',
        'q': 'ספר על ביקורת קשה שקיבלת. איך הגבת לה?',
        'duration_sec': 180,
        'tips_for_practice': [
            'בחר ביקורת אמיתית שלמדת ממנה',
            'אל תזלזל בה ("זה היה שטות") — תראה רצינות',
            'הסבר את התהליך הרגשי — לא רק "קיבלתי בהבנה"',
            'הראה את השינוי שעשית בעקבותיה'
        ]
    },
    {
        'category': 'teamwork',
        'q': 'ספר על מצב שעבדת בצוות עם אדם קשה לשיתוף פעולה. איך התמודדת?',
        'duration_sec': 180,
        'tips_for_practice': [
            'אל תכפיש את האדם השני — תאר התנהגות, לא אופי',
            'הראה ניסיון להבין את נקודת המבט שלו',
            'הצג את מה שעשית כדי שהצוות יצליח',
            'הראה שאתה לא רק "סובל בשקט"'
        ]
    },
    {
        'category': 'patient_difficult',
        'q': 'תאר מצב היפותטי: מטופל בקליניקה צועק עליך בעוצמה. מה אתה עושה?',
        'duration_sec': 180,
        'tips_for_practice': [
            'אל תהיה התקפי — הראה רוגע',
            'הצג שלבים: 1) הקשבה, 2) הבנה, 3) פעולה',
            'הראה אמפתיה — הכעס בא מאיפשהו',
            'אל תוותר על גבולות מקצועיים גם בשעת לחץ'
        ]
    },
    {
        'category': 'diversity',
        'q': 'מה היית עושה אם מטופל מקבוצת אוכלוסייה שאתה לא מכיר היטב היה מסרב לטיפול שאתה ממליץ עליו?',
        'duration_sec': 180,
        'tips_for_practice': [
            'הצג סקרנות ולמידה, לא ניסיון לשכנע בכוח',
            'הראה כבוד לאוטונומיה של המטופל',
            'הסבר שאתה היית מבקש עזרה (תרבותית, רוחנית) במידת הצורך',
            'הראה מודעות לכך שזה תהליך, לא תשובה אחת'
        ]
    },
    {
        'category': 'self_awareness',
        'q': 'מה הוא חולשה אישיותית שאתה עובד עליה? תן דוגמה.',
        'duration_sec': 150,  # 2.5 דקות
        'tips_for_practice': [
            'בחר חולשה אמיתית — לא "אני יותר מדי מושלם"',
            'הראה מודעות עצמית מעמיקה',
            'הצג צעדים ספציפיים שאתה עושה',
            'אל תיפול לקלישאות'
        ]
    },
    {
        'category': 'why_medicine',
        'q': 'למה רפואה? תאר רגע ספציפי שבו ידעת שזה הכיוון שלך.',
        'duration_sec': 180,
        'tips_for_practice': [
            'אל תפתח עם "תמיד רציתי" — זה שטחי',
            'בחר רגע ספציפי, מקום, אנשים',
            'הראה גם הבנה של הקושי במקצוע — לא רק זוהר',
            'חבר את המוטיבציה שלך לערך מקצועי'
        ]
    },
    {
        'category': 'failure',
        'q': 'ספר על כישלון משמעותי שחווית. איך הגבת?',
        'duration_sec': 180,
        'tips_for_practice': [
            'בחר כישלון אמיתי — לא "פעם קיבלתי 90"',
            'תיאר את הרגשות בפועל, לא תיאוריה',
            'הראה התאוששות והתפתחות',
            'אל תבזה אחרים על הכישלון שלך'
        ]
    },
    {
        'category': 'boundaries',
        'q': 'תאר מצב שמישהו ביקש ממך לעשות משהו שעבר את הגבולות שלך. איך הגבת?',
        'duration_sec': 150,
        'tips_for_practice': [
            'הראה שאתה מסוגל לאמר "לא"',
            'הצג שיקול דעת — לא סירוב אוטומטי',
            'הסבר איך אמרת "לא" בדרך מכבדת',
            'הראה שעמדת על שלך גם כשהיה לחץ'
        ]
    },
    {
        'category': 'role_model',
        'q': 'מי דמות מקצועית שאתה מעריץ ולמה? מה למדת ממנה?',
        'duration_sec': 150,
        'tips_for_practice': [
            'בחר דמות אמיתית מתוך התחום או חיים אישיים',
            'תיאר תכונה ספציפית — לא "הכל"',
            'חבר את ההערכה ללמידה אישית',
            'אל תבחר דמות פוליטית או מפלגת'
        ]
    },
]


# ============================================================
# Video Follow-Up Questions — לפי קטגוריית האמינות
# ============================================================
# מתפרצות אחרי שעניתי על מספר שאלות אמינות מאותה קטגוריה.
# מטרה: לבדוק עקביות תחת לחץ — אם ענית "אף פעם לא גנבתי", 
# האם תוכל לתאר מקרה שראית גניבה?
HAIFA_FOLLOWUP_VIDEO = {
    'theft': [
        {
            'q': 'ספר על מקרה שראית מישהו לוקח משהו שלא שייך לו במקום עבודה או לימודים. איך הגבת?',
            'duration_sec': 180,
            'tips_for_practice': [
                'בחר מקרה אמיתי — קטן או גדול',
                'תאר מה ראית בלי להאשים יתר על המידה',
                'הסבר את שיקול הדעת שלך — האם דיווחת? למה כן/לא?',
                'הראה שאתה מבין את הדילמה (לא רק "כל גנב צריך להיענש")'
            ]
        },
        {
            'q': 'תאר מצב שבו פיתית להיכנס לדבר לא הוגן והחלטת לא — מה עזר לך?',
            'duration_sec': 150,
            'tips_for_practice': [
                'תהיה כן — כולנו מתפתים לפעמים',
                'תאר את הקול הפנימי שעצר אותך',
                'חבר לערך מקצועי (יושרה רפואית)',
                'אל תהיה מטיף — שיהיה אישי'
            ]
        },
    ],
    'drugs': [
        {
            'q': 'תאר מצב שראית מישהו תחת השפעת אלכוהול או סמים בעבודה או בלימודים. איך התמודדת?',
            'duration_sec': 180,
            'tips_for_practice': [
                'גם אם לא ראית בעבודה — אפשר ממסיבה או חוויה אחרת',
                'הראה דאגה לאדם, לא רק לחוקים',
                'אל תהיה שיפוטי — ההתמכרות היא מחלה',
                'תאר מה עשית בפועל'
            ]
        },
        {
            'q': 'מה היית עושה אם היית מגלה שעמית בעבודה (בעתיד, כרופא) משתמש בחומרים אסורים?',
            'duration_sec': 180,
            'tips_for_practice': [
                'אל תקפוץ ל"דיווח מיידי" — תהיה מורכב',
                'הראה שלב ראשון של דיבור עם האדם',
                'הסבר מתי כן צריך לדווח (סכנת מטופלים)',
                'הראה אמפתיה גם לקשיים של עמית'
            ]
        },
    ],
    'gambling': [
        {
            'q': 'תאר מצב שראית מישהו בסיכון מוגזם — בכסף, בריאות, או בכל תחום. איך הגבת?',
            'duration_sec': 150,
            'tips_for_practice': [
                'בחר מצב אמיתי, גם אם לא דרמטי',
                'הראה דאגה ולא ביקורת',
                'תאר מה עשית כדי לעזור (אם משהו)',
                'חבר ליכולת רפואית — לראות סימני אזהרה'
            ]
        },
    ],
    'unethical': [
        {
            'q': 'ספר על מצב שראית התנהגות לא אתית — בעבודה, לימודים או חיים אישיים. מה עשית?',
            'duration_sec': 180,
            'tips_for_practice': [
                'בחר מקרה ספציפי — לא הכללה',
                'תאר את הדילמה האמיתית (לא רק "ידעתי שזה רע")',
                'הסבר את ההחלטה שלך — לדווח/לא לדווח',
                'תהיה מוכן לסבירות שטעית — אנושיות'
            ]
        },
        {
            'q': 'תאר מצב שעמדת בפני פיתוי לקצר דרך באופן לא הגון. מה החליט אותך?',
            'duration_sec': 150,
            'tips_for_practice': [
                'תהיה כן — לפעמים אנחנו רוצים לקצר',
                'הראה את התהליך הפנימי שלך',
                'חבר לערכים מקצועיים',
                'הימנע מקלישאות'
            ]
        },
    ],
    'termination': [
        {
            'q': 'תאר מצב שעזבת מקום עבודה או לימודים בנסיבות מורכבות. מה למדת?',
            'duration_sec': 180,
            'tips_for_practice': [
                'אל תכפיש את המקום הקודם',
                'קח אחריות על חלקך אם היה',
                'הראה למידה ושינוי בעקבות',
                'הצג את הפרספקטיבה הבוגרת שלך עכשיו'
            ]
        },
    ],
    'academic': [
        {
            'q': 'ספר על מצב שראית מישהו מעתיק או רומה במבחן/עבודה. מה הרגשת ועשית?',
            'duration_sec': 180,
            'tips_for_practice': [
                'אל תהיה ילדותי ("הלשנתי")',
                'הצג את המורכבות — חברתית מול אקדמית',
                'הסבר שיקול דעתך — מה עשית בפועל',
                'חבר לחשיבות יושרה אקדמית ברפואה'
            ]
        },
        {
            'q': 'תאר מצב שהיית בלחץ אקדמי קיצוני. איך התמודדת בלי לפגוע ביושר שלך?',
            'duration_sec': 180,
            'tips_for_practice': [
                'תהיה כן על הקושי',
                'תאר אסטרטגיות שעבדו',
                'הראה שאתה לא לבד — ביקשת עזרה',
                'חבר ליכולת התמודדות בלימודי רפואה'
            ]
        },
    ],
    'whistleblowing': [
        {
            'q': 'תאר מצב ששקלת לדווח על משהו לא תקין אבל היססת. מה עזר לך להחליט?',
            'duration_sec': 180,
            'tips_for_practice': [
                'הראה שיש לך ספקות בריאים — לא רק ביטחון',
                'תאר את התהליך הפנימי',
                'הצג גם את העלות של דיווח (יחסים, הוקעה)',
                'חבר ליכולת לעמוד מול לחץ חברתי כרופא'
            ]
        },
    ],
    'feedback': [
        {
            'q': 'ספר על ביקורת קשה מאוד שקיבלת מבן זוג, חבר או מנהל. איך הרגשת ומה עשית?',
            'duration_sec': 180,
            'tips_for_practice': [
                'אל תזלזל בביקורת ("הוא טעה")',
                'תאר את התהליך הרגשי האמיתי — כעס/הגנה',
                'הראה איך הגעת לקבל את הביקורת',
                'הצג שינוי או צמיחה בעקבותיה'
            ]
        },
    ],
    'teamwork': [
        {
            'q': 'תאר מצב שעבדת בצוות שלא תפקד טוב. מה היה תפקידך והאם ניסית לתקן?',
            'duration_sec': 180,
            'tips_for_practice': [
                'אל תאשים את כולם חוץ ממך',
                'קח אחריות על חלקך',
                'תאר ניסיונות תיקון ספציפיים',
                'הראה למידה גם אם לא הצלחת'
            ]
        },
    ],
    'harassment': [
        {
            'q': 'תאר מצב שראית התנהגות שגרמה לאי-נוחות לאדם אחר במקום עבודה. איך הגבת?',
            'duration_sec': 180,
            'tips_for_practice': [
                'בחר מקרה אמיתי ספציפי',
                'תאר את ההתנהגות בלי לפרט יותר מדי',
                'הראה שזיהית את הבעיה גם אם היא הייתה דקה',
                'הסבר מה עשית — האם דיברת עם הקורבן/המבצע/הממונה',
                'אל תכפיש ואל תצדק יתר על המידה'
            ]
        },
        {
            'q': 'מה היית עושה כרופא אם היית רואה עמית מתנהג בצורה לא ראויה כלפי מטופלת או עובדת?',
            'duration_sec': 180,
            'tips_for_practice': [
                'הראה גישה הדרגתית: שיחה אישית → ממונה → דיווח רשמי',
                'אל תקפוץ ל"ארגיש את אלה" — תהיה אסטרטגי',
                'הסבר את החובה המקצועית להגן על מטופלים',
                'הראה אמפתיה גם לאדם שטעה (אם זה היה חד-פעמי)'
            ]
        },
    ],
    'procedures': [
        {
            'q': 'תאר מקרה שבו הפרת נוהל או הוראה — בעבודה, לימודים או חיים אישיים. למה זה קרה?',
            'duration_sec': 180,
            'tips_for_practice': [
                'בחר מקרה אמיתי — כולם מפרים נוהל לפעמים',
                'הסבר את הסיבה בכנות (אבל בלי תירוצים)',
                'תאר את ההשלכות',
                'הראה למידה — מה תעשה אחרת בפעם הבאה',
                'אל תהיה ילדותי ("המורה היה רע")'
            ]
        },
        {
            'q': 'מה היית עושה אם היית רואה עמית רופא מדלג על שלב בפרוטוקול רפואי?',
            'duration_sec': 180,
            'tips_for_practice': [
                'הראה שאתה לוקח את זה ברצינות (זו בטיחות מטופלים)',
                'תאר גישה הדרגתית — לא לתקוף מיד',
                'הסבר מתי כן צריך לדווח (סכנה ממשית)',
                'הראה הבנה לעומס שלפעמים גורם לקיצורים',
                'חבר לערך מקצועי של דיוק רפואי'
            ]
        },
    ],
}


# מסכי "אינך דובר אמת" — שמתפרצים בתרגול חיפה
HAIFA_FAKE_DETECTION_MESSAGES = [
    {
        'icon': '🚨',
        'title': 'התראת מערכת: חשד לחוסר כנות',
        'detail': 'התשובות האחרונות שלך מציגות תמונה חיובית באופן חריג. רופאים אמיתיים מודים בחולשות. אנא ענה בכנות בהמשך — המערכת מתעדת.',
        'cta': 'אני מבין, אענה בכנות'
    },
    {
        'icon': '⚠️',
        'title': 'זוהו פערים בתשובות',
        'detail': 'תשובות שנתת בסעיפים שונים סותרות זו את זו. אנו ממליצים לעצור, לקרוא בעיון, ולענות בעקביות.',
        'cta': 'הבנתי'
    },
    {
        'icon': '🔴',
        'title': 'אזהרה: דפוס תשובות חשוד',
        'detail': 'כל בני האדם — כולל הרופאים הטובים ביותר — מתמודדים עם חולשות וקשיים. תשובות חיוביות מדי בכל תחום פוגעות באמינות שלך.',
        'cta': 'הבנתי, אענה כן'
    },
]


def get_haifa_questions(count=80, video_count=4):
    """
    בונה רצף שאלות לתרגול חיפה:
    - שאלות HEXACO (~45%)
    - שאלות אמינות תרחישים (~45%)
    - שאלות מטא (פוליגרף/חרטה/כנות) — מתפרצות באקראיות אמיתית
    - שאלות וידאו פתע (count_video מהן, אקראיות)
    """
    questions = []
    meta_pool = []
    meta_categories = {'polygraph', 'regret', 'honesty_meta'}
    
    # ~45% HEXACO
    hex_count = int(count * 0.45)
    try:
        hex_df = load_hexaco_questions()
        if not hex_df.empty:
            hex_sample = pd.DataFrame(get_balanced_questions(hex_df, total_limit=hex_count))
            for _, row in hex_sample.iterrows():
                q_dict = row.to_dict()
                q_dict['quiz_format'] = 'haifa_text'
                q_dict['source'] = 'hexaco'
                questions.append(q_dict)
    except Exception:
        pass
    
    # ~45% אמינות (תרחישים בלבד — מטא נשמר בנפרד)
    int_count = int(count * 0.45)
    if int_count > 0:
        try:
            int_df = load_integrity_questions_csv()
            if not int_df.empty:
                cat_col = 'category' if 'category' in int_df.columns else 'trait'
                if cat_col in int_df.columns:
                    # תרחישים רגילים
                    int_filtered = int_df[~int_df[cat_col].isin(meta_categories)]
                    if not int_filtered.empty:
                        int_sample = int_filtered.sample(n=min(int_count, len(int_filtered)))
                        for _, row in int_sample.iterrows():
                            q_dict = row.to_dict()
                            q_dict['quiz_format'] = 'haifa_text'
                            q_dict['source'] = 'integrity'
                            q_dict['is_scenario'] = True
                            if 'trait' not in q_dict and 'category' in q_dict:
                                q_dict['trait'] = q_dict['category']
                            questions.append(q_dict)
                    
                    # שאלות מטא — נשמרות בנפרד להזרקה אקראית
                    meta_df = int_df[int_df[cat_col].isin(meta_categories)]
                    for _, row in meta_df.iterrows():
                        q_dict = row.to_dict()
                        q_dict['quiz_format'] = 'haifa_text'
                        q_dict['source'] = 'meta'
                        q_dict['is_meta_question'] = True
                        if 'trait' not in q_dict and 'category' in q_dict:
                            q_dict['trait'] = q_dict['category']
                        meta_pool.append(q_dict)
        except Exception:
            pass
    
    random.shuffle(questions)
    
    # ===== הזרקת שאלות מטא באקראיות אמיתית =====
    # כמות תלויה באורך: 3 בקצר, 4 בבינוני, 5 במלא, 8 ב-300
    if meta_pool and len(questions) >= 20:
        if count <= 50:
            num_meta = 3
        elif count <= 90:
            num_meta = 4
        elif count <= 150:
            num_meta = 5
        else:
            num_meta = 8  # ל-300 שאלות — יותר אירועי לחץ
        
        num_meta = min(num_meta, len(meta_pool))
        meta_sample = random.sample(meta_pool, num_meta)
        
        # אקראיות אמיתית — מיקומים אקראיים בתחום בטוח
        # לא ב-10 הראשונות, לא ב-10 האחרונות, ולא צמודות מדי זה לזה
        safe_start = 10
        safe_end = max(safe_start + 1, len(questions) - 10)
        
        if safe_end > safe_start:
            chosen_positions = []
            attempts = 0
            min_gap = 5  # מינימום 5 שאלות בין מטא למטא
            
            while len(chosen_positions) < num_meta and attempts < 100:
                pos = random.randint(safe_start, safe_end)
                if all(abs(pos - p) >= min_gap for p in chosen_positions):
                    chosen_positions.append(pos)
                attempts += 1
            
            # ממיינים מהסוף להתחלה כדי ש-insert לא ישבש אינדקסים
            chosen_positions.sort(reverse=True)
            for i, pos in enumerate(chosen_positions):
                if i < len(meta_sample):
                    questions.insert(min(pos, len(questions)), meta_sample[i])
    
    # ===== הוספת שאלות וידאו אקראית =====
    if video_count > 0 and len(questions) > 10:
        video_sample = random.sample(HAIFA_VIDEO_QUESTIONS, min(video_count, len(HAIFA_VIDEO_QUESTIONS)))
        
        if len(questions) >= video_count:
            segment_size = max(1, len(questions) // video_count)
            for i, vq in enumerate(video_sample):
                segment_start = i * segment_size + 5
                segment_end = min((i + 1) * segment_size, len(questions))
                if segment_start < segment_end:
                    pos = random.randint(segment_start, segment_end)
                    video_q = dict(vq)
                    video_q['quiz_format'] = 'haifa_video'
                    video_q['source'] = 'video'
                    video_q['trait'] = vq['category']
                    questions.insert(min(pos, len(questions)), video_q)
    
    return questions


def should_inject_fake_detection(responses, current_q):
    """
    מחליט אם להציג מסך "אינך דובר אמת" כעת.
    מבוסס על דפוסים בתשובות האחרונות:
    - יותר מדי תשובות "מושלמות" ברצף (5/5 ב-HEXACO חיוביות, 1 בשליליות)
    - אקראיות מסוימת (10% הסיכוי כל ~25 שאלות)
    """
    # לא בתחילת המבחן
    if current_q < 15:
        return False
    
    # לא בלי תשובות
    if not responses or len(responses) < 8:
        return False
    
    # אקראית — פעם ב-25-40 שאלות
    if current_q % random.randint(25, 40) != 0:
        # בכל זאת — אם יש דפוס חשוד, נבדוק
        recent = responses[-8:]
        extreme_count = sum(1 for r in recent if int(r.get('answer', 3)) in (1, 5, 2, 4) and 
                           int(r.get('answer', 3)) in (1, 5))
        # אם יש 6 מתוך 8 קיצוניות בכיוון אידיאלי
        if extreme_count >= 6:
            return random.random() < 0.5  # 50% סיכוי בקבוצה חשודה
        return False
    
    return True


def should_inject_followup_video(responses, current_q, already_injected_categories):
    """
    מחליט אם להזריק שאלת וידאו פולו-אפ.
    תנאים:
    - ענית על 3+ שאלות מאותה קטגוריית אמינות
    - הקטגוריה הזו עדיין לא קיבלה פולו-אפ
    - לא מוקדם מדי במבחן (אחרי שאלה 12)
    
    מחזיר: (category, video_data) או (None, None)
    """
    if current_q < 12 or not responses:
        return None, None
    
    # סופרים תשובות לכל קטגוריית אמינות
    category_counts = {}
    for r in responses:
        cat = r.get('category', '') or r.get('trait', '')
        if cat in HAIFA_FOLLOWUP_VIDEO and cat not in already_injected_categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # מחפשים קטגוריה עם 3+ תשובות
    eligible = [cat for cat, c in category_counts.items() if c >= 3]
    
    if not eligible:
        return None, None
    
    # סיכוי 30% להזריק (כדי שזה יהיה פתע, לא צפוי)
    if random.random() > 0.3:
        return None, None
    
    # בוחרים קטגוריה אקראית מהזמינות
    chosen_cat = random.choice(eligible)
    video_options = HAIFA_FOLLOWUP_VIDEO[chosen_cat]
    chosen_video = dict(random.choice(video_options))
    
    # הוספת מטא-דאטה
    chosen_video['quiz_format'] = 'haifa_video'
    chosen_video['source'] = 'followup'
    chosen_video['followup_category'] = chosen_cat
    chosen_video['category'] = chosen_cat
    chosen_video['trait'] = chosen_cat
    
    return chosen_cat, chosen_video





def detect_statement_polarity(question_text):
    """
    מזהה האם ההיגד "מתחייב" את התכונה (חיובי) או "שולל" אותה (בעל שלילה).
    מחזיר: 'affirms' (מתחייב) / 'negates' (שולל) / 'neutral'
    """
    text = str(question_text).lower()
    
    # סופרים מילות שלילה
    negation_count = sum(1 for hint in NEGATION_HINTS if hint in text)
    
    if negation_count >= 1:
        return 'negates'
    return 'affirms'


def get_decision_tree_analysis(question_data):
    """
    מבצע את עץ ההחלטה של מכון נועם:
    1. זיהוי התכונה
    2. חיובית/שלילית/מאוזנת
    3. מתחייב/שולל בהיגד
    4. תשובה מומלצת
    
    מחזיר dict עם כל השלבים — לתצוגה למשתמש.
    """
    trait = question_data.get('trait', question_data.get('category', ''))
    text = str(question_data.get('q', question_data.get('question', '')))
    is_reverse = str(question_data.get('reverse', False)).strip().lower() in ['true', '1', '1.0', 'yes']
    
    trait_info = TRAIT_DIRECTIONS.get(trait)
    trait_he = TRAIT_DICT.get(trait, trait)
    
    # תרחיש אמינות (שאלות מ-integrity_questions.csv)
    if not trait_info:
        # תרחישים שליליים
        negative_cats = {'theft', 'drugs', 'gambling', 'unethical', 'termination', 'academic'}
        positive_cats = {'whistleblowing', 'feedback', 'teamwork'}
        category = question_data.get('category', '')
        
        if category in negative_cats:
            return {
                'is_scenario': True,
                'trait_he': category,
                'direction': 'negative',
                'direction_label': '🔴 התנהגות שלילית מובהקת',
                'polarity': detect_statement_polarity(text),
                'recommended': 'לא נכון',
                'recommended_value': 2,
                'why': 'התנהגויות כאלה (גניבה, סמים, וכו\') לא יכולות לאפיין רופא.',
                'reasoning_chain': [
                    f"1️⃣ סוג ההיגד: תרחיש אמינות (קטגוריה: {category})",
                    f"2️⃣ זה תיאור של התנהגות שלילית מובהקת",
                    f"3️⃣ לכן: {'נכון' if detect_statement_polarity(text) == 'negates' else 'לא נכון'}"
                ]
            }
        elif category in positive_cats:
            return {
                'is_scenario': True,
                'trait_he': category,
                'direction': 'positive',
                'direction_label': '🟢 התנהגות חיובית',
                'polarity': detect_statement_polarity(text),
                'recommended': 'נכון',
                'recommended_value': 4,
                'why': 'אלה התנהגויות שמתאימות לרופא — שיתוף פעולה, יושרה, אחריות.',
                'reasoning_chain': [
                    f"1️⃣ סוג ההיגד: תרחיש אמינות (קטגוריה: {category})",
                    f"2️⃣ זה תיאור של התנהגות חיובית",
                    f"3️⃣ לכן: נכון"
                ]
            }
        return None
    
    # שאלת HEXACO רגילה
    direction = trait_info['direction']
    polarity = detect_statement_polarity(text)
    
    # מטריצת ההחלטה של מכון נועם:
    # תכונה חיובית + מתחייבת = נכון
    # תכונה חיובית + נשללת   = לא נכון
    # תכונה שלילית + מתחייבת = לא נכון
    # תכונה שלילית + נשללת   = נכון
    
    # תיקון: הקובץ שלך משתמש ב-reverse — ההיגד נשלל לוגית
    # אם reverse=True זה אומר שהציון מתהפך, מה שמרמז שההיגד מנוסח "הפוך" מהתכונה
    effective_polarity = polarity
    if is_reverse and polarity == 'affirms':
        effective_polarity = 'negates'
    elif is_reverse and polarity == 'negates':
        effective_polarity = 'affirms'
    
    if direction == 'positive':
        if effective_polarity == 'affirms':
            recommended = 'נכון'
            value = 4
            reasoning = f'התכונה {trait_he} חיובית לרפואה, וההיגד מתחייב אותה → "נכון"'
        else:
            recommended = 'לא נכון'
            value = 2
            reasoning = f'התכונה {trait_he} חיובית לרפואה, וההיגד שולל אותה → "לא נכון"'
    elif direction == 'balanced':
        # למאוזן — תלוי בתת-תכונה (אקטיביות חיובית, חרדה שלילית)
        # ננסה לזהות מילות מפתח של תת-תכונה שלילית
        text_lower = text.lower()
        is_neg_subtrait = any(neg_word in text_lower 
                              for neg_word in trait_info.get('subtraits_negative', []))
        is_pos_subtrait = any(pos_word in text_lower 
                              for pos_word in trait_info.get('subtraits_positive', []))
        
        if is_neg_subtrait and not is_pos_subtrait:
            # תת-תכונה שלילית
            if effective_polarity == 'affirms':
                recommended = 'לא נכון'
                value = 2
                reasoning = f'ההיגד מתחייב תת-תכונה שלילית של {trait_he} → "לא נכון"'
            else:
                recommended = 'נכון'
                value = 4
                reasoning = f'ההיגד שולל תת-תכונה שלילית של {trait_he} → "נכון"'
        elif is_pos_subtrait and not is_neg_subtrait:
            # תת-תכונה חיובית
            if effective_polarity == 'affirms':
                recommended = 'נכון'
                value = 4
                reasoning = f'ההיגד מתחייב תת-תכונה חיובית של {trait_he} → "נכון"'
            else:
                recommended = 'לא נכון'
                value = 2
                reasoning = f'ההיגד שולל תת-תכונה חיובית של {trait_he} → "לא נכון"'
        else:
            # אמצע — לפי הכיוון הכללי (התכונה רוצה ציון בינוני-גבוה)
            if effective_polarity == 'affirms':
                recommended = 'נכון'
                value = 4
                reasoning = f'התכונה {trait_he} מאוזנת — והיגד נייטרלי → לרוב "נכון" (אקטיביות עדיפה)'
            else:
                recommended = 'לא נכון'
                value = 2
                reasoning = f'התכונה {trait_he} מאוזנת — וההיגד שולל → "לא נכון"'
    else:
        # default
        recommended = 'נכון' if effective_polarity == 'affirms' else 'לא נכון'
        value = 4 if recommended == 'נכון' else 2
        reasoning = 'בחר לפי האמת שלך.'
    
    polarity_he = 'מתחייב' if polarity == 'affirms' else 'נשלל'
    if is_reverse:
        polarity_he += ' (היגד הפוך)'
    
    return {
        'is_scenario': False,
        'trait_he': trait_he,
        'direction': direction,
        'direction_label': trait_info['label'],
        'polarity': polarity,
        'polarity_he': polarity_he,
        'recommended': recommended,
        'recommended_value': value,
        'why': trait_info['why_medical'],
        'subtraits_positive': trait_info.get('subtraits_positive', []),
        'subtraits_negative': trait_info.get('subtraits_negative', []),
        'reasoning_chain': [
            f"1️⃣ **התכונה הנבדקת:** {trait_he}",
            f"2️⃣ **כיוון לרפואה:** {trait_info['label']}",
            f"3️⃣ **ההיגד:** {polarity_he}",
            f"4️⃣ **תשובה אידיאלית:** {recommended}",
        ]
    }


# ============================================================
# Smart Contradiction Detection — Trigram-Based Hebrew Similarity
# ============================================================
def _clean_for_trigrams(text):
    """ניקוי טקסט לפני יצירת trigrams — שומרים על אותיות ורווחים בלבד."""
    import re
    text = str(text).lower()
    # רק אותיות עברית/אנגלית + רווח
    text = re.sub(r'[^\u05D0-\u05EA\u05F0-\u05F4a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _trigrams(text, n=3):
    """יוצר סט של תת-מחרוזות באורך n מהטקסט.
    שיטה עמידה למורפולוגיה עברית — מתעלם מקידומות וסיומות.
    """
    text = _clean_for_trigrams(text)
    if len(text) < n:
        return set()
    return set(text[i:i+n] for i in range(len(text) - n + 1))


def _text_similarity(text1, text2):
    """דמיון Jaccard על trigrams — מתאים מאוד לעברית.
    מחזיר 0.0 - 1.0.
    """
    t1 = _trigrams(text1, n=3)
    t2 = _trigrams(text2, n=3)
    if not t1 or not t2:
        return 0.0
    intersection = t1 & t2
    union = t1 | t2
    return len(intersection) / len(union) if union else 0.0


def find_smart_contradictions(responses, similarity_threshold=0.30, min_score_gap=2.5):
    """
    מזהה סתירות אמיתיות:
    שאלות שאומרות דברים דומים (לפי דמיון trigram) — אבל קיבלו תשובות שונות מאוד.
    
    threshold=0.30: מעל זה נחשב "דומה" (מתאים לעברית).
    min_score_gap=2.5: לפחות פער 2.5 בציונים נחשב סתירה.
    """
    contradictions = []
    if not responses or len(responses) < 2:
        return contradictions
    
    # חישוב הציון בפועל (אחרי reverse) לכל תשובה
    items = []
    for i, r in enumerate(responses):
        try:
            answer = int(r.get('answer', 3))
            is_reverse = str(r.get('reverse', False)).strip().lower() in ['true', '1', '1.0', 'yes', 't']
            score = (6 - answer) if is_reverse else answer
            score = max(1, min(5, score))
            items.append({
                'idx': i,
                'question': str(r.get('question', '')),
                'raw_answer': answer,
                'score': score,
                'trait': r.get('trait', r.get('category', '')),
                'reverse': is_reverse,
            })
        except Exception:
            continue
    
    # השוואה בין כל זוג שאלות
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            
            sim = _text_similarity(a['question'], b['question'])
            
            if sim >= similarity_threshold:
                gap = abs(a['score'] - b['score'])
                if gap >= min_score_gap:
                    severity = 'critical' if (gap >= 3.5 and sim >= 0.45) else 'high'
                    contradictions.append({
                        'q1': a['question'],
                        'q2': b['question'],
                        'ans1': a['raw_answer'],
                        'ans2': b['raw_answer'],
                        'score1': a['score'],
                        'score2': b['score'],
                        'gap': round(gap, 1),
                        'similarity': round(sim, 2),
                        'trait': a['trait'],
                        'severity': severity,
                        'message': f"שתי שאלות דומות עם תשובות הפוכות — דמיון {int(sim*100)}%, פער {int(gap)}"
                    })
    
    contradictions.sort(key=lambda x: (-x['similarity'], -x['gap']))
    return contradictions[:10]


def calculate_pressure_stability(responses):
    """
    מחשב מדד יציבות תחת לחץ.
    
    הלוגיקה:
    1. מזהה "אירועי לחץ" — שאלות מטא, וידאו, או מסכי "אינך דובר אמת"
    2. מסמן 5 שאלות לפני כל אירוע כ"לפני" ו-5 אחרי כ"אחרי"
    3. מחשב ציון ממוצע לכל תכונה לפני/אחרי
    4. מודד את ההפרש — ככל שגדול, היציבות נמוכה
    
    מחזיר:
    - score: 0-100 (100 = יציבות מושלמת)
    - changes: dict של {trait: {before, after, delta, severity}}
    - summary: טקסט קצר
    """
    if not responses or len(responses) < 15:
        return {'score': 100, 'changes': {}, 'summary': 'לא מספיק נתונים', 'events': 0}
    
    # זיהוי אירועי לחץ
    pressure_events = []
    for i, r in enumerate(responses):
        is_meta = (
            r.get('source') == 'meta' or 
            r.get('is_meta_question') or 
            r.get('category') in ('polygraph', 'regret', 'honesty_meta')
        )
        is_video = r.get('is_video', False) or r.get('quiz_format') == 'haifa_video'
        is_followup = r.get('source') == 'followup'
        
        if is_meta or is_video or is_followup:
            pressure_events.append({
                'index': i,
                'type': 'meta' if is_meta else ('video' if is_video else 'followup'),
            })
    
    if not pressure_events:
        return {'score': 100, 'changes': {}, 'summary': 'לא היו אירועי לחץ במבחן', 'events': 0}
    
    # חישוב ציונים לפני/אחרי לכל אירוע
    # פוקוס על תשובות HEXACO רק (יש להן ציון מספרי משמעותי)
    hexaco_traits = {'Conscientiousness', 'Honesty-Humility', 'Agreeableness',
                     'Emotionality', 'Extraversion', 'Openness to Experience'}
    
    trait_changes = {}  # {trait: [(before_score, after_score), ...]}
    
    for event in pressure_events:
        idx = event['index']
        
        # 5 שאלות לפני (לא כולל אירועי לחץ אחרים)
        before_responses = []
        for i in range(idx - 1, max(idx - 8, -1), -1):
            r = responses[i]
            if r.get('trait') in hexaco_traits and not r.get('is_video'):
                before_responses.append(r)
                if len(before_responses) >= 5:
                    break
        
        # 5 שאלות אחרי
        after_responses = []
        for i in range(idx + 1, min(idx + 8, len(responses))):
            r = responses[i]
            if r.get('trait') in hexaco_traits and not r.get('is_video'):
                after_responses.append(r)
                if len(after_responses) >= 5:
                    break
        
        # סופרים את הציונים האפקטיביים לכל תכונה
        for trait in hexaco_traits:
            before_for_trait = [_calc_effective(r) for r in before_responses if r.get('trait') == trait]
            after_for_trait = [_calc_effective(r) for r in after_responses if r.get('trait') == trait]
            
            if len(before_for_trait) >= 1 and len(after_for_trait) >= 1:
                avg_before = sum(before_for_trait) / len(before_for_trait)
                avg_after = sum(after_for_trait) / len(after_for_trait)
                
                if trait not in trait_changes:
                    trait_changes[trait] = []
                trait_changes[trait].append((avg_before, avg_after))
    
    # חישוב מדד יציבות
    if not trait_changes:
        return {'score': 100, 'changes': {}, 'summary': 'לא נמצאו זוגות לפני/אחרי', 'events': len(pressure_events)}
    
    changes_summary = {}
    total_delta = 0
    count_significant = 0
    
    for trait, pairs in trait_changes.items():
        avg_before = sum(p[0] for p in pairs) / len(pairs)
        avg_after = sum(p[1] for p in pairs) / len(pairs)
        delta = abs(avg_after - avg_before)
        
        if delta >= 1.0:
            severity = 'high'
            count_significant += 1
        elif delta >= 0.5:
            severity = 'medium'
            count_significant += 0.5
        else:
            severity = 'low'
        
        changes_summary[trait] = {
            'before': round(avg_before, 2),
            'after': round(avg_after, 2),
            'delta': round(avg_after - avg_before, 2),
            'severity': severity,
        }
        total_delta += delta
    
    # ציון יציבות: 100 = אין שינוי, 0 = שינויים גדולים
    avg_delta = total_delta / max(1, len(trait_changes))
    stability_score = max(0, min(100, round(100 - (avg_delta * 30))))
    
    # סיכום טקסטואלי
    if stability_score >= 85:
        summary = '🛡️ יציבות מצוינת — האישיות שלך נשארת קבועה גם תחת לחץ'
    elif stability_score >= 70:
        summary = '✅ יציבות טובה — שינויים קלים בלבד תחת לחץ'
    elif stability_score >= 55:
        summary = '⚠️ יציבות בינונית — אתה משתנה במידה מסוימת תחת לחץ'
    else:
        summary = '🔴 יציבות נמוכה — האישיות שלך משתנה בצורה משמעותית תחת לחץ'
    
    return {
        'score': stability_score,
        'changes': changes_summary,
        'summary': summary,
        'events': len(pressure_events),
    }


def _calc_effective(response):
    """ציון אפקטיבי בתכונה (אחרי reverse)."""
    try:
        ans = int(response.get('answer', 3))
        is_rev = str(response.get('reverse', False)).strip().lower() in ['true', '1', '1.0', 'yes', 't']
        score = (6 - ans) if is_rev else ans
        return max(1, min(5, score))
    except Exception:
        return 3


def calculate_smart_reliability(responses, contradictions, is_binary=False):
    """
    מחשב אמינות מותאם — עם תיקונים:
    1. במבחן בינארי, לא מענישים על "תשובות קיצוניות" (כולן בינאריות)
    2. סופר רק סתירות אמיתיות (מהפונקציה החכמה)
    """
    if not responses:
        return 100
    
    score = 100.0
    
    # סתירות חכמות — קנס לפי חומרה
    for c in contradictions:
        if c.get('severity') == 'critical':
            score -= 12  # פחות אגרסיבי מהמקור
        else:
            score -= 6
    
    # תשובות מהירות מדי
    fast_count = sum(1 for r in responses if r.get('response_time', 99) < 1.4)
    score -= fast_count * 2
    
    # מונוטוניות (תשובות זהות)
    answers = [int(r.get('answer', 3)) for r in responses]
    if len(answers) > 5:
        unique = len(set(answers))
        if is_binary:
            # במבחן בינארי, מינימום 2 ערכים זה נורמלי
            if unique == 1:
                score -= 30  # רק 1 ערך = רק "כן" או רק "לא" → דגל גדול
        else:
            # במבחן רגיל
            if unique <= 1:
                score -= 30
            elif unique == 2:
                score -= 15
        
        # פיזור (std)
        try:
            import statistics
            std = statistics.stdev(answers)
            if not is_binary and std < 0.3:
                score -= 15
        except Exception:
            pass
    
    # קיצוניות — *לא* בודקים במבחן בינארי
    if not is_binary and len(answers) > 0:
        extreme_ratio = sum(1 for a in answers if a in (1, 5)) / len(answers)
        if extreme_ratio > 0.7:
            score -= 20
    
    return max(0, min(100, round(score)))


# ============================================================
# CSV Loading — תיקון נתיבים (עכשיו בודק כמה אופציות)
# ============================================================
def _find_csv(filename):
    """מנסה למצוא את קובץ ה-CSV בכמה מקומות אפשריים."""
    candidates = [
        filename,
        f"data/{filename}",
        f"./{filename}",
        os.path.join(os.path.dirname(__file__), filename) if "__file__" in globals() else filename,
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return filename  # יחזיר את המקורי גם אם לא נמצא, נטפל בשגיאה במקום אחר


@st.cache_data
def load_hexaco_questions():
    try:
        path = _find_csv("questions.csv")
        return pd.read_csv(path)
    except Exception as e:
        st.error(f"שגיאה בטעינת שאלות HEXACO: {e}")
        return pd.DataFrame()


@st.cache_data
def load_integrity_questions_csv():
    try:
        path = _find_csv("integrity_questions.csv")
        return pd.read_csv(path)
    except Exception as e:
        st.error(f"שגיאה בטעינת שאלות אמינות: {e}")
        return pd.DataFrame()


# ============================================================
# Quick Quiz (נכון/לא נכון) — לוגיקה חדשה
# ============================================================
def get_quick_quiz_questions(count=50, focus_trait=None):
    """
    שאלון מהיר נכון/לא נכון:
    - מערבב שאלות HEXACO ושאלות תרחיש מאמינות
    - אם focus_trait מסופק, מתמקד רק בתכונה הזו
    
    הסולם: 2 ערכים בלבד (1 = לא נכון לגביי, 5 = נכון לגביי)
    """
    questions = []
    
    # שאלות HEXACO
    hexaco_df = load_hexaco_questions()
    if not hexaco_df.empty:
        if focus_trait and focus_trait != 'all':
            # סינון לפי תכונה
            trait_col = 'trait' if 'trait' in hexaco_df.columns else 'Trait'
            filtered = hexaco_df[hexaco_df[trait_col] == focus_trait]
            if not filtered.empty:
                hexaco_count = min(count, len(filtered))
                hexaco_sample = filtered.sample(n=hexaco_count)
            else:
                hexaco_sample = hexaco_df.sample(n=min(count // 2, len(hexaco_df)))
        else:
            # שאלון מאוזן בין כל התכונות
            hexaco_count = int(count * 0.7)  # 70% HEXACO
            hexaco_sample = pd.DataFrame(get_balanced_questions(hexaco_df, total_limit=hexaco_count))
        
        for _, row in hexaco_sample.iterrows() if hasattr(hexaco_sample, 'iterrows') else []:
            q_dict = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
            q_dict['quiz_format'] = 'binary'
            questions.append(q_dict)
    
    # שאלות תרחיש מאמינות (רק אם לא במצב focus)
    if not focus_trait or focus_trait == 'all':
        integrity_count = count - len(questions)
        if integrity_count > 0:
            int_df = load_integrity_questions_csv()
            if not int_df.empty:
                # מסננים החוצה את שאלות הלחץ והבקרה — רוצים רק תרחישים
                exclude_cats = {'polygraph', 'regret', 'honesty_meta'}
                cat_col = 'category' if 'category' in int_df.columns else 'trait'
                if cat_col in int_df.columns:
                    int_filtered = int_df[~int_df[cat_col].isin(exclude_cats)]
                    if not int_filtered.empty:
                        int_sample = int_filtered.sample(n=min(integrity_count, len(int_filtered)))
                        for _, row in int_sample.iterrows():
                            q_dict = row.to_dict()
                            q_dict['quiz_format'] = 'binary'
                            q_dict['is_scenario'] = True
                            # נוודא שיש 'trait' (לתאימות עם הקוד הקיים)
                            if 'trait' not in q_dict and 'category' in q_dict:
                                q_dict['trait'] = q_dict['category']
                            questions.append(q_dict)
    
    random.shuffle(questions)
    return questions[:count]


def _calculate_effective_score(user_answer, is_reverse):
    """מחשב את הציון האפקטיבי בתכונה (אחרי reverse)."""
    try:
        score = int(user_answer)
        if is_reverse:
            score = 6 - score
        return max(1, min(5, score))
    except Exception:
        return 3


def get_instant_tip(question_data, user_answer):
    """
    טיפ מיידי אחרי תשובה — מותאם לסולם המבחן (1-5 או בינארי).
    מסביר איך התשובה משפיעה על הציון, מה הטווח האידיאלי, ולמה.
    """
    analysis = get_decision_tree_analysis(question_data)
    if not analysis:
        return None
    
    trait = question_data.get('trait', question_data.get('category', ''))
    is_reverse = str(question_data.get('reverse', False)).strip().lower() in ['true', '1', '1.0', 'yes']
    is_binary = (st.session_state.get('test_type') == 'quick')
    
    trait_info = TRAIT_DIRECTIONS.get(trait)
    is_scenario = analysis.get('is_scenario', False)
    
    # === מקרה 1: תרחיש אמינות (לא HEXACO) ===
    if is_scenario:
        recommended = analysis['recommended']
        user_label = "נכון" if user_answer >= 4 else "לא נכון"
        is_match = (user_label == recommended)
        
        if is_match:
            header = "✅ **תשובה מצוינת!**"
        else:
            header = "💭 **כדאי לחשוב על זה:**"
        
        return (f"{header}\n\n"
                f"**סוג ההיגד:** תרחיש אמינות — {analysis['trait_he']}\n\n"
                f"**כיוון:** {analysis['direction_label']}\n\n"
                f"**תשובה אידיאלית:** {recommended}\n\n"
                f"**💡 למה:** {analysis['why']}\n\n"
                f"**🎯 ענית:** \"{user_label}\"" + (" — מושלם!" if is_match else ""))
    
    # === מקרה 2: שאלת HEXACO ===
    if not trait_info:
        return None
    
    # מחשב את הציון האפקטיבי בתכונה
    effective_score = _calculate_effective_score(user_answer, is_reverse)
    direction = trait_info['direction']
    trait_he = analysis['trait_he']
    low, high = IDEAL_RANGES.get(trait, (3.0, 5.0))
    
    # === בינארי: 2 או 4 בלבד ===
    if is_binary:
        recommended = analysis['recommended']
        user_label = "נכון" if user_answer >= 4 else "לא נכון"
        is_match = (user_label == recommended)
        
        if is_match:
            header = "✅ **תשובה מצוינת!**"
            verdict = f"בדיוק כמו שצריך — תשובה זו מקדמת את {trait_he} לכיוון הנכון."
        else:
            header = "💭 **תשובה לא אידיאלית**"
            verdict = f"תשובה זו מרחיקה אותך מהטווח האידיאלי של {trait_he} ({low}-{high})."
        
        return (f"{header}\n\n"
                f"**🔍 התכונה:** {trait_he} — {trait_info['label']}\n\n"
                f"**✏️ ההיגד:** {analysis.get('polarity_he', 'לא ברור')}\n\n"
                f"**🎯 תשובה אידיאלית:** {recommended}\n\n"
                f"**🎯 ענית:** {user_label}\n\n"
                f"**💡 הסבר:** {verdict}\n\n"
                f"**🏥 רלוונטיות לרפואה:** {trait_info['why_medical']}")
    
    # === סולם 1-5: דירוג מפורט ===
    # נחשב מה היה צריך להיות הציון האפקטיבי האידיאלי
    # אז נדע איזו תשובה (1-5) המשתמש היה צריך לתת
    target_effective = (low + high) / 2  # מרכז הטווח האידיאלי
    
    if is_reverse:
        # אם reverse, התשובה האידיאלית היא 6 - target
        ideal_answer_low = round(6 - high)
        ideal_answer_high = round(6 - low)
    else:
        ideal_answer_low = round(low)
        ideal_answer_high = round(high)
    
    # מקובע בין 1 ל-5
    ideal_answer_low = max(1, min(5, ideal_answer_low))
    ideal_answer_high = max(1, min(5, ideal_answer_high))
    if ideal_answer_low > ideal_answer_high:
        ideal_answer_low, ideal_answer_high = ideal_answer_high, ideal_answer_low
    
    answer_labels = {1: "בכלל לא", 2: "לא מסכים", 3: "נייטרלי", 4: "מסכים", 5: "מסכים מאוד"}
    user_label = answer_labels.get(user_answer, str(user_answer))
    
    # קביעת ה-verdict לפי הציון האפקטיבי
    # סובלנות של 0.5: ציון 4 ייחשב "בטווח" גם אם הטווח מתחיל ב-4.3
    tolerance = 0.5
    if (low - tolerance) <= effective_score <= (high + tolerance):
        # בטווח האידיאלי (כולל סובלנות)
        emoji = "🟢"
        if low <= effective_score <= high:
            header = "✅ **תשובה מצוינת — בדיוק בטווח האידיאלי!**"
        else:
            header = "✅ **תשובה טובה — קרוב מאוד לטווח האידיאלי**"
        verdict = (f"הציון שלך ב-{trait_he} מהשאלה הזו: **{effective_score}** "
                   f"(הטווח האידיאלי: {low}-{high}). שמור על הקצב הזה!")
    elif effective_score < low - tolerance:
        # מתחת לטווח
        gap = low - effective_score
        if direction == 'positive':
            if gap >= 2:
                emoji = "🔴"
                severity = "משמעותית מדי"
                header = "🔴 **תשובה רחוקה מהאידיאל**"
            else:
                emoji = "🟠"
                severity = "מעט"
                header = "🟠 **תשובה נמוכה מהאידיאל**"
            verdict = (f"הציון שלך ב-{trait_he}: **{effective_score}** — "
                       f"{severity} מתחת לטווח האידיאלי ({low}-{high}). "
                       f"זו תכונה {trait_info['label'][2:]} לרפואה — צריך ציון גבוה יותר.")
        else:  # mixed/balanced
            emoji = "🟠"
            header = "🟠 **תשובה נמוכה**"
            verdict = (f"הציון שלך: **{effective_score}**. הטווח האידיאלי הוא {low}-{high}.")
    else:  # effective_score > high
        gap = effective_score - high
        if direction == 'balanced' and trait == 'Emotionality':
            # רגשנות גבוהה מדי = חרדתיות
            emoji = "🔴"
            header = "🔴 **תשובה גבוהה מדי**"
            verdict = (f"הציון שלך ב-{trait_he}: **{effective_score}**. "
                       f"גבוה מדי — מצביע על חרדתיות יתר, שעלולה לעורר חשש "
                       f"לקושי בתפקוד תחת לחץ. הטווח האידיאלי: {low}-{high}.")
        elif direction == 'balanced':
            emoji = "🟠"
            header = "🟠 **תשובה גבוהה מהאידיאל**"
            verdict = (f"הציון שלך: **{effective_score}**, אבל הטווח האידיאלי הוא "
                       f"{low}-{high}. זו תכונה מאוזנת — קיצוניות לא רצויה.")
        else:
            # תכונה חיובית עם ציון מעל הטווח
            emoji = "🟡"
            header = "🟡 **תשובה גבוהה מאוד — זהירות מ-'מושלם מדי'**"
            verdict = (f"הציון שלך: **{effective_score}**. גבוה מאוד — "
                       f"אם תמיד תענה כך תיראה לא אותנטי. הטווח האידיאלי: {low}-{high}.")
    
    # מציע מה היה אידיאלי
    if ideal_answer_low == ideal_answer_high:
        ideal_suggestion = f"**{ideal_answer_low}** ({answer_labels[ideal_answer_low]})"
    else:
        ideal_suggestion = (f"**{ideal_answer_low}-{ideal_answer_high}** "
                            f"({answer_labels[ideal_answer_low]} עד {answer_labels[ideal_answer_high]})")
    
    reverse_note = ""
    if is_reverse:
        reverse_note = ("\n\n⚠️ **שים לב — זוהי שאלה הפוכה!** "
                        f"היגד ששולל את התכונה. ענית {user_answer} → "
                        f"זה תורגם לציון {effective_score} בתכונה.")
    
    tip = (f"{header}\n\n"
           f"**🔍 התכונה:** {trait_he} ({trait_info['label']})\n\n"
           f"**🎯 ענית:** {user_answer} ({user_label})\n\n"
           f"**📊 ציון אפקטיבי בתכונה:** {emoji} **{effective_score}/5**\n\n"
           f"**🎯 תשובה אידיאלית:** {ideal_suggestion}\n\n"
           f"**💡 ניתוח:** {verdict}\n\n"
           f"**🏥 רלוונטיות לרפואה:** {trait_info['why_medical']}"
           f"{reverse_note}")
    
    return tip


# ============================================================
# Session State Init
# ============================================================
def init_session_state():
    defaults = {
        'step': 'HOME',
        'test_type': None,
        'user_name': '',
        'questions': [],
        'current_q': 0,
        'responses': [],
        'hesitation_count': 0,
        'speed_flag_count': 0,
        'q_start_time': 0,
        'stress_active': False,
        'stress_start': 0,
        'stress_msg_index': 0,
        'reliability_score': None,
        'contradictions': [],
        'gemini_report': None,
        'claude_report': None,
        'results_data': None,
        'summary_data': None,
        'int_summary_data': None,
        'medical_fit': None,
        'fatigue_index': None,
        'practice_mode': False,
        'ai_ready': False,
        'user_id': str(uuid.uuid4()),
        'ai_status': 'pending',
        'balloons_shown': False,
        'focus_trait': 'all',
        'last_tip': None,
        'last_tip_time': 0,
        'ai_future': None,
        'ai_submitted_at': 0,
        'decision_tree_mode': False,
        'tree_step': 1,
        'tree_answer_trait': None,
        'tree_answer_direction': None,
        'tree_answer_polarity': None,
        'haifa_simulation': True,
        'haifa_video_enabled': False,
        'fake_alert_active': False,
        'fake_alert_acknowledged': {},
        'video_responses': {},
        'video_start_time': 0,
        'db_save_status': None,
        'db_save_error': None,
        'test_finalized': False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ============================================================
# HOME Screen
# ============================================================
def render_home():
    st.markdown("""
    <div class="hero-section">
        <h1>🧠 Mednitai HEXACO</h1>
        <p class="hero-subtitle">מערכת הכנה חכמה למבדקי אישיות לקבלה לרפואה</p>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input("✍️ מה השם שלך?", value=st.session_state.get('user_name', ''),
                          placeholder="הכנס את שמך המלא ולחץ Enter")
    st.session_state.user_name = name
    is_name_valid = bool(name.strip())

    if not is_name_valid:
        st.warning("⚠️ הקלד את שמך למעלה ולחץ Enter כדי לפתוח את המבדקים.")
    else:
        st.success(f"✅ שלום {name}! בחר את סוג המבדק:")
        
        tab_haifa, tab_quick, tab_full, tab_archive = st.tabs([
            "🏥 חיפה — תרגול",
            "🎓 בן גוריון — מהיר", 
            "📘 בר אילן — מלאים",
            "📜 ההיסטוריה שלי"
        ])
        
        # ===== Tab 0: תרגול חיפה (חדש!) =====
        with tab_haifa:
            st.markdown("### 🏥 אוניברסיטת חיפה — סימולציה למבחן הקבלה")
            st.caption("מכון אדם מילא • 3 חלקים: משחקים → שאלון אמינות → שאלון AMPQ (אישיות)")
            st.markdown("""
            🎯 **מה זה?** סימולציה של מבחן הקבלה לרפואה בחיפה.
            
            🧠 **מה כולל?**
            - שאלות **HEXACO** + **אמינות** + **תרחישים** מעורבבות אקראית
            - **שאלות וידאו פתע** (3 דקות בעל פה — אתה תקליט את עצמך בנפרד)
            - **מסכי "אינך דובר אמת"** מתפרצים — כמו במבחן האמיתי
            - **לחץ זמן ושעון חול** במצב סימולציה
            """)
            
            st.markdown("---")
            
            col_a, col_b = st.columns(2)
            with col_a:
                haifa_length = st.radio(
                    "אורך הסימולציה:",
                    ["קצרה (40 שאלות + 2 וידאו — ~15 דקות)",
                     "בינונית (80 שאלות + 4 וידאו — ~30 דקות)",
                     "מלאה (140 שאלות + 6 וידאו — ~50 דקות)",
                     "🔥 סימולציית 300 (300 שאלות + 8 וידאו — ~75 דקות, מלא כמו במבחן)"],
                    key="haifa_length"
                )
            with col_b:
                haifa_mode = st.radio(
                    "מצב התרגול:",
                    ["🚨 סימולציה (לחץ זמן + מסכים מתפרצים)",
                     "📚 תרגול (ללא לחץ, ללא מסכים — עם טיפים)"],
                    key="haifa_mode"
                )
            
            st.write("")
            
            if "סימולציה" in haifa_mode:
                st.warning(
                    "🚨 **מצב סימולציה**: כל המנגנונים פעילים — לחץ זמן (8 שניות), "
                    "שעון חול, ומסכי 'אינך דובר אמת'. תכין את עצמך — זה כמו במבחן האמיתי."
                )
            else:
                st.info(
                    "📚 **מצב תרגול**: ללא לחץ זמן, ללא מסכים מתפרצים. "
                    "תקבל טיפ מיידי אחרי כל תשובה. מומלץ למתחילים."
                )
            
            st.write("")
            
            # צ'קבוקס להפעלת/כיבוי שאלות וידאו
            include_video = st.checkbox(
                "🎥 כלול שאלות וידאו בתרגול",
                value=False,
                key="haifa_include_video",
                help="במבחן חיפה של 2026 לא היו שאלות וידאו בפרק האישיות, אבל בשנים קודמות כן היו. "
                     "סמן אם תרצה להתאמן גם עליהן (תקליט את עצמך בנפרד על המכשיר)."
            )
            if include_video:
                st.caption("🎬 שאלות וידאו יופיעו באקראי במהלך התרגול. תצטרך להקליט את עצמך באפליקציית מצלמה.")
            else:
                st.caption("ℹ️ ללא וידאו — כמו במבחן חיפה האחרון (2026).")
            
            if st.button("🏥 התחל תרגול חיפה", key="btn_haifa", type="primary", use_container_width=True):
                start_haifa_test(haifa_length, "סימולציה" in haifa_mode, include_video)
        
        # ===== Tab 1: מבחן מהיר =====
        with tab_quick:
            st.markdown("### 🎓 אוניברסיטת בן גוריון — מבחן מהיר נכון / לא נכון")
            st.caption("פורמט בן גוריון: היגדים עם תשובת נכון/לא נכון")
            st.markdown("""
            🎯 **מה זה?** שאלון מהיר עם 2 תשובות בלבד (כן או לא) — מהיר, ממוקד, וקל ללמידה.
            
            🧠 **מה כלול?** שאלות HEXACO ושאלות תרחיש מבדק האמינות.
            """)
            
            col_a, col_b = st.columns(2)
            with col_a:
                quick_length = st.radio(
                    "אורך המבחן:",
                    ["מיני (20 שאלות — 5 דקות)",
                     "קצר (40 שאלות — 10 דקות)",
                     "רגיל (70 שאלות — 15 דקות)"],
                    key="quick_length"
                )
            with col_b:
                focus_options = {
                    'all': '🎲 כל התכונות (מאוזן)',
                    'Conscientiousness': '✅ רק מצפוניות (C)',
                    'Honesty-Humility': '🤝 רק כנות-ענווה (H)',
                    'Agreeableness': '💚 רק נעימות (A)',
                    'Emotionality': '💗 רק רגשנות (E)',
                    'Extraversion': '🌟 רק מוחצנות (X)',
                    'Openness to Experience': '🌀 רק פתיחות (O)',
                }
                focus_trait = st.selectbox(
                    "🎯 אימון ממוקד לתכונה:",
                    options=list(focus_options.keys()),
                    format_func=lambda x: focus_options[x],
                    key="focus_select"
                )
            
            practice_quick = st.checkbox(
                "📚 מצב תרגול — קבל טיפ מיידי אחרי כל תשובה",
                value=True,
                key="practice_quick"
            )
            
            decision_tree_mode = st.checkbox(
                "🧠 מצב 'עץ ההחלטה' — לפני התשובה תפעיל את שיטת מכון נועם בעצמך (זיהוי תכונה → חיובית/שלילית → מתחייב/נשלל). מומלץ למתחילים!",
                value=False,
                key="decision_tree_check"
            )
            
            if st.button("⚡ התחל מבחן מהיר", key="btn_quick", type="primary", use_container_width=True):
                st.session_state.practice_mode = practice_quick
                st.session_state.focus_trait = focus_trait
                st.session_state.decision_tree_mode = decision_tree_mode
                start_quick_test(quick_length, focus_trait)
        
        # ===== Tab 2: מבחנים מלאים =====
        with tab_full:
            st.markdown("### 📘 אוניברסיטת בר אילן — מבחנים מלאים (סולם 1-5)")
            st.caption("פורמט בר אילן: HEXACO ואמינות בנפרד (שני מבחנים נפרדים)")
            test_length = st.radio("⏱️ אורך המבדק:",
                                   ["קצר (תרגול: 36-76 שאלות)",
                                    "רגיל (מומלץ: 60-140 שאלות)",
                                    "מלא (סימולציה: 120-260 שאלות)"],
                                   horizontal=True)

            col1, col2, col3 = st.columns(3, gap="large")
            with col1:
                st.markdown("#### 🎯 HEXACO")
                st.caption("6 תכונות אישיות מרכזיות")
                if st.button("התחל HEXACO", key="btn_hexaco", type="primary", use_container_width=True):
                    start_test('hexaco', test_length)
            with col2:
                st.markdown("#### 🔍 אמינות")
                st.caption("בדיקת עקביות ויושרה")
                if st.button("התחל אמינות", key="btn_integrity", type="primary", use_container_width=True):
                    start_test('integrity', test_length)
            with col3:
                st.markdown("#### 🏥 משולב")
                st.caption("HEXACO + אמינות")
                if st.button("התחל משולב", key="btn_combined", type="primary", use_container_width=True):
                    start_test('combined', test_length)

            st.markdown("---")
            practice = st.checkbox("📚 מצב תרגול (ללא לחץ, עם הסברים)",
                                   value=st.session_state.get('practice_mode', False))
            st.session_state.practice_mode = practice
        
        # ===== Tab 3: היסטוריה =====
        with tab_archive:
            history = get_db_history(name)
            if history:
                st.markdown(f"### 📂 ההיסטוריה של {name}")
                for i, entry in enumerate(reversed(history)):
                    test_date = entry.get('test_date', 'N/A')
                    test_time = entry.get('test_time', '')
                    test_type_lbl = entry.get('test_type', 'HEXACO')
                    
                    with st.expander(f"📅 מבדק {test_type_lbl} — {test_date} {test_time}"):
                        results = entry.get('results', {})
                        if results:
                            try:
                                fig = get_radar_chart(results)
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True, 
                                                  key=f"hist_chart_{i}_{uuid.uuid4().hex[:8]}")
                            except Exception:
                                pass
                        report = entry.get('ai_report', '')
                        if isinstance(report, list):
                            t_gem, t_cld = st.tabs(["🤖 Gemini", "🩺 Claude"])
                            with t_gem:
                                st.markdown(html.escape(str(report[0])) if len(report) > 0 else "אין נתונים")
                            with t_cld:
                                st.markdown(html.escape(str(report[1])) if len(report) > 1 else "אין נתונים")
                        elif report:
                            st.markdown(html.escape(str(report)))
                        
                        # ===== תשובות וידאו (רק בתרגול חיפה) =====
                        video_responses = entry.get('video_responses', [])
                        if video_responses and isinstance(video_responses, list):
                            st.markdown("#### 🎥 תשובות הווידאו שלך")
                            for vidx, vr in enumerate(video_responses, 1):
                                if not isinstance(vr, dict):
                                    continue
                                vq = vr.get('question', 'שאלת וידאו')
                                va = vr.get('answer_text', '')
                                st.markdown(f"**🎬 שאלה {vidx}:** {html.escape(str(vq))}")
                                if va and va != '(דולג)':
                                    st.markdown(f"""
                                    <div style="background: #ccfbf1; padding: 10px; border-radius: 8px; 
                                                margin: 4px 0 12px 0; border-right: 3px solid #0d9488;">
                                        <span style="color: #134e4a;">{html.escape(str(va))}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.caption("(לא נכתב סיכום / דולג)")
            else:
                st.info("עדיין לא ביצעת מבדקים. עשה את הראשון כדי לראות את ההיסטוריה כאן!")

    st.markdown("---")
    with st.expander("🔐 גישת מנהל"):
        admin_pass = st.text_input("סיסמה", type="password", key="admin_pw")
        if st.button("כניסת מנהל", key="btn_admin", type="primary"):
            try:
                if admin_pass == st.secrets.get("ADMIN_PASS", st.secrets.get("ADMIN_USER", "")):
                    st.session_state.step = 'ADMIN_VIEW'
                    st.rerun()
                else:
                    st.error("סיסמה שגויה")
            except Exception:
                st.error("שגיאה בגישה למערכת")


def start_haifa_test(length_label, is_simulation, include_video=False):
    """
    התחלת תרגול חיפה — שאלון מעורב + (אופציונלי) שאלות וידאו + מסכי "אינך דובר אמת".
    is_simulation: True = מצב סימולציה (לחץ + מסכים), False = מצב תרגול (רגוע)
    include_video: True = כלול שאלות וידאו (כמו אשתקד), False = בלי (כמו 2026)
    """
    if "300" in length_label:
        count, video_count = 300, 8
    elif "קצרה" in length_label:
        count, video_count = 40, 2
    elif "בינונית" in length_label:
        count, video_count = 80, 4
    else:
        count, video_count = 140, 6
    
    # אם המשתמש כיבה וידאו — אפס את כמות שאלות הווידאו
    if not include_video:
        video_count = 0
    
    st.session_state.test_type = 'haifa'
    st.session_state.haifa_simulation = is_simulation
    st.session_state.haifa_video_enabled = include_video
    st.session_state.practice_mode = not is_simulation  # תרגול = ללא לחץ
    st.session_state.current_q = 0
    st.session_state.responses = []
    st.session_state.hesitation_count = 0
    st.session_state.speed_flag_count = 0
    st.session_state.stress_active = False
    st.session_state.fake_alert_active = False
    st.session_state.fake_alert_acknowledged = {}
    st.session_state.video_responses = {}  # {q_index: text}
    st.session_state.q_start_time = time.time()
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.fatigue_index = None
    st.session_state.ai_status = 'pending'
    st.session_state.balloons_shown = False
    st.session_state.test_finalized = False
    st.session_state.last_tip = None
    
    try:
        questions = get_haifa_questions(count=count, video_count=video_count)
        if not questions:
            st.error("לא נמצאו שאלות. בדוק שקבצי ה-CSV נמצאים בתיקיה.")
            return
        st.session_state.questions = questions
        st.session_state.step = 'QUIZ'
        st.rerun()
    except Exception as e:
        st.error(f"שגיאה בטעינת שאלות: {e}")


def start_quick_test(length_label, focus_trait):
    """התחלת מבחן מהיר נכון/לא נכון."""
    if "מיני" in length_label:
        count = 20
    elif "קצר" in length_label:
        count = 40
    else:
        count = 70
    
    st.session_state.test_type = 'quick'
    st.session_state.current_q = 0
    st.session_state.responses = []
    st.session_state.hesitation_count = 0
    st.session_state.speed_flag_count = 0
    st.session_state.stress_active = False
    st.session_state.q_start_time = time.time()
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.fatigue_index = None
    st.session_state.ai_ready = False
    st.session_state.ai_status = 'pending'
    st.session_state.balloons_shown = False
    st.session_state.test_finalized = False
    st.session_state.last_tip = None
    
    try:
        questions = get_quick_quiz_questions(count=count, focus_trait=focus_trait)
        if not questions:
            st.error("לא נמצאו שאלות. בדוק שקבצי ה-CSV נמצאים בתיקיה.")
            return
        st.session_state.questions = questions
        st.session_state.step = 'QUIZ'
        st.rerun()
    except Exception as e:
        st.error(f"שגיאה בטעינת שאלות: {e}")


def start_test(test_type, test_length):
    st.session_state.test_type = test_type
    st.session_state.current_q = 0
    st.session_state.responses = []
    st.session_state.hesitation_count = 0
    st.session_state.speed_flag_count = 0
    st.session_state.stress_active = False
    st.session_state.stress_msg_index = random.randint(0, len(STRESS_MESSAGES) - 1)
    st.session_state.q_start_time = time.time()
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.fatigue_index = None
    st.session_state.ai_ready = False
    st.session_state.ai_status = 'pending'
    st.session_state.balloons_shown = False
    st.session_state.test_finalized = False
    st.session_state.last_tip = None

    try:
        if test_type == 'hexaco':
            df = load_hexaco_questions()
            if "קצר" in test_length: count = 36
            elif "רגיל" in test_length: count = 60
            else: count = 120
            st.session_state.questions = get_balanced_questions(df, total_limit=count)

        elif test_type == 'integrity':
            if "קצר" in test_length: count = 60
            elif "רגיל" in test_length: count = 100
            else: count = 140
            st.session_state.questions = get_integrity_questions(count=count)

        elif test_type == 'combined':
            df = load_hexaco_questions()
            if "קצר" in test_length: hex_c, int_c = 36, 40
            elif "רגיל" in test_length: hex_c, int_c = 60, 80
            else: hex_c, int_c = 120, 140

            hexaco_q = get_balanced_questions(df, total_limit=hex_c)
            integrity_q = get_integrity_questions(count=int_c)
            combined = hexaco_q + integrity_q
            random.shuffle(combined)
            st.session_state.questions = combined

        st.session_state.step = 'QUIZ'
        st.rerun()
    except Exception as e:
        st.error(f"שגיאה בטעינת שאלות: {e}")


# ============================================================
# QUIZ Screen
# ============================================================
def _render_haifa_video_question(q_data, current):
    """
    מציג שאלת וידאו — טיימר חי + תיבת טקסט להתאמן בתשובה.
    הזמן והתשובה נשמרים, וכשהמשתמש לוחץ "סיום" עוברים לשאלה הבאה.
    """
    duration = q_data.get('duration_sec', 180)
    
    # התחלת טיימר
    if st.session_state.video_start_time == 0:
        st.session_state.video_start_time = time.time()
    
    elapsed = time.time() - st.session_state.video_start_time
    remaining = max(0, duration - int(elapsed))
    
    # רענון כל שנייה לעדכון הטיימר
    st_autorefresh(interval=1000, limit=int(duration) + 10, key=f"video_timer_{current}")
    
    # מציג כותרת מודגשת — עם דגש על שההקלטה צריכה להתחיל מיד
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                border-right: 5px solid #dc2626;
                border-radius: 14px;
                padding: 20px;
                margin: 15px 0;
                animation: pulse-warning 2s ease-in-out infinite;">
        <div style="font-size: 1.3rem; font-weight: 800; color: #991b1b; margin-bottom: 8px;">
            🎥 שאלת וידאו — שאלה {current + 1} מתוך {len(st.session_state.questions)}
        </div>
        <div style="color: #7f1d1d; font-size: 0.95rem; font-weight: 600;">
            ⚠️ <strong>הטיימר רץ עכשיו!</strong> פתח את אפליקציית המצלמה והתחל להקליט מיד —
            זמן הקריאה הוא חלק מהזמן הכולל. אין שהות למחשבה.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # טיימר גדול
    minutes = remaining // 60
    seconds = remaining % 60
    
    # צבע לפי הזמן
    progress = 1 - (remaining / duration)
    if progress < 0.5:
        timer_color = "#10b981"
    elif progress < 0.8:
        timer_color = "#f59e0b"
    else:
        timer_color = "#dc2626"
    
    st.markdown(f"""
    <div style="background: #f9fafb; border: 2px solid {timer_color};
                border-radius: 14px; padding: 20px; margin: 15px 0;
                text-align: center;">
        <div style="font-size: 0.9rem; color: #6b7280; margin-bottom: 5px;">⏱️ זמן נותר להקלטה</div>
        <div style="font-size: 3rem; font-weight: 800; color: {timer_color}; font-family: 'Rubik', sans-serif;">
            {minutes:02d}:{seconds:02d}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # השאלה
    st.markdown(f"""
    <div class="question-card">
        <div class="question-category">🎥 שאלת וידאו — קטגוריה: {q_data.get('category', '')}</div>
        <div class="question-text">{html.escape(str(q_data.get('q', '')))}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== סקציית הקלטה ידנית — מקוצר, בלי כפתור התחלה =====
    minutes_text = duration // 60
    seconds_text = duration % 60
    duration_text = f"{minutes_text}:{seconds_text:02d}"
    
    st.markdown(f"""
    <div style="background: #fef3c7; border-right: 5px solid #d97706;
                border-radius: 12px; padding: 14px 18px; margin: 12px 0;">
        <div style="font-size: 1rem; font-weight: 700; color: #78350f; margin-bottom: 8px;">
            🎬 איך להקליט (פתח את האפליקציה במקביל)
        </div>
        <div style="color: #78350f; font-size: 0.9rem; line-height: 1.6;">
            • <strong>Mac</strong>: Photo Booth (⌘+Space → "photo booth")<br>
            • <strong>Windows</strong>: אפליקציית "מצלמה" בתפריט התחל<br>
            • <strong>טלפון</strong>: אפליקציית מצלמה במצב וידאו<br>
            <span style="color: #9a3412;">🔒 הסרטון נשמר רק אצלך — לא נשלח לאינטרנט</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # תיבת טקסט להתשובה
    response_key = f"video_resp_{current}"
    user_response = st.text_area(
        "✍️ סיכום קצר של התשובה שלך (אחרי שהקלטת):",
        value=st.session_state.video_responses.get(current, ''),
        key=response_key,
        height=140,
        placeholder="כתוב כאן 2-3 משפטים על מה אמרת בהקלטה — זה יעזור לך לחזור ולשפר בפעם הבאה."
    )
    st.session_state.video_responses[current] = user_response
    
    # מעקב אחרי שמות קבצים (אופציונלי)
    filename_key = f"video_file_{current}"
    saved_filename = st.text_input(
        "📁 שם הקובץ ששמרת (אופציונלי, רק לעקוב):",
        value=st.session_state.video_responses.get(f"file_{current}", ''),
        key=filename_key,
        placeholder="למשל: haifa_video_q3_conflict.mov"
    )
    st.session_state.video_responses[f"file_{current}"] = saved_filename
    
    # טיפים — רק במצב תרגול
    is_practice = st.session_state.get('practice_mode', False)
    if is_practice:
        with st.expander("💡 טיפים לתשובה הזו", expanded=False):
            tips = q_data.get('tips_for_practice', [])
            for tip in tips:
                st.markdown(f"- {tip}")
    
    # כפתורי ניווט
    col_finish, col_skip = st.columns([2, 1])
    
    with col_finish:
        if st.button("✅ סיימתי / עבור לשאלה הבאה",
                     key=f"video_finish_{current}",
                     use_container_width=True, type="primary"):
            # שומרים את התשובה ב-responses
            st.session_state.responses.append({
                'question_index': current,
                'question': str(q_data.get('q', '')),
                'answer': 0,  # אין ציון מספרי לשאלת וידאו
                'response_time': round(time.time() - st.session_state.video_start_time, 2) if st.session_state.video_start_time > 0 else 0,
                'wpm_threshold': 0,
                'is_too_fast': False,
                'is_hesitation': False,
                'trait': q_data.get('category', 'video'),
                'reverse': False,
                'is_stress_meta': False,
                'category': q_data.get('category', 'video'),
                'is_video': True,
                'video_response_text': user_response,
                'video_filename': saved_filename,  # שם הקובץ ששמר אצלו
            })
            st.session_state.current_q += 1
            st.session_state.video_start_time = 0
            st.session_state.q_start_time = time.time()
            st.rerun()
    
    with col_skip:
        if st.button("⏭️ דלג", key=f"video_skip_{current}",
                     use_container_width=True, type="secondary"):
            st.session_state.responses.append({
                'question_index': current,
                'question': str(q_data.get('q', '')),
                'answer': 0,
                'response_time': 0,
                'is_video': True,
                'video_response_text': '(דולג)',
                'trait': q_data.get('category', 'video'),
                'category': q_data.get('category', 'video'),
            })
            st.session_state.current_q += 1
            st.session_state.video_start_time = 0
            st.session_state.q_start_time = time.time()
            st.rerun()


def _render_fake_detection_screen(current_q, ack_key):
    """
    מציג מסך "אינך דובר אמת" — מתפרץ באמצע השאלון.
    דורש אישור משתמש כדי להמשיך.
    """
    # בוחר הודעה אקראית
    if 'haifa_fake_msg_idx' not in st.session_state or st.session_state.get('last_fake_q') != current_q:
        st.session_state.haifa_fake_msg_idx = random.randint(0, len(HAIFA_FAKE_DETECTION_MESSAGES) - 1)
        st.session_state.last_fake_q = current_q
    
    msg = HAIFA_FAKE_DETECTION_MESSAGES[st.session_state.haifa_fake_msg_idx]
    
    st.markdown(f"""
    <div class="stress-screen">
        <div class="stress-icon">{msg['icon']}</div>
        <div class="stress-title">{msg['title']}</div>
        <div class="stress-detail">{msg['detail']}</div>
        <div class="stress-warning-bar">🔒 מערכת זיהוי אי-עקביות פעילה</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    if st.button(f"✓ {msg['cta']}",
                 key=f"fake_ack_{current_q}",
                 use_container_width=True, type="primary"):
        st.session_state.fake_alert_acknowledged[ack_key] = True
        st.session_state.q_start_time = time.time()  # מאפסים טיימר
        st.rerun()


def _render_timer_visual(elapsed_seconds, show_warning=True):
    """
    מצייר שעון חול SVG שמתרוקן עם הזמן.
    מציג גם הודעת אזהרה אחרי 8 שניות (אם show_warning=True).
    """
    THRESHOLD_WARN = 8
    THRESHOLD_MAX = 15
    
    progress = min(1.0, elapsed_seconds / THRESHOLD_MAX)
    top_fill = max(0, 1 - progress)
    bottom_fill = progress
    
    # צבע לפי הזמן
    if elapsed_seconds < 3:
        sand_color = "#10b981"
        bg_color = "#d1fae5"
        status_text = "✅ קח את הזמן שלך"
        status_color = "#065f46"
    elif elapsed_seconds < 6:
        sand_color = "#f59e0b"
        bg_color = "#fef3c7"
        status_text = "⏱️ מתקרב לסיום זמן הקריאה"
        status_color = "#92400e"
    elif elapsed_seconds < THRESHOLD_WARN:
        sand_color = "#f97316"
        bg_color = "#ffedd5"
        status_text = "⚠️ קצת איטי — תכף יסומן כהיסוס"
        status_color = "#9a3412"
    else:
        sand_color = "#ef4444"
        bg_color = "#fee2e2"
        status_text = f"🔴 איחור! ({elapsed_seconds}s) — נרשם כהיסוס"
        status_color = "#991b1b"
    
    top_height = 60 * top_fill
    bottom_height = 60 * bottom_fill
    shake_class = "shake-animation" if elapsed_seconds >= THRESHOLD_WARN else ""
    
    # ID יחיד לכל clipPath כדי למנוע התנגשויות
    cid = f"hg{elapsed_seconds}"
    
    # מציג טפטוף רק אם החול עדיין נופל (בערך באמצע)
    drop_visible = "1" if 0.05 < progress < 0.95 else "0"
    
    # SVG נקי בלבד — בלי <style> מוטמע!
    svg_html = (
        f'<div class="hourglass-container {shake_class}" style="background: {bg_color};">'
        f'<svg width="80" height="120" viewBox="0 0 100 150" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="M 15 10 L 85 10 L 85 25 L 55 70 L 55 80 L 85 125 L 85 140 L 15 140 L 15 125 L 45 80 L 45 70 L 15 25 Z" '
        f'fill="none" stroke="#374151" stroke-width="3" stroke-linejoin="round"/>'
        f'<defs>'
        f'<clipPath id="top-{cid}"><path d="M 18 13 L 82 13 L 82 25 L 52 68 L 48 68 L 18 25 Z"/></clipPath>'
        f'<clipPath id="bot-{cid}"><path d="M 48 82 L 52 82 L 82 125 L 82 137 L 18 137 L 18 125 Z"/></clipPath>'
        f'</defs>'
        f'<rect x="15" y="{13 + 60 * progress}" width="70" height="{top_height}" '
        f'fill="{sand_color}" clip-path="url(#top-{cid})"/>'
        f'<rect x="15" y="{137 - bottom_height}" width="70" height="{bottom_height}" '
        f'fill="{sand_color}" clip-path="url(#bot-{cid})"/>'
        f'<circle cx="50" cy="80" r="2" fill="{sand_color}" opacity="{drop_visible}">'
        f'<animate attributeName="cy" from="72" to="88" dur="0.6s" repeatCount="indefinite"/>'
        f'</circle>'
        f'<line x1="10" y1="142" x2="90" y2="142" stroke="#374151" stroke-width="3" stroke-linecap="round"/>'
        f'<line x1="10" y1="8" x2="90" y2="8" stroke="#374151" stroke-width="3" stroke-linecap="round"/>'
        f'</svg>'
        f'<div class="hourglass-info">'
        f'<div class="hourglass-num" style="color: {status_color};">'
        f'{elapsed_seconds}<span class="hourglass-num-unit"> שניות</span>'
        f'</div>'
        f'<div class="hourglass-status" style="color: {status_color};">{status_text}</div>'
        f'</div>'
        f'</div>'
    )
    
    st.markdown(svg_html, unsafe_allow_html=True)
    
    # הודעת אזהרה אחרי 8 שניות
    if show_warning and elapsed_seconds >= THRESHOLD_WARN:
        st.markdown(
            '<div class="timer-warning-box">'
            '⚠️ <strong>שים לב:</strong> עליך לענות מהר יותר! היסוס יתר נרשם במערכת.'
            '</div>',
            unsafe_allow_html=True
        )


def render_quiz():
    questions = st.session_state.questions
    current = st.session_state.current_q
    total = len(questions)

    if current >= total:
        finish_test_fast()
        return

    q_data = questions[current]
    is_stress = str(q_data.get('is_stress_meta', '')).strip().lower() in ["1", "1.0", "true"]
    is_quick = (st.session_state.test_type == 'quick')
    is_haifa = (st.session_state.test_type == 'haifa')
    is_haifa_simulation = is_haifa and st.session_state.get('haifa_simulation', True)
    
    # ===== Haifa: בדיקת הזרקת פולו-אפ וידאו (פעם אחת לפני כל שאלה רגילה) =====
    # רק אם המשתמש הפעיל שאלות וידאו!
    if (is_haifa and st.session_state.get('haifa_video_enabled', False) and
        q_data.get('quiz_format') != 'haifa_video' and 
        not st.session_state.get(f'followup_check_done_{current}', False)):
        # מסמן שעשינו את הבדיקה (כדי לא לחזור על זה ברענון)
        st.session_state[f'followup_check_done_{current}'] = True
        
        already_injected = st.session_state.get('followup_categories_used', set())
        cat, video_q = should_inject_followup_video(
            st.session_state.responses, current, already_injected
        )
        
        if video_q is not None:
            # מוסיפים את הקטגוריה לרשימה (כדי לא לחזור עליה)
            if 'followup_categories_used' not in st.session_state:
                st.session_state.followup_categories_used = set()
            st.session_state.followup_categories_used.add(cat)
            
            # מזריקים את שאלת הפולו-אפ למיקום הנוכחי
            st.session_state.questions.insert(current, video_q)
            st.rerun()
    
    # ===== Haifa: שאלת וידאו =====
    if is_haifa and q_data.get('quiz_format') == 'haifa_video':
        _render_haifa_video_question(q_data, current)
        return
    
    # ===== Haifa: מסך "אינך דובר אמת" (פתע, רק בסימולציה) =====
    if is_haifa_simulation and not st.session_state.practice_mode:
        # בודקים אם להציג מסך — רק פעם אחת לכל שאלה
        ack_key = f"fake_q{current}"
        if (not st.session_state.fake_alert_acknowledged.get(ack_key) and
            should_inject_fake_detection(st.session_state.responses, current)):
            _render_fake_detection_screen(current, ack_key)
            return

    # ===== מסך לחץ — רק במבחנים מלאים, לא במהיר =====
    if is_stress and not st.session_state.practice_mode and not is_quick and not is_haifa:
        # רענון אוטומטי רק במסך הלחץ — חכם!
        st_autorefresh(interval=1000, limit=20, key=f"stress_timer_{current}")
        
        if st.session_state.get('stress_completed_q') != current:
            if not st.session_state.stress_active:
                st.session_state.stress_active = True
                st.session_state.stress_start = time.time()
                st.session_state.stress_msg_index = random.randint(0, len(STRESS_MESSAGES) - 1)

            stress_elapsed = time.time() - st.session_state.stress_start
            remaining = max(0, 15 - int(stress_elapsed))

            if remaining > 0:
                msg = STRESS_MESSAGES[st.session_state.stress_msg_index]
                st.markdown(f"""
                <div class="stress-screen">
                    <div class="stress-icon">{msg['icon']}</div>
                    <div class="stress-title">{msg['title']}</div>
                    <div class="stress-detail">{msg['detail']}</div>
                    <div class="stress-timer">{remaining}</div>
                    <div class="stress-warning-bar">🔒 {msg['bar']}</div>
                </div>
                """, unsafe_allow_html=True)
                return
            else:
                st.session_state.stress_active = False
                st.session_state.stress_completed_q = current
                st.session_state.q_start_time = time.time()

    # ===== Smart Auto-Refresh — רק כשממתינים לתשובה =====
    # רענון כל 1.5 שניות (במקום כל שנייה) — מקל על העומס משמעותית.
    # limit=60 כי אין סיבה לרענן שאלה אחת יותר מ-90 שניות.
    # במצב תרגול (ללא לחץ זמן) — אין צורך ברענון בכלל!
    if not st.session_state.practice_mode:
        st_autorefresh(interval=1500, limit=60, key=f"quiz_timer_{current}")
    
    # מחושב פעם אחת — נשתמש בו לתצוגה ולהתראה
    elapsed = time.time() - st.session_state.q_start_time
    elapsed_int = int(elapsed)
    
    # ===== Progress & Header =====
    st.progress(current / total)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write(f"שאלה **{current + 1}** מתוך **{total}**")
    with col2:
        if not st.session_state.practice_mode:
            st.caption(f"⚡ {st.session_state.hesitation_count} היסוסים | 🏎️ {st.session_state.speed_flag_count} מהירים")
    
    # ===== Hourglass Timer + Warning =====
    # מציג את שעון החול רק כשיש לחץ זמן (לא במצב תרגול).
    # במצב תרגול אין רענון אוטומטי, אז השעון ממילא לא יזוז — מסתירים אותו.
    if not st.session_state.practice_mode:
        _render_timer_visual(elapsed_int, show_warning=True)

    # ===== Question Card =====
    q_text = q_data.get('q', q_data.get('question', q_data.get('text', 'שאלה חסרה')))
    q_category = q_data.get('trait', q_data.get('category', ''))
    
    # תרגום שם התכונה לעברית להצגה
    q_category_display = TRAIT_DICT.get(str(q_category), str(q_category))

    st.markdown(f"""
    <div class="question-card">
        <div class="question-category">{html.escape(str(q_category_display))}</div>
        <div class="question-text">{html.escape(str(q_text))}</div>
    </div>
    """, unsafe_allow_html=True)

    # ===== Answer Buttons =====
    if is_quick:
        # === Mode C: Decision Tree Practice ===
        # אם הופעל מצב עץ ההחלטה — מציג את שלבי החשיבה לפני התשובה הסופית
        if st.session_state.get('decision_tree_mode', False):
            _render_decision_tree_ui(q_data, current, is_stress)
        else:
            # מצב רגיל: 2 כפתורים
            # FIXED: מיפוי לא-קיצוני — נכון=4, לא נכון=2 (לא 5/1!)
            col_no, col_yes = st.columns(2)
            if col_no.button("❌ לא נכון לגביי", key=f"ans_no_{current}",
                             use_container_width=True, type="secondary"):
                _handle_answer(q_data, 2, current, is_stress)
            if col_yes.button("✅ נכון לגביי", key=f"ans_yes_{current}",
                              use_container_width=True, type="secondary"):
                _handle_answer(q_data, 4, current, is_stress)
    else:
        # 5 כפתורים רגילים
        options = [("בכלל לא", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)]
        cols = st.columns(5)
        for i, (label, val) in enumerate(options):
            if cols[i].button(f"{val} — {label}", key=f"ans_{current}_{val}",
                              use_container_width=True, type="secondary"):
                _handle_answer(q_data, val, current, is_stress)

    # ===== Instant Tip (רק במצב תרגול) =====
    if st.session_state.practice_mode and st.session_state.last_tip:
        # מציגים את הטיפ של השאלה הקודמת
        st.markdown(f'<div class="instant-tip">{st.session_state.last_tip}</div>',
                    unsafe_allow_html=True)

    # ===== Back Button =====
    if current > 0:
        if st.button("⬅️ חזור לשאלה הקודמת", key=f"back_btn_{current}", type="secondary"):
            st.session_state.current_q -= 1
            if st.session_state.responses:
                st.session_state.responses.pop()
            st.session_state.q_start_time = time.time()
            st.session_state.last_tip = None
            _reset_tree_state()
            st.rerun()


def _reset_tree_state():
    """מאפס את מצב עץ ההחלטה לשאלה הבאה."""
    st.session_state.tree_step = 1
    st.session_state.tree_answer_trait = None
    st.session_state.tree_answer_direction = None
    st.session_state.tree_answer_polarity = None


# תוויות כיווני תכונות לתצוגה
_DIR_LABELS = {
    'positive': '✅ חיובית',
    'balanced': '⚖️ מאוזנת',
    'negative': '🔴 שלילית',
    'unknown': 'לא ברור',
}


def _render_decision_tree_ui(q_data, current, is_stress):
    """
    מצב עץ ההחלטה (C) — המשתמש עובר 4 שלבים לפני התשובה:
    שלב 1: זיהוי התכונה
    שלב 2: חיובית/שלילית/מאוזנת לרפואה
    שלב 3: מתחייב/נשלל בהיגד
    שלב 4: התשובה הסופית (תוצאה אוטומטית של 1-3, אבל המשתמש מאשר)
    """
    step = st.session_state.tree_step
    actual_trait = q_data.get('trait', q_data.get('category', ''))
    is_scenario = actual_trait not in TRAIT_DICT
    
    # מד התקדמות בעץ ההחלטה
    progress_text = f"🧠 שלב {step}/4 בעץ ההחלטה"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
                padding: 12px 16px; border-radius: 10px; margin-bottom: 15px;
                border-right: 4px solid #6a1b9a;">
        <div style="font-weight: 700; color: #4a148c;">{progress_text}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== שלב 1: זיהוי התכונה =====
    if step == 1:
        st.markdown("### 🔍 שלב 1: איזו תכונה ההיגד הזה בודק?")
        st.caption("חשוב על המשמעות של ההיגד ועל איזו תכונה הוא מתאר.")
        
        if is_scenario:
            # תרחיש אמינות
            scenario_options = {
                'theft': '🔒 גניבה / יושר עם רכוש',
                'drugs': '💊 התמכרויות / סמים',
                'gambling': '🎰 הימורים / סיכון',
                'unethical': '⚖️ אי-מוסריות / שחיתות',
                'termination': '🏢 פיטורים / קונפליקט בעבודה',
                'academic': '📚 יושר אקדמי / העתקות',
                'whistleblowing': '📢 דיווח על הפרות / יושרה',
                'feedback': '💬 קבלת ביקורת',
                'teamwork': '🤝 עבודת צוות',
            }
            options = list(scenario_options.values())
            options_keys = list(scenario_options.keys())
            
            choice = st.radio("בחר את הקטגוריה:", options, key=f"tree_scenario_{current}",
                              label_visibility="collapsed")
            chosen_idx = options.index(choice)
            chosen_key = options_keys[chosen_idx]
            
            if st.button("➡️ המשך לשלב 2", key=f"tree_next1_{current}", type="primary"):
                st.session_state.tree_answer_trait = chosen_key
                st.session_state.tree_step = 2
                st.rerun()
        else:
            # HEXACO
            options = list(TRAIT_DICT.values())
            options_keys = list(TRAIT_DICT.keys())
            
            choice = st.radio("בחר את התכונה:", options, key=f"tree_trait_{current}",
                              label_visibility="collapsed")
            chosen_idx = options.index(choice)
            chosen_key = options_keys[chosen_idx]
            
            if st.button("➡️ המשך לשלב 2", key=f"tree_next1_{current}", type="primary"):
                st.session_state.tree_answer_trait = chosen_key
                st.session_state.tree_step = 2
                st.rerun()
        
        # אפשרות לדלג ולענות ישר
        st.caption("💡 לא בטוח? ענה לפי האינסטינקט שלך:")
        col_skip_no, col_skip_yes = st.columns(2)
        if col_skip_no.button("דלג: ❌ לא נכון", key=f"skip_no_{current}", type="secondary"):
            _handle_answer(q_data, 2, current, is_stress)
            _reset_tree_state()
        if col_skip_yes.button("דלג: ✅ נכון", key=f"skip_yes_{current}", type="secondary"):
            _handle_answer(q_data, 4, current, is_stress)
            _reset_tree_state()
    
    # ===== שלב 2: חיובית/שלילית =====
    elif step == 2:
        chosen_trait = st.session_state.tree_answer_trait
        chosen_label = TRAIT_DICT.get(chosen_trait, chosen_trait)
        actual_label = TRAIT_DICT.get(actual_trait, actual_trait)
        
        # פידבק על שלב 1
        if chosen_trait == actual_trait:
            st.success(f"✅ זיהית נכון: **{chosen_label}**")
        else:
            st.warning(f"💭 בחרת: **{chosen_label}** • התכונה האמיתית: **{actual_label}**")
        
        st.markdown("### 📊 שלב 2: התכונה הזו חיובית או שלילית לרפואה?")
        st.caption("חשוב: לא 'האם זה נכון לגביי?' — אלא 'האם רופא צריך תכונה כזו?'")
        
        direction_options = [
            ('positive', '✅ חיובית מובהקת — רופא חייב את זה'),
            ('balanced', '⚖️ מאוזנת — צריך מידה מסוימת, לא קיצוני'),
            ('negative', '🔴 שלילית — רופא לא צריך את זה'),
        ]
        
        labels = [opt[1] for opt in direction_options]
        keys = [opt[0] for opt in direction_options]
        choice = st.radio("הכיוון:", labels, key=f"tree_dir_{current}", label_visibility="collapsed")
        chosen_dir = keys[labels.index(choice)]
        
        if st.button("➡️ המשך לשלב 3", key=f"tree_next2_{current}", type="primary"):
            st.session_state.tree_answer_direction = chosen_dir
            st.session_state.tree_step = 3
            st.rerun()
        
        if st.button("⬅️ חזור לשלב 1", key=f"tree_back2_{current}", type="secondary"):
            st.session_state.tree_step = 1
            st.rerun()
    
    # ===== שלב 3: מתחייב או נשלל =====
    elif step == 3:
        chosen_dir = st.session_state.tree_answer_direction
        actual_analysis = get_decision_tree_analysis(q_data)
        actual_dir = actual_analysis.get('direction', 'unknown') if actual_analysis else 'unknown'
        
        # פידבק על שלב 2
        if chosen_dir == actual_dir:
            st.success(f"✅ זיהית נכון: {_DIR_LABELS[chosen_dir]}")
        else:
            st.warning(f"💭 בחרת: {_DIR_LABELS.get(chosen_dir, '?')} • הכיוון האמיתי: {_DIR_LABELS.get(actual_dir, '?')}")
        
        st.markdown("### ✏️ שלב 3: ההיגד מתחייב או שולל את התכונה?")
        st.caption('דוגמה: "אני אדם מסודר" = מתחייב את המצפוניות. "אני נוטה לאחר" = שולל את המצפוניות.')
        
        polarity_options = [
            ('affirms', '➕ מתחייב — ההיגד אומר "כן, יש לי את התכונה"'),
            ('negates', '➖ שולל — ההיגד אומר "אין לי את התכונה" או מתאר התנהגות הפוכה'),
        ]
        labels = [opt[1] for opt in polarity_options]
        keys = [opt[0] for opt in polarity_options]
        choice = st.radio("ההיגד:", labels, key=f"tree_pol_{current}", label_visibility="collapsed")
        chosen_pol = keys[labels.index(choice)]
        
        if st.button("➡️ המשך לתשובה הסופית", key=f"tree_next3_{current}", type="primary"):
            st.session_state.tree_answer_polarity = chosen_pol
            st.session_state.tree_step = 4
            st.rerun()
        
        if st.button("⬅️ חזור לשלב 2", key=f"tree_back3_{current}", type="secondary"):
            st.session_state.tree_step = 2
            st.rerun()
    
    # ===== שלב 4: התשובה הסופית (לפי המטריצה של מכון נועם) =====
    elif step == 4:
        chosen_dir = st.session_state.tree_answer_direction
        chosen_pol = st.session_state.tree_answer_polarity
        
        # מטריצת ההחלטה של מכון נועם
        # תכונה חיובית + מתחייב = נכון
        # תכונה חיובית + נשלל   = לא נכון
        # תכונה שלילית + מתחייב = לא נכון
        # תכונה שלילית + נשלל   = נכון
        # תכונה מאוזנת — תלוי במשתמש (חיובית בכלליות אלא אם מדובר בקיצון)
        
        if chosen_dir == 'positive':
            recommended = 'נכון' if chosen_pol == 'affirms' else 'לא נכון'
        elif chosen_dir == 'negative':
            recommended = 'לא נכון' if chosen_pol == 'affirms' else 'נכון'
        else:  # balanced
            recommended = 'נכון' if chosen_pol == 'affirms' else 'לא נכון'
        
        st.markdown("### 🎯 שלב 4: התשובה לפי עץ ההחלטה")
        
        # מציג סיכום
        dir_emoji = {'positive': '✅', 'balanced': '⚖️', 'negative': '🔴'}.get(chosen_dir, '?')
        pol_emoji = '➕' if chosen_pol == 'affirms' else '➖'
        st.markdown(f"""
        <div style="background: #fff3e0; padding: 16px; border-radius: 10px; margin: 10px 0;">
        <strong>📋 סיכום ניתוח שלך:</strong><br>
        • שלב 2: התכונה {dir_emoji} {_DIR_LABELS.get(chosen_dir, '?')}<br>
        • שלב 3: ההיגד {pol_emoji} {'מתחייב' if chosen_pol == 'affirms' else 'שולל'} את התכונה<br>
        <br>
        <strong>🎯 לפי מטריצת מכון נועם → התשובה: <span style="color: #d84315; font-size: 1.2em;">{recommended}</span></strong>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("💡 אם אתה לא מסכים עם הניתוח שלך — תוכל לבחור אחרת. אבל זה הוא הניתוח **הלוגי** לפי שיטת מכון נועם.")
        
        col_no, col_yes = st.columns(2)
        if col_no.button("❌ לא נכון לגביי", key=f"tree_final_no_{current}",
                         use_container_width=True, type="secondary"):
            _handle_answer(q_data, 2, current, is_stress)
            _reset_tree_state()
        if col_yes.button("✅ נכון לגביי", key=f"tree_final_yes_{current}",
                          use_container_width=True, type="secondary"):
            _handle_answer(q_data, 4, current, is_stress)
            _reset_tree_state()
        
        if st.button("⬅️ חזור לשלב 3", key=f"tree_back4_{current}", type="secondary"):
            st.session_state.tree_step = 3
            st.rerun()


def _handle_answer(q_data, val, current, is_stress):
    """מטפל בלחיצה על תשובה."""
    response_time = time.time() - st.session_state.q_start_time
    q_text = q_data.get('q', q_data.get('question', ''))
    
    wpm_threshold = calculate_dynamic_wpm_threshold(str(q_text))
    is_too_fast = response_time < wpm_threshold
    is_hesitation = response_time > (wpm_threshold * 4)

    if not st.session_state.practice_mode:
        if is_too_fast:
            st.session_state.speed_flag_count += 1
        if is_hesitation:
            st.session_state.hesitation_count += 1

    st.session_state.responses.append({
        'question_index': current,
        'question': str(q_text),
        'answer': int(val),
        'response_time': round(response_time, 2),
        'wpm_threshold': round(wpm_threshold, 2),
        'is_too_fast': is_too_fast,
        'is_hesitation': is_hesitation,
        'trait': q_data.get('trait', q_data.get('category', '')),
        'reverse': q_data.get('reverse', False),
        'is_stress_meta': is_stress,
        'category': q_data.get('category', q_data.get('trait', '')),
    })
    
    # יצירת טיפ מיידי במצב תרגול
    if st.session_state.practice_mode:
        tip = get_instant_tip(q_data, val)
        st.session_state.last_tip = tip
    else:
        st.session_state.last_tip = None

    st.session_state.current_q += 1
    st.session_state.q_start_time = time.time()
    st.session_state.stress_active = False
    # איפוס מצב עץ ההחלטה לשאלה הבאה
    st.session_state.tree_step = 1
    st.session_state.tree_answer_trait = None
    st.session_state.tree_answer_direction = None
    st.session_state.tree_answer_polarity = None
    st.rerun()


# ============================================================
# Background AI — FIXED: Future-based pattern (100% reliable)
# ============================================================
from concurrent.futures import ThreadPoolExecutor


@st.cache_resource
def _get_executor():
    """Singleton ThreadPoolExecutor — נשאר חי בין reruns."""
    return ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai_worker")


def _run_ai_pure(username, test_type, s_data, i_data, rel, cont, hes, hist,
                 firebase_creds=None):
    """
    פונקציה טהורה — לא נוגעת ב-st.session_state.
    מקבלת את כל הקלט כפרמטרים, מחזירה dict עם התוצאה.
    זו המפתח לתיקון: ה-thread לא מנסה לכתוב ל-session state יותר.
    """
    result = {
        'gemini': None,
        'claude': None,
        'status': 'done',
        'error': None,
        'saved_to_db': False,
    }
    
    try:
        g, c = None, None
        if test_type in ('hexaco', 'quick', 'haifa'):
            g, c = get_multi_ai_analysis(username, s_data, hist)
        elif test_type == 'integrity':
            g, c = get_integrity_ai_analysis(username, rel, cont, s_data, hist)
        elif test_type == 'combined':
            g, c = get_combined_ai_analysis(username, s_data, rel, cont, hist)
        
        result['gemini'] = g
        result['claude'] = c
        result['saved_to_db'] = True  # נשמר כבר ב-thread הראשי, לפני קריאת AI
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        result['gemini'] = f"שגיאה בהפקת ניתוח AI: {str(e)}"
    
    return result


def _check_ai_future():
    """
    בודק את ה-Future ב-session state — אם הוא מוכן, שולף את התוצאה.
    נקרא בכל rerun במסך התוצאות.
    """
    future = st.session_state.get('ai_future')
    if future is None:
        return
    
    if future.done():
        try:
            result = future.result(timeout=0.1)
            st.session_state.gemini_report = result.get('gemini')
            st.session_state.claude_report = result.get('claude')
            st.session_state.ai_status = result.get('status', 'done')
            st.session_state.ai_future = None  # ניקוי
        except Exception as e:
            st.session_state.gemini_report = f"שגיאה: {e}"
            st.session_state.ai_status = 'error'
            st.session_state.ai_future = None


def finish_test_fast():
    # ===== מניעת כפילות: אם כבר עיבדנו וסיימנו את המבחן הזה — עוברים ישר לתוצאות =====
    if st.session_state.get('test_finalized', False):
        st.session_state.step = 'RESULTS'
        st.rerun()
        return
    
    test_type = st.session_state.test_type
    responses = st.session_state.responses
    st.session_state.fatigue_index = calculate_fatigue_index(responses)
    
    is_binary = (test_type == 'quick')

    if test_type in ('hexaco', 'quick'):
        df_raw, summary_df = process_results(responses)
        st.session_state.results_data = df_raw
        st.session_state.summary_data = summary_df
        st.session_state.medical_fit = calculate_medical_fit(summary_df)
        
        # FIXED: שימוש בזיהוי סתירות חכם — לפי דמיון טקסט, לא לפי קטגוריה
        smart_contradictions = find_smart_contradictions(responses)
        st.session_state.contradictions = smart_contradictions
        
        # FIXED: חישוב אמינות חכם — לא מעניש על קיצוניות במבחן בינארי
        st.session_state.reliability_score = calculate_smart_reliability(
            responses, smart_contradictions, is_binary=is_binary
        )

    elif test_type == 'integrity':
        df_raw, summary_df = process_integrity_results(responses)
        st.session_state.results_data = df_raw
        st.session_state.summary_data = summary_df
        st.session_state.reliability_score = calculate_reliability_score(df_raw)
        # גם כאן — סתירות חכמות במקום הרגילות
        st.session_state.contradictions = find_smart_contradictions(responses)

    elif test_type == 'haifa':
        # תרגול חיפה — דומה ל-combined, מחלקים את התשובות:
        # 1. שאלות וידאו — מסכמים בנפרד (לא נכנסות לציון מספרי)
        # 2. שאלות HEXACO — מחושבות בקוד הסטנדרטי
        # 3. שאלות אמינות — מחושבות בקוד האמינות
        video_resp = [r for r in responses if r.get('is_video', False)]
        non_video = [r for r in responses if not r.get('is_video', False)]
        
        hexaco_traits = {'Conscientiousness', 'Honesty-Humility', 'Agreeableness',
                         'Emotionality', 'Extraversion', 'Openness to Experience'}
        hexaco_resp = [r for r in non_video if r.get('trait') in hexaco_traits]
        integrity_resp = [r for r in non_video if r.get('trait') not in hexaco_traits]
        
        summary_hex = pd.DataFrame()
        summary_int = pd.DataFrame()
        reliability = 0
        
        if hexaco_resp:
            _, summary_hex = process_results(hexaco_resp)
            st.session_state.medical_fit = calculate_medical_fit(summary_hex)
        if integrity_resp:
            df_int, summary_int = process_integrity_results(integrity_resp)
            reliability = calculate_reliability_score(df_int)
        
        # סתירות חכמות על כל התשובות הטקסטואליות (לא וידאו)
        contradictions = find_smart_contradictions(non_video)
        
        st.session_state.summary_data = summary_hex
        st.session_state.int_summary_data = summary_int
        st.session_state.reliability_score = reliability
        st.session_state.contradictions = contradictions
        st.session_state.video_count = len(video_resp)
        
        # חישוב מדד יציבות תחת לחץ (חדש!)
        stability = calculate_pressure_stability(responses)
        st.session_state.pressure_stability = stability

    elif test_type == 'combined':
        hexaco_traits = {'Conscientiousness', 'Honesty-Humility', 'Agreeableness',
                         'Emotionality', 'Extraversion', 'Openness to Experience'}
        hexaco_resp = [r for r in responses if r.get('trait') in hexaco_traits]
        integrity_resp = [r for r in responses if r not in hexaco_resp]

        summary_hex = pd.DataFrame()
        summary_int = pd.DataFrame()
        reliability = 0
        contradictions = []

        if hexaco_resp:
            _, summary_hex = process_results(hexaco_resp)
            st.session_state.medical_fit = calculate_medical_fit(summary_hex)
        if integrity_resp:
            df_int, summary_int = process_integrity_results(integrity_resp)
            reliability = calculate_reliability_score(df_int)
        
        # סתירות חכמות על כל התשובות יחד
        contradictions = find_smart_contradictions(responses)

        st.session_state.summary_data = summary_hex
        st.session_state.int_summary_data = summary_int
        st.session_state.reliability_score = reliability
        st.session_state.contradictions = contradictions

    # ===== CRITICAL FIX: שמירה ל-DB מיד, לפני ה-AI =====
    # בעבר: השמירה רצה מ-thread רקע אחרי ה-AI. אם ה-AI נכשל — שום דבר לא נשמר.
    # עכשיו: שומרים מיד עם הציונים (בלי AI). ה-AI מתעדכן אחר כך, אבל הרשומה כבר קיימת.
    save_success = False
    save_error_msg = None
    try:
        s_dict = st.session_state.summary_data.to_dict() if hasattr(st.session_state.summary_data, 'to_dict') else st.session_state.summary_data
        i_dict = st.session_state.int_summary_data.to_dict() if hasattr(st.session_state.int_summary_data, 'to_dict') else st.session_state.int_summary_data
        rel = st.session_state.reliability_score
        hes = st.session_state.hesitation_count
        username = st.session_state.user_name
        
        # ניתוח ראשוני — "Pending AI"
        initial_report = "המבחן נשמר. הניתוח המעמיק יופיע ברגע שה-AI יסיים..."
        
        if test_type == 'haifa':
            video_count = st.session_state.get('video_count', 0)
            # אוספים את תשובות הווידאו לשמירה בהיסטוריה
            video_data = [
                {
                    'question': r.get('question', ''),
                    'answer_text': r.get('video_response_text', ''),
                    'filename': r.get('video_filename', ''),
                    'category': r.get('category', ''),
                }
                for r in responses if r.get('is_video', False)
            ]
            save_success = save_haifa_test_to_db(username, s_dict, initial_report,
                                                  hesitation=hes, video_count=video_count,
                                                  video_data=video_data)
        elif test_type in ('hexaco', 'quick'):
            save_success = save_to_db(username, s_dict, initial_report, hesitation=hes)
        elif test_type == 'integrity':
            save_success = save_integrity_test_to_db(username, s_dict, rel, initial_report, hesitation=hes)
        elif test_type == 'combined':
            save_success = save_combined_test_to_db(username, s_dict, i_dict, rel, initial_report, hesitation=hes)
    except Exception as e:
        save_error_msg = str(e)
    
    # נציג הודעה למשתמש על תוצאת השמירה (יוצג במסך התוצאות)
    st.session_state.db_save_status = 'success' if save_success else 'error'
    st.session_state.db_save_error = save_error_msg

    st.session_state.ai_status = 'processing'
    hist = []
    try:
        if test_type in ('hexaco', 'quick', 'haifa'):
            hist = get_db_history(st.session_state.user_name)
        elif test_type == 'integrity':
            hist = get_integrity_history(st.session_state.user_name)
        else:
            hist = get_combined_history(st.session_state.user_name)
    except Exception:
        pass

    # FIXED: שולח לעבודה דרך executor — לא thread גולמי
    # ה-Future נשמר ב-session state, ובכל rerun נבדוק אם הוא מוכן
    executor = _get_executor()
    future = executor.submit(
        _run_ai_pure,
        st.session_state.user_name,
        test_type,
        st.session_state.summary_data,
        st.session_state.int_summary_data,
        st.session_state.reliability_score,
        st.session_state.contradictions,
        st.session_state.hesitation_count,
        hist,
    )
    st.session_state.ai_future = future
    st.session_state.ai_submitted_at = time.time()

    # ===== מסמנים שהמבחן הזה כבר עובד ונשמר — מונע כפילות =====
    st.session_state.test_finalized = True

    st.session_state.step = 'RESULTS'
    st.rerun()


# ============================================================
# Quick Summary — 3 Key Takeaways
# ============================================================
def get_quick_takeaways(summary_df, contradictions, fatigue, hesitations, speed_flags):
    """מחזיר 3 דברים חשובים שכדאי לזכור לפעם הבאה."""
    takeaways = []
    
    # 1. תכונה הכי חלשה
    if summary_df is not None and hasattr(summary_df, 'iterrows') and not summary_df.empty:
        worst_trait = None
        worst_gap = 0
        for _, row in summary_df.iterrows():
            trait = row.get('Trait', row.get('trait', ''))
            score = float(row.get('Mean', row.get('avg_score', 0)))
            if trait in IDEAL_RANGES:
                low, high = IDEAL_RANGES[trait]
                if score < low:
                    gap = low - score
                elif score > high:
                    gap = score - high
                else:
                    gap = 0
                if gap > worst_gap:
                    worst_gap = gap
                    worst_trait = trait
        
        if worst_trait:
            trait_he = TRAIT_EXPLANATIONS.get(worst_trait, {}).get('name', worst_trait)
            takeaways.append({
                'icon': '🎯',
                'title': f'התמקד ב{trait_he}',
                'text': f'התכונה הזו הכי רחוקה מהטווח האידיאלי. כדאי לתרגל אותה במצב "אימון ממוקד".'
            })
    
    # 2. סתירות
    if contradictions and len(contradictions) > 2:
        takeaways.append({
            'icon': '⚠️',
            'title': f'זוהו {len(contradictions)} סתירות',
            'text': 'נסה לקרוא שאלות שדומות זו לזו ולוודא שאתה עקבי. שאלות "הפוכות" — אם ענית "כן" באחת, אולי צריך "לא" באחרת.'
        })
    
    # 3. מהירות / היסוס
    if speed_flags > 5:
        takeaways.append({
            'icon': '🐢',
            'title': 'האט קצת',
            'text': f'{speed_flags} תשובות נחשבו "מהירות מדי". המערכת חושדת בכך — קרא כל שאלה במלואה.'
        })
    elif hesitations > 8:
        takeaways.append({
            'icon': '⚡',
            'title': 'שמור על קצב',
            'text': f'{hesitations} היסוסים — לפעמים אתה חושב יותר מדי. סמוך על האינסטינקט הראשון.'
        })
    
    # 4. עייפות
    if fatigue and fatigue > 40:
        takeaways.append({
            'icon': '😴',
            'title': 'עייפות גבוהה',
            'text': 'התשובות שלך השתנו לקראת הסוף. במבחן האמיתי — נוח טוב לפני!'
        })
    
    # תמיד לפחות אחד
    if not takeaways:
        takeaways.append({
            'icon': '✨',
            'title': 'ביצוע מצוין!',
            'text': 'התוצאות שלך נראות מאוזנות. המשך לתרגל כדי לשמור על העקביות.'
        })
    
    return takeaways[:3]  # מקסימום 3


# ============================================================
# RESULTS Screen
# ============================================================
def _retry_save():
    """נסה לשמור שוב ל-DB אם הניסיון הראשון נכשל."""
    try:
        s_dict = st.session_state.summary_data.to_dict() if hasattr(st.session_state.summary_data, 'to_dict') else st.session_state.summary_data
        i_dict = st.session_state.int_summary_data.to_dict() if hasattr(st.session_state.int_summary_data, 'to_dict') else st.session_state.int_summary_data
        rel = st.session_state.reliability_score
        hes = st.session_state.hesitation_count
        username = st.session_state.user_name
        test_type = st.session_state.test_type
        
        report = "המבחן נשמר. הניתוח המעמיק יופיע ברגע שה-AI יסיים..."
        
        success = False
        if test_type == 'haifa':
            video_count = st.session_state.get('video_count', 0)
            responses = st.session_state.get('responses', [])
            video_data = [
                {
                    'question': r.get('question', ''),
                    'answer_text': r.get('video_response_text', ''),
                    'filename': r.get('video_filename', ''),
                    'category': r.get('category', ''),
                }
                for r in responses if r.get('is_video', False)
            ]
            success = save_haifa_test_to_db(username, s_dict, report,
                                             hesitation=hes, video_count=video_count,
                                             video_data=video_data)
        elif test_type in ('hexaco', 'quick'):
            success = save_to_db(username, s_dict, report, hesitation=hes)
        elif test_type == 'integrity':
            success = save_integrity_test_to_db(username, s_dict, rel, report, hesitation=hes)
        elif test_type == 'combined':
            success = save_combined_test_to_db(username, s_dict, i_dict, rel, report, hesitation=hes)
        
        if success:
            st.session_state.db_save_status = 'success'
            st.session_state.db_save_error = None
            st.rerun()
        else:
            st.session_state.db_save_status = 'error'
            st.session_state.db_save_error = "השמירה נכשלה שוב"
    except Exception as e:
        st.session_state.db_save_status = 'error'
        st.session_state.db_save_error = str(e)


def render_results():
    # FIXED: בודק את ה-Future בכל rerun — אם הוא מוכן, שולף את התוצאה
    _check_ai_future()
    
    name_safe = html.escape(st.session_state.user_name)
    st.markdown(f"""
    <div class="hero-section">
        <h1>📊 תוצאות המבדק</h1>
        <p class="hero-subtitle">שלום {name_safe} — הנה התוצאות שלך</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== משוב על שמירה ל-DB =====
    db_status = st.session_state.get('db_save_status')
    if db_status == 'success':
        st.success("✅ **המבחן נשמר בהיסטוריה שלך** — תוכל לחזור אליו בכל זמן מטאב 'ההיסטוריה שלי'")
    elif db_status == 'error':
        err = st.session_state.get('db_save_error', 'שגיאה לא ידועה')
        st.error(f"⚠️ **המבחן לא נשמר** — שגיאת חיבור למסד הנתונים: `{err}`\n\n"
                 f"התוצאות עדיין מוצגות כאן, אבל לא יישמרו בהיסטוריה. "
                 f"זו לא בעיה אצלך — זו תקלה במערכת. נסה ב-30 שניות.")
        if st.button("🔄 נסה לשמור שוב", key="retry_save"):
            _retry_save()

    # ===== 3 Quick Takeaways =====
    takeaways = get_quick_takeaways(
        st.session_state.get('summary_data'),
        st.session_state.get('contradictions', []),
        st.session_state.get('fatigue_index'),
        st.session_state.get('hesitation_count', 0),
        st.session_state.get('speed_flag_count', 0)
    )
    
    st.markdown("### 🎯 מה לקחת מהמבחן הזה")
    for t in takeaways:
        st.markdown(f"""
        <div class="summary-card">
            <h4>{t['icon']} {t['title']}</h4>
            <p>{t['text']}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== Metrics =====
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏥 התאמה", f"{st.session_state.get('medical_fit', 0)}%")
    c2.metric("🔒 אמינות", f"{st.session_state.get('reliability_score', 0)}")
    c3.metric("⚡ היסוסים", f"{st.session_state.get('hesitation_count', 0)}")

    fatigue = st.session_state.get('fatigue_index')
    if fatigue is not None:
        fatigue_label = "נמוכה" if fatigue < 20 else "בינונית" if fatigue < 40 else "גבוהה"
        c4.metric("😴 עייפות", f"{fatigue}% ({fatigue_label})")
    else:
        c4.metric("🏎️ מהירות", f"{st.session_state.get('speed_flag_count', 0)}")
    
    # ===== Pressure Stability — רק בתרגול חיפה =====
    stability = st.session_state.get('pressure_stability')
    if stability and stability.get('events', 0) > 0:
        st.markdown("---")
        st.markdown("### 🛡️ יציבות תחת לחץ")
        
        score = stability['score']
        # צבע לפי הציון
        if score >= 85:
            stab_color = "#10b981"
            stab_bg = "#d1fae5"
        elif score >= 70:
            stab_color = "#0d9488"
            stab_bg = "#ccfbf1"
        elif score >= 55:
            stab_color = "#f59e0b"
            stab_bg = "#fef3c7"
        else:
            stab_color = "#dc2626"
            stab_bg = "#fee2e2"
        
        st.markdown(f"""
        <div style="background: {stab_bg}; padding: 20px; border-radius: 14px; 
                    border-right: 5px solid {stab_color}; margin: 15px 0;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: {stab_color};">
                        {stability['summary']}
                    </div>
                    <div style="color: #555; margin-top: 6px; font-size: 0.95rem;">
                        זוהו {stability['events']} אירועי לחץ במהלך המבחן (וידאו, מטא, אזהרות)
                    </div>
                </div>
                <div style="font-size: 3rem; font-weight: 800; color: {stab_color}; 
                            font-family: 'Rubik', sans-serif;">
                    {score}<span style="font-size: 1rem;">/100</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # פירוט שינויים בתכונות (רק אם יש שינויים משמעותיים)
        changes = stability.get('changes', {})
        significant = {t: c for t, c in changes.items() if c['severity'] in ('high', 'medium')}
        
        if significant:
            with st.expander(f"📊 פירוט: {len(significant)} תכונות שהשתנו תחת לחץ", expanded=True):
                trait_names_he = {
                    'Conscientiousness': 'מצפוניות (C)',
                    'Honesty-Humility': 'כנות-ענווה (H)',
                    'Agreeableness': 'נעימות (A)',
                    'Emotionality': 'רגשנות (E)',
                    'Extraversion': 'מוחצנות (X)',
                    'Openness to Experience': 'פתיחות (O)',
                }
                
                for trait, change in significant.items():
                    trait_he = trait_names_he.get(trait, trait)
                    delta = change['delta']
                    arrow = "📈" if delta > 0 else "📉"
                    sev_icon = "🔴" if change['severity'] == 'high' else "🟠"
                    
                    direction = "עלה" if delta > 0 else "ירד"
                    abs_delta = abs(delta)
                    
                    st.markdown(f"""
                    <div style="background: #fff; padding: 14px; border-radius: 10px; 
                                margin: 8px 0; border-right: 3px solid {stab_color};">
                        <div style="font-weight: 700; color: #333;">
                            {sev_icon} {arrow} <strong>{trait_he}</strong>
                        </div>
                        <div style="color: #555; margin-top: 6px;">
                            לפני אירוע לחץ: <strong>{change['before']}</strong> → 
                            אחרי: <strong>{change['after']}</strong> 
                            ({direction} ב-{abs_delta:.1f})
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.info(
                    "💡 **מה זה אומר?** התכונות האלה השתנו אצלך תחת לחץ. "
                    "במבחן האמיתי — שים לב לסימני הלחץ אצלך (פוליגרף, וידאו, אזהרות) "
                    "ונסה לחזור למצב הרגיל לפני שאתה עונה."
                )
        else:
            st.success("✅ **לא היו שינויים משמעותיים** — האישיות שלך נשארה יציבה גם תחת לחץ. זה בדיוק מה שמחפשים.")

    if st.session_state.ai_status == 'done' and not st.session_state.balloons_shown:
        st.balloons()
        st.session_state.balloons_shown = True

    # FIXED: רענון רק כשמחכים ל-AI, וגם הצגת התקדמות יפה
    if st.session_state.ai_status == 'processing':
        elapsed = int(time.time() - st.session_state.get('ai_submitted_at', time.time()))
        # רענון אגרסיבי יותר כדי לתפוס את הסיום מהר
        st_autorefresh(interval=2000, limit=300, key="ai_polling")
        
        # מחוון התקדמות חזותי
        progress_pct = min(95, elapsed * 2)  # 50 שניות = 100%
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                    padding: 16px; border-radius: 12px; margin: 10px 0;
                    border-right: 4px solid #1976d2;">
            <div style="font-weight: 600; color: #0d47a1;">
                🤖 מנועי ה-AI מנתחים את התוצאות שלך... ({elapsed} שניות)
            </div>
            <div style="background: #fff; height: 8px; border-radius: 4px; margin-top: 8px; overflow: hidden;">
                <div style="background: linear-gradient(90deg, #1976d2, #42a5f5); 
                            height: 100%; width: {progress_pct}%; 
                            transition: width 0.5s ease;"></div>
            </div>
            <div style="font-size: 0.85rem; color: #555; margin-top: 8px;">
                💡 בינתיים אתה יכול לעיין בתוצאות, בלמידה ובהורדות. הניתוח יופיע אוטומטית.
            </div>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 תוצאות", "🤖 ניתוח AI", "📚 למידה", "📥 הורדות"])

    with tab1:
        _render_results_tab()
    with tab3:
        _render_learning_tab()
    with tab4:
        _render_downloads_tab()
    with tab2:
        if st.session_state.ai_status == 'processing':
            elapsed = int(time.time() - st.session_state.get('ai_submitted_at', time.time()))
            st.info(f"🤖 **ה-AI מנתח את התוצאות שלך ברקע... ({elapsed} שניות עברו)**\n\n"
                    f"זה לוקח בדרך כלל 30-90 שניות. הדוח יופיע כאן אוטומטית כשיהיה מוכן.\n\n"
                    f"💡 בינתיים תוכל לעיין בלשוניות אחרות — התוצאות, מדריך הלמידה, וההורדות זמינות עכשיו.")
        elif st.session_state.ai_status == 'error':
            st.error("❌ הייתה בעיה בהפקת הניתוח. כנראה שגיאה בחיבור ל-AI. בדוק את ה-API keys.")
            if st.session_state.get('gemini_report'):
                st.code(str(st.session_state.gemini_report))
        else:
            _render_ai_tab()

    st.markdown("---")
    if st.button("🏠 חזרה לדף הבית", use_container_width=True, type="primary"):
        # ביטול Future אם עדיין רץ
        f = st.session_state.get('ai_future')
        if f and not f.done():
            # לא מבטלים — נותנים לו להמשיך כדי שהתוצאה תישמר ב-DB
            pass
        for key in ['responses', 'results_data', 'summary_data', 'int_summary_data',
                    'gemini_report', 'claude_report', 'last_tip', 'ai_future']:
            if key in st.session_state:
                st.session_state[key] = None if 'data' in key or 'report' in key or 'tip' in key or 'future' in key else []
        st.session_state.ai_status = 'pending'
        st.session_state.balloons_shown = False
        st.session_state.test_finalized = False
        st.session_state.step = 'HOME'
        st.rerun()


def _render_results_tab():
    summary = st.session_state.get('summary_data')
    if summary is not None and hasattr(summary, 'empty') and not summary.empty:
        try:
            radar = get_radar_chart(summary)
            if radar:
                st.plotly_chart(radar, use_container_width=True)
        except Exception:
            pass
        try:
            bar = get_comparison_chart(summary)
            if bar:
                st.plotly_chart(bar, use_container_width=True)
        except Exception:
            pass

        st.markdown("### 📋 טבלת סיכום")
        display_df = summary.copy()
        trait_col = next((c for c in display_df.columns if str(c).lower() in ['trait', 'category']), None)
        if trait_col:
            display_df[trait_col] = display_df[trait_col].apply(lambda x: TRAIT_DICT.get(str(x), str(x)))
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    speed = st.session_state.get('speed_flag_count', 0)
    if speed > 3:
        st.warning(f"🏎️ **{speed} תשובות מהירות מדי** — תשובות מתחת לסף הקריאה הסביר.")

    contradictions = st.session_state.get('contradictions', [])
    responses = st.session_state.get('responses', [])

    if contradictions:
        st.markdown("### ⚠️ סתירות שזוהו")
        st.caption("המערכת מצאה זוגות של שאלות דומות שענית עליהן באופן שונה.")
        
        for c in contradictions:
            c_dict = c if isinstance(c, dict) else {'message': str(c)}
            sev = c_dict.get('severity', '')
            icon = "🔴" if sev == 'critical' else "🟠" if sev == 'high' else "🔵"
            msg = html.escape(str(c_dict.get('message', str(c))))
            
            sim = c_dict.get('similarity', 0)
            sim_pct = int(sim * 100) if sim else 0
            sim_label = f" • דמיון {sim_pct}%" if sim_pct else ""
            
            with st.expander(f"{icon} {msg}{sim_label}"):
                q1 = c_dict.get('q1', c_dict.get('question1', ''))
                q2 = c_dict.get('q2', c_dict.get('question2', ''))
                
                if q1 and q2:
                    a1 = c_dict.get('ans1', c_dict.get('answer1', '?'))
                    a2 = c_dict.get('ans2', c_dict.get('answer2', '?'))
                    
                    # תרגום הציון לתשובה ידידותית
                    def _label(v):
                        try:
                            v = int(v)
                            return {1: "בכלל לא", 2: "לא מסכים", 3: "נייטרלי", 
                                    4: "מסכים", 5: "מסכים מאוד"}.get(v, str(v))
                        except Exception:
                            return str(v)
                    
                    st.markdown(f"""
                    <div style="background: #fff3e0; padding: 12px; border-radius: 8px; margin: 8px 0;">
                    <strong>📌 שאלה 1:</strong><br>
                    <em style="font-size: 1.05em;">{html.escape(str(q1))}</em><br>
                    <span style="color: #d84315;">🔹 ענית: <strong>{a1} — {_label(a1)}</strong></span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="background: #e3f2fd; padding: 12px; border-radius: 8px; margin: 8px 0;">
                    <strong>📌 שאלה 2:</strong><br>
                    <em style="font-size: 1.05em;">{html.escape(str(q2))}</em><br>
                    <span style="color: #1565c0;">🔹 ענית: <strong>{a2} — {_label(a2)}</strong></span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    trait_he = TRAIT_DICT.get(c_dict.get('trait', ''), '')
                    if trait_he:
                        st.caption(f"💡 שתי השאלות שייכות ל-**{trait_he}** ואומרות דברים דומים — כדאי לוודא עקביות.")
                else:
                    # fallback ישן (לסתירות שמגיעות מקוד אחר)
                    st.markdown(f"_פרטים נוספים לא זמינים._")

    rel = st.session_state.get('reliability_score')
    if rel is not None:
        st.info(f"🔒 פירוש ציון האמינות ({rel}): {get_integrity_interpretation(rel)}")

    # ===== תשובות הווידאו — הצגת הסיכומים שכתבת =====
    responses = st.session_state.get('responses', [])
    video_responses = [r for r in responses if r.get('is_video', False)]
    
    if video_responses:
        st.markdown("---")
        st.markdown("### 🎥 תשובות הווידאו שלך")
        st.caption("כאן מרוכזים כל הסיכומים שכתבת לשאלות הווידאו — חזור אליהם כדי לשפר בפעם הבאה.")
        
        for i, vr in enumerate(video_responses, 1):
            question = vr.get('question', 'שאלת וידאו')
            answer_text = vr.get('video_response_text', '')
            filename = vr.get('video_filename', '')
            response_time = vr.get('response_time', 0)
            
            # כותרת ה-expander
            preview = answer_text[:40] + "..." if len(str(answer_text)) > 40 else answer_text
            if not preview or preview == '(דולג)':
                preview = "⏭️ דולג"
            
            with st.expander(f"🎬 שאלה {i}: {preview}"):
                st.markdown(f"""
                <div style="background: #fef3c7; padding: 14px; border-radius: 10px; margin: 8px 0;
                            border-right: 4px solid #d97706;">
                    <strong>❓ השאלה:</strong><br>
                    <em style="font-size: 1.05em; color: #78350f;">{html.escape(str(question))}</em>
                </div>
                """, unsafe_allow_html=True)
                
                if answer_text and answer_text != '(דולג)':
                    st.markdown(f"""
                    <div style="background: #ccfbf1; padding: 14px; border-radius: 10px; margin: 8px 0;
                                border-right: 4px solid #0d9488;">
                        <strong>✍️ הסיכום שכתבת:</strong><br>
                        <span style="color: #134e4a;">{html.escape(str(answer_text))}</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("לא כתבת סיכום לשאלה זו (דילגת או השארת ריק).")
                
                # מטא-דאטה
                meta_parts = []
                if response_time and response_time > 0:
                    mins = int(response_time) // 60
                    secs = int(response_time) % 60
                    meta_parts.append(f"⏱️ זמן: {mins}:{secs:02d}")
                if filename:
                    meta_parts.append(f"📁 קובץ: {filename}")
                if meta_parts:
                    st.caption(" • ".join(meta_parts))
        
        st.success(
            "💡 **טיפ:** קרא את הסיכומים שלך בקול. האם הם ברורים? האם הם עונים ישירות "
            "על השאלה? במבחן האמיתי תצטרך לדבר אותם בביטחון תוך 2-4 דקות."
        )


def _render_ai_tab():
    gemini = st.session_state.get('gemini_report')
    claude = st.session_state.get('claude_report')

    if gemini:
        st.markdown("### 🤖 ניתוח Gemini")
        st.markdown(f'<div class="question-card">{html.escape(str(gemini))}</div>',
                    unsafe_allow_html=True)
        try:
            g = create_token_gauge(str(gemini))
            if g:
                st.plotly_chart(g, use_container_width=True)
        except Exception:
            pass

    if claude:
        st.markdown("### 🧠 ניתוח Claude")
        st.markdown(f'<div class="question-card">{html.escape(str(claude))}</div>',
                    unsafe_allow_html=True)


def _render_learning_tab():
    summary = st.session_state.get('summary_data')
    st.markdown("### 📚 מדריך למידה אישי")

    if summary is not None and hasattr(summary, 'iterrows'):
        for _, row in summary.iterrows():
            trait = row.get('Trait', row.get('trait', ''))
            score = float(row.get('Mean', row.get('avg_score', 0)))
            if trait not in TRAIT_EXPLANATIONS:
                continue

            info = TRAIT_EXPLANATIONS[trait]
            low, high = IDEAL_RANGES.get(trait, (3.0, 5.0))

            if low <= score <= high:
                status = "✅ בטווח האידיאלי"
            elif score < low:
                status = "📉 מתחת לטווח"
            else:
                status = "📈 מעל הטווח"

            with st.expander(f"**{info['name']}** — {score:.1f} {status}"):
                st.markdown(f"**מהי?** {info['desc']}")
                st.markdown(f"**🏥 רלוונטיות:** {info['medical']}")
                if score < low:
                    st.markdown(f'<div class="learning-warning">💡 {info["tip_low"]}</div>',
                                unsafe_allow_html=True)
                elif score > high:
                    st.markdown(f'<div class="learning-tip">💡 {info["tip_high"]}</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown('<div class="learning-tip">✅ בטווח האידיאלי — שמור על זה!</div>',
                                unsafe_allow_html=True)
                st.caption(f"טווח אידיאלי: {low} — {high}")
    else:
        st.info("נתוני HEXACO מוצגים רק במבדקי HEXACO, מהיר ומשולב.")


def _render_downloads_tab():
    st.markdown("### 📥 הורדת דוחות")
    col1, col2 = st.columns(2)
    with col1:
        try:
            summary = st.session_state.get('summary_data')
            responses = st.session_state.get('responses', [])
            if summary is not None:
                pdf = create_pdf_report(summary, responses)
                if isinstance(pdf, bytes):
                    st.download_button("📄 הורד PDF", pdf,
                                       f"mednitai_{st.session_state.user_name}.pdf",
                                       "application/pdf", use_container_width=True, type="primary")
        except Exception as e:
            st.warning(f"שגיאה ב-PDF: {e}")
    with col2:
        try:
            responses = st.session_state.get('responses', [])
            if responses:
                excel = create_excel_download(responses)
                if isinstance(excel, bytes):
                    st.download_button("📊 הורד Excel", excel,
                                       f"mednitai_{st.session_state.user_name}.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       use_container_width=True, type="primary")
                else:
                    # האקסל החזיר טקסט שגיאה — נציג fallback ל-CSV
                    st.warning(f"⚠️ יצירת Excel נכשלה: {excel}")
                    try:
                        import io
                        df = pd.DataFrame(responses).fillna('')
                        csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📄 הורד CSV (במקום Excel)", csv_bytes,
                                           f"mednitai_{st.session_state.user_name}.csv",
                                           "text/csv", use_container_width=True, type="secondary")
                    except Exception as e2:
                        st.error(f"גם CSV נכשל: {e2}")
            else:
                st.info("אין תשובות לייצוא.")
        except Exception as e:
            st.warning(f"שגיאה ב-Excel: {e}")
            # fallback ל-CSV גם במקרה של חריגה
            try:
                import io
                responses = st.session_state.get('responses', [])
                if responses:
                    df = pd.DataFrame(responses).fillna('')
                    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📄 הורד CSV (במקום Excel)", csv_bytes,
                                       f"mednitai_{st.session_state.user_name}.csv",
                                       "text/csv", use_container_width=True, type="secondary")
            except Exception:
                pass


# ============================================================
# ADMIN Screen (כמו שהיה)
# ============================================================
def render_admin():
    st.markdown("# 🔐 ממשק ניהול — Dashboard")
    if st.button("🏠 חזרה לדף הבית", type="primary"):
        st.session_state.step = 'HOME'
        st.rerun()
    st.markdown("---")

    try:
        all_tests = get_all_tests()
        if not all_tests:
            st.info("אין מבדקים במערכת")
            return

        st.markdown("### 📊 מדדי רוחב — כלל המערכת")
        total_tests = len(all_tests)
        unique_users = len(set(t.get('user_name', '') for t in all_tests))
        hesitation_vals = [t.get('hesitation_count', 0) for t in all_tests if t.get('hesitation_count') is not None]
        reliability_vals = [t.get('reliability_score', 0) for t in all_tests if t.get('reliability_score') is not None]
        avg_hesitation = sum(hesitation_vals) / len(hesitation_vals) if hesitation_vals else 0
        avg_reliability = sum(reliability_vals) / len(reliability_vals) if reliability_vals else 0

        type_counts = {}
        for t in all_tests:
            tt = t.get('test_type', 'unknown')
            type_counts[tt] = type_counts.get(tt, 0) + 1

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.markdown(f"""<div class="admin-stat-card"><div class="admin-stat-value">{total_tests}</div><div class="admin-stat-label">סה״כ מבדקים</div></div>""", unsafe_allow_html=True)
        sc2.markdown(f"""<div class="admin-stat-card"><div class="admin-stat-value">{unique_users}</div><div class="admin-stat-label">מועמדים ייחודיים</div></div>""", unsafe_allow_html=True)
        sc3.markdown(f"""<div class="admin-stat-card"><div class="admin-stat-value">{avg_hesitation:.1f}</div><div class="admin-stat-label">ממוצע היסוסים</div></div>""", unsafe_allow_html=True)
        sc4.markdown(f"""<div class="admin-stat-card"><div class="admin-stat-value">{avg_reliability:.0f}</div><div class="admin-stat-label">ממוצע אמינות</div></div>""", unsafe_allow_html=True)

        if type_counts:
            st.markdown("### 📈 התפלגות סוגי מבדקים")
            fig = go.Figure(data=[go.Pie(labels=list(type_counts.keys()), values=list(type_counts.values()),
                                          marker=dict(colors=['#0f3460', '#533483', '#e94560', '#ff9800']),
                                          textinfo='label+percent+value')])
            fig.update_layout(height=300, showlegend=True, font=dict(family="Assistant, sans-serif"))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### 👤 תיק מועמד")
        all_names = sorted(set(t.get('user_name', '') for t in all_tests if t.get('user_name')))
        selected_name = st.selectbox("בחר מועמד:", ["— בחר —"] + all_names)

        if selected_name and selected_name != "— בחר —":
            candidate_tests = [t for t in all_tests if t.get('user_name') == selected_name]
            candidate_tests.sort(key=lambda x: x.get('test_date', ''))
            st.markdown(f"### 📋 {html.escape(selected_name)} — {len(candidate_tests)} מבדקים")

            for i, test in enumerate(candidate_tests):
                with st.expander(f"📝 {test.get('test_type', 'N/A')} — {test.get('test_date', 'N/A')} | אמינות: {test.get('reliability_score', 'N/A')} | היסוסים: {test.get('hesitation_count', 'N/A')}"):
                    st.json(test.get('results', {}))
                    report = test.get('ai_report', '')
                    if isinstance(report, list):
                        for r in report:
                            st.markdown(html.escape(str(r)))
                    elif report:
                        st.markdown(html.escape(str(report)))

    except Exception as e:
        st.error(f"שגיאה: {e}")


# ============================================================
# Main
# ============================================================
def main():
    init_session_state()
    step = st.session_state.step
    if step == 'HOME':
        render_home()
    elif step == 'QUIZ':
        render_quiz()
    elif step == 'RESULTS':
        render_results()
    elif step == 'ADMIN_VIEW':
        render_admin()
    else:
        st.session_state.step = 'HOME'
        st.rerun()


if __name__ == "__main__":
    main()