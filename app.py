import streamlit as st
import time
import pandas as pd
import random
import json
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ==========================================
# 1. לוגיקה עסקית (logic.py) - מוטמעת
# ==========================================
def calculate_score(val, reverse):
    return (6 - val) if reverse else val

def process_results(responses):
    df_raw = pd.DataFrame(responses)
    summary_df = df_raw.groupby('trait').agg(
        final_score=('final_score', 'mean'),
        avg_time=('time_taken', 'mean')
    ).reset_index()
    return df_raw, summary_df

def get_balanced_questions(df, count):
    if df.empty: return []
    traits = df['trait'].unique()
    per_trait = count // len(traits)
    selected = []
    for t in traits:
        trait_qs = df[df['trait'] == t]
        selected.extend(trait_qs.sample(min(per_trait, len(trait_qs))).to_dict('records'))
    random.shuffle(selected)
    return selected

def calculate_medical_fit(summary_df):
    ideal = {"Honesty-Humility": 4.5, "Emotionality": 3.2, "Extraversion": 3.8, 
             "Agreeableness": 4.2, "Conscientiousness": 4.6, "Openness": 3.5}
    scores = summary_df.set_index('trait')['final_score'].to_dict()
    diffs = [abs(scores.get(t, 3) - ideal.get(t, 3)) for t in ideal]
    return int(max(0, 100 - (sum(diffs) * 6)))

def calculate_reliability_index(df_raw):
    fast_responses = len(df_raw[df_raw['time_taken'] < 1.5])
    penalty = fast_responses * 3
    return max(0, 100 - penalty)

def analyze_consistency(df_raw):
    alerts = []
    if df_raw['time_taken'].mean() < 2.0:
        alerts.append({"text": "זמן מענה ממוצע מהיר מדי - ייתכן חוסר ריכוז."})
    return alerts

# ==========================================
# 2. AI ונתונים (database/gemini_ai) - מוטמע
# ==========================================
def get_all_tests():
    # כאן ניתן לחבר DB אמיתי. כרגע מחזיר רשימה ריקה למניעת שגיאה.
    return []

def get_db_history(name):
    return []

