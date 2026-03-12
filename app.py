"""
Mednitai HEXACO System — Main Application
==========================================
With: Dynamic WPM, Fatigue Index, Real Stress Effect, Enhanced Admin
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
from enum import Enum

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
# Professional CSS Theme
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

.stButton > button {
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
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(15, 52, 96, 0.4);
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

/* ===== STRESS SCREEN — Intimidating ===== */
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
.stress-icon {
    font-size: 4rem;
    margin-bottom: 15px;
    animation: pulse 1.5s infinite;
}
.stress-title {
    font-size: 1.8rem;
    font-weight: 800;
    font-family: 'Rubik', sans-serif;
    color: #ff1744;
    text-shadow: 0 0 20px rgba(255, 23, 68, 0.4);
    margin-bottom: 15px;
    letter-spacing: 1px;
}
.stress-detail {
    font-size: 1.1rem;
    color: #ff8a80;
    margin: 8px 0;
    max-width: 500px;
    line-height: 1.6;
}
.stress-timer {
    font-size: 5rem;
    font-weight: 800;
    font-family: 'Rubik', sans-serif;
    color: #ff1744;
    text-shadow: 0 0 40px rgba(255, 23, 68, 0.6);
    margin: 20px 0;
    animation: timerPulse 1s infinite;
}
.stress-warning-bar {
    background: rgba(255, 23, 68, 0.15);
    border: 1px solid rgba(255, 23, 68, 0.3);
    border-radius: 10px;
    padding: 12px 24px;
    margin-top: 20px;
    font-size: 0.9rem;
    color: #ff8a80;
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
    background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
    border: 1px solid #e0e0e0;
    border-radius: 16px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    animation: fadeIn 0.4s ease;
}
.question-text {
    font-size: 1.25rem; font-weight: 600; color: #1a1a2e; line-height: 1.8;
}
.question-category { font-size: 0.85rem; color: #888; margin-bottom: 8px; }

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

/* ===== Admin Cards ===== */
.admin-stat-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    color: white;
}
.admin-stat-value {
    font-size: 2.2rem;
    font-weight: 800;
    font-family: 'Rubik', sans-serif;
    color: #e94560;
}
.admin-stat-label {
    font-size: 0.9rem;
    color: #aaa;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# Enums & Constants
# ============================================================
class Step(Enum):
    HOME = "home"
    QUIZ = "quiz"
    RESULTS = "results"
    ADMIN_VIEW = "admin"

# ---------- Stress Messages (the real ones from the spec) ----------
STRESS_MESSAGES = [
    {
        'icon': '⚠️',
        'title': 'זוהה חוסר עקביות בתשובות',
        'detail': 'המערכת זיהתה פערים משמעותיים בין תשובותיך. מתבצע ניתוח מעמיק של דפוסי התגובה...',
        'bar': 'מודול אימות אמינות פעיל — אנא המתן'
    },
    {
        'icon': '🔍',
        'title': 'נדרשת בדיקת אימות נוספת',
        'detail': 'דפוס התשובות שלך חורג מהנורמה הסטטיסטית. המערכת בודקת את מדד העקביות הפנימי...',
        'bar': 'סריקת Integrity פעילה — אנא המתן'
    },
    {
        'icon': '🛡️',
        'title': 'התקבלה התראת מערכת',
        'detail': 'אלגוריתם הבקרה זיהה חריגה בזמני התגובה שלך. מתבצע ניתוח סטטיסטי מורחב...',
        'bar': 'מנגנון Anti-Fake פעיל — אנא המתן'
    },
    {
        'icon': '📊',
        'title': 'ניתוח דפוסים חריג',
        'detail': 'המערכת זיהתה שינוי מגמה חד בתשובותיך. מתבצעת השוואה מול מאגר נורמטיבי...',
        'bar': 'מודול Cross-Validation פעיל — בודק עקביות'
    },
    {
        'icon': '🔐',
        'title': 'נדרש אימות פרופיל',
        'detail': 'ציון האמינות הנוכחי שלך ירד מתחת לסף הקריטי. המערכת מבצעת בדיקה מחודשת...',
        'bar': 'פרוטוקול אימות — סורק תשובות אחרונות'
    },
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


# ============================================================
# Cached Data Loading
# ============================================================
@st.cache_data
def load_hexaco_questions():
    try:
        return pd.read_csv("data/questions.csv")
    except Exception as e:
        st.error(f"שגיאה בטעינת שאלות HEXACO: {e}")
        return pd.DataFrame()


# ============================================================
# Session State Init
# ============================================================
def init_session_state():
    defaults = {
        'step': Step.HOME,
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
        'medical_fit': None,
        'fatigue_index': None,
        'practice_mode': False,
        'user_id': str(uuid.uuid4()),
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
        <p class="hero-subtitle">מערכת הכנה חכמה למבדקי אישיות למיון לבתי ספר לרפואה</p>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input("✍️ מה השם שלך?", value=st.session_state.get('user_name', ''),
                          placeholder="הכנס את שמך המלא")
    st.session_state.user_name = name

    st.write("")
    st.markdown("### בחר סוג מבדק")

    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        st.markdown("#### 🎯 HEXACO")
        st.caption("6 תכונות אישיות מרכזיות")
        if st.button("התחל HEXACO", key="btn_hexaco"):
            _start_if_named(name, 'hexaco')
    with col2:
        st.markdown("#### 🔍 אמינות")
        st.caption("בדיקת עקביות ויושרה")
        if st.button("התחל אמינות", key="btn_integrity"):
            _start_if_named(name, 'integrity')
    with col3:
        st.markdown("#### 🏥 משולב")
        st.caption("HEXACO + אמינות — סימולציה מלאה")
        if st.button("התחל משולב", key="btn_combined"):
            _start_if_named(name, 'combined')

    st.markdown("---")
    practice = st.checkbox("📚 מצב תרגול (ללא טיימר, ללא לחץ, עם הסברים)",
                           value=st.session_state.get('practice_mode', False))
    st.session_state.practice_mode = practice
    if practice:
        st.info("במצב תרגול: ללא מסכי לחץ, ללא מדידת זמן, עם הסברים אחרי כל שאלה.")

    st.markdown("---")
    with st.expander("🔐 גישת מנהל"):
        admin_pass = st.text_input("סיסמה", type="password", key="admin_pw")
        if st.button("כניסת מנהל", key="btn_admin"):
            try:
                if admin_pass == st.secrets.get("ADMIN_USER", ""):
                    st.session_state.step = Step.ADMIN_VIEW
                    st.rerun()
                else:
                    st.error("סיסמה שגויה")
            except Exception:
                st.error("שגיאה בגישה למערכת")


def _start_if_named(name, test_type):
    if not name.strip():
        st.warning("נא להכניס שם לפני תחילת המבדק")
    else:
        start_test(test_type)


def start_test(test_type):
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

    try:
        if test_type == 'hexaco':
            df = load_hexaco_questions()
            st.session_state.questions = get_balanced_questions(df, total_limit=60)
        elif test_type == 'integrity':
            st.session_state.questions = get_integrity_questions(count=140)
        elif test_type == 'combined':
            df = load_hexaco_questions()
            hexaco_q = get_balanced_questions(df, total_limit=40)
            integrity_q = get_integrity_questions(count=80)
            combined = hexaco_q + integrity_q
            random.shuffle(combined)
            st.session_state.questions = combined

        st.session_state.step = Step.QUIZ
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
        finish_test()
        return

    q_data = questions[current]
    is_stress = str(q_data.get('is_stress_meta', '')).strip().lower() in ["1", "1.0", "true"]

    # ==================== STRESS SCREEN (Real intimidating) ====================
    if is_stress and not st.session_state.practice_mode:
        if not st.session_state.stress_active:
            st.session_state.stress_active = True
            st.session_state.stress_start = time.time()
            # Pick a random stress message for this occurrence
            st.session_state.stress_msg_index = random.randint(0, len(STRESS_MESSAGES) - 1)

        elapsed = time.time() - st.session_state.stress_start
        remaining = max(0, 15 - int(elapsed))

        if remaining > 0:
            st_autorefresh(interval=1000, limit=20, key=f"stress_{current}")

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

    # ==================== Progress ====================
    st.progress(current / total)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        st.caption(f"שאלה {current + 1} מתוך {total}")
    with col2:
        type_labels = {'hexaco': '🎯 HEXACO', 'integrity': '🔍 אמינות', 'combined': '🏥 משולב'}
        st.caption(type_labels.get(st.session_state.test_type, ''))
    with col3:
        if not st.session_state.practice_mode:
            st.caption(f"⚡ {st.session_state.hesitation_count} היסוסים | 🏎️ {st.session_state.speed_flag_count} מהירות")

    # ==================== Question ====================
    q_text = q_data.get('question', q_data.get('text', 'שאלה חסרה'))
    q_category = q_data.get('trait', q_data.get('category', ''))

    st.markdown(f"""
    <div class="question-card">
        <div class="question-category">{html.escape(str(q_category))}</div>
        <div class="question-text">{html.escape(str(q_text))}</div>
    </div>
    """, unsafe_allow_html=True)

    # ==================== Answer ====================
    ans_labels = {1: "לא מסכים בכלל", 2: "לא מסכים", 3: "ניטרלי", 4: "מסכים", 5: "מסכים מאוד"}
    answer = st.radio("בחר תשובה:", options=[1, 2, 3, 4, 5],
                       format_func=lambda x: f"{x} — {ans_labels[x]}",
                       horizontal=True, key=f"a_{current}", index=None)

    if st.button("➡️ שאלה הבאה", key=f"next_{current}", use_container_width=True):
        if answer is None:
            st.warning("נא לבחור תשובה")
            return

        response_time = time.time() - st.session_state.q_start_time

        # ===== Dynamic WPM Threshold =====
        wpm_threshold = calculate_dynamic_wpm_threshold(str(q_text))
        is_too_fast = response_time < wpm_threshold
        is_hesitation = response_time > (wpm_threshold * 4)  # 4x the minimum = hesitation

        if not st.session_state.practice_mode:
            if is_too_fast:
                st.session_state.speed_flag_count += 1
            if is_hesitation:
                st.session_state.hesitation_count += 1

        st.session_state.responses.append({
            'question_index': current,
            'question': str(q_text),
            'answer': int(answer),
            'response_time': round(response_time, 2),
            'wpm_threshold': round(wpm_threshold, 2),
            'is_too_fast': is_too_fast,
            'is_hesitation': is_hesitation,
            'trait': q_data.get('trait', q_data.get('category', '')),
            'reverse': q_data.get('reverse', False),
            'is_stress_meta': is_stress,
            'category': q_data.get('category', q_data.get('trait', '')),
        })

        # Practice mode explanation
        if st.session_state.practice_mode and q_category in TRAIT_EXPLANATIONS:
            info = TRAIT_EXPLANATIONS[q_category]
            st.info(f"ℹ️ **{info['name']}**: {info['desc']}")
            st.caption(f"🏥 {info['medical']}")

        st.session_state.current_q += 1
        st.session_state.q_start_time = time.time()
        st.session_state.stress_active = False
        st.rerun()


# ============================================================
# Finish Test
# ============================================================
def finish_test():
    try:
        test_type = st.session_state.test_type
        responses = st.session_state.responses

        # ===== Calculate Fatigue Index =====
        fatigue = calculate_fatigue_index(responses)
        st.session_state.fatigue_index = fatigue

        if test_type == 'hexaco':
            df_raw, summary_df = process_results(responses)
            st.session_state.results_data = df_raw
            st.session_state.summary_data = summary_df
            st.session_state.medical_fit = calculate_medical_fit(summary_df)
            st.session_state.reliability_score = calculate_reliability_index(df_raw)
            st.session_state.contradictions = get_inconsistent_questions(df_raw)
            _run_ai_and_save_hexaco(summary_df)

        elif test_type == 'integrity':
            df_raw, summary_df = process_integrity_results(responses)
            contradictions = detect_contradictions(df_raw)
            reliability = calculate_reliability_score(df_raw)
            st.session_state.results_data = df_raw
            st.session_state.summary_data = summary_df
            st.session_state.reliability_score = reliability
            st.session_state.contradictions = contradictions
            _run_ai_and_save_integrity(summary_df, reliability, contradictions)

        elif test_type == 'combined':
            _process_combined(responses)

        st.session_state.step = Step.RESULTS
        st.rerun()
    except Exception as e:
        st.error(f"שגיאה בעיבוד תוצאות: {e}")


def _run_ai_and_save_hexaco(summary_df):
    try:
        history = get_db_history(st.session_state.user_name)
        g, c = get_multi_ai_analysis(st.session_state.user_name, summary_df, history)
        st.session_state.gemini_report = g
        st.session_state.claude_report = c
    except Exception as e:
        st.session_state.gemini_report = f"ניתוח AI לא זמין: {e}"
        st.session_state.claude_report = None
    try:
        save_to_db(st.session_state.user_name,
                   summary_df.to_dict() if hasattr(summary_df, 'to_dict') else summary_df,
                   st.session_state.gemini_report,
                   hesitation=st.session_state.hesitation_count)
    except Exception:
        pass


def _run_ai_and_save_integrity(summary_df, reliability, contradictions):
    try:
        history = get_integrity_history(st.session_state.user_name)
        g, c = get_integrity_ai_analysis(
            st.session_state.user_name, reliability, contradictions, summary_df, history)
        st.session_state.gemini_report = g
        st.session_state.claude_report = c
    except Exception as e:
        st.session_state.gemini_report = f"ניתוח AI לא זמין: {e}"
        st.session_state.claude_report = None
    try:
        save_integrity_test_to_db(
            st.session_state.user_name,
            summary_df.to_dict() if hasattr(summary_df, 'to_dict') else summary_df,
            reliability, st.session_state.gemini_report,
            hesitation=st.session_state.hesitation_count)
    except Exception:
        pass


def _process_combined(responses):
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
        contradictions = detect_contradictions(df_int)
        reliability = calculate_reliability_score(df_int)

    st.session_state.summary_data = summary_hex
    st.session_state.reliability_score = reliability
    st.session_state.contradictions = contradictions

    try:
        history = get_combined_history(st.session_state.user_name)
        g, c = get_combined_ai_analysis(
            st.session_state.user_name, summary_hex, reliability, contradictions, history)
        st.session_state.gemini_report = g
        st.session_state.claude_report = c
    except Exception as e:
        st.session_state.gemini_report = f"ניתוח AI לא זמין: {e}"
        st.session_state.claude_report = None
    try:
        save_combined_test_to_db(
            st.session_state.user_name,
            summary_hex.to_dict() if hasattr(summary_hex, 'to_dict') else summary_hex,
            summary_int.to_dict() if hasattr(summary_int, 'to_dict') else summary_int,
            reliability, st.session_state.gemini_report,
            hesitation=st.session_state.hesitation_count)
    except Exception:
        pass


# ============================================================
# RESULTS Screen
# ============================================================
def render_results():
    st.balloons()

    name_safe = html.escape(st.session_state.user_name)
    st.markdown(f"""
    <div class="hero-section">
        <h1>📊 תוצאות המבדק</h1>
        <p class="hero-subtitle">שלום {name_safe} — הנה התוצאות שלך</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Top Metrics (now with Fatigue) ---
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

    st.write("")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 תוצאות", "🤖 ניתוח AI", "📚 למידה וטיפים", "📥 הורדות"])

    with tab1:
        _render_results_tab()
    with tab2:
        _render_ai_tab()
    with tab3:
        _render_learning_tab()
    with tab4:
        _render_downloads_tab()

    st.markdown("---")
    if st.button("🏠 חזרה לדף הבית", use_container_width=True):
        for key in ['responses', 'results_data', 'summary_data', 'gemini_report', 'claude_report']:
            st.session_state[key] = None if 'data' in key or 'report' in key else []
        st.session_state.step = Step.HOME
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
        st.dataframe(summary, use_container_width=True)

    # Fatigue breakdown
    fatigue = st.session_state.get('fatigue_index')
    if fatigue is not None and fatigue > 15:
        st.warning(f"😴 **מדד עייפות: {fatigue}%** — זוהה ירידה בעקביות לקראת סוף המבדק. "
                   f"ייתכן שזה משפיע על הציונים האחרונים.")

    # Speed flags
    speed = st.session_state.get('speed_flag_count', 0)
    if speed > 3:
        st.warning(f"🏎️ **{speed} תשובות מהירות מדי** — תשובות שניתנו מתחת לסף הקריאה הדינמי (WPM).")

    contradictions = st.session_state.get('contradictions', [])
    if contradictions:
        st.markdown("### ⚠️ סתירות שזוהו")
        for c in contradictions:
            if isinstance(c, dict):
                sev = c.get('severity', '')
                icon = "🔴" if sev == 'critical' else "🟠" if sev == 'high' else "🔵"
                st.markdown(f"{icon} {html.escape(str(c.get('message', str(c))))}")
            else:
                st.markdown(f"⚠️ {html.escape(str(c))}")

    rel = st.session_state.get('reliability_score')
    if rel is not None:
        st.info(f"🔒 פירוש ציון אמינות ({rel}): {get_integrity_interpretation(rel)}")


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

    if not gemini and not claude:
        st.info("ניתוח AI לא זמין כרגע. ניתן להוריד PDF עם התוצאות המספריות.")


