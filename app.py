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
    get_db_history, get_integrity_history, get_combined_history,
    get_all_tests
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

html, body, [class*="css"] {
    font-family: 'Assistant', 'Rubik', sans-serif;
    direction: rtl;
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
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    font-size: 2.4rem !important;
}
h2, h3 { font-family: 'Rubik', sans-serif; color: #1a1a2e; }

button[kind="primary"] {
    background: linear-gradient(135deg, #0f3460 0%, #533483 50%, #e94560 100%);
    color: white !important;
    border: none;
    border-radius: 14px;
    padding: 0.7rem 2.2rem;
    font-size: 1.1rem;
    font-weight: 600;
    font-family: 'Assistant', sans-serif;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(15, 52, 96, 0.25);
}
button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(15, 52, 96, 0.4);
}

button[kind="secondary"] {
    background: transparent !important;
    color: #1a1a2e !important;
    border: 2px solid #533483 !important;
    border-radius: 14px;
    padding: 0.7rem 1rem;
    font-size: 1.1rem;
    font-weight: 600;
    font-family: 'Assistant', sans-serif;
    transition: all 0.2s ease;
}
button[kind="secondary"]:hover, button[kind="secondary"]:active, button[kind="secondary"]:focus {
    background: linear-gradient(135deg, #0f3460 0%, #533483 50%, #e94560 100%) !important;
    color: white !important;
    border: 2px solid transparent !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(15, 52, 96, 0.25);
}

.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #0f3460, #533483, #e94560);
    border-radius: 10px;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Assistant', sans-serif;
    font-weight: 600;
    border-radius: 10px 10px 0 0;
    padding: 10px 24px;
}
[data-testid="stMetricValue"] {
    font-size: 2rem; font-weight: 700; color: #0f3460;
}

.stress-screen {
    background: linear-gradient(180deg, #0a0a0a 0%, #1a0000 50%, #0a0a0a 100%);
    color: #ff1744;
    text-align: center;
    padding: 60px 20px;
    border-radius: 20px;
    min-height: 450px;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    border: 2px solid rgba(255, 23, 68, 0.3);
    box-shadow: 0 0 60px rgba(255, 23, 68, 0.15);
}
.stress-icon { font-size: 4rem; margin-bottom: 15px; animation: pulse 1.5s infinite; }
.stress-title {
    font-size: 1.8rem; font-weight: 800; font-family: 'Rubik', sans-serif;
    color: #ff1744; text-shadow: 0 0 20px rgba(255, 23, 68, 0.4);
    margin-bottom: 15px; letter-spacing: 1px;
}
.stress-detail { font-size: 1.1rem; color: #ff8a80; margin: 8px 0; max-width: 500px; line-height: 1.6; }
.stress-timer {
    font-size: 5rem; font-weight: 800; font-family: 'Rubik', sans-serif;
    color: #ff1744; text-shadow: 0 0 40px rgba(255, 23, 68, 0.6);
    margin: 20px 0; animation: timerPulse 1s infinite;
}
.stress-warning-bar {
    background: rgba(255, 23, 68, 0.15);
    border: 1px solid rgba(255, 23, 68, 0.3);
    border-radius: 10px; padding: 12px 24px; margin-top: 20px;
    font-size: 0.9rem; color: #ff8a80;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.15); opacity: 0.8; }
}
@keyframes timerPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.question-card {
    background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
    border: 1px solid #e0e0e0;
    border-radius: 16px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    animation: fadeIn 0.4s ease;
    text-align: right;
    direction: rtl;
}
.question-text {
    font-size: 1.25rem; font-weight: 600; color: #1a1a2e;
    line-height: 1.8; text-align: right;
}
.question-category { font-size: 0.85rem; color: #888; margin-bottom: 8px; text-align: right; }

.hero-section {
    text-align: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 20px;
    margin-bottom: 30px;
    animation: fadeIn 0.5s ease;
}
.hero-subtitle { font-size: 1.15rem; color: #555; margin-top: 10px; }

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.learning-tip {
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    border-right: 4px solid #4caf50;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 10px 0;
}
.learning-warning {
    background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
    border-right: 4px solid #ff9800;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 10px 0;
}

.instant-tip {
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    border-right: 4px solid #1976d2;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 12px 0;
    font-size: 0.95rem;
    line-height: 1.6;
}

.summary-card {
    background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
    border-radius: 16px;
    padding: 24px;
    margin: 20px 0;
    border-right: 5px solid #533483;
}
.summary-card h4 { color: #4a148c; margin-bottom: 10px; }

.admin-stat-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    color: white;
}
.admin-stat-value {
    font-size: 2.2rem; font-weight: 800; font-family: 'Rubik', sans-serif; color: #e94560;
}
.admin-stat-label { font-size: 0.9rem; color: #aaa; margin-top: 5px; }
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


def get_instant_tip(question_data, user_answer):
    """
    טיפ מיידי אחרי תשובה במצב תרגול.
    מסביר מה התשובה האידיאלית הייתה ולמה.
    """
    trait = question_data.get('trait', question_data.get('category', ''))
    is_reverse = str(question_data.get('reverse', False)).strip().lower() in ['true', '1', '1.0', 'yes']
    is_scenario = question_data.get('is_scenario', False)
    
    # תרחיש אמינות — לוגיקה אחרת
    if is_scenario:
        # בתרחישים שליליים (גניבה, סמים, וכו'), התשובה הרצויה היא 1 (לא)
        negative_cats = {'theft', 'drugs', 'gambling', 'unethical', 'termination', 'academic'}
        positive_cats = {'whistleblowing', 'feedback', 'teamwork'}
        category = question_data.get('category', '')
        
        if category in negative_cats:
            ideal = "לא נכון לגביי (1)"
            reason = "תרחישים כאלה — התנהגויות בעייתיות שאתה רוצה להראות שלא מאפיינות אותך."
        elif category in positive_cats:
            ideal = "נכון לגביי (5)"
            reason = "אלה התנהגויות חיוביות שמתאימות לרופא — שיתוף פעולה, יושרה, אחריות."
        else:
            ideal = "תלוי בנסיבות"
            reason = "ענה לפי האמת שלך, אבל זכור את הקונטקסט הרפואי."
        
        return f"💡 **תשובה אידיאלית:** {ideal}\n\n**למה:** {reason}"
    
    # שאלת HEXACO רגילה
    if trait not in IDEAL_RANGES:
        return None
    
    low, high = IDEAL_RANGES[trait]
    trait_he = TRAIT_EXPLANATIONS.get(trait, {}).get('name', trait)
    target_mid = (low + high) / 2
    
    # לקבוע מה הכיוון הרצוי
    # אם reverse=False, ציון גבוה לשאלה = ציון גבוה בתכונה
    # אם reverse=True, ציון גבוה לשאלה = ציון נמוך בתכונה
    
    # האם רוצים ציון גבוה בתכונה הזו? (כל היעדים שלנו הם 3.5+, אז כן)
    want_high_trait = target_mid >= 3.5
    
    if is_reverse:
        # שאלה הפוכה — אם רוצים ציון גבוה, נענה "לא נכון"
        ideal_answer = "לא נכון לגביי" if want_high_trait else "נכון לגביי"
    else:
        # שאלה רגילה — אם רוצים ציון גבוה, נענה "נכון"
        ideal_answer = "נכון לגביי" if want_high_trait else "לא נכון לגביי"
    
    # FIXED: מזהה "כן" לפי >=4 (כי במבחן הבינארי החדש "כן"=4 ולא 5)
    user_label = "נכון לגביי" if user_answer >= 4 else "לא נכון לגביי"
    is_match = (user_label == ideal_answer)
    
    icon = "✅" if is_match else "💭"
    status = "תשובה אידיאלית!" if is_match else "כדאי לחשוב על זה"
    
    tip = (f"{icon} **{status}**\n\n"
           f"**תכונה:** {trait_he}\n"
           f"**טווח אידיאלי לרופאים:** {low}—{high}\n"
           f"**תשובה אידיאלית:** {ideal_answer}\n"
           f"**ענית:** {user_label}")
    
    if not is_match:
        explanation = TRAIT_EXPLANATIONS.get(trait, {}).get('medical', '')
        if explanation:
            tip += f"\n\n**למה זה חשוב:** {explanation}"
    
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
        
        tab_quick, tab_full, tab_archive = st.tabs([
            "⚡ מבחן מהיר (כן/לא)", 
            "📝 מבחנים מלאים",
            "📜 ההיסטוריה שלי"
        ])
        
        # ===== Tab 1: מבחן מהיר =====
        with tab_quick:
            st.markdown("### ⚡ מבחן מהיר — נכון / לא נכון")
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
            
            if st.button("⚡ התחל מבחן מהיר", key="btn_quick", type="primary", use_container_width=True):
                st.session_state.practice_mode = practice_quick
                st.session_state.focus_trait = focus_trait
                start_quick_test(quick_length, focus_trait)
        
        # ===== Tab 2: מבחנים מלאים =====
        with tab_full:
            st.markdown("### 📝 מבחנים מלאים (סולם 1-5)")
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

    # ===== מסך לחץ — רק במבחנים מלאים, לא במהיר =====
    if is_stress and not st.session_state.practice_mode and not is_quick:
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

    # ===== Progress & Header =====
    st.progress(current / total)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write(f"שאלה **{current + 1}** מתוך **{total}**")
    with col2:
        if not st.session_state.practice_mode:
            elapsed = time.time() - st.session_state.q_start_time
            st.caption(f"⏱️ {int(elapsed)}s | ⚡ {st.session_state.hesitation_count} | 🏎️ {st.session_state.speed_flag_count}")

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
        # FIXED: מיפוי לא-קיצוני — מתאים יותר לתשובות בינאריות
        # נכון = 4 (מסכים), לא נכון = 2 (לא מסכים) — לא 5 ו-1!
        # זה מונע "קנס תשובות קיצוניות" שגוי, ומקרב את הציון לטווחים אידיאליים
        col_no, col_yes = st.columns(2)
        if col_no.button("❌ לא נכון לגביי", key=f"ans_no_{current}",
                         use_container_width=True, type="secondary"):
            _handle_answer(q_data, 2, current, is_stress)  # 2 = לא מסכים
        if col_yes.button("✅ נכון לגביי", key=f"ans_yes_{current}",
                          use_container_width=True, type="secondary"):
            _handle_answer(q_data, 4, current, is_stress)  # 4 = מסכים
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
        if test_type in ('hexaco', 'quick'):
            g, c = get_multi_ai_analysis(username, s_data, hist)
        elif test_type == 'integrity':
            g, c = get_integrity_ai_analysis(username, rel, cont, s_data, hist)
        elif test_type == 'combined':
            g, c = get_combined_ai_analysis(username, s_data, rel, cont, hist)
        
        result['gemini'] = g
        result['claude'] = c
        
        # שמירה ל-DB (גם אם נכשל, התוצאה תוצג)
        try:
            s_dict = s_data.to_dict() if hasattr(s_data, 'to_dict') else s_data
            i_dict = i_data.to_dict() if hasattr(i_data, 'to_dict') else i_data
            report_arg = [g, c] if c else g
            
            if test_type in ('hexaco', 'quick'):
                save_to_db(username, s_dict, report_arg, hesitation=hes)
            elif test_type == 'integrity':
                save_integrity_test_to_db(username, s_dict, rel, report_arg, hesitation=hes)
            elif test_type == 'combined':
                save_combined_test_to_db(username, s_dict, i_dict, rel, report_arg, hesitation=hes)
            
            result['saved_to_db'] = True
        except Exception as db_err:
            result['db_error'] = str(db_err)
        
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

    st.session_state.ai_status = 'processing'
    hist = []
    try:
        if test_type in ('hexaco', 'quick'):
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
        except Exception as e:
            st.warning(f"שגיאה ב-Excel: {e}")


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