def save_to_db(name, scores, report):
    pass

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
    keys = [st.secrets.get("GEMINI_KEY_1", ""), st.secrets.get("GEMINI_KEY_2", "")]
    claude_key = st.secrets.get("CLAUDE_KEY", "")
    prompt = f"Analyze HEXACO for {name}: {json.dumps(scores)} in Hebrew."
    
    gem_report = "⚠️ שגיאה ב-Gemini"
    for k in [key for key in keys if key]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={k}"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if res.status_code == 200:
                gem_report = res.json()['candidates'][0]['content']['parts'][0]['text']
                break
        except: continue
    
    claude_report = "⚠️ שגיאה ב-Claude"
    if claude_key:
        try:
            headers = {"x-api-key": claude_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            res = requests.post("https://api.anthropic.com/v1/messages", headers=headers,
                                json={"model": "claude-3-5-sonnet-20240620", "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}, timeout=20)
            if res.status_code == 200: claude_report = res.json()['content'][0]['text']
        except: pass
    return gem_report, claude_report

# ==========================================
# 3. ממשק משתמש (Frontend)
# ==========================================
st.set_page_config(page_title="Mednitai HEXACO", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div.stButton > button {
        width: 100%; border-radius: 8px; height: 75px !important; font-size: 19px !important; 
        background-color: white; color: #212529; font-weight: 500; margin-bottom: 10px;
    }
    .admin-entry-btn button { background-color: #1e3a8a !important; color: white !important; }
    .question-text { 
        font-size: 42px; font-weight: 800; text-align: center; padding: 40px; 
        color: #1a2a6c; background-color: #f8f9fa; border-radius: 15px; margin-bottom: 20px;
    }
    .ai-report-box { 
        padding: 25px; border-right: 8px solid; border-radius: 12px; font-size: 17px; 
        background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.08); min-height: 400px;
    }
    @media (max-width: 768px) { .question-text { font-size: 24px !important; } }
    </style>
    """, unsafe_allow_html=True)

# אתחול Session State
for key in ['step', 'responses', 'current_q', 'user_name', 'questions', 'start_time', 'gemini_report', 'claude_report']:
    if key not in st.session_state:
        st.session_state[key] = 'HOME' if key == 'step' else ([] if key in ['responses', 'questions'] else (0 if key == 'current_q' else (time.time() if key == 'start_time' else None)))

# --- ממשק ניהול ---
if st.session_state.step == 'ADMIN_VIEW':
    st.title("📊 לוח בקרת מנהל")
    if st.button("🚪 התנתק"): st.session_state.step = 'HOME'; st.rerun()
    all_data = get_all_tests()
    if not all_data: st.info("אין נתונים להצגה.")

# --- מסך בית ---
elif st.session_state.step == 'HOME':
    st.markdown('<h1 style="text-align: right; color: #1e3a8a;">🏥 סימולטור HEXACO למיוני רפואה</h1>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input("הכנס שם מלא:", st.session_state.user_name if st.session_state.user_name else "")
    
    if st.session_state.user_name == "adminMednitai":
        if st.button("🚀 כניסה לממשק ניהול"): st.session_state.step = 'ADMIN_VIEW'; st.rerun()

    if st.session_state.user_name and st.session_state.user_name != "adminMednitai":
        tab1, tab2 = st.tabs(["📝 מבחן חדש", "📜 היסטוריה"])
        with tab1:
            try: qs_df = pd.read_csv('data/questions.csv')
            except: qs_df = pd.DataFrame()
            if not qs_df.empty:
                c1, c2, c3 = st.columns(3)
                if c1.button("⏳ קצר (36)"):
                    st.session_state.questions = get_balanced_questions(qs_df, 36)
                    st.session_state.step = 'QUIZ'; st.rerun()
                if c2.button("📋 סטנדרט (120)"):
                    st.session_state.questions = get_balanced_questions(qs_df, 120)
                    st.session_state.step = 'QUIZ'; st.rerun()

# --- מסך מבדק ---
elif st.session_state.step == 'QUIZ':
    st_autorefresh(interval=1000, key="quiz_timer")
    q_idx = st.session_state.current_q
    if q_idx < len(st.session_state.questions):
        q = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time
        st.progress(q_idx / len(st.session_state.questions))
        st.markdown(f'<div class="question-text">{q["q"]}</div>', unsafe_allow_html=True)
        cols = st.columns(5)
        opts = [("בכלל לא", 1), ("לא", 2), ("נייטרלי", 3), ("מסכים", 4), ("מאוד", 5)]
        for i, (label, val) in enumerate(opts):
            if cols[i].button(label, key=f"q_{q_idx}_{val}"):
                st.session_state.responses.append({'trait': q['trait'], 'final_score': calculate_score(val, q['reverse']), 'time_taken': elapsed})
                st.session_state.current_q += 1
                st.session_state.start_time = time.time()
                st.rerun()
    else: st.session_state.step = 'RESULTS'; st.rerun()

# --- מסך תוצאות ---
elif st.session_state.step == 'RESULTS':
    st.title(f"📊 דוח - {st.session_state.user_name}")
    df_raw, summary = process_results(st.session_state.responses)
    scores = summary.set_index('trait')['final_score'].to_dict()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 התאמה לרפואה", f"{calculate_medical_fit(summary)}%")
    m2.metric("🛡️ אמינות", f"{calculate_reliability_index(df_raw)}%")
    m3.metric("⏱️ זמן ממוצע", f"{summary['avg_time'].mean():.1f} ש'")
    
    st.plotly_chart(get_radar_chart(scores), use_container_width=True)

    if not st.session_state.gemini_report:
        with st.spinner("AI מנתח..."):
            st.session_state.gemini_report, st.session_state.claude_report = get_multi_ai_analysis(st.session_state.user_name, scores, [])
    
    t1, t2 = st.tabs(["🤖 Gemini", "☁️ Claude"])
    with t1: st.markdown(f'<div class="ai-report-box" style="border-right-color: #1e3a8a;">{st.session_state.gemini_report}</div>', unsafe_allow_html=True)
    with t2: st.markdown(f'<div class="ai-report-box" style="border-right-color: #d97706;">{st.session_state.claude_report}</div>', unsafe_allow_html=True)
    
    if st.button("🏁 חזור לתפריט"):
        for k in ['step', 'responses', 'current_q', 'gemini_report', 'claude_report']: st.session_state[k] = None
        st.session_state.step = 'HOME'; st.rerun()
