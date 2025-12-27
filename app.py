import streamlit as st
import time
import pandas as pd
import random
from streamlit_autorefresh import st_autorefresh

# ייבוא לוגיקה עסקית - שימור כל הפונקציות מהקובץ logic.py
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

# ייבוא שכבת הבינה המלאכותית (Gemini & Graphs)
from gemini_ai import get_multi_ai_analysis, get_comparison_chart, get_radar_chart

# 1. הגדרות דף ו-RTL (יישור לימין)
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# 2. אתחול משתני Session State - ניהול מצב האפליקציה
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []
if 'start_time' not in st.session_state: st.session_state.start_time = time.time()

# עיצוב CSS מלא - יישור לימין, כפתורים נקיים ותיבות AI צבעוניות
st.markdown("""
    <style>
    .stApp, div[data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    
    /* עיצוב כפתורי תשובה מקצועיים */
    div.stButton > button {
        width: 100%; border-radius: 8px; border: 1px solid #ced4da;
        height: 60px; font-size: 18px; transition: all 0.2s; 
        background-color: white; color: #212529; font-weight: 500;
    }
    div.stButton > button:hover {
        border-color: #1e90ff; background-color: #f8f9fa; color: #1e90ff;
    }
    
    .question-text { font-size: 30px; font-weight: bold; text-align: center; padding: 40px; color: #2c3e50; }
    
    /* תיבות הדיווח של ה-AI */
    .ai-report-box { 
        padding: 25px; border-right: 8px solid; 
        border-radius: 12px; line-height: 1.7; text-align: right; font-size: 16px; 
        white-space: pre-wrap; min-height: 500px; color: #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    input { text-align: right; direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_questions():
    """טעינת מאגר השאלות מקובץ CSV"""
    try:
        df = pd.read_csv('data/questions.csv')
        return df
    except Exception as e:
        st.error(f"שגיאה קריטית בטעינת מאגר השאלות: {e}")
        return pd.DataFrame()

def get_balanced_questions(df, total_limit):
    """בחירת שאלות מאוזנת לפי תכונות"""
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
    """שמירת תשובה ואיפוס השעון לשאלה הבאה"""
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
    # עדכון זמן התחלה לשאלה הבאה
    st.session_state.start_time = time.time()

# --- ניווט בין מסכי המערכת ---

if st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: right; color: #1e3a8a;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא לזיהוי במערכת:", st.session_state.user_name)
    
    if st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 היסטוריית מבדקים"])
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר את היקף הסימולציה שברצונך לבצע:")
                col1, col2, col3 = st.columns(3)
                
                configs = [
                    (col1, "⏳ תרגול קצר (36 שאלות)", 36),
                    (col2, "📋 סימולציה רגילה (120 שאלות)", 120),
                    (col3, "🔍 מבדק מלא (300 שאלות)", 300)
                ]
                
                for col, label, count in configs:
                    if col.button(label):
                        st.session_state.questions = get_balanced_questions(all_qs_df, count)
                        st.session_state.step = 'QUIZ'
                        st.session_state.current_q = 0
                        st.session_state.responses = []
                        st.session_state.start_time = time.time()
                        st.rerun()

        with tab_archive:
            history = get_db_history(st.session_state.user_name)
            if history:
                for i, entry in enumerate(history):
                    with st.expander(f"📅 מבדק מיום {entry.get('test_date')} ({entry.get('test_time')})"):
                        st.plotly_chart(get_comparison_chart(entry['results']), key=f"hist_chart_{i}")
                        st.markdown(f'<div class="ai-report-box" style="background-color:#f8f9fa; border-right-color:#cbd5e1;">{entry.get("ai_report", "אין דוח זמין")}</div>', unsafe_allow_html=True)
            else:
                st.info("לא נמצאו מבדקים קודמים עבור משתמש זה.")

elif st.session_state.step == 'QUIZ':
    # הפעלת רענון אוטומטי (שעון חי) כל שנייה
    st_autorefresh(interval=1000, key="quiz_clock")
    
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        
        # חישוב זמן שעבר מתחילת השאלה
        elapsed = time.time() - st.session_state.start_time
        
        # תצוגת התקדמות
        st.progress((q_idx) / len(st.session_state.questions))
        st.write(f"שאלה **{q_idx + 1}** מתוך **{len(st.session_state.questions)}**")
        
        # וידג'ט שעון
        if elapsed > 10:
            st.warning(f"זמן שעבר: {int(elapsed)} שניות. נסה לענות מהר יותר לפי אינטואיציה.", icon="⏳")
        else:
            st.info(f"זמן לשאלה זו: {int(elapsed)} שניות")

        st.markdown(f'<p class="question-text">{q_data["q"]}</p>', unsafe_allow_html=True)
        
        # כפתורי תשובה נקיים
        options = [
            ("בכלל לא מסכים", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)
        ]
        
        cols = st.columns(5)
        for i, (label, val) in enumerate(options):
            if cols[i].button(label, key=f"btn_{q_idx}_{val}"):
                record_answer(val, q_data)
                st.rerun()
    else:
        st.session_state.step = 'RESULTS'
        st.rerun()

elif st.session_state.step == 'RESULTS':
    st.markdown(f'<h1 style="text-align: right;">📊 דוח תוצאות מפורט - {st.session_state.user_name}</h1>', unsafe_allow_html=True)
    
    # 1. עיבוד נתונים
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()
    
    # 2. ויזואליזציה (גרפים)
    col_radar, col_bar = st.columns(2)
    with col_radar:
        st.markdown("### 🕸️ פרופיל אישיות היקפי")
        st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True)
    with col_bar:
        st.markdown("### 📊 השוואה לפרופיל יעד רפואי")
        st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True)
    
    st.divider()

    # 3. ניתוח עקביות (תיקון ה-AttributeError על ידי המרה ל-DataFrame)
    df_responses_final = pd.DataFrame(st.session_state.responses)
    consistency_score = analyze_consistency(df_responses_final)
    inconsistent_qs = get_inconsistent_questions(df_responses_final)
    
    if consistency_score < 75:
        st.error(f"⚠️ מדד עקביות: {consistency_score}% - שים לב לסתירות מהותיות בתשובותיך.")
        with st.expander("לחץ כאן לצפייה בשאלות שבהן לא היית עקבי:"):
            for item in inconsistent_qs:
                st.write(f"• {item}")
    else:
        st.success(f"✅ מדד עקביות מעולה: {consistency_score}% - התשובות מהימנות.")

    st.divider()

    # 4. פרשנות מובנית לכל תכונה
    st.markdown("### 🔍 ניתוח תכונות מעמיק")
    for _, row in summary_df.iterrows():
        st.info(f"**{row['trait']}:** {get_static_interpretation(row['trait'], row['final_score'])}")

    st.divider()
    
    # 5. פאנל בוחני AI (Gemini & Claude)
    st.markdown("### 🤖 פאנל בוחני AI: ניתוח רב-מודלי")
    
    if 'ai_multi_reports' not in st.session_state:
        with st.spinner("הבוחנים מגבשים חוות דעת מקצועית..."):
            past_history = get_db_history(st.session_state.user_name)
            g_report, c_report = get_multi_ai_analysis(st.session_state.user_name, trait_scores, past_history)
            st.session_state.ai_multi_reports = (g_report, c_report)
            
            # שמירה למסד הנתונים
            combined = f"--- Gemini ---\n{g_report}\n\n--- Claude ---\n{c_report}"
            save_to_db(st.session_state.user_name, trait_scores, combined)

    col_g, col_c = st.columns(2)
    with col_g:
        st.markdown('<p style="color:#1E90FF; font-weight:bold; font-size:22px;">🛡️ בוחן 1: Gemini (Google)</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #1E90FF; background-color: #f0f7ff;">{st.session_state.ai_multi_reports[0]}</div>', unsafe_allow_html=True)
    
    with col_c:
        st.markdown('<p style="color:#D97757; font-weight:bold; font-size:22px;">🔮 בוחן 2: Claude (Anthropic)</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #D97757; background-color: #fffaf0;">{st.session_state.ai_multi_reports[1]}</div>', unsafe_allow_html=True)

    st.divider()

    # 6. פעולות סיום (PDF וחזרה לבית)
    col_pdf, col_home = st.columns(2)
    with col_pdf:
        pdf_data = create_pdf_report(summary_df, st.session_state.responses)
        st.download_button(
            label="📥 הורד דוח PDF מלא",
            data=pdf_data,
            file_name=f"HEXACO_Report_{st.session_state.user_name}.pdf",
            mime="application/pdf"
        )
    with col_home:
        if st.button("🏁 סיום וחזרה לתפריט הראשי"):
            # ניקוי בטוח של ה-session
            keys = ['step', 'responses', 'current_q', 'questions', 'ai_multi_reports', 'start_time']
            for k in keys:
                if k in st.session_state: del st.session_state[k]
            st.rerun()