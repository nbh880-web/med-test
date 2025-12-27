import streamlit as st
import time
import pandas as pd
import random
from streamlit_autorefresh import st_autorefresh

# ייבוא לוגיקה עסקית
from logic import (
    calculate_score, 
    process_results, 
    analyze_consistency, 
    create_pdf_report,
    get_inconsistent_questions,
    get_static_interpretation # פונקציה חדשה שנוסיף ל-logic.py
)

# ייבוא שכבת הנתונים (Firebase)
from database import save_to_db, get_db_history

# ייבוא שכבת הבינה המלאכותית (Gemini)
from gemini_ai import get_ai_analysis, get_comparison_chart, get_radar_chart # הוספנו את המכ"ם

# 1. הגדרות דף ו-RTL
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# 2. אתחול משתני Session State
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []
if 'toast_shown' not in st.session_state: st.session_state.toast_shown = False

# עיצוב CSS - יישור לימין ותמיכה במובייל
st.markdown("""
    <style>
    .stApp, div[data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    div.stButton > button {
        width: 100%; border-radius: 12px; border: 1px solid #d1d8e0;
        height: 60px; font-size: 18px; transition: all 0.2s; direction: rtl;
    }
    .question-text { font-size: 26px; font-weight: bold; text-align: center; padding: 20px; color: #2c3e50; }
    .ai-report-box { 
        background-color: #f0f7ff; padding: 25px; border-right: 6px solid #1e90ff; 
        border-radius: 8px; line-height: 1.8; text-align: right; font-size: 16px; white-space: pre-wrap;
    }
    input { text-align: right; direction: rtl; }
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

# --- ניווט בין מסכים ---

if st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: right;">🏥 מערכת סימולציה HEXACO - הכנה למס"ר</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס את שמך המלא להתחלה:", st.session_state.user_name)
    
    if st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 ארכיון מבחנים קודמים"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר את אורך הסימולציה:")
                col1, col2, col3 = st.columns(3)
                if col1.button("⏳ תרגול מהיר (36 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 36)
                    st.session_state.step = 'QUIZ'
                    st.rerun()
                if col2.button("📋 סימולציה רגילה (120 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 120)
                    st.session_state.step = 'QUIZ'
                    st.rerun()
                if col3.button("🔍 סימולציה מלאה (300 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 300)
                    st.session_state.step = 'QUIZ'
                    st.rerun()

        with tab_archive:
            history = get_db_history(st.session_state.user_name)
            if history:
                for i, entry in enumerate(history):
                    with st.expander(f"סימולציה מיום {entry.get('test_date')} בשעה {entry.get('test_time')}"):
                        st.plotly_chart(get_comparison_chart(entry['results']), key=f"arch_{i}")
                        st.markdown(f'<div class="ai-report-box">{entry["ai_report"]}</div>', unsafe_allow_html=True)
            else:
                st.info("לא נמצאו מבחנים קודמים.")

elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="timer_refresh")
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        if 'start_time' not in st.session_state: st.session_state.start_time = time.time()
        elapsed = time.time() - st.session_state.start_time
        
        st.progress((q_idx) / len(st.session_state.questions))
        st.write(f"שאלה {q_idx + 1} מתוך {len(st.session_state.questions)} | זמן: {int(elapsed)} שניות")
        
        if elapsed > 8: st.warning("⚠️ חלפו 8 שניות. מומלץ לענות בזריזות.", icon="⏳")
        st.markdown(f'<p class="question-text">{q_data["q"]}</p>', unsafe_allow_html=True)
        
        # כפתורים עם אימוג'ים לשיפור ה-UX
        options = [
            ("🔴 בכלל לא מסכים", 1),
            ("🟠 לא מסכים", 2),
            ("⚪ נייטרלי", 3),
            ("🟢 מסכים", 4),
            ("✨ מסכים מאוד", 5)
        ]
        for label, val in options:
            if st.button(label, key=f"btn_{q_idx}_{val}"):
                record_answer(val, q_data)
                st.rerun()
    else:
        st.session_state.step = 'RESULTS'
        st.rerun()

elif st.session_state.step == 'RESULTS':
    st.markdown(f'<h1 style="text-align: right;">📊 דוח תוצאות - {st.session_state.user_name}</h1>', unsafe_allow_html=True)
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()
    
    # --- חלק 1: גרפים משולבים ---
    col_radar, col_bar = st.columns(2)
    with col_radar:
        st.markdown("### 🕸️ פרופיל אישיות היקפי")
        st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True)
    with col_bar:
        st.markdown("### 📊 השוואה ליעד רפואי")
        st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True)
    
    st.divider()

    # --- חלק 2: פרשנות מובנית (העוגנים) ---
    st.markdown("### 🔍 ניתוח תכונות מובנה")
    for _, row in summary_df.iterrows():
        text = get_static_interpretation(row['trait'], row['final_score'])
        st.info(f"**{row['trait']}:** {text}")

    st.divider()
    
    # --- חלק 3: ניתוח AI ---
    st.markdown("### 🤖 ניתוח מאמן AI מעמיק")
    if 'ai_report_done' not in st.session_state:
        with st.spinner("ה-AI מגבש את חוות דעתו..."):
            history = get_db_history(st.session_state.user_name)
            report_text = get_ai_analysis(st.session_state.user_name, trait_scores, history)
            save_to_db(st.session_state.user_name, trait_scores, report_text)
            st.session_state.ai_report_done = report_text
    st.markdown(f'<div class="ai-report-box">{st.session_state.ai_report_done}</div>', unsafe_allow_html=True)

    # --- חלק 4: טיפים קבועים ---
    st.success("""
    ### 💡 טיפים קריטיים ליום המיונים (מס"ר):
    * **ענווה (H):** אל תפחד לומר "אני לא יודע, אבדוק זאת". זה מראה על בטיחות המטופל.
    * **סבלנות (A):** בסימולציות מול שחקן כועס - הקשב עד הסוף לפני שתגיב.
    * **דיוק (C):** הקפד על פרטים טכניים במשימות שיוצגו לך.
    * **יציבות (E):** שמור על קור רוח גם כשהבוחנים מנסים להלחיץ אותך.
    """, icon="🩺")

    col_pdf, col_home = st.columns(2)
    with col_pdf:
        pdf_bytes = create_pdf_report(summary_df, st.session_state.responses)
        st.download_button("📥 הורד דוח PDF", data=pdf_bytes, file_name="HEXACO_Report.pdf")
    with col_home:
        if st.button("חזרה למסך הבית"):
            for key in ['step', 'responses', 'current_q', 'questions', 'ai_report_done']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()