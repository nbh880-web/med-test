import streamlit as st
import time
import pandas as pd
import random

# ייבוא לוגיקה עסקית
from logic import (
    calculate_score, 
    process_results, 
    analyze_consistency, 
    create_pdf_report
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

# עיצוב CSS מקצועי
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
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
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
    duration = time.time() - st.session_state.start_time
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
    st.title("🏥 מערכת סימולציה HEXACO - הכנה למס\"ר")
    st.subheader("ניתוח אישיות מקצועי מבוסס ענן ובינה מלאכותית")
    
    st.session_state.user_name = st.text_input("הכנס את שמך המלא להתחלה:", st.session_state.user_name)
    
    if st.session_state.user_name:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 ארכיון מבחנים קודמים"])
        
        with tab_new:
            all_qs_df = load_questions()
            if not all_qs_df.empty:
                st.write(f"שלום **{st.session_state.user_name}**, בחר את אורך הסימולציה:")
                col1, col2, col3 = st.columns(3)
                configs = [
                    ("⏳ תרגול מהיר (36 שאלות)", 36, col1),
                    ("📋 סימולציה רגילה (120 שאלות)", 120, col2),
                    ("🔍 סימולציה מלאה (300 שאלות)", 300, col3)
                ]
                for label, limit, col in configs:
                    if col.button(label):
                        st.session_state.questions = get_balanced_questions(all_qs_df, limit)
                        st.session_state.step = 'QUIZ'
                        st.session_state.start_time = time.time()
                        st.rerun()

        with tab_archive:
            st.subheader(f"היסטוריית תרגול עבור: {st.session_state.user_name}")
            with st.spinner("שולף נתונים מהענן..."):
                history = get_db_history(st.session_state.user_name)
                if not history:
                    st.info("לא נמצאו מבחנים קודמים המקושרים לשם זה.")
                else:
                    for entry in history:
                        date_label = f"סימולציה מיום {entry.get('test_date')} בשעה {entry.get('test_time')}"
                        with st.expander(date_label):
                            # תיקון אזהרת use_container_width
                            st.plotly_chart(get_comparison_chart(entry['results']), width='stretch')
                            st.markdown(f'<div class="ai-report-box">{entry["ai_report"]}</div>', unsafe_allow_html=True)

elif st.session_state.step == 'QUIZ':
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        st.progress((q_idx) / len(st.session_state.questions))
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
    st.title(f"📊 דוח תוצאות מסכם - {st.session_state.user_name}")
    
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()
    
    st.subheader("📊 השוואה לפרופיל רופא יעד")
    # תיקון אזהרת use_container_width
    st.plotly_chart(get_comparison_chart(trait_scores), width='stretch')

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📋 ציוני תכונות")
        summary_df['סטטוס'] = summary_df['final_score'].apply(lambda x: "✅ תקין" if 3.5 <= x <= 4.5 else "⚠️ דורש תשומת לב")
        st.table(summary_df[['trait', 'final_score', 'סטטוס']].rename(columns={'trait': 'תכונה', 'final_score': 'ציון'}))
    
    with col_b:
        st.subheader("⚠️ בקרת עקביות")
        alerts = analyze_consistency(df_raw)
        if not alerts:
            st.success("לא נמצאו סתירות מהותיות. התשובות נראות עקביות ומהימנות.")
        else:
            for alert in alerts:
                if alert['level'] == 'red': st.error(alert['text'])
                else: st.warning(alert['text'])

    st.divider()

    st.subheader("🤖 ניתוח מאמן AI והכנת דוח סופי")
    if st.button("הפק ניתוח AI ושמור לארכיון"):
        with st.spinner("המאמן חוקר מודלים ומנתח נתונים..."):
            # 1. שליפת היסטוריה לצורך הניתוח
            history = get_db_history(st.session_state.user_name)
            
            # 2. קבלת ניתוח מה-AI (הפונקציה עכשיו משתמשת ב-Explorer פנימי)
            report_text = get_ai_analysis(st.session_state.user_name, trait_scores, history)
            
            # 3. שמירה של הכל (כולל הניתוח) ב-Database
            save_to_db(st.session_state.user_name, trait_scores, report_text)
            
            st.markdown("### 💡 תובנות והכנה למס\"ר:")
            st.markdown(f'<div class="ai-report-box">{report_text}</div>', unsafe_allow_html=True)
            
            try:
                pdf_bytes = create_pdf_report(summary_df, st.session_state.responses)
                st.download_button(
                    label="📥 הורד דוח PDF מלא",
                    data=pdf_bytes,
                    file_name=f"HEXACO_Report_{st.session_state.user_name}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"שגיאה ביצירת PDF: {e}")

    if st.button("חזרה למסך הבית"):
        for key in ['step', 'responses', 'current_q', 'questions']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