def _render_learning_tab():
    summary = st.session_state.get('summary_data')
    st.markdown("### 📚 מדריך למידה אישי")

    if summary is not None and hasattr(summary, 'iterrows'):
        for _, row in summary.iterrows():
            trait = row.get('trait', row.get('Trait', ''))
            score = float(row.get('avg_score', row.get('Mean', 0)))
            if trait not in TRAIT_EXPLANATIONS:
                continue

            info = TRAIT_EXPLANATIONS[trait]
            low, high = IDEAL_RANGES.get(trait, (3.0, 5.0))

            if low <= score <= high:
                status = "✅ בטווח"
            elif score < low:
                status = "📉 מתחת"
            else:
                status = "📈 מעל"

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
                    st.markdown('<div class="learning-tip">✅ בטווח האידיאלי!</div>',
                                unsafe_allow_html=True)
                st.caption(f"טווח אידיאלי: {low} — {high}")
    else:
        st.info("נתוני תכונות HEXACO מוצגים רק במבדקי HEXACO ומשולב.")

    st.markdown("---")
    st.markdown("### 📈 התקדמות")
    try:
        history = get_db_history(st.session_state.user_name)
        if history and len(history) > 1:
            for i, entry in enumerate(history[-5:]):
                st.caption(f"מבדק {i+1} — {entry.get('test_date', 'N/A')}")
        else:
            st.info("אחרי עוד מבדקים תוכל לראות כאן את ההתקדמות!")
    except Exception:
        st.info("אחרי עוד מבדקים תוכל לראות כאן את ההתקדמות!")


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
                                       "application/pdf", use_container_width=True)
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
                                       use_container_width=True)
        except Exception as e:
            st.warning(f"שגיאה ב-Excel: {e}")


