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

# ייבוא שכבת הנתונים וה-AI
from database import save_to_db, get_db_history, get_all_tests
from gemini_ai import get_multi_ai_analysis, get_comparison_chart, get_radar_chart, create_token_gauge

# --- 1. הגדרות דף ו-CSS (RTL עם התאמה למובייל) ---
st.set_page_config(page_title="Mednitai HEXACO System", layout="wide")

st.markdown("""
    <style>
    .stApp, div[data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    
    /* עיצוב כפתורי התשובות - כללי */
    div.stButton > button {
        width: 100%; border-radius: 8px; border: 1px solid #ced4da;
        height: 65px; font-size: 20px; transition: all 0.2s; 
        background-color: white; color: #212529; font-weight: 500;
        margin-bottom: 10px;
    }
    div.stButton > button:hover {
        border-color: #1e90ff; background-color: #f8f9fa; color: #1e90ff;
    }
    
    /* הגדרות היגד (שאלה) למחשב */
    .question-text { 
        font-size: 42px; 
        font-weight: 800; 
        text-align: center; 
        padding: 50px 20px; 
        color: #1a2a6c; 
        line-height: 1.3;
        background-color: #f8f9fa;
        border-radius: 15px;
        margin-bottom: 30px;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.02);
    }

    /* --- התאמה לטלפונים ניידים (מובייל) --- */
    @media (max-width: 768px) {
        .question-text {
            font-size: 24px; /* הקטנה משמעותית לטלפון */
            padding: 25px 15px;
            margin-bottom: 20px;
        }
        div.stButton > button {
            height: 55px; /* קיצור גובה הכפתורים */
            font-size: 18px;
            margin-bottom: 8px;
        }
        .main .block-container {
            padding-top: 1rem;
            padding-right: 1rem;
            padding-left: 1rem;
        }
    }
    
    .ai-report-box { 
        padding: 25px; border-right: 8px solid; border-radius: 12px; 
        line-height: 1.7; text-align: right; font-size: 16px; 
        white-space: pre-wrap; min-height: 500px; color: #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    input { text-align: right; direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. אתחול Session State ---
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []
if 'start_time' not in st.session_state: st.session_state.start_time = time.time()

# --- 3. פונקציות עזר (טעינה, איזון והקלטה) ---
@st.cache_data
def load_questions():
    try:
        return pd.read_csv('data/questions.csv')
    except Exception as e:
        st.error(f"שגיאה בטעינת קובץ השאלות: {e}")
        return pd.DataFrame()

def get_balanced_questions(df, total_limit):
    traits = df['trait'].unique()
    qs_per_trait = total_limit // len(traits)
    selected_qs = []
    for trait in traits:
        trait_qs = df[df['trait'] == trait].to_dict('records')
        count = min(len(trait_qs), qs_per_trait)
        selected_qs.extend(random.sample(trait_qs, count))
    random.shuffle(selected_qs)
    return selected_qs

def record_answer(ans_value, q_data):
    if st.session_state.current_q >= len(st.session_state.questions):
        return
    duration = time.time() - st.session_state.start_time
    score = calculate_score(ans_value, q_data['reverse'])
    st.session_state.responses.append({
        'question': q_data['q'],
        'trait': q_data['trait'],
        'original_answer': ans_value,
        'final_score': score,
        'time_taken': duration,
        'reverse': q_data['reverse']
    })
    st.session_state.current_q += 1
    st.session_state.start_time = time.time()

# --- 4. פונקציית דף הניהול (ADMIN) ---
def show_admin_dashboard():
    st.sidebar.title(f"🔑 מנהל: {st.session_state.user_name}")
    if st.sidebar.button("התנתק וחזור לדף הבית"):
        st.session_state.user_name = ""
        st.session_state.step = 'HOME'
        st.rerun()

    st.title("📊 לוח בקרת מנהל - Mednitai")
    
    all_data = get_all_tests()
    if not all_data:
        st.info("אין עדיין נתונים ב-Firestore.")
        return

    df = pd.DataFrame(all_data)
    df['tokens'] = df['ai_report'].apply(lambda x: int(len(str(x).split()) * 1.6))

    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ מבדקים", len(df))
    m2.metric("משתמשים שונים", df['user_name'].nunique())
    m3.metric("ממוצע טוקנים", int(df['tokens'].mean()))

    st.divider()
    search = st.text_input("🔍 חפש מועמד:")
    if search:
        df = df[df['user_name'].str.contains(search, case=False)]
    
    st.dataframe(df[['user_name', 'test_date', 'test_time', 'tokens']], use_container_width=True)

    st.subheader("📄 פירוט דוח ומצב טוקנים")
    if not df.empty:
        selected_idx = st.selectbox("בחר מועמד לצפייה בדוח:", df.index, format_func=lambda x: f"{df.loc[x, 'user_name']} ({df.loc[x, 'test_date']})")
        col_rep, col_gauge = st.columns([2, 1])
        with col_rep:
            st.markdown(f'<div class="ai-report-box" style="border-right-color: #1e3a8a; background-color: #f9f9f9;">{df.loc[selected_idx, "ai_report"]}</div>', unsafe_allow_html=True)
        with col_gauge:
            st.plotly_chart(create_token_gauge(df.loc[selected_idx, "ai_report"]), use_container_width=True)
            st.info(f"טוקנים בדוח זה: {df.loc[selected_idx, 'tokens']}")

# --- 5. ניווט ראשי ---

if st.session_state.user_name == "adminMednitai":
    show_admin_dashboard()

elif st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: right; color: #1e3a8a;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא לזיהוי במערכת:", st.session_state.user_name)
    
    if st.session_state.user_name == "adminMednitai":
        st.rerun()

    if st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 היסטוריית מבדקים"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר היקף סימולציה:")
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
                    with st.expander(f"📅 מבחן מיום {entry.get('test_date', 'לא ידוע')}"):
                        st.plotly_chart(get_comparison_chart(entry['results']), key=f"h_{i}")
                        st.write(entry.get('ai_report', 'אין דוח שמור'))
            else: st.info("לא נמצאו מבדקים קודמים.")

elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="quiz_clock")
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time
        st.progress(q_idx / len(st.session_state.questions))
        st.write(f"שאלה **{q_idx + 1}** מתוך {len(st.session_state.questions)}")
        
        if elapsed > 8: st.warning(f"זמן לשאלה: {int(elapsed)} שניות. נסה לענות מהר יותר.")
        else: st.info(f"זמן לשאלה זו: {int(elapsed)} שניות")

        st.markdown(f'<div class="question-text">{q_data["q"]}</div>', unsafe_allow_html=True)
        options = [("בכלל לא מסכים", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)]
        cols = st.columns(5)
        for i, (label, val) in enumerate(options):
            if cols[i].button(label, key=f"b_{q_idx}_{val}"):
                record_answer(val, q_data)
                st.rerun()
    else:
        st.session_state.step = 'RESULTS'
        st.rerun()

elif st.session_state.step == 'RESULTS':
    st.markdown(f'# 📊 דוח תוצאות - {st.session_state.user_name}')
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()

    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True)
    with c2: st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True)

    # ניתוח עקביות
    df_logic = pd.DataFrame(st.session_state.responses)
    consistency_score = analyze_consistency(df_logic)
    if isinstance(consistency_score, list): consistency_score = consistency_score[0]
    
    if consistency_score < 75:
        st.error(f"⚠️ מדד עקביות: {consistency_score}%")
        inconsistent = get_inconsistent_questions(df_logic)
        if inconsistent:
            with st.expander("ראה שאלות שסתרו זו את זו"):
                for item in inconsistent: st.write(f"• {item}")
    else:
        st.success(f"✅ מדד עקביות גבוה: {consistency_score}%")

    st.divider()
    st.markdown("### 🔍 ניתוח תכונות מובנה")
    for _, row in summary_df.iterrows():
        st.info(f"**{row['trait']}:** {get_static_interpretation(row['trait'], row['final_score'])}")

    # בוחני AI
    st.divider()
    st.markdown("### 🤖 ניתוח מעמיק על ידי בוחני AI")
    if st.button("🔄 רענן דוח AI"):
        st.session_state.pop('ai_multi_reports', None)
        st.rerun()

    if 'ai_multi_reports' not in st.session_state:
        with st.spinner("בוחני ה-AI מנתחים..."):
            hist = get_db_history(st.session_state.user_name)
            g_report, c_report = get_multi_ai_analysis(st.session_state.user_name, trait_scores, hist)
            st.session_state.ai_multi_reports = (g_report, c_report)
            save_to_db(st.session_state.user_name, trait_scores, f"Gemini: {g_report}\n\nClaude: {c_report}")

    cg, cc = st.columns(2)
    with cg:
        st.markdown('<p style="color:#1E90FF; font-weight:bold;">🛡️ Gemini</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #1E90FF;">{st.session_state.ai_multi_reports[0]}</div>', unsafe_allow_html=True)
    with cc:
        st.markdown('<p style="color:#D97757; font-weight:bold;">🔮 Claude</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #D97757;">{st.session_state.ai_multi_reports[1]}</div>', unsafe_allow_html=True)

    st.divider()
    cp, ch = st.columns(2)
    with cp:
        try:
            pdf = create_pdf_report(summary_df, st.session_state.responses)
            st.download_button("📥 הורד דוח PDF מלא", data=pdf, file_name=f"HEXACO_{st.session_state.user_name}.pdf")
        except: st.warning("הכנת ה-PDF נכשלה.")
    with ch:
        if st.button("🏁 חזרה לתפריט הראשי"):
            for k in ['step', 'responses', 'current_q', 'questions', 'ai_multi_reports']:
                st.session_state.pop(k, None)
            st.rerun()