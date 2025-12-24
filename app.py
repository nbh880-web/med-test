import streamlit as st
import time
import pandas as pd
import random
# ייבוא הרכיב לריענון אוטומטי
from streamlit_autorefresh import st_autorefresh

# ייבוא לוגיקה עסקית
from logic import (
    calculate_score, 
    process_results, 
    analyze_consistency, 
    create_pdf_report,
    get_inconsistent_questions
)

# ייבוא שכבת הנתונים (Firebase)
from database import save_to_db, get_db_history

# ייבוא שכבת הבינה המלאכותית (Gemini)
from gemini_ai import get_ai_analysis, get_comparison_chart

# 1. הגדרות דף ו-RTL
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# 2. אתחול משתני Session State
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []

# עיצוב CSS
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    div.stButton > button {
        width: 100%; border-radius: 12px; border: 1px solid #d1d8e0;
        height: 60px; font-size: 18px; transition: all 0.2s;
    }
    .question-text { font-size: 28px; font-weight: bold; text-align: center; padding: 30px; color: #2c3e50; }
    .ai-report-box { 
        background-color: #f0f7ff; 
        padding: 25px; 
        border-right: 6px solid #1e90ff; 
        border-radius: 8px; 
        line-height: 1.8;
        text-align: right;
        font-size: 16px;
        white-space: pre-wrap;
    }
    input { text-align: right; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_questions():
    try:
        df = pd.read_csv('data/questions.csv')
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת קובץ השאלות: {e}")
        return pd.DataFrame()

def get_balanced_questions(df, total_limit):
    traits = df['trait'].unique()
    qs_per_trait = total_limit // len(traits)
    selected_qs = []
    for trait in traits:
        trait_qs = df[df['trait'] == trait].to_dict('records')
        if len(trait_qs) >= qs_per_trait:
            selected_qs.extend(random.sample(trait_qs, qs_per_trait))
        else:
            selected_qs.extend(trait_qs)
    random.shuffle(selected_qs)
    return selected_qs

def record_answer(ans_value, q_data):
    duration = time.time() - st.session_state.get('start_time', time.time())
    final_score = calculate_score(ans_value, q_data['reverse'])
    st.session_state.responses.append({
        'question': q_data['q'],
        'trait': q_data['trait'],
        'original_answer': ans_value,
        'final_score': final_score,
        'time_taken': duration,
        'reverse': q_data['reverse']
    })
    st.session_state.current_q += 1
    st.session_state.start_time = time.time()
    st.session_state.toast_shown = False

# --- ניווט בין מסכים ---

if st.session_state.step == 'HOME':
    st.title("🏥 מערכת סימולציה HEXACO - הכנה למס\"ר")
    st.session_state.user_name = st.text_input("הכנס את שמך המלא להתחלה:", st.session_state.user_name)
    
    if st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 ארכיון מבחנים קודמים"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                col1, col2, col3 = st.columns(3)
                if col1.button("⏳ תרגול מהיר"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 36)
                    st.session_state.step = 'QUIZ'
                    st.session_state.start_time = time.time()
                    st.rerun()

elif st.session_state.step == 'QUIZ':
    # ריענון אוטומטי כל שנייה כדי לבדוק את הזמן שחלף
    st_autorefresh(interval=1000, key="timer_refresh")
    
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        
        # חישוב זמן שחלף
        elapsed = time.time() - st.session_state.get('start_time', time.time())
        
        # בדיקה אם עברו 8 שניות
        if elapsed > 8 and not st.session_state.get('toast_shown', False):
            st.toast("חלפו 8 שניות על שאלה זו. במבחן אמת, מומלץ לענות על שאלות באופן כנה", icon="⏳")
            st.session_state.toast_shown = True

        st.progress((q_idx) / len(st.session_state.questions))
        st.write(f"שאלה {q_idx + 1} | זמן: {int(elapsed)} שניות")
        st.markdown(f'<p class="question-text">{q_data["q"]}</p>', unsafe_allow_html=True)
        
        cols = st.columns(5)
        labels = ["בכלל לא מסכים", "לא מסכים", "נייטרלי", "מסכים", "מסכים מאוד"]
        for i, label in enumerate(labels):
            if cols[i].button(label, key=f"q_{q_idx}_{i}"):
                record_answer(i+1, q_data)
                st.rerun()
    else:
        st.session_state.step = 'RESULTS'
        st.rerun()

# ... (יתר חלקי הקוד של ה-RESULTS נשארים אותו דבר)
elif st.session_state.step == 'RESULTS':
    st.title(f"📊 דוח תוצאות - {st.session_state.user_name}")
    df_raw, summary_df = process_results(st.session_state.responses)
    st.plotly_chart(get_comparison_chart(summary_df.set_index('trait')['final_score'].to_dict()))
    if st.button("חזרה למסך הבית"):
        st.session_state.step = 'HOME'
        st.rerun()
