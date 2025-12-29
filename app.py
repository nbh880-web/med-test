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
    st.error("⚠️ חלק מקבצי העזר (database/gemini_ai) חסרים בתיקייה.")

# --- 1. הגדרות דף ו-CSS (תמיכה מלאה ב-RTL) ---
st.set_page_config(
    page_title="Mednitai HEXACO System", 
    layout="wide",
    initial_sidebar_state="collapsed" 
)

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { min-width: 280px !important; background-color: #f1f3f6; }
    div.stButton > button {
        width: 100%; border-radius: 8px; height: 70px !important; 
        font-size: 18px !important; background-color: white; color: #212529;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: 0.3s;
    }
    div.stButton > button:hover { border-color: #1e3a8a; color: #1e3a8a; }
    .admin-entry-btn button { background-color: #1e3a8a !important; color: white !important; }
    .question-text { 
        font-size: 38px; font-weight: 800; text-align: center; 
        padding: 40px 20px; color: #1a2a6c; background-color: #f8f9fa; 
        border-radius: 15px; margin-bottom: 25px; border: 1px solid #e9ecef;
    }
    .ai-report-box { 
        padding: 25px; border-right: 8px solid #1e3a8a; border-radius: 12px; 
        background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        line-height: 1.8; text-align: right; font-size: 17px;
    }
    .stProgress > div > div > div > div { background-color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. אתחול Session State ---
def init_session():
    defaults = {
        'step': 'HOME', 'responses': [], 'current_q': 0, 
        'user_name': "", 'questions': [], 'start_time': 0, 'ai_report': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# --- 3. פונקציות עזר ---
@st.cache_data
def load_questions():
    try: return pd.read_csv('data/questions.csv')
    except: return pd.DataFrame()

def record_answer(ans_value, q_data):
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
    st.sidebar.markdown(f"### 🔑 מחובר כסופר-אדמין")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.step = 'HOME'; st.rerun()

    st.title("📊 מערכת ניהול ובקרת מבדקים")
    all_data = get_all_tests()
    if not all_data:
        st.info("טרם בוצעו מבדקים במערכת."); return

    df = pd.DataFrame(all_data)
    df['tokens'] = df['ai_report'].apply(lambda x: int(len(str(x).split()) * 1.6) if x else 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ מבדקים", len(df))
    m2.metric("משתמשים ייחודיים", df['user_name'].nunique())
    m3.metric("ממוצע טוקנים לניתוח", int(df['tokens'].mean()))

    st.divider()
    search = st.text_input("🔍 חיפוש מועמד לפי שם:")
    if search:
        df = df[df['user_name'].str.contains(search, case=False)]

    st.dataframe(df[['user_name', 'test_date', 'test_time', 'tokens']], use_container_width=True)

    if not df.empty:
        selected_idx = st.selectbox("בחר מועמד לתצוגה מלאה:", df.index, 
                                    format_func=lambda x: f"{df.loc[x, 'user_name']} ({df.loc[x, 'test_date']})")
        
        row = df.loc[selected_idx]
        col_rep, col_gauge = st.columns([2, 1])
        with col_rep:
            st.subheader(f"ניתוח עבור: {row['user_name']}")
            st.markdown(f'<div class="ai-report-box">{row["ai_report"]}</div>', unsafe_allow_html=True)
        with col_gauge:
            # הוספת Key ייחודי למניעת שגיאת Duplicate ID
            st.plotly_chart(create_token_gauge(row["ai_report"]), use_container_width=True, key=f"admin_gauge_{selected_idx}")
            if "results" in row:
                st.plotly_chart(get_radar_chart(row["results"]), use_container_width=True, key=f"admin_radar_{selected_idx}")

# --- 5. ניווט ראשי ---
if st.session_state.user_name == "adminMednitai" and st.session_state.step == 'ADMIN_VIEW':
    show_admin_dashboard()

elif st.session_state.step == 'HOME':
    st.markdown('<h1 style="color: #1e3a8a;">🏥 Mednitai: סימולטור HEXACO לרפואה</h1>', unsafe_allow_html=True)
    name_input = st.text_input("הכנס שם מלא לתחילת המבדק:", value=st.session_state.user_name)
    st.session_state.user_name = name_input

    if name_input == "adminMednitai":
        if st.button("🚀 כניסה לממשק ניהול", key="admin_btn"):
            st.session_state.step = 'ADMIN_VIEW'; st.rerun()

    elif name_input:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 היסטוריית מבדקים"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.info(f"שלום {name_input}, ברוך הבא לסימולטור. בחר את אורך המבדק הרצוי:")
                col1, col2, col3 = st.columns(3)
                config = [("⏳ תרגול קצר (36)", 36), ("📋 סימולציה (120)", 120), ("🔍 מבדק מלא (300)", 300)]
                for i, (label, count) in enumerate(config):
                    if [col1, col2, col3][i].button(label, key=f"cfg_{count}"):
                        from logic import get_balanced_questions
                        st.session_state.questions = get_balanced_questions(all_qs_df, count)
                        st.session_state.step = 'QUIZ'; st.session_state.start_time = time.time(); st.rerun()
        
        with tab_archive:
            history = get_db_history(name_input)
            if history:
                for i, entry in enumerate(history):
                    with st.expander(f"📅 מבדק מיום {entry.get('test_date')} בשעה {entry.get('test_time')}"):
                        st.plotly_chart(get_radar_chart(entry['results']), key=f"hist_chart_{i}", use_container_width=True)
                        st.markdown(f'<div class="ai-report-box">{entry.get("ai_report", "אין דוח")}</div>', unsafe_allow_html=True)
            else: st.info("לא נמצאו מבדקים קודמים עבורך.")

elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="quiz_timer")
    q_idx = st.session_state.current_q
    
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time
        
        # תצוגה עליונה
        prog = (q_idx) / len(st.session_state.questions)
        st.progress(prog)
        c_left, c_right = st.columns([1,1])
        c_left.write(f"שאלה **{q_idx + 1}** מתוך {len(st.session_state.questions)}")
        c_right.write(f"⏱️ זמן לשאלה: **{int(elapsed)}** שניות")
        
        if elapsed > 10: st.warning("⚠️ שים לב: זמן תגובה ארוך מדי עלול להעיד על חוסר ספונטניות.")
        
        st.markdown(f'<div class="question-text">{q_data["q"]}</div>', unsafe_allow_html=True)

        options = [("בכלל לא", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)]
        cols = st.columns(5)
        for i, (label, val) in enumerate(options):
            if cols[i].button(label, key=f"ans_{q_idx}_{val}"):
                record_answer(val, q_data); st.rerun()
        
        # כפתור חזרה (רק אם אנחנו לא בשאלה הראשונה)
        if q_idx > 0:
            if st.button("⬅️ חזור לשאלה הקודמת", key="back_btn"):
                st.session_state.current_q -= 1
                st.session_state.responses.pop()
                st.rerun()
    else:
        st.session_state.step = 'RESULTS'; st.rerun()

elif st.session_state.step == 'RESULTS':
    st.markdown(f'# 📊 דוח ניתוח אישיות - {st.session_state.user_name}')
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()

    m1, m2, m3 = st.columns(3)
    fit_score = calculate_medical_fit(summary_df)
    m1.metric("🎯 התאמה לרפואה", f"{fit_score}%")
    m2.metric("🛡️ מדד אמינות", f"{calculate_reliability_index(df_raw)}%")
    m3.metric("⏱️ קצב מענה ממוצע", f"{summary_df['avg_time'].mean():.1f} שניות")

    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True, key="res_radar")
    with c2: st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True, key="res_bar")

    # ניתוח AI - מתרחש רק פעם אחת
    if st.session_state.ai_report is None:
        with st.spinner("🤖 מנוע ה-AI מנתח את הפרופיל שלך מול דרישות מס\"ר..."):
            try:
                # שליחת היסטוריה לניתוח מגמות אם קיימת
                hist = get_db_history(st.session_state.user_name)
                gem_rep, _ = get_multi_ai_analysis(st.session_state.user_name, trait_scores, hist)
                st.session_state.ai_report = gem_rep
                save_to_db(st.session_state.user_name, trait_scores, gem_rep)
            except Exception as e:
                st.error(f"שגיאה בהפקת דוח AI: {e}")
                st.session_state.ai_report = "לא ניתן היה להפיק דוח AI כרגע."

    st.markdown(f'<div class="ai-report-box">{st.session_state.ai_report}</div>', unsafe_allow_html=True)

    st.divider()
    col_pdf, col_reset = st.columns(2)
    with col_pdf:
        pdf_data = create_pdf_report(summary_df, df_raw)
        st.download_button("📥 הורד דוח PDF מלא", pdf_data, f"HEXACO_{st.session_state.user_name}.pdf")
    
    with col_reset:
        if st.button("🏁 סיום וחזרה לתפריט"):
            # איפוס מבוקר של ה-Session
            for k in ['step', 'responses', 'current_q', 'questions', 'ai_report']:
                st.session_state[k] = [] if k in ['responses', 'questions'] else (0 if k=='current_q' else ('HOME' if k=='step' else None))
            st.rerun()
