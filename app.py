import streamlit as st
import time
import pandas as pd
import random
import json
import requests
import html
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import uuid
from enum import Enum

# --- סטטוסים (Enum במקום מחרוזות קסם) ---
class Step(str, Enum):
    HOME = "HOME"
    QUIZ = "QUIZ"
    RESULTS = "RESULTS"
    ADMIN_VIEW = "ADMIN_VIEW"

# --- ייבוא לוגיקה עסקית ---
from logic import (
    calculate_score,
    process_results,
    analyze_consistency,
    create_pdf_report,
    get_inconsistent_questions,
    get_static_interpretation,
    calculate_medical_fit,
    calculate_reliability_index,
    get_balanced_questions,
    create_excel_download
)

# --- ייבוא לוגיקת אמינות ---
try:
    from integrity_logic import (
        get_integrity_questions,
        calculate_integrity_score,
        process_integrity_results,
        calculate_reliability_score,
        get_integrity_interpretation,
        detect_contradictions,
        get_category_risk_level,
        INTEGRITY_CATEGORIES
    )
    INTEGRITY_AVAILABLE = True
except ImportError:
    INTEGRITY_AVAILABLE = False

# --- ייבוא שכבת נתונים ו-AI ---
try:
    from database import save_to_db, get_db_history, get_all_tests
    from gemini_ai import (
        get_multi_ai_analysis,
        get_comparison_chart,
        get_radar_chart,
        create_token_gauge
    )
    if INTEGRITY_AVAILABLE:
        try:
            from gemini_ai import get_integrity_ai_analysis, get_combined_ai_analysis
        except ImportError:
            pass
    try:
        from database import (
            save_integrity_test_to_db,
            save_combined_test_to_db,
            get_integrity_history,
            get_combined_history
        )
    except ImportError:
        pass
except ImportError:
    st.error("⚠️ חלק מקבצי העזר (database/gemini_ai) חסרים בתיקייה.")