# ============================================================
# ADMIN Screen — Enhanced Dashboard
# ============================================================
def render_admin():
    st.markdown("# 🔐 ממשק ניהול — Dashboard")
    if st.button("🏠 חזרה לדף הבית"):
        st.session_state.step = Step.HOME
        st.rerun()

    st.markdown("---")

    try:
        all_tests = get_all_tests()
        if not all_tests:
            st.info("אין מבדקים במערכת")
            return

        # ===== System-Wide Stats =====
        st.markdown("### 📊 מדדי רוחב — כלל המערכת")

        total_tests = len(all_tests)
        unique_users = len(set(t.get('user_name', '') for t in all_tests))

        # Calculate averages
        avg_hesitation = 0
        avg_reliability = 0
        hesitation_vals = [t.get('hesitation_count', 0) for t in all_tests if t.get('hesitation_count') is not None]
        reliability_vals = [t.get('reliability_score', 0) for t in all_tests if t.get('reliability_score') is not None]

        if hesitation_vals:
            avg_hesitation = sum(hesitation_vals) / len(hesitation_vals)
        if reliability_vals:
            avg_reliability = sum(reliability_vals) / len(reliability_vals)

        # Test type breakdown
        type_counts = {}
        for t in all_tests:
            tt = t.get('test_type', 'unknown')
            type_counts[tt] = type_counts.get(tt, 0) + 1

        # Display stats
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.markdown(f"""<div class="admin-stat-card">
            <div class="admin-stat-value">{total_tests}</div>
            <div class="admin-stat-label">סה״כ מבדקים</div>
        </div>""", unsafe_allow_html=True)
        sc2.markdown(f"""<div class="admin-stat-card">
            <div class="admin-stat-value">{unique_users}</div>
            <div class="admin-stat-label">מועמדים ייחודיים</div>
        </div>""", unsafe_allow_html=True)
        sc3.markdown(f"""<div class="admin-stat-card">
            <div class="admin-stat-value">{avg_hesitation:.1f}</div>
            <div class="admin-stat-label">ממוצע היסוסים</div>
        </div>""", unsafe_allow_html=True)
        sc4.markdown(f"""<div class="admin-stat-card">
            <div class="admin-stat-value">{avg_reliability:.0f}</div>
            <div class="admin-stat-label">ממוצע אמינות</div>
        </div>""", unsafe_allow_html=True)

        st.write("")

        # Test type distribution
        if type_counts:
            st.markdown("### 📈 התפלגות סוגי מבדקים")
            fig = go.Figure(data=[go.Pie(
                labels=list(type_counts.keys()),
                values=list(type_counts.values()),
                marker=dict(colors=['#0f3460', '#533483', '#e94560']),
                textinfo='label+percent+value'
            )])
            fig.update_layout(height=300, showlegend=True,
                            font=dict(family="Assistant, sans-serif"))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ===== Candidate Profile Search =====
        st.markdown("### 👤 תיק מועמד")

        all_names = sorted(set(t.get('user_name', '') for t in all_tests if t.get('user_name')))
        selected_name = st.selectbox("בחר מועמד:", ["— בחר —"] + all_names)

        if selected_name and selected_name != "— בחר —":
            candidate_tests = [t for t in all_tests if t.get('user_name') == selected_name]
            candidate_tests.sort(key=lambda x: x.get('test_date', ''))

            st.markdown(f"### 📋 {html.escape(selected_name)} — {len(candidate_tests)} מבדקים")

            # Candidate metrics
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("מבדקים", len(candidate_tests))

            cand_reliability = [t.get('reliability_score', 0) for t in candidate_tests
                               if t.get('reliability_score') is not None]
            if cand_reliability:
                cc2.metric("אמינות ממוצעת", f"{sum(cand_reliability)/len(cand_reliability):.0f}")

            cand_hesitation = [t.get('hesitation_count', 0) for t in candidate_tests
                              if t.get('hesitation_count') is not None]
            if cand_hesitation:
                cc3.metric("היסוס ממוצע", f"{sum(cand_hesitation)/len(cand_hesitation):.1f}")

            # Progress over time (if multiple tests)
            if len(candidate_tests) > 1 and cand_reliability:
                st.markdown("#### 📈 מגמת אמינות לאורך זמן")
                dates = [t.get('test_date', f'מבדק {i+1}') for i, t in enumerate(candidate_tests)
                         if t.get('reliability_score') is not None]
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=dates, y=cand_reliability,
                    mode='lines+markers',
                    line=dict(color='#533483', width=3),
                    marker=dict(size=10),
                    name='אמינות'
                ))
                fig_trend.update_layout(
                    yaxis=dict(range=[0, 105], title="ציון אמינות"),
                    height=300,
                    font=dict(family="Assistant, sans-serif")
                )
                st.plotly_chart(fig_trend, use_container_width=True)

            # Individual test details
            for i, test in enumerate(candidate_tests):
                with st.expander(
                    f"📝 {test.get('test_type', 'N/A')} — {test.get('test_date', 'N/A')} "
                    f"| אמינות: {test.get('reliability_score', 'N/A')} "
                    f"| היסוסים: {test.get('hesitation_count', 'N/A')}"
                ):
                    st.json(test.get('results', {}))
                    report = test.get('ai_report', '')
                    if isinstance(report, list):
                        for r in report:
                            st.markdown(html.escape(str(r)))
                    elif report:
                        st.markdown(html.escape(str(report)))

        st.markdown("---")

        # ===== Full Test List =====
        st.markdown("### 📋 כל המבדקים")
        for test in all_tests:
            with st.expander(
                f"{test.get('user_name','N/A')} — {test.get('test_type','N/A')} — "
                f"{test.get('test_date','N/A')} | "
                f"אמינות: {test.get('reliability_score', 'N/A')}"
            ):
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
    if step == Step.HOME:
        render_home()
    elif step == Step.QUIZ:
        render_quiz()
    elif step == Step.RESULTS:
        render_results()
    elif step == Step.ADMIN_VIEW:
        render_admin()
    else:
        st.session_state.step = Step.HOME
        st.rerun()

if __name__ == "__main__":
    main()
