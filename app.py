import streamlit as st
import time
import pandas as pd
import random
import json
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ייבוא לוגיקה עסקית (logic.py)
from logic import (
    calculate_score, 
    process_results, 
    analyze_consistency, 
    create_pdf_report,
    get_inconsistent_questions,
    get_static_interpretation,
    calculate_medical_fit,
    calculate_reliability_index
)

# ייבוא שכבת הנתונים וה-AI (database.py, gemini_ai.py)
try:
    from database import save_to_db, get_db_history, get_all_tests
    from gemini_ai import get_multi_ai_analysis, get_comparison_chart, get_radar_chart, create_token_gauge
except ImportError:
    st.error("חלק מקבצי העזר (database/gemini_ai) חסרים. וודא שהם בתיקייה.")

# --- 1. הגדרות דף ו-CSS מקיף (RTL ותמיכה במובייל) ---
st.set_page_config(
    page_title="Mednitai HEXACO System", 
    layout="wide",
    initial_sidebar_state="collapsed" 
)

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { min-width: 280px !important; background-color: #f1f3f6; }
    [data-testid="stSidebar"] * { 
        word-break: normal !important; 
        white-space: normal !important; 
        text-align: right; 
    }
    
    div.stButton > button {
        width: 100%; border-radius: 8px; height: 75px !important; 
        font-size: 19px !important; line-height: 1.2 !important;
        background-color: white; color: #212529; font-weight: 500;
        margin-bottom: 10px; display: flex; align-items: center; justify-content: center;
    }
    
    .admin-entry-btn button { background-color: #1e3a8a !important; color: white !important; font-weight: bold !important; }

    .question-text { 
        font-size: 42px; font-weight: 800; text-align: center; 
        padding: 40px 20px; color: #1a2a6c; background-color: #f8f9fa; 
        border-radius: 15px; margin-bottom: 20px; box-shadow: inset 0 0 10px rgba(0,0,0,0.02);
    }

    @media (max-width: 768px) {
        .question-text { font-size: 24px !important; padding: 20px 10px !important; }
        div.stButton > button { height: 60px !important; font-size: 17px !important; }
    }
    
    .ai-report-box { 
        padding: 20px; border-right: 8px solid; border-radius: 12px; 
        background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        line-height: 1.6; text-align: right;
    }
    input { text-align: right; direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. אתחול Session State ---
for key in ['step', 'responses', 'current_q', 'user_name', 'questions', 'start_time', 'ai_report']:
    if key not in st.session_state:
        st.session_state[key] = 'HOME' if key == 'step' else ([] if key in ['responses', 'questions'] else (0 if key == 'current_q' else ""))

# --- 3. פונקציות עזר לניהול המבדק ---
@st.cache_data
def load_questions():
    try: return pd.read_csv('data/questions.csv')
    except: return pd.DataFrame()

def record_answer(ans_value, q_data):
    if st.session_state.current_q >= len(st.session_state.questions): return
    duration = time.time() - st.session_state.start_time
    score = calculate_score(ans_value, q_data['reverse'])
    st.session_state.responses.append({
        'question': q_data['q'], 'trait': q_data['trait'], 'original_answer': ans_value,
        'final_score': score, 'time_taken': duration, 'reverse': q_data['reverse']
    })
    st.session_state.current_q += 1
    st.session_state.start_time = time.time()

# --- 4. ממשק ניהול (ADMIN) ---
def show_admin_dashboard():
    st.sidebar.markdown(f"### 🔑 מנהל: \n**{st.session_state.user_name}**")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.user_name = ""; st.session_state.step = 'HOME'; st.rerun()

    st.title("📊 לוח בקרת מנהל")
    all_data = get_all_tests()
    if not all_data:
        st.info("אין נתונים להצגה."); return

    df = pd.DataFrame(all_data)
    df['tokens'] = df['ai_report'].apply(lambda x: int(len(str(x).split()) * 1.6))

    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ מבדקים", len(df))
    m2.metric("משתמשים ייחודיים", df['user_name'].nunique())
    m3.metric("ממוצע טוקנים", int(df['tokens'].mean()))

    st.divider()
    search = st.text_input("🔍 חפש מועמד:")
    if search:
        df = df[df['user_name'].str.contains(search, case=False)]

    st.dataframe(df[['user_name', 'test_date', 'test_time', 'tokens']], use_container_width=True)

    if not df.empty:
        selected_idx = st.selectbox("בחר מועמד לפירוט:", df.index, format_func=lambda x: f"{df.loc[x, 'user_name']} ({df.loc[x, 'test_date']})")
        col_rep, col_gauge = st.columns([2, 1])
        with col_rep:
            st.markdown(f'<div class="ai-report-box" style="border-right-color: #1e3a8a;">{df.loc[selected_idx, "ai_report"]}</div>', unsafe_allow_html=True)
        with col_gauge:
            st.plotly_chart(create_token_gauge(df.loc[selected_idx, "ai_report"]), use_container_width=True)

# --- 5. ניווט ראשי ---
if st.session_state.user_name == "adminMednitai" and st.session_state.step == 'ADMIN_VIEW':
    show_admin_dashboard()

elif st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: right; color: #1e3a8a;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא:", st.session_state.user_name)

    if st.session_state.user_name == "adminMednitai":
        st.markdown('<div class="admin-entry-btn">', unsafe_allow_html=True)
        if st.button("🚀 כניסה לממשק ניהול"):
            st.session_state.step = 'ADMIN_VIEW'; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 היסטוריה"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר אורך מבדק:")
                col1, col2, col3 = st.columns(3)
                config = [("⏳ תרגול קצר (36)", 36), ("📋 סימולציה (120)", 120), ("🔍 מבדק מלא (300)", 300)]
                for i, (label, count) in enumerate(config):
                    if [col1, col2, col3][i].button(label):
                        from logic import get_balanced_questions
                        st.session_state.questions = get_balanced_questions(all_qs_df, count)
                        st.session_state.step = 'QUIZ'; st.session_state.start_time = time.time(); st.rerun()

        with tab_archive:
            history = get_db_history(st.session_state.user_name)
            if history:
                for i, entry in enumerate(history):
                    with st.expander(f"📅 מבדק מ-{entry.get('test_date', 'לא ידוע')}"):
                        st.plotly_chart(get_comparison_chart(entry['results']), key=f"hist_{i}", use_container_width=True)
                        st.markdown(f'<div class="ai-report-box">{entry.get("ai_report", "אין דוח")}</div>', unsafe_allow_html=True)
            else: st.info("לא נמצאו מבדקים קודמים.")

elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="quiz_clock")
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time
        if elapsed > 8: st.warning("⚠️ עברו 8 שניות נא לענות בכנות")
            
        st.progress(q_idx / len(st.session_state.questions))
        st.write(f"שאלה **{q_idx + 1}** מתוך {len(st.session_state.questions)} | ⏱️ {int(elapsed)} ש' לשאלה")
        st.markdown(f'<div class="question-text">{q_data["q"]}</div>', unsafe_allow_html=True)

        options = [("בכלל לא", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)]
        cols = st.columns(5)
        for i, (label, val) in enumerate(options):
            if cols[i].button(label, key=f"b_{q_idx}_{val}"):
                record_answer(val, q_data); st.rerun()
    else:
        st.session_state.step = 'RESULTS'; st.rerun()

elif st.session_state.step == 'RESULTS':
    st.markdown(f'# 📊 דוח תוצאות - {st.session_state.user_name}')
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()

    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 התאמה לרפואה", f"{calculate_medical_fit(summary_df)}%")
    m2.metric("🛡️ אמינות", f"{calculate_reliability_index(df_raw)}%")
    m3.metric("⏱️ זמן ממוצע", f"{summary_df['avg_time'].mean():.1f} ש'")

    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True)
    with c2: st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True)

    # ניתוח AI בזמן אמת
    if not st.session_state.ai_report:
        with st.spinner("AI מנתח את התוצאות שלך..."):
            gem_rep, claude_rep = get_multi_ai_analysis(st.session_state.user_name, trait_scores, [])
            st.session_state.ai_report = gem_rep
            # שמירה אוטומטית למסד הנתונים
            save_to_db(st.session_state.user_name, trait_scores, gem_rep)

    st.markdown(f'<div class="ai-report-box" style="border-right-color: #1e3a8a;">{st.session_state.ai_report}</div>', unsafe_allow_html=True)

    col_pdf, col_reset = st.columns(2)
    with col_pdf:
        pdf = create_pdf_report(summary_df, df_raw)
        st.download_button("📥 הורד דוח PDF", pdf, f"Report_{st.session_state.user_name}.pdf")
    with col_reset:
        if st.button("🏁 חזרה לתפריט"):
            for k in ['step', 'responses', 'current_q', 'questions', 'ai_report']: st.session_state.pop(k, None)
            st.rerun()
