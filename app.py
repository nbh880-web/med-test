import streamlit as st
import time
import pandas as pd
import random
from logic import (
    calculate_score, 
    process_results, 
    get_profile_match, 
    analyze_consistency, 
    create_pdf_report
)
from gemini_ai import get_ai_analysis

# הגדרות דף ו-RTL
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# עיצוב CSS משודרג
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
    .ai-report-box { 
        background-color: #f8f9fa; 
        padding: 20px; 
        border-right: 5px solid #2e86de; 
        border-radius: 5px; 
        line-height: 1.6;
    }
    /* עיצוב שדה הקלט */
    input { text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# טעינת שאלות מה-CSV
@st.cache_data
def load_questions():
    try:
        df = pd.read_csv('data/questions.csv')
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת קובץ השאלות: {e}")
        return pd.DataFrame()

# פונקציה לבחירת שאלות מאוזנת
def get_balanced_questions(df, total_limit):
    traits = df['trait'].unique()
    qs_per_trait = total_limit // len(traits)
    selected_qs = []
    
    for trait in traits:
        trait_qs = df[df['trait'] == trait].to_dict('records')
        if len(trait_qs) >= qs_per_trait:
            selected_qs.extend(random.sample(trait_qs, qs_per_trait))
        else:
            selected_qs.extend(trait_qs) # אם אין מספיק שאלות, קח את כולן
            
    random.shuffle(selected_qs)
    return selected_qs

# אתחול משתני Session State
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# פונקציית שמירת תשובה
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

# --- מסכי האפליקציה ---

if st.session_state.step == 'HOME':
    st.title("🏥 מערכת סימולציה HEXACO לרפואה")
    st.subheader("תרגול ממוקד לזיהוי עקביות ואמינות")
    
    # הוספת שדה שם
    st.session_state.user_name = st.text_input("הכנס את שמך המלא:", st.session_state.user_name)
    
    all_qs_df = load_questions()
    
    if all_qs_df.empty:
        st.warning("לא נמצאו שאלות ב-data/questions.csv")
    elif not st.session_state.user_name:
        st.info("אנא הכנס שם כדי להמשיך לבחירת סימולציה.")
    else:
        st.write(f"שלום {st.session_state.user_name}, בחר את סוג הסימולציה:")
        col1, col2, col3 = st.columns(3)
        
        configs = [
            ("⏳ תרגול מהיר (36)", 36, col1),
            ("📋 סימולציה רגילה (120)", 120, col2),
            ("🔍 סימולציה מלאה (300)", 300, col3)
        ]
        
        for label, limit, col in configs:
            if col.button(label):
                st.session_state.questions = get_balanced_questions(all_qs_df, limit)
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
    st.title(f"📊 דוח אישיות ואמינות - {st.session_state.user_name}")
    
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()
    
    st.subheader("📋 סיכום ציונים וטווחים")
    summary_df['עומד בטווח?'] = summary_df['final_score'].apply(
        lambda x: "✅ כן" if 3.5 <= x <= 4.5 else "❌ לא"
    )
    st.table(summary_df[['trait', 'final_score', 'עומד בטווח?']].rename(columns={
        'trait': 'תכונה', 'final_score': 'ציון ממוצע'
    }))

    st.subheader("🎯 התאמה לפרופיל רופא")
    status_map = get_profile_match(trait_scores)
    cols = st.columns(len(status_map))
    for i, (trait, status) in enumerate(status_map.items()):
        cols[i].metric(label=trait, value=f"{trait_scores[trait]:.2f}", delta=status)

    # הצגת התראות עקביות ברמזור
    st.subheader("⚠️ בקרת עקביות (Reliability)")
    alerts = analyze_consistency(df_raw)
    if not alerts:
        st.success("עקביות מצוינת! לא נמצאו סתירות מהותיות בתשובותייך.")
    else:
        for alert in alerts:
            if alert['level'] == 'red':
                st.error(alert['text'])
            else:
                st.warning(alert['text'])

    st.divider()

    st.subheader("🤖 ניתוח מערכת וייצוא דוח")
    if st.button("צור ניתוח AI והכן דוח PDF להורדה"):
        with st.spinner("מנתח נתונים עבורך..."):
            ai_data = summary_df.to_string()
            # שים לב: שלחנו את השם לפונקציה של ה-AI
            report_text = get_ai_analysis(st.session_state.user_name, ai_data)
            
            st.markdown("### חוות דעת AI אישית:")
            st.markdown(f'<div class="ai-report-box">{report_text}</div>', unsafe_allow_html=True)
            
            try:
                pdf_bytes = create_pdf_report(summary_df, st.session_state.responses)
                st.download_button(
                    label="📥 הורד דוח PDF להדפסה",
                    data=pdf_bytes,
                    file_name=f"HEXACO_Report_{st.session_state.user_name}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"שגיאה בהפקת ה-PDF: {e}")

    if st.button("חזרה למסך הבית"):
        for key in ['step', 'responses', 'current_q', 'questions', 'user_name']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