# --- 1. הגדרות דף ו-CSS ---
st.set_page_config(
    page_title="Mednitai HEXACO System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_css(path: str = "styles.css"):
    """טוען קובץ CSS חיצוני לתוך הדף"""
    try:
        with open(path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"⚠️ קובץ עיצוב לא נמצא: {path}")

load_css()


def show_copyright():
    st.markdown('<div class="copyright-footer">© זכויות יוצרים לניתאי מלכה</div>', unsafe_allow_html=True)


# --- 2. אתחול Session State ---
def init_session():
    defaults = {
        'step': Step.HOME,
        'responses': [],
        'current_q': 0,
        'user_name': "",
        'questions': [],
        'start_time': 0,
        'gemini_report': None,
        'claude_report': None,
        'run_id': str(uuid.uuid4())[:8],
        'test_type': 'HEXACO',
        'reliability_score': None,
        'contradictions': [],
        'stress_active': False,
        'stress_start': 0,
        'stress_msg': "",
        'hesitation_count': 0
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session()


# --- 3. אפקט לחץ — ללא time.sleep() חוסם ---
def trigger_stress_effect():
    """מפעיל overlay ללא חסימת השרת — הcountdown מתבצע דרך autorefresh"""
    messages = [
        "מזהה סתירה פוטנציאלית בתשובותיך...",
        "מחשב מדד אמינות רגעית... נא להמתין",
        "מערכת הבקרה זיהתה חוסר עקביות בנתונים",
        "⚠️ בקרת איכות: נדרש ריכוז מקסימלי, המערכת מזהה ניסיון הטיה."
    ]
    st.session_state.stress_active = True
    st.session_state.stress_start = time.time()
    st.session_state.stress_msg = random.choice(messages)


# --- 4. פונקציות עזר ---
@st.cache_data
def load_questions_data():
    try:
        return pd.read_csv('data/questions.csv')
    except:
        return pd.DataFrame()


def record_answer(ans_value, q_data):
    duration = time.time() - st.session_state.start_time

    if duration > 8:
        st.session_state.hesitation_count += 1

    origin = q_data.get('origin', st.session_state.test_type)

    if origin == 'INTEGRITY' and INTEGRITY_AVAILABLE:
        score = calculate_integrity_score(ans_value, q_data['reverse'])
    else:
        score = calculate_score(ans_value, q_data.get('reverse', False))

    st.session_state.responses.append({
        'question': q_data['q'],
        'trait': q_data.get('trait') or q_data.get('category'),
        'category': q_data.get('category', ''),
        'control_type': q_data.get('control_type', 'none'),
        'origin': origin,
        'original_answer': ans_value,
        'final_score': score,
        'time_taken': duration,
        'reverse': q_data['reverse']
    })

    st.session_state.current_q += 1
    st.session_state.start_time = time.time()

    # תומך בערכים מהקוד (True) ומה-CSV (1, "1")
    is_stress_trigger = q_data.get('is_stress_meta') in [1, "1", True, "True"]
    if is_stress_trigger:
        trigger_stress_effect()
    st.rerun()


# --- 5. ממשק ניהול ---
def show_admin_dashboard():
    if st.button("🚪 התנתק וחזור לבית", key="admin_logout"):
        st.session_state.step = Step.HOME
        st.rerun()

    st.title("📊 מערכת ניהול: תיקי מועמדים")

    all_data = get_all_tests()
    if not all_data:
        st.info("טרם בוצעו מבדקים במערכת.")
        return

    df = pd.DataFrame(all_data)

    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ מבדקים", len(df))
    m2.metric("מועמדים ייחודיים", df['user_name'].nunique())
    avg_hesitation = df['hesitation_count'].mean() if 'hesitation_count' in df.columns else 0
    m3.metric("ממוצע היסוס מערכתי", f"{avg_hesitation:.1f}")

    st.divider()

    unique_users = sorted(df['user_name'].unique())
    selected_user = st.selectbox("🔍 חפש ובחר מועמד:", [""] + list(unique_users))

    if selected_user:
        st.markdown(f"## 📂 תיק מועמד: **{selected_user}**")
        user_df = df[df['user_name'] == selected_user].sort_values('timestamp', ascending=False)

        for idx, row in user_df.iterrows():
            test_type = row.get('test_type', 'HEXACO')
            test_date = row.get('test_date', 'N/A')
            test_time = row.get('test_time', '')

            with st.expander(f"📄 מבדק {test_type} | תאריך: {test_date} | שעה: {test_time}"):
                col_rep, col_viz = st.columns([2, 1])

                with col_rep:
                    st.subheader("📋 ניתוח המבדק")
                    if 'hesitation_count' in row and row['hesitation_count'] > 0:
                        st.warning(f"⚠️ **מדד היסוס:** המועמד חרג מהזמן ב-{row['hesitation_count']} שאלות.")

                    ai_report = row.get("ai_report", "")
                    if isinstance(ai_report, (list, tuple)):
                        t1, t2 = st.tabs(["🤖 Gemini Analysis", "🩺 Claude Expert"])
                        # ניקוי XSS לפני הצגה
                        safe_r0 = html.escape(str(ai_report[0])) if ai_report[0] else ""
                        safe_r1 = html.escape(str(ai_report[1])) if len(ai_report) > 1 else ""
                        t1.markdown(f'<div class="ai-report-box">{safe_r0}</div>', unsafe_allow_html=True)
                        t2.markdown(f'<div class="claude-report-box">{safe_r1}</div>', unsafe_allow_html=True)
                    else:
                        safe_report = html.escape(str(ai_report))
                        st.markdown(f'<div class="ai-report-box">{safe_report}</div>', unsafe_allow_html=True)

                with col_viz:
                    st.subheader("📊 גרף תוצאות")
                    scores = row.get('results') or row.get('int_scores')
                    if scores:
                        fig = get_radar_chart(scores)
                        st.plotly_chart(fig, use_container_width=True, key=f"admin_chart_{idx}")
                    else:
                        st.info("לא נמצאו נתוני גרף זמינים.")
    else:
        st.info("אנא בחר שם מועמד מהרשימה למעלה.")

    show_copyright()


# --- 6. ניווט ראשי ---
ADMIN_USER = st.secrets.get("ADMIN_USER", "adminMednitai")  # ✅ מאובטח דרך Secrets

if st.session_state.user_name == ADMIN_USER and st.session_state.step == Step.ADMIN_VIEW:
    show_admin_dashboard()

elif st.session_state.step == Step.HOME:
    st.markdown('<h1 style="color: #1e3a8a; text-align: center;">🏥 Mednitai: סימולטור HEXACO לרפואה</h1>', unsafe_allow_html=True)
    name_input = st.text_input("הכנס שם מלא לתחילת המבדק:", value=st.session_state.user_name)
    st.session_state.user_name = name_input

    if name_input == ADMIN_USER:
        if st.button("🚀 כניסה לממשק ניהול", key="admin_entry"):
            st.session_state.step = Step.ADMIN_VIEW
            st.rerun()

    elif name_input:
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 היסטוריית מבדקים"])
        with tab_new:
            all_qs_df = load_questions_data()
            if not all_qs_df.empty:
                st.info(f"שלום {name_input}, ברוך הבא לסימולטור. בחר את סוג ואורך המבדק:")

                if INTEGRITY_AVAILABLE:
                    test_type = st.radio(
                        "סוג המבדק:",
                        ["אישיות HEXACO", "אמינות ויושרה", "🌟 מבחן משולב"],
                        horizontal=True, key="test_type_selector"
                    )
                else:
                    test_type = "אישיות HEXACO"

                if test_type == "אישיות HEXACO":
                    st.session_state.test_type = 'HEXACO'
                    col1, col2, col3 = st.columns(3)
                    config = [("⏳ תרגול קצר (36)", 36), ("📋 סימולציה (120)", 120), ("🔍 מבדק מלא (300)", 300)]
                    for i, (label, count) in enumerate(config):
                        if [col1, col2, col3][i].button(label, key=f"cfg_{count}_{st.session_state.run_id}"):
                            hex_traits = ['Honesty-Humility', 'Emotionality', 'Extraversion', 'Agreeableness', 'Conscientiousness', 'Openness to Experience']
                            hex_only_df = all_qs_df[all_qs_df['trait'].isin(hex_traits)]
                            st.session_state.questions = get_balanced_questions(hex_only_df, count)
                            for q in st.session_state.questions:
                                q['origin'] = 'HEXACO'
                            st.session_state.step = Step.QUIZ
                            st.session_state.start_time = time.time()
                            st.rerun()

                elif test_type == "אמינות ויושרה" and INTEGRITY_AVAILABLE:
                    st.session_state.test_type = 'INTEGRITY'
                    st.markdown("**מבחן יושרה ואמינות מקיף** - בודק התנהגות אתית, יושרה ועקביות תשובות")
                    col1, col2, col3, col4 = st.columns(4)
                    int_config = [("⚡ קצר (60)", 60), ("📋 רגיל (100)", 100), ("🔍 מקיף (140)", 140), ("💯 מלא (160)", 160)]
                    for i, (label, count) in enumerate(int_config):
                        if [col1, col2, col3, col4][i].button(label, key=f"int_{count}_{st.session_state.run_id}"):
                            st.session_state.questions = get_integrity_questions(count)
                            for q in st.session_state.questions:
                                q['origin'] = 'INTEGRITY'
                            st.session_state.step = Step.QUIZ
                            st.session_state.start_time = time.time()
                            st.rerun()

                elif test_type == "🌟 מבחן משולב" and INTEGRITY_AVAILABLE:
                    st.session_state.test_type = 'COMBINED'
                    st.markdown("**מבחן משולב מתקדם** - 100 שאלות בסיס + הזרקת שאלות מטא")
                    if st.button("🚀 התחל מבחן משולב", key=f"combined_{st.session_state.run_id}"):
                        all_qs_df = load_questions_data()
                        hex_pool = get_balanced_questions(all_qs_df, 60)
                        int_pool = get_integrity_questions(40)
                        for q in hex_pool:
                            q['origin'] = 'HEXACO'
                        for q in int_pool:
                            q['origin'] = 'INTEGRITY'

                        combined_list = []
                        for i in range(10):
                            combined_list.extend(hex_pool[i*6:(i+1)*6])
                            combined_list.extend(int_pool[i*4:(i+1)*4])

                        if 'is_stress_meta' in all_qs_df.columns:
                            all_qs_df['is_stress_meta'] = pd.to_numeric(all_qs_df['is_stress_meta'], errors='coerce').fillna(0)
                            meta_qs_df = all_qs_df[all_qs_df['is_stress_meta'] == 1]
                            if not meta_qs_df.empty:
                                meta_list = meta_qs_df.to_dict('records')
                                num_to_inject = min(10, len(meta_list))
                                meta_to_inject = random.sample(meta_list, num_to_inject)
                                for mq in meta_to_inject:
                                    mq['origin'] = 'INTEGRITY'
                                    insert_pos = random.randint(10, len(combined_list) - 5)
                                    combined_list.insert(insert_pos, mq)

                        st.session_state.questions = combined_list
                        st.session_state.current_q = 0
                        st.session_state.step = Step.QUIZ
                        st.session_state.start_time = time.time()
                        st.rerun()

        with tab_archive:
            history = get_db_history(name_input)
            if history:
                for i, entry in enumerate(history):
                    with st.expander(f"📅 מבדק מיום {entry.get('test_date')} בשעה {entry.get('test_time')}"):
                        st.plotly_chart(get_radar_chart(entry['results']), key=f"hist_chart_{i}_{st.session_state.run_id}", use_container_width=True)
                        if st.button(f"🔍 הצג ניתוח AI מלא", key=f"view_rep_btn_{i}"):
                            @st.dialog(f"דוח מפורט - מבדק מיום {entry.get('test_date')}", width="large")
                            def show_modal(data):
                                st.write(f"### חוות דעת מומחי AI עבור {name_input}")
                                reps = data.get("ai_report", ["אין נתונים", "אין נתונים"])
                                t_gem, t_cld = st.tabs(["Gemini Analysis", "Claude Expert"])
                                with t_gem:
                                    st.markdown(f'<div class="ai-report-box">{html.escape(str(reps[0]))}</div>', unsafe_allow_html=True)
                                with t_cld:
                                    st.markdown(f'<div class="claude-report-box">{html.escape(str(reps[1]))}</div>', unsafe_allow_html=True)
                            show_modal(entry)
            else:
                st.info("לא נמצאו מבדקים קודמים עבורך.")

    show_copyright()

elif st.session_state.step == Step.QUIZ:
    # autorefresh מטפל ב-countdown של לחץ ובשעון — ללא sleep
    st_autorefresh(interval=1000, key="quiz_refresh")

    # --- טיפול ב-stress overlay ללא חסימה ---
    if st.session_state.get('stress_active'):
        elapsed = time.time() - st.session_state.get('stress_start', time.time())
        remaining = max(0, 15 - int(elapsed))
        if remaining > 0:
            msg = st.session_state.get('stress_msg', 'בדיקת מערכת...')
            progress_pct = (remaining / 15) * 100
            st.markdown(f"""
                <div class="stress-overlay">
                    <h1 style="color: #ff3b3b; font-size: 40px; margin-bottom: 10px; text-align: center;">⚠️ לבדיקת המערכת</h1>
                    <h2 style="text-align: center; padding: 0 20px; color: white;">{msg}</h2>
                    <div style="width: 300px; height: 15px; background: #333; margin: 20px auto; border-radius: 10px; overflow: hidden;">
                        <div style="height: 100%; background: #ff3b3b; width: {progress_pct}%; transition: width 1s linear;"></div>
                    </div>
                    <p style="font-size: 22px; color: #ff3b3b; font-weight: bold; text-align: center;">המבדק ימשך בעוד {remaining} שניות...</p>
                    <div style="margin-top: 50px; color: #666; text-align: center;">© זכויות יוצרים לניתאי מלכה</div>
                </div>
            """, unsafe_allow_html=True)
            st.stop()  # עוצר רינדור — autorefresh ידאג לעדכון
        else:
            st.session_state.stress_active = False
            # ממשיך לרינדר את השאלה

    q_idx = st.session_state.current_q

    if q_idx < len(st.session_state.questions):
        q_data = st.session_state.questions[q_idx]
        elapsed = time.time() - st.session_state.start_time

        if elapsed > 8:
            st.markdown('<div class="time-warning">⚠️ שים לב: עליך לענות במהירות! היסוס יתר נרשם במערכת.</div>', unsafe_allow_html=True)

        st.progress(q_idx / len(st.session_state.questions))
        c_left, c_right = st.columns([1, 1])
        c_left.write(f"שאלה **{q_idx + 1}** מתוך {len(st.session_state.questions)}")
        c_right.write(f"⏱️ זמן לשאלה: **{int(elapsed)}** שניות")

        # ניקוי XSS לשאלה עצמה
        safe_question = html.escape(str(q_data.get("q", "")))
        st.markdown(f'<div class="question-text">{safe_question}</div>', unsafe_allow_html=True)

        options = [("בכלל לא", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)]
        cols = st.columns(5)
        for i, (label, val) in enumerate(options):
            if cols[i].button(label, key=f"ans_{q_idx}_{val}_{st.session_state.run_id}"):
                record_answer(val, q_data)

        if q_idx > 0:
            if st.button("⬅️ חזור לשאלה הקודמת", key=f"back_btn_{st.session_state.run_id}"):
                st.session_state.current_q -= 1
                if st.session_state.responses:
                    st.session_state.responses.pop()
                st.rerun()
    else:
        st.session_state.step = Step.RESULTS
        st.rerun()
    show_copyright()

elif st.session_state.step == Step.RESULTS:
    st.markdown(f'# 📊 דוח ניתוח אישיות - {st.session_state.user_name}')

    resp_df = pd.DataFrame(st.session_state.responses)

    # ✅ תיקון באג: שימוש נכון ב-Pandas במקום .get()
    if 'origin' in resp_df.columns:
        hex_data = resp_df[resp_df['origin'] == 'HEXACO']
        int_data = resp_df[resp_df['origin'] == 'INTEGRITY']
    else:
        hex_data = resp_df
        int_data = pd.DataFrame()

    df_raw, summary_df = process_results(
        hex_data.to_dict('records') if not hex_data.empty else st.session_state.responses
    )
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()

    m1, m2, m3, m4 = st.columns(4)
    fit_score = calculate_medical_fit(summary_df)
    m1.metric("🎯 התאמה לרפואה", f"{fit_score}%")
    m4.metric("⏳ מדד היסוס", st.session_state.hesitation_count)

    int_scores = {}
    if not int_data.empty and INTEGRITY_AVAILABLE:
        df_int_raw, int_summary = process_integrity_results(int_data.to_dict('records'))
        reliability_score = calculate_reliability_score(df_int_raw)
        contradictions = detect_contradictions(df_int_raw)

        try:
            int_scores = int_summary.set_index(int_summary.columns[0])[int_summary.columns[-1]].to_dict()
        except Exception:
            int_scores = {}
            st.error("⚠️ תקלה במבנה נתוני האמינות")

        m2.metric("🛡️ מדד אמינות", f"{reliability_score}%")
        interp = get_integrity_interpretation(reliability_score)
        m3.markdown(f"**רמה:** {interp['level']}")

        st.session_state.reliability_score = reliability_score
        st.session_state.contradictions = contradictions
    else:
        m2.metric("🛡️ מדד אמינות", f"{calculate_reliability_index(df_raw)}%")
        m3.metric("⏱️ זמן מענה ממוצע", f"{summary_df['avg_time'].mean():.1f} שניות")

    # --- גרפים ---
    if st.session_state.test_type == 'INTEGRITY':
        st.subheader("📊 ניתוח מדדי אמינות ויושרה")
        if not int_data.empty and INTEGRITY_AVAILABLE and int_scores:
            st.plotly_chart(get_radar_chart(int_scores), use_container_width=True, key=f"int_only_radar_{st.session_state.run_id}")
        else:
            st.info("לא נמצאו נתוני אמינות להצגה")

    elif st.session_state.test_type == 'HEXACO':
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("פרופיל אישיות HEXACO")
            st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True, key=f"hex_only_radar_{st.session_state.run_id}")
        with c2:
            st.subheader("השוואת נורמות")
            st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True, key=f"hex_only_bar_{st.session_state.run_id}")

    elif st.session_state.test_type == 'COMBINED':
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("פרופיל אישיות HEXACO")
            st.plotly_chart(get_radar_chart(trait_scores), use_container_width=True, key=f"comb_hex_radar_{st.session_state.run_id}")
        with c2:
            st.subheader("מדדי אמינות")
            if not int_data.empty and INTEGRITY_AVAILABLE and int_scores:
                st.plotly_chart(get_radar_chart(int_scores), use_container_width=True, key=f"comb_int_radar_{st.session_state.run_id}")
            else:
                st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True, key=f"comb_bar_fallback_{st.session_state.run_id}")

    if not int_data.empty and INTEGRITY_AVAILABLE and st.session_state.contradictions:
        st.divider()
        st.subheader("⚠️ ממצאי עקביות")
        critical = [c for c in st.session_state.contradictions if c.get('severity') == 'critical']
        high = [c for c in st.session_state.contradictions if c.get('severity') == 'high']
        if critical:
            st.error(f"🚨 נמצאו {len(critical)} סתירות קריטיות")
            for c in critical[:3]:
                st.markdown(f"- **{c.get('category')}**: {c.get('message', 'סתירה בתשובות')}")
        if high:
            st.warning(f"⚠️ נמצאו {len(high)} סתירות חמורות")

    st.divider()
    st.subheader("📥 שמירת תוצאות והמשך")

    col_pdf, col_excel, col_reset = st.columns(3)

    with col_pdf:
        pdf_data = create_pdf_report(summary_df, df_raw)
        st.download_button(
            "📥 הורד דוח PDF מלא",
            pdf_data,
            f"HEXACO_{st.session_state.user_name}.pdf",
            key=f"pdf_dl_{st.session_state.run_id}"
        )

    with col_excel:
        if st.session_state.responses:
            result = create_excel_download(st.session_state.responses)
            if isinstance(result, bytes):
                st.download_button(
                    label="📊 הורד פירוט תשובות (Excel)",
                    data=result,
                    file_name=f"Answers_{st.session_state.user_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"excel_dl_{st.session_state.run_id}"
                )
            else:
                st.error("⚠️ יצירת האקסל נכשלה")
                with st.expander("פרטי השגיאה הטכנית"):
                    st.code(result)
        else:
            st.warning("אין נתונים זמינים להורדה")

    with col_reset:
        if st.button("🏁 סיום וחזרה לתפריט", key=f"finish_reset_{st.session_state.run_id}"):
            current_name = st.session_state.user_name
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session()
            st.session_state.user_name = current_name
            st.rerun()

    st.divider()

    if st.session_state.gemini_report is None:
        with st.spinner("🤖 מנתח את הפרופיל מול שני מומחי AI..."):
            try:
                hist = get_db_history(st.session_state.user_name)

                if st.session_state.test_type == 'COMBINED' and INTEGRITY_AVAILABLE and not int_data.empty:
                    gem_rep, cld_rep = get_combined_ai_analysis(
                        st.session_state.user_name, trait_scores,
                        st.session_state.reliability_score,
                        st.session_state.contradictions, hist
                    )
                elif st.session_state.test_type == 'INTEGRITY' and INTEGRITY_AVAILABLE:
                    gem_rep, cld_rep = get_integrity_ai_analysis(
                        st.session_state.user_name,
                        st.session_state.reliability_score,
                        st.session_state.contradictions,
                        int_scores, hist
                    )
                else:
                    gem_rep, cld_rep = get_multi_ai_analysis(
                        st.session_state.user_name, trait_scores, hist
                    )

                st.session_state.gemini_report = gem_rep
                st.session_state.claude_report = cld_rep

                hesitation = st.session_state.hesitation_count
                report_pair = [gem_rep, cld_rep]

                # ✅ שמירה עם חתימות פונקציות מאוחדות
                try:
                    if st.session_state.test_type == 'COMBINED' and not int_data.empty:
                        save_combined_test_to_db(
                            st.session_state.user_name, trait_scores,
                            int_scores, st.session_state.reliability_score,
                            report_pair, hesitation
                        )
                    elif st.session_state.test_type == 'INTEGRITY' and not int_data.empty:
                        save_integrity_test_to_db(
                            st.session_state.user_name, int_scores,
                            st.session_state.reliability_score,
                            report_pair, hesitation
                        )
                    else:
                        save_to_db(st.session_state.user_name, trait_scores, report_pair, hesitation)
                except Exception as db_err:
                    st.warning(f"⚠️ הניתוח הושלם, אך לא הצלחנו לשמור ב-DB: {db_err}")

            except Exception as e:
                st.error(f"שגיאה בהפקת דוח: {e}")

    st.subheader("💡 ניתוח מומחי AI משולב")
    rep_tab1, rep_tab2 = st.tabs(["📝 חוות דעת Gemini", "🩺 חוות דעת Claude"])
    with rep_tab1:
        safe_gem = html.escape(str(st.session_state.gemini_report or ""))
        st.markdown(f'<div class="ai-report-box">{safe_gem}</div>', unsafe_allow_html=True)
    with rep_tab2:
        safe_cld = html.escape(str(st.session_state.claude_report or ""))
        st.markdown(f'<div class="claude-report-box">{safe_cld}</div>', unsafe_allow_html=True)

    show_copyright()
