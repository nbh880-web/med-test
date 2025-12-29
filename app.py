import streamlit as st
import time
import pandas as pd
import random
import json
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ייבוא הלוגיקה המורכבת (הלב של האפליקציה)
import logic 

# ==========================================
# 1. פונקציות עזר ותצוגה (AI וגרפים)
# ==========================================
def create_token_gauge(text):
    tokens = int(len(str(text).split()) * 1.6)
    fig = go.Figure(go.Indicator(mode="gauge+number", value=tokens, title={'text': "Tokens"},
                                   gauge={'axis': {'range': [None, 3000]}, 'bar': {'color': "#1e3a8a"}}))
    fig.update_layout(height=250)
    return fig

def get_radar_chart(scores):
    categories = list(scores.keys())
    values = list(scores.values())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', name='הפרופיל שלך'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 5])), showlegend=False)
    return fig

def get_multi_ai_analysis(name, scores, history):
    """מנוע ה-AI המשולב - ללא שינוי לוגיקה, רק תיקון שגיאות"""
    keys = [st.secrets.get("GEMINI_KEY_1", ""), st.secrets.get("GEMINI_KEY_2", "")]
    claude_key = st.secrets.get("CLAUDE_KEY", "")
    prompt = f"Analyze HEXACO for {name}: {json.dumps(scores)} in Hebrew based on medical school requirements."
    
    gem_report = "⚠️ שגיאה בחיבור ל-Gemini"
    for k in [key for key in keys if key]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={k}"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if res.status_code == 200:
                gem_report = res.json()['candidates'][0]['content']['parts'][0]['text']
                break
        except: continue
    
    claude_report = "⚠️ שגיאה בחיבור ל-Claude"
    if claude_key:
        try:
            headers = {"x-api-key": claude_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            res = requests.post("https://api.anthropic.com/v1/messages", headers=headers,
                                json={"model": "claude-3-5-sonnet-20240620", "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}, timeout=20)
            if res.status_code == 200: claude_report = res.json()['content'][0]['text']
        except: pass
    return gem_report, claude_report

# ==========================================
# 2. ממשק משתמש (Frontend)
# ==========================================
st.set_page_config(page_title="Mednitai HEXACO", layout="wide", initial_sidebar_state="collapsed")

# הזרקת CSS לשיפור המראה ושמירה על RTL
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div.stButton > button {
        width: 100%; border-radius: 8px; height: 75px !important; font-size: 19px !important; 
        background-color: white; color: #212529; font-weight: 500; margin-bottom: 10px;
        border: 1px solid #dee2e6;
    }
    .question-text { 
        font-size: 32px; font-weight: 800; text-align: center; padding: 40px; 
        color: #1a2a6c; background-color: #f8f9fa; border-radius: 15px; margin-bottom: 20px;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.05);
    }
    .ai-report-box { 
        padding: 25px; border-right: 8px solid; border-radius: 12px; font-size: 17px; 
        background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.08); min-height: 400px;
    }
    </style>
    """, unsafe_allow_html=True)

# אתחול Session State - מוודא שכלום לא נעלם ברענון
if 'step' not in st.session_state: st.session_state.step = 'HOME'
if 'responses' not in st.session_state: st.session_state.responses = []
if 'current_q' not in st.session_state: st.session_state.current_q = 0
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'questions' not in st.session_state: st.session_state.questions = []
if 'start_time' not in st.session_state: st.session_state.start_time = time.time()
if 'gemini_report' not in st.session_state: st.session_state.gemini_report = None
if 'claude_report' not in st.session_state: st.session_state.claude_report = None

# --- מסך בית ---
if st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: center; color: #1e3a8a;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא למילוי המבדק:", st.session_state.user_name)
    
    if st.session_state.user_name == "adminMednitai":
        if st.button("🚀 כניסה לממשק ניהול"):
            st.session_state.step = 'ADMIN_VIEW'
            st.rerun()

    if st.session_state.user_name and st.session_state.user_name != "adminMednitai":
        tab1, tab2 = st.tabs(["📝 מבחן חדש", "📜 היסטוריה אישית"])
        with tab1:
            try:
                qs_df = pd.read_csv('data/questions.csv')
                c1, c2 = st.columns(2)
                if c1.button("⏳ מבדק קצר (36 שאלות)"):
                    st.session_state.questions = logic.get_balanced_questions(qs_df, 36)
                    st.session_state.step = 'QUIZ'
                    st.rerun()
                if c2.button("📋 מבדק מלא (120 שאלות)"):
                    st.session_state.questions = logic.get_balanced_questions(qs_df, 120)
                    st.session_state.step = 'QUIZ'
                    st.rerun()
            except:
                st.error("שגיאה בטעינת קובץ השאלות. וודא ש-data/questions.csv קיים.")

# --- מסך מבדק (QUIZ) ---
elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="quiz_timer")
    q_idx = st.session_state.current_q
    
    if q_idx < len(st.session_state.questions):
        q = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time
        
        # התקדמות
        st.progress(q_idx / len(st.session_state.questions))
        st.write(f"שאלה {q_idx + 1} מתוך {len(st.session_state.questions)}")
        
        st.markdown(f'<div class="question-text">{q["q"]}</div>', unsafe_allow_html=True)
        
        cols = st.columns(5)
        opts = [("בכלל לא", 1), ("לא", 2), ("נייטרלי", 3), ("מסכים", 4), ("מאוד", 5)]
        
        for i, (label, val) in enumerate(opts):
            if cols[i].button(label, key=f"btn_{q_idx}_{val}"):
                # שימוש בלוגיקה של logic.py לחישוב הציון
                final_score = logic.calculate_score(val, q['reverse'])
                st.session_state.responses.append({
                    'trait': q['trait'], 
                    'final_score': final_score, 
                    'original_answer': val,
                    'time_taken': elapsed,
                    'question': q['q']
                })
                st.session_state.current_q += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        st.session_state.step = 'RESULTS'
        st.rerun()

# --- מסך תוצאות ---
elif st.session_state.step == 'RESULTS':
    st.title(f"📊 דוח תוצאות עבור: {st.session_state.user_name}")
    
    # עיבוד נתונים באמצעות הלב (logic.py)
    df_raw, summary = logic.process_results(st.session_state.responses)
    scores = summary.set_index('trait')['final_score'].to_dict()
    
    medical_fit = logic.calculate_medical_fit(summary)
    reliability = logic.calculate_reliability_index(df_raw)
    
    # תצוגת מדדים עליונה
    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 התאמה לרפואה", f"{medical_fit}%")
    m2.metric("🛡️ מדד אמינות", f"{reliability}%")
    m3.metric("⏱️ זמן ממוצע לשאלה", f"{summary['avg_time'].mean():.1f} ש'")
    
    # גרף רדאר
    st.plotly_chart(get_radar_chart(scores), use_container_width=True)
    
    # התראות עקביות
    alerts = logic.analyze_consistency(df_raw)
    for alert in alerts:
        st.warning(alert['text'])

    # ניתוח AI
    if not st.session_state.gemini_report:
        with st.spinner("ה-AI מנתח את הפרופיל שלך לעומק..."):
            st.session_state.gemini_report, st.session_state.claude_report = get_multi_ai_analysis(st.session_state.user_name, scores, [])
    
    t1, t2 = st.tabs(["🤖 Gemini Analysis", "☁️ Claude Insights"])
    with t1:
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #1e3a8a;">{st.session_state.gemini_report}</div>', unsafe_allow_html=True)
    with t2:
        st.markdown(f'<div class="ai-report-box" style="border-right-color: #d97706;">{st.session_state.claude_report}</div>', unsafe_allow_html=True)
    
    # כפתור PDF (חיבור לפונקציה מ-logic.py)
    if st.button("📥 הורד דוח PDF מלא"):
        pdf_bytes = logic.create_pdf_report(summary, df_raw)
        st.download_button("לחץ להורדה", data=pdf_bytes, file_name=f"HEXACO_{st.session_state.user_name}.pdf")

    if st.button("🏁 סיום וחזרה לתפריט"):
        for k in ['responses', 'current_q', 'gemini_report', 'claude_report', 'questions']:
            st.session_state[k] = [] if isinstance(st.session_state[k], list) else None
        st.session_state.step = 'HOME'
        st.rerun()
