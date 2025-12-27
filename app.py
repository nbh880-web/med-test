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
    get_static_interpretation
)

# ייבוא שכבת הנתונים (Firebase)
from database import save_to_db, get_db_history

# ייבוא שכבת הבינה המלאכותית המעודכנת (החלפת get_ai_analysis ב-get_multi_ai_analysis)
from gemini_ai import get_multi_ai_analysis, get_comparison_chart, get_radar_chart

# 1. הגדרות דף ו-RTL
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# 2. אתחול משתני Session State
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []

# עיצוב CSS - יישור לימין, כפתורים נקיים ותמיכה במובייל
st.markdown("""
    <style>
    .stApp, div[data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    
    /* עיצוב כפתורי תשובה נקיים ומקצועיים */
    div.stButton > button {
        width: 100%; border-radius: 8px; border: 1px solid #ced4da;
        height: 55px; font-size: 18px; transition: all 0.2s; 
        background-color: white; color: #212529;
    }
    div.stButton > button:hover {
        border-color: #1e90ff; background-color: #f8f9fa;
    }
    
    .question-text { font-size: 28px; font-weight: bold; text-align: center; padding: 30px; color: #2c3e50; }
    
    .ai-report-box { 
        padding: 20px; border-right: 6px solid; 
        border-radius: 8px; line-height: 1.6; text-align: right; font-size: 15px; 
        white-space: pre-wrap; min-height: 450px; color: #333;
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
    st.markdown('<h1 style="text-align: right;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא לזיהוי במערכת:", st.session_state.user_name)
    
    if st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 היסטוריית מבדקים"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר את היקף הסימולציה:")
                col1, col2, col3 = st.columns(3)
                if col1.button("⏳ תרגול קצר (36 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 36)
                    st.session_state.step = 'QUIZ'
                    st.rerun()
                if col2.button("📋 סימולציה רגילה (120 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 120)
                    st.session_state.step = 'QUIZ'
                    st.rerun()
                if col3.button("🔍 מבדק מלא (300 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 300)
                    st.session_state.step = 'QUIZ'
                    st.rerun()

        with tab_archive:
            history = get_db_history(st.session_state.user_name)
            if history:
                for i, entry in enumerate(history):
                    with st.expander(f"מבחן מיום {entry.get('test_date')} ({entry.get('test_time')})"):
                        st.plotly_chart(get_comparison_chart(entry['results']), key=f"arch_{i}")
                        st.markdown(f'<div class="ai-report-box" style="background-color:#f9f9f9; border-right-color:#ccc;">{entry.get("ai_report", "אין דוח")}</div>', unsafe_allow_html=True)
            else:
                st.info("לא נמצאו מבחנים קודמים לשם זה.")

elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="timer_refresh")
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        if 'start_time' not in st.session_state: st.session_state.start_time = time.time()
        elapsed = time.time() - st.session_state.start_time
        
        st.progress((q_idx) / len(st.session_state.questions))
        st.write(f"שאלה {q_idx + 1} מתוך {len(st.session_state.questions)}")
        
        if elapsed > 8: st.warning("מומלץ לענות לפי תחושת בטן ראשונית.", icon="⏳")
        st.markdown(f'<p class="question-text">{q_data["q"]}</p>', unsafe_allow_html=True)
        
        # אפשרויות נקיות ללא סמלים ואימוג'ים
        options = [
            ("בכלל לא מסכים", 1),
            ("לא מסכים", 2),
            ("נייטרלי", 3),
            ("מסכים", 4),
            ("מסכים מאוד", 5)
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

    # --- חלק 2: פרשנות מובנית ---
    st.markdown("### 🔍 ניתוח תכונות מובנה")
    for _, row in summary_df.iterrows():
        text = get_static_interpretation(row['trait'], row['final_score'])
        st.info(f"**{row['trait']}:** {text}")

    st.divider()
    
    # --- חלק 3: פאנל בוחני AI (Gemini & Claude) ---
    st.markdown("### 🤖 פאנל בוחני AI: Gemini & Claude")
    
    if 'ai_multi_reports' not in st.session_state:
        with st.spinner("הבוחנים מגבשים חוות דעת..."):
            history = get_db_history(st.session_state.user_name)
            g_report, c_report = get_multi_ai_analysis(st.session_state.user_name, trait_scores, history)
            st.session_state.ai_multi_reports = (g_report, c_report)
            
            # שמירה ל-DB (דוח מאוחד)
            combined_report = f"--- Gemini ---\n{g_report}\n\n--- Claude ---\n{c_report}"
            save_to_db(st.session_state.user_name, trait_scores, combined_report)

    # הצגה בטורים עם הפרדת צבעים
    col_g, col_c = st.columns(2)
    with col_g:
        st.markdown('<p style="color:#1E90FF; font-weight:bold; font-size:20px;">🛡️ בוחן 1: Gemini (Google)</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #1E90FF; background-color: #f0f7ff;">{st.session_state.ai_multi_reports[0]}</div>', unsafe_allow_html=True)
    
    with col_c:
        st.markdown('<p style="color:#D97757; font-weight:bold; font-size:20px;">🔮 בוחן 2: Claude (Anthropic)</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #D97757; background-color: #fffaf0;">{st.session_state.ai_multi_reports[1]}</div>', unsafe_allow_html=True)

    st.divider()

    # --- חלק 4: טיפים קבועים ---
    st.success("### 💡 דגשים קריטיים לסימולציה: הקפד על ענווה, סבלנות ודיוק רב בפרטים.", icon="🩺")

    col_pdf, col_home = st.columns(2)
    with col_pdf:
        pdf_bytes = create_pdf_report(summary_df, st.session_state.responses)
        st.download_button("📥 הורד דוח PDF", data=pdf_bytes, file_name="HEXACO_Full_Report.pdf")
    with col_home:
        if st.button("סיום וחזרה לבית"):
            # ניקוי Session state לצורך מבחן חדש
            keys_to_delete = ['step', 'responses', 'current_q', 'questions', 'ai_multi_reports']
            for key in keys_to_delete:
                if key in st.session_state: del st.session_state[key]
            st.rerun()