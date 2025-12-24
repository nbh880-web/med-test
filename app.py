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
# ייבוא הפונקציות החדשות מהמנוע המעודכן
from gemini_ai import get_ai_analysis, get_comparison_chart, get_history

# 1. הגדרות דף ו-RTL (חייב להיות בתחילת הקובץ)
st.set_page_config(page_title="HEXACO Medical Prep", layout="wide")

# 2. אתחול משתני Session State (למניעת NameError)
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# עיצוב CSS
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    div.stButton > button {
        width: 100%; border-radius: 12px; border: 1px solid #d1d8e0;
        height: 60px; font-size: 18px; transition: all 0.2s;
    }
    .question-text { font-size: 30px; font-weight: bold; text-align: center; padding: 40px; color: #2c3e50; }
    .ai-report-box { 
        background-color: #f8f9fa; 
        padding: 20px; 
        border-right: 5px solid #2e86de; 
        border-radius: 5px; 
        line-height: 1.6;
        text-align: right;
    }
    input { text-align: right; }
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
    st.subheader("תרגול ממוקד לזיהוי עקביות ואמינות")
    
    # הזנת שם משתמש
    st.session_state.user_name = st.text_input("הכנס את שמך המלא:", st.session_state.user_name)
    
    if st.session_state.user_name:
        # יצירת טאבים למסך הבית
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 ארכיון אישי"])
        
        with tab_new:
            all_qs_df = load_questions()
            if all_qs_df.empty:
                st.warning("לא נמצאו שאלות ב-data/questions.csv")
            else:
                st.write(f"שלום {st.session_state.user_name}, בחר סימולציה להתחלה:")
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

        with tab_archive:
            st.subheader(f"היסטוריית תרגול עבור: {st.session_state.user_name}")
            with st.spinner("טוען ארכיון..."):
                history = get_history(st.session_state.user_name)
                if not history:
                    st.info("לא נמצאו מבחנים קודמים בשם זה ב-Firebase.")
                else:
                    for entry in history:
                        time_str = entry.get('timestamp').strftime('%d/%m/%Y %H:%M') if entry.get('timestamp') else "תאריך לא ידוע"
                        with st.expander(f"סימולציה מתאריך: {time_str}"):
                            # הצגת גרף השוואתי מהארכיון
                            st.plotly_chart(get_comparison_chart(entry['results']), use_container_width=True)
                            st.markdown(f'<div class="ai-report-box">{entry["ai_report"]}</div>', unsafe_allow_html=True)

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
    st.title(f"📊 דוח הכנה למס\"ר - {st.session_state.user_name}")
    
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()
    
    # 1. גרף השוואתי (חדש)
    st.subheader("📊 השוואה לפרופיל היעד (רופא אופטימלי)")
    st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True)

    # 2. טבלת ציונים
    st.subheader("📋 סיכום ציונים וטווחים")
    summary_df['עומד בטווח?'] = summary_df['final_score'].apply(lambda x: "✅ כן" if 3.5 <= x <= 4.5 else "❌ לא")
    st.table(summary_df[['trait', 'final_score', 'עומד בטווח?']].rename(columns={'trait': 'תכונה', 'final_score': 'ציון ממוצע'}))

    # 3. בקרת עקביות
    st.subheader("⚠️ בקרת עקביות (Reliability)")
    alerts = analyze_consistency(df_raw)
    if not alerts:
        st.success("עקביות מצוינת! לא נמצאו סתירות מהותיות בתשובותייך.")
    else:
        for alert in alerts:
            if alert['level'] == 'red': st.error(alert['text'])
            else: st.warning(alert['text'])

    st.divider()

    # 4. ניתוח AI וייצוא
    st.subheader("🤖 ניתוח מאמן AI וייצוא דוח")
    if st.button("צור ניתוח הכנה למס\"ר והכן PDF"):
        with st.spinner("המאמן האישי מנתח את התוצאות מול היסטוריית הארכיון..."):
            report_text = get_ai_analysis(st.session_state.user_name, trait_scores)
            st.markdown("### 💡 טיפים והכנה למס\"ר:")
            st.markdown(f'<div class="ai-report-box">{report_text}</div>', unsafe_allow_html=True)
            
            try:
                pdf_bytes = create_pdf_report(summary_df, st.session_state.responses)
                st.download_button(
                    label="📥 הורד דוח PDF להדפסה",
                    data=pdf_bytes,
                    file_name=f"MSR_Prep_{st.session_state.user_name}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"שגיאה בהפקת ה-PDF: {e}")

    if st.button("חזרה למסך הבית"):
        for key in ['step', 'responses', 'current_q', 'questions']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
