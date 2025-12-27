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
from database import save_to_db, get_db_history
from gemini_ai import get_multi_ai_analysis, get_comparison_chart, get_radar_chart

# 1. הגדרות דף ו-RTL
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# 2. אתחול Session State
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []
if 'start_time' not in st.session_state: st.session_state.start_time = time.time()

# עיצוב CSS למבנה RTL נקי
st.markdown("""
    <style>
    .stApp, div[data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    
    div.stButton > button {
        width: 100%; border-radius: 8px; border: 1px solid #ced4da;
        height: 60px; font-size: 18px; transition: all 0.2s; 
        background-color: white; color: #212529; font-weight: 500;
    }
    div.stButton > button:hover {
        border-color: #1e90ff; background-color: #f8f9fa; color: #1e90ff;
    }
    
    .question-text { font-size: 30px; font-weight: bold; text-align: center; padding: 40px; color: #2c3e50; line-height: 1.4; }
    
    .ai-report-box { 
        padding: 25px; border-right: 8px solid; border-radius: 12px; 
        line-height: 1.7; text-align: right; font-size: 16px; 
        white-space: pre-wrap; min-height: 500px; color: #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
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
        count = min(len(trait_qs), qs_per_trait)
        selected_qs.extend(random.sample(trait_qs, count))
    random.shuffle(selected_qs)
    return selected_qs

def record_answer(ans_value, q_data):
    # מניעת רישום כפול אם המשתמש לוחץ מהר מדי
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

# --- ניווט בין מסכים ---

if st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: right; color: #1e3a8a;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא לזיהוי במערכת:", st.session_state.user_name)
    
    if st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 היסטוריית מבדקים"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר את היקף הסימולציה:")
                col1, col2, col3 = st.columns(3)
                
                # כפתורי בחירה עם איפוס מונים
                if col1.button("⏳ תרגול קצר (36 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 36)
                    st.session_state.current_q = 0
                    st.session_state.responses = []
                    st.session_state.step = 'QUIZ'
                    st.session_state.start_time = time.time()
                    st.rerun()
                if col2.button("📋 סימולציה רגילה (120 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 120)
                    st.session_state.current_q = 0
                    st.session_state.responses = []
                    st.session_state.step = 'QUIZ'
                    st.session_state.start_time = time.time()
                    st.rerun()
                if col3.button("🔍 מבדק מלא (300 שאלות)"):
                    st.session_state.questions = get_balanced_questions(all_qs_df, 300)
                    st.session_state.current_q = 0
                    st.session_state.responses = []
                    st.session_state.step = 'QUIZ'
                    st.session_state.start_time = time.time()
                    st.rerun()

        with tab_archive:
            history = get_db_history(st.session_state.user_name)
            if history:
                for i, entry in enumerate(history):
                    date_val = entry.get('test_date', 'לא ידוע')
                    with st.expander(f"📅 מבחן מיום {date_val}"):
                        if 'results' in entry:
                            st.plotly_chart(get_comparison_chart(entry['results']), key=f"h_{i}")
                        st.write(entry.get('ai_report', 'אין דוח טקסטואלי שמור'))
            else:
                st.info("לא נמצאו מבדקים קודמים עבור שם זה.")

elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="quiz_clock")
    
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time
        
        st.progress((q_idx) / len(st.session_state.questions))
        st.write(f"שאלה **{q_idx + 1}** מתוך {len(st.session_state.questions)}")
        
        if elapsed > 8:
            st.warning(f"זמן לשאלה: {int(elapsed)} שניות. נסה לענות מהר יותר.", icon="⏳")
        else:
            st.info(f"זמן לשאלה זו: {int(elapsed)} שניות")

        st.markdown(f'<p class="question-text">{q_data["q"]}</p>', unsafe_allow_html=True)
        
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
    
    # 1. עיבוד נתונים והכנה
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()
    
    # 2. הצגת גרפים
    
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True)
    with c2: st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True)
    
    st.divider()

    # 3. בדיקת עקביות (הגנה מ-TypeError)
    df_for_logic = pd.DataFrame(st.session_state.responses)
    consistency_score = analyze_consistency(df_for_logic)
    inconsistent_qs = get_inconsistent_questions(df_for_logic)
    
    if isinstance(consistency_score, (int, float)):
        if consistency_score < 75:
            st.error(f"⚠️ מדד עקביות: {consistency_score}%")
            if inconsistent_qs:
                with st.expander("ראה שאלות שסתרו זו את זו"):
                    for item in inconsistent_qs: st.write(f"• {item}")
        else:
            st.success(f"✅ מדד עקביות גבוה: {consistency_score}%")
    else:
        st.info("מדד העקביות מחושב על בסיס התשובות שלך...")

    st.divider()

    # 4. ניתוח תכונות סטטי
    st.markdown("### 🔍 ניתוח תכונות מובנה")
    for _, row in summary_df.iterrows():
        st.info(f"**{row['trait']}:** {get_static_interpretation(row['trait'], row['final_score'])}")

    st.divider()
    
    # 5. בוחני AI (שימוש ב-cache בתוך ה-session)
    if 'ai_multi_reports' not in st.session_state:
        with st.spinner("בוחני ה-AI מנתחים את הפרופיל שלך..."):
            hist = get_db_history(st.session_state.user_name)
            # אם אין היסטוריה, נשלח רשימה ריקה
            hist = hist if hist else []
            g_report, c_report = get_multi_ai_analysis(st.session_state.user_name, trait_scores, hist)
            st.session_state.ai_multi_reports = (g_report, c_report)
            
            # שמירה למסד הנתונים
            save_to_db(st.session_state.user_name, trait_scores, f"Gemini: {g_report}\nClaude: {c_report}")

    cg, cc = st.columns(2)
    with cg:
        st.markdown('<p style="color:#1E90FF; font-weight:bold; font-size:20px;">🛡️ Gemini (בוחן א\')</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #1E90FF; background-color: #f0f7ff;">{st.session_state.ai_multi_reports[0]}</div>', unsafe_allow_html=True)
    with cc:
        st.markdown('<p style="color:#D97757; font-weight:bold; font-size:20px;">🔮 Claude (בוחן ב\')</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #D97757; background-color: #fffaf0;">{st.session_state.ai_multi_reports[1]}</div>', unsafe_allow_html=True)

    st.divider()

    # 6. פעולות סיום
    cp, ch = st.columns(2)
    with cp:
        try:
            pdf = create_pdf_report(summary_df, st.session_state.responses)
            st.download_button("📥 הורד דוח PDF מלא", data=pdf, file_name=f"HEXACO_{st.session_state.user_name}.pdf")
        except:
            st.warning("הכנת ה-PDF נכשלה, אך ניתן לצפות בתוצאות כאן.")
    with ch:
        if st.button("🏁 חזרה לתפריט הראשי"):
            # ניקוי בטוח של המצב ללא מחיקת ה-User Name
            for k in ['step', 'responses', 'current_q', 'questions', 'ai_multi_reports', 'start_time']:
                st.session_state.pop(k, None)
            st.rerun()