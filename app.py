import streamlit as st
import time
import pandas as pd
import random
from logic import (
    calculate_score, 
    check_response_time, 
    process_results, 
    get_profile_match, 
    analyze_consistency, 
    create_pdf_report
)
from gemini_ai import get_ai_analysis

# הגדרות דף ו-RTL
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# עיצוב CSS לתיקון כיווניות ומראה הכפתורים
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    div.stButton > button {
        width: 100%; border-radius: 12px; border: 1px solid #d1d8e0;
        height: 60px; font-size: 18px; transition: all 0.2s;
    }
    div.stButton > button:hover {
        border-color: #2e86de; background-color: #f0f7ff !important; color: #2e86de !important;
    }
    .question-text { font-size: 30px; font-weight: bold; text-align: center; padding: 40px; color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)

# טעינת שאלות מה-CSV
@st.cache_data
def load_questions():
    try:
        # הנתיב חייב להתאים למבנה ב-GitHub
        df = pd.read_csv('data/questions.csv')
        return df.to_dict('records')
    except Exception as e:
        st.error(f"שגיאה בטעינת קובץ השאלות: {e}")
        return []

# אתחול משתני Session State
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0

# פונקציית שמירת תשובה
def record_answer(ans_value, q_data):
    duration = time.time() - st.session_state.start_time
    
    # חישוב הציון האמיתי (כולל הפיכת סולם במידת הצורך)
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

# --- מסכי האפליקציה ---

if st.session_state.step == 'HOME':
    st.title("🏥 מערכת סימולציה HEXACO לרפואה")
    st.subheader("תרגול ממוקד לזיהוי עקביות ואמינות")
    
    all_qs = load_questions()
    
    if not all_qs:
        st.warning("לא נמצאו שאלות בקובץ הנתונים. וודא שקובץ data/questions.csv קיים.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⏳ תרגול מהיר (36)"):
                st.session_state.limit = 36
                st.session_state.questions = random.sample(all_qs, min(36, len(all_qs)))
                st.session_state.step = 'QUIZ'
                st.session_state.start_time = time.time()
                st.rerun()
        with col2:
            if st.button("📋 סימולציה רגילה (120)"):
                st.session_state.limit = 120
                st.session_state.questions = random.sample(all_qs, min(120, len(all_qs)))
                st.session_state.step = 'QUIZ'
                st.session_state.start_time = time.time()
                st.rerun()
        with col3:
            if st.button("🔍 סימולציה מלאה (300)"):
                st.session_state.limit = 300
                st.session_state.questions = random.sample(all_qs, min(300, len(all_qs)))
                st.session_state.step = 'QUIZ'
                st.session_state.start_time = time.time()
                st.rerun()

elif st.session_state.step == 'QUIZ':
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        
        st.write(f"שאלה {q_idx + 1} מתוך {len(st.session_state.questions)}")
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

elif st.session_state.step == 'RESULTS':
    st.title("📊 דוח ניתוח אישיות ואמינות")
    
    # 1. עיבוד נתונים
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()
    
    # 2. הצגת טבלת סיכום וטווחים
    st.subheader("📋 סיכום ציונים וטווחים")
    
    summary_df['עומד בטווח?'] = summary_df['final_score'].apply(
        lambda x: "✅ כן" if 3.5 <= x <= 4.5 else "❌ לא"
    )
    
    st.table(summary_df[['trait', 'final_score', 'עומד בטווח?']].rename(columns={
        'trait': 'תכונה',
        'final_score': 'ציון ממוצע'
    }))

    # 3. תצוגת רמזורים
    st.subheader("🎯 התאמה לפרופיל רופא")
    status_map = get_profile_match(trait_scores)
    cols = st.columns(len(status_map))
    for i, (trait, status) in enumerate(status_map.items()):
        cols[i].metric(label=trait, value=f"{trait_scores[trait]:.2f}", delta=status)

    # 4. התראות עקביות
    alerts = analyze_consistency(df_raw)
    for alert in alerts:
        st.error(alert)

    st.divider()

    # 5. ניתוח AI והורדת PDF
    st.subheader("🤖 ניתוח עומק וייצוא נתונים")
    
    if st.button("צור ניתוח AI והפק דוח PDF"):
        with st.spinner("מנתח נתונים ומכין את הקובץ..."):
            ai_data = summary_df.to_string()
            report = get_ai_analysis(ai_data)
            
            st.markdown("### חוות דעת מערכת:")
            st.write(report)
            
            try:
                pdf_bytes = create_pdf_report(summary_df, st.session_state.responses, report)
                st.download_button(
                    label="📥 הורד דוח PDF מלא",
                    data=pdf_bytes,
                    file_name="medical_test_report.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"שגיאה בהפקת ה-PDF: {e}")

    # כפתור חזרה
    if st.button("חזרה למסך הבית"):
        for key in ['step', 'responses', 'current_q', 'questions']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
