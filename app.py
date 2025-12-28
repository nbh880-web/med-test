import streamlit as st
import time
import pandas as pd
import random
from streamlit_autorefresh import st_autorefresh

# --- ייבוא לוגיקה עסקית (logic.py) ---
from logic import (
    calculate_score, 
    process_results, 
    analyze_consistency, 
    create_pdf_report,
    get_inconsistent_questions,
    get_static_interpretation,
    get_balanced_questions
)

# --- ייבוא שכבת הנתונים וה-AI (database.py & gemini_ai.py) ---
from database import save_to_db, get_db_history, get_all_tests
from gemini_ai import (
    get_multi_ai_analysis, 
    get_comparison_chart, 
    get_radar_chart, 
    create_token_gauge
)

# --- 1. הגדרות דף ו-CSS מקיף (RTL ועיצוב כפתורים מלא) ---
st.set_page_config(
    page_title="Mednitai HEXACO System", 
    layout="wide",
    initial_sidebar_state="collapsed" 
)

st.markdown("""
    <style>
    /* הגדרות RTL כלליות */
    .stApp, div[data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    
    /* תיקון סיידבר */
    [data-testid="stSidebar"] { min-width: 280px !important; background-color: #f1f3f6; }
    [data-testid="stSidebar"] * {
        word-break: normal !important;
        white-space: normal !important;
        text-align: right;
    }

    /* עיצוב כפתורי התשובות והניווט */
    div.stButton > button {
        width: 100%; border-radius: 8px; border: 1px solid #ced4da;
        height: 75px !important; 
        font-size: 19px !important; 
        line-height: 1.2 !important;
        background-color: white; color: #212529; font-weight: 500;
        margin-bottom: 10px;
        display: flex; align-items: center; justify-content: center;
    }
    
    /* כפתור מנהל ייעודי */
    .admin-entry-btn button {
        background-color: #1e3a8a !important;
        color: white !important;
        font-weight: bold !important;
    }

    /* עיצוב טקסט השאלה (ההיגד) */
    .question-text { 
        font-size: 42px; font-weight: 800; text-align: center; 
        padding: 40px 20px; color: #1a2a6c; line-height: 1.2;
        background-color: #f8f9fa; border-radius: 15px; margin-bottom: 20px;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.02);
    }

    /* תיבות דוח AI */
    .ai-report-box { 
        padding: 25px; border-right: 8px solid; border-radius: 12px; 
        line-height: 1.8; text-align: right; font-size: 17px; 
        white-space: pre-wrap; color: #333; background-color: #ffffff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }

    /* התאמות למובייל */
    @media (max-width: 768px) {
        .question-text { font-size: 24px !important; padding: 20px 10px !important; }
        div.stButton > button { height: 60px !important; font-size: 17px !important; }
    }
    
    input { text-align: right; direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. אתחול Session State (ניהול זיכרון מלא) ---
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []
if 'start_time' not in st.session_state: st.session_state.start_time = time.time()
if 'gemini_report' not in st.session_state: st.session_state.gemini_report = None
if 'claude_report' not in st.session_state: st.session_state.claude_report = None

# --- 3. פונקציות עזר לניהול המבדק ---
@st.cache_data
def load_all_questions():
    try: return pd.read_csv('data/questions.csv')
    except: return pd.DataFrame()

def record_answer_full(ans_value, q_data):
    duration = time.time() - st.session_state.start_time
    score = calculate_score(ans_value, q_data['reverse'])
    st.session_state.responses.append({
        'question': q_data['q'], 'trait': q_data['trait'], 'original_answer': ans_value,
        'final_score': score, 'time_taken': duration, 'reverse': q_data['reverse']
    })
    st.session_state.current_q += 1
    st.session_state.start_time = time.time()

# --- 4. ממשק ניהול (ADMIN) - כולל השוואה מלאה ---
def show_admin_dashboard():
    st.sidebar.markdown(f"### 🔑 מנהל מחובר: \n**{st.session_state.user_name}**")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.user_name = ""; st.session_state.step = 'HOME'; st.rerun()

    st.title("📊 לוח בקרת מנהל - Mednitai")
    all_data = get_all_tests()
    if not all_data:
        st.info("אין נתונים בבסיס הנתונים."); return

    df_admin = pd.DataFrame(all_data)
    df_admin['tokens'] = df_admin['ai_report'].apply(lambda x: int(len(str(x).split()) * 1.6) if x else 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ מבדקים", len(df_admin))
    m2.metric("משתמשים ייחודיים", df_admin['user_name'].nunique())
    m3.metric("ממוצע טוקנים לדוח", int(df_admin['tokens'].mean()))

    search = st.text_input("🔍 חפש מועמד (לפי שם):")
    if search:
        df_admin = df_admin[df_admin['user_name'].str.contains(search, case=False)]
    
    st.dataframe(df_admin[['user_name', 'test_date', 'tokens']], use_container_width=True)

    if not df_admin.empty:
        sel_idx = st.selectbox("בחר מועמד לתצוגה מפורטת:", df_admin.index, 
                               format_func=lambda x: f"{df_admin.loc[x, 'user_name']} ({df_admin.loc[x, 'test_date']})")
        
        col_rep, col_viz = st.columns([2, 1])
        with col_rep:
            t_gem, t_claude = st.tabs(["🤖 דוח Gemini", "☁️ דוח Claude"])
            with t_gem:
                st.markdown(f'<div class="ai-report-box" style="border-right-color: #1e3a8a;">{df_admin.loc[sel_idx, "ai_report"]}</div>', unsafe_allow_html=True)
            with t_claude:
                claude_val = df_admin.loc[sel_idx].get('claude_report', "לא נשמר דוח קלוד למבדק זה.")
                st.markdown(f'<div class="ai-report-box" style="border-right-color: #d97706;">{claude_val}</div>', unsafe_allow_html=True)
        with col_viz:
            st.plotly_chart(create_token_gauge(df_admin.loc[sel_idx, "ai_report"]), use_container_width=True)
            if 'results' in df_admin.columns:
                st.plotly_chart(get_radar_chart(df_admin.loc[sel_idx, "results"]), use_container_width=True)

# --- 5. ניווט ראשי (HOME / QUIZ / RESULTS) ---
if st.session_state.step == 'ADMIN_VIEW':
    show_admin_dashboard()

elif st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: right; color: #1e3a8a;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא:", st.session_state.user_name)
    
    if st.session_state.user_name == "adminMednitai":
        st.markdown('<div class="admin-entry-btn">', unsafe_allow_html=True)
        if st.button("🚀 כניסה לממשק ניהול"):
            st.session_state.step = 'ADMIN_VIEW'; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_name and st.session_state.user_name != "adminMednitai":
        tab_n, tab_h = st.tabs(["📝 מבחן חדש", "📜 היסטוריה אישית"])
        with tab_n:
            qs_df = load_all_questions()
            if not qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר את אורך המבדק:")
                c1, c2, c3 = st.columns(3)
                if c1.button("⏳ תרגול קצר (36)"):
                    st.session_state.questions = get_balanced_questions(qs_df, 36)
                    st.session_state.step = 'QUIZ'; st.session_state.current_q = 0; st.session_state.responses = []; st.rerun()
                if c2.button("📋 סימולציה סטנדרטית (120)"):
                    st.session_state.questions = get_balanced_questions(qs_df, 120)
                    st.session_state.step = 'QUIZ'; st.session_state.current_q = 0; st.session_state.responses = []; st.rerun()
                if c3.button("🔍 מבדק מלא (300)"):
                    st.session_state.questions = get_balanced_questions(qs_df, 300)
                    st.session_state.step = 'QUIZ'; st.session_state.current_q = 0; st.session_state.responses = []; st.rerun()
        with tab_h:
            hist = get_db_history(st.session_state.user_name)
            if hist:
                for i, entry in enumerate(hist):
                    with st.expander(f"📅 מבדק מ-{entry.get('test_date')}"):
                        st.plotly_chart(get_radar_chart(entry['results']), key=f"hist_r_{i}")
                        st.write(entry.get('ai_report'))
            else: st.info("לא נמצאו מבדקים קודמים.")

elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="quiz_timer")
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time
        
        if elapsed > 8:
            st.warning("⚠️ עברו מעל 8 שניות. ענה לפי התחושה הראשונה!")
            
        st.progress(q_idx / len(st.session_state.questions))
        st.write(f"שאלה **{q_idx + 1}** מתוך {len(st.session_state.questions)} | ⏱️ {int(elapsed)} שניות")
        st.markdown(f'<div class="question-text">{q_data["q"]}</div>', unsafe_allow_html=True)
        
        cols = st.columns(5)
        options = [("בכלל לא", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)]
        for i, (label, val) in enumerate(options):
            if cols[i].button(label, key=f"btn_{q_idx}_{val}"):
                record_answer_full(val, q_data); st.rerun()
    else:
        st.session_state.step = 'RESULTS'; st.rerun()

elif st.session_state.step == 'RESULTS':
    st.markdown(f'# 📊 דוח תוצאות סופי - {st.session_state.user_name}')
    df_raw, summary_df = process_results(st.session_state.responses)
    scores = summary_df.set_index('trait')['final_score'].to_dict()

    # תצוגה גרפית משולבת (Radar + Comparison)
    g1, g2 = st.columns(2)
    with g1: st.plotly_chart(get_radar_chart(scores), use_container_width=True)
    with g2: st.plotly_chart(get_comparison_chart(scores), use_container_width=True)

    st.divider()
    st.subheader("🧠 ניתוח אישיות והתאמה לרפואה (AI Comparison)")
    
    if st.session_state.gemini_report is None:
        with st.spinner("מבצע ניתוח מעמיק מול שני מודלי AI..."):
            user_h = get_db_history(st.session_state.user_name)
            gem_rep, cld_rep = get_multi_ai_analysis(st.session_state.user_name, scores, user_h)
            st.session_state.gemini_report = gem_rep
            st.session_state.claude_report = cld_rep
            # שמירה ל-DB (שומר את ה-Gemini כדו"ח ראשי)
            save_to_db(st.session_state.user_name, scores, gem_rep)

    # לשוניות השוואה תמידיות
    t_res_gem, t_res_cld = st.tabs(["🤖 ניתוח Gemini (מודל ראשי)", "☁️ ניתוח Claude (נקודת מבט נוספת)"])
    with t_res_gem:
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #1e3a8a;">{st.session_state.gemini_report}</div>', unsafe_allow_html=True)
        st.plotly_chart(create_token_gauge(st.session_state.gemini_report), use_container_width=True)
    with t_res_cld:
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #d97706;">{st.session_state.claude_report}</div>', unsafe_allow_html=True)

    # ניתוח עקביות מ-logic.py
    with st.expander("🔍 ניתוח אמינות ועקביות המבדק"):
        alerts = analyze_consistency(df_raw)
        if alerts:
            for a in alerts: st.warning(f"- {a['text']}")
        else: st.success("המבדק נמצא בעל מהימנות גבוהה.")
        
        incon_qs = get_inconsistent_questions(df_raw)
        if not incon_qs.empty:
            st.write("שאלות שקיבלו ציונים סותרים:")
            st.dataframe(incon_qs)

    # הפקת PDF
    pdf = create_pdf_report(summary_df, df_raw)
    st.download_button("📥 הורד דוח PDF מלא", data=pdf, file_name=f"HEXACO_{st.session_state.user_name}.pdf")

    if st.button("🏁 סיום וחזרה לתפריט"):
        for k in ['step', 'responses', 'current_q', 'questions', 'gemini_report', 'claude_report']:
            if k in st.session_state: del st.session_state[k]
        st.rerun()