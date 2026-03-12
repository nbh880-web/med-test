import streamlit as st
import time
import pandas as pd
import random
import json
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import uuid

# --- ייבוא לוגיקה עסקית (logic.py) ---
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

# --- ייבוא לוגיקת אמינות (integrity_logic.py) ---
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

# --- ייבוא שכבת הנתונים וה-AI (database.py, gemini_ai.py) ---
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

# --- 1. הגדרות דף ו-CSS מורחב ---
st.set_page_config(
page_title="Mednitai HEXACO System", 
layout="wide",
initial_sidebar_state="collapsed" 
)

st.markdown("""
   <style>
   [data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="stSidebarCollapsedControl"] {
       display: none !important;
   }
   .stApp { direction: rtl; text-align: right; }
   
   /* עיצוב כפתורים */
   div.stButton > button {
       width: 100%; border-radius: 8px; height: 60px !important; 
       font-size: 18px !important; background-color: white; color: #212529;
       box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: 0.3s;
   }
   div.stButton > button:hover { border-color: #1e3a8a; color: #1e3a8a; }
   
   .question-text { 
       font-size: 32px; font-weight: 800; text-align: center; 
       padding: 40px 20px; color: #1a2a6c; background-color: #f8f9fa; 
       border-radius: 15px; margin-bottom: 25px; border: 1px solid #e9ecef;
   }

   /* סגנון לשכבת הלחץ */
   .stress-overlay {
       position: fixed; top: 0; left: 0; width: 100%; height: 100%;
       background: rgba(0,0,0,0.9); z-index: 9999;
       display: flex; flex-direction: column; justify-content: center; align-items: center;
       color: white; font-family: sans-serif;
   }
   .progress-container {
       width: 300px; height: 12px; background: #333; border-radius: 6px; margin-top: 20px; overflow: hidden;
   }
   .progress-bar-fill {
       height: 100%; background: #ff3b3b; width: 100%;
       animation: shrink 30s linear forwards;
   }
   @keyframes shrink {
       from { width: 100%; }
       to { width: 0%; }
   }
   
   .copyright-footer {
       text-align: center;
       padding: 20px;
       color: #666;
       font-size: 14px;
   }

   /* --- NEW ADDITION: CSS התראת זמן --- */
   .time-warning {
       background-color: #fff3cd;
       color: #856404;
       padding: 15px;
       border-radius: 10px;
       border-right: 5px solid #ffc107;
       text-align: center;
       font-weight: bold;
       margin-bottom: 20px;
       animation: flash 1s infinite alternate;
   }
   @keyframes flash {
       from { opacity: 1; }
       to { opacity: 0.7; }
   }
   </style>
   """, unsafe_allow_html=True)

def show_copyright():
st.markdown('<div class="copyright-footer">© זכויות יוצרים לניתאי מלכה</div>', unsafe_allow_html=True)

# --- 2. אתחול Session State ---
def init_session():
defaults = {
'step': 'HOME', 'responses': [], 'current_q': 0, 
'user_name': "", 'questions': [], 'start_time': 0, 
'gemini_report': None, 'claude_report': None,
'run_id': str(uuid.uuid4())[:8],
'test_type': 'HEXACO',
'reliability_score': None,
'contradictions': [],
'show_stress': False,
'stress_msg': "",
'hesitation_count': 0  # --- NEW ADDITION ---
}
for key, val in defaults.items():
if key not in st.session_state:
st.session_state[key] = val

init_session()

# --- 3. פונקציית הלחץ החדשה (Stress Effect) ---
def trigger_stress_effect():
"""מציג הודעת אזהרה למשך 15 שניות וחוסם את רענון הדף"""
messages = [
"מזהה סתירה פוטנציאלית בתשובותיך...",
"מחשב מדד אמינות רגעית... נא להמתין",
"מערכת הבקרה זיהתה חוסר עקביות בנתונים",
"⚠️ בקרת איכות: נדרש ריכוז מקסימלי, המערכת מזהה ניסיון הטיה."
]
msg = random.choice(messages)

# יצירת מיכל שמשתלט על התצוגה
placeholder = st.empty()

total_seconds = 15  # הזמן שביקשת

for i in range(total_seconds, -1, -1):
with placeholder.container():
st.markdown(f"""
               <div class="stress-overlay">
                   <h1 style="color: #ff3b3b; font-size: 40px; margin-bottom: 10px; text-align: center;">⚠️ לבדיקת המערכת</h1>
                   <h2 style="text-align: center; padding: 0 20px; color: white;">{msg}</h2>
                   <div class="progress-container" style="width: 300px; height: 15px; background: #333; margin: 20px auto; border-radius: 10px; overflow: hidden;">
                       <div style="height: 100%; background: #ff3b3b; width: {(i / total_seconds) * 100}%; transition: width 1s linear;"></div>
                   </div>
                   <p style="font-size: 22px; color: #ff3b3b; font-weight: bold; text-align: center;">המבדק ימשך בעוד {i} שניות...</p>
                   <div style="margin-top: 50px; color: #666; text-align: center;">© זכויות יוצרים לניתאי מלכה</div>
               </div>
           """, unsafe_allow_html=True)
time.sleep(1)  # מחכה שנייה אחת בכל פעם

# --- השורות שחייבות להופיע כאן: ---
placeholder.empty() # מנקה את המסך השחור
st.rerun()          # מכריח את הדף להתרענן ולהציג את השאלה הבאה

# --- 4. פונקציות עזר לממשק ---
@st.cache_data
def load_questions_data():
try: return pd.read_csv('data/questions.csv')
except: return pd.DataFrame()

def record_answer(ans_value, q_data):
duration = time.time() - st.session_state.start_time
origin = q_data.get('origin', st.session_state.test_type)

# --- NEW ADDITION: עדכון מדד ההיסוס ---
if duration > 8:
st.session_state.hesitation_count += 1

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

# בודק אם השאלה הזו אמורה להפעיל לחץ
is_meta = q_data.get('is_stress_meta') or q_data.get('stress_mode')

# מקדם לשאלה הבאה
st.session_state.current_q += 1
st.session_state.start_time = time.time()

    # --- השינוי כאן ---
    # אם התנאי מתקיים, המערכת תפעיל את האפקט ותחכה 5 שניות לפני שהיא ממשיכה
    # זה הבלוק שצריך להחליף/להוסיף:
    is_meta = str(q_data.get('is_stress_meta')) == "1"
if is_meta:
        # הפונקציה הזו כבר עושה המתנה ו-rerun בסופה
trigger_stress_effect()
else:
        # פקודה שמרעננת את המסך לשאלה הבאה רק אם זו לא שאלת לחץ
st.rerun()

# --- 5. ממשק ניהול (Admin) ---
def show_admin_dashboard():
# 1. כפתור יציאה
if st.button("🚪 התנתק וחזור לבית", key="admin_logout"):
st.session_state.step = 'HOME'; st.rerun()

st.title("📊 מערכת ניהול: תיקי מועמדים")

# 2. שליפת כל הנתונים המאוחדים מכל ה-Collections
all_data = get_all_tests() # מוודא שזה מושך מכל ה-DB
if not all_data:
st.info("טרם בוצעו מבדקים במערכת."); return

df = pd.DataFrame(all_data)

# 3. מטריקות בראש העמוד
m1, m2, m3 = st.columns(3)
m1.metric("סה\"כ מבדקים", len(df))
m2.metric("מועמדים ייחודיים", df['user_name'].nunique())
# חישוב ממוצע היסוס כללי (אם השדה קיים)
avg_hesitation = df['hesitation_count'].mean() if 'hesitation_count' in df.columns else 0
m3.metric("ממוצע היסוס מערכתי", f"{avg_hesitation:.1f}")

st.divider()

# 4. מנגנון חיפוש ובחירת מועמד (הופך את הרשימה לנקייה)
unique_users = sorted(df['user_name'].unique())
selected_user = st.selectbox("🔍 חפש ובחר מועמד לצפייה בהיסטוריה המלאה:", [""] + list(unique_users))

if selected_user:
st.markdown(f"## 📂 תיק מועמד: **{selected_user}**")

# סינון המבחנים של המשתמש בלבד, מהחדש לישן
user_df = df[df['user_name'] == selected_user].sort_values('timestamp', ascending=False)

# 5. הצגת כל מבחן בתוך Expander נפרד
for idx, row in user_df.iterrows():
test_type = row.get('test_type', 'HEXACO')
test_date = row.get('test_date', 'N/A')
test_time = row.get('test_time', '')

# כותרת Expander דינמית
with st.expander(f"📄 מבדק {test_type} | תאריך: {test_date} | שעה: {test_time}"):
col_rep, col_viz = st.columns([2, 1])

with col_rep:
st.subheader("📋 ניתוח המבדק")
# תצוגת מדד היסוס
if 'hesitation_count' in row and row['hesitation_count'] > 0:
st.warning(f"⚠️ **מדד היסוס:** המועמד חרג מהזמן ב-{row['hesitation_count']} שאלות.")

# הצגת דוחות AI לפי המבנה ששמרת (רשימה של Gemini ו-Claude)
if isinstance(row["ai_report"], (list, tuple)):
t1, t2 = st.tabs(["🤖 Gemini Analysis", "🩺 Claude Expert"])
t1.markdown(f'<div class="ai-report-box">{row["ai_report"][0]}</div>', unsafe_allow_html=True)
t2.markdown(f'<div class="claude-report-box">{row["ai_report"][1]}</div>', unsafe_allow_html=True)
else:
st.markdown(f'<div class="ai-report-box">{row["ai_report"]}</div>', unsafe_allow_html=True)

with col_viz:
st.subheader("📊 גרף תוצאות")
# בחירת נתוני הניקוד (תומך ב-HEXACO ובאמינות)
scores = row.get('results') or row.get('int_scores')
if scores:
# שימוש ב-Radar Chart הקיים שלך
fig = get_radar_chart(scores)
st.plotly_chart(fig, use_container_width=True, key=f"admin_chart_{idx}")
else:
st.info("לא נמצאו נתוני גרף זמינים.")
else:
st.info("אנא בחר שם מועמד מהרשימה למעלה כדי לצפות בפרטים.")

show_copyright()

# --- 6. ניווט ראשי ---
if st.session_state.user_name == "adminMednitai" and st.session_state.step == 'ADMIN_VIEW':
show_admin_dashboard()
show_copyright()

elif st.session_state.step == 'HOME':
st.markdown('<h1 style="color: #1e3a8a; text-align: center;">🏥 Mednitai: סימולטור HEXACO לרפואה</h1>', unsafe_allow_html=True)
name_input = st.text_input("הכנס שם מלא לתחילת המבדק:", value=st.session_state.user_name)
st.session_state.user_name = name_input

if name_input == "adminMednitai":
if st.button("🚀 כניסה לממשק ניהול", key="admin_entry"):
st.session_state.step = 'ADMIN_VIEW'; st.rerun()

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
horizontal=True,
key="test_type_selector"
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
st.session_state.step = 'QUIZ'
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
st.session_state.step = 'QUIZ'
st.session_state.start_time = time.time()
st.rerun()

elif test_type == "🌟 מבחן משולב" and INTEGRITY_AVAILABLE:
st.session_state.test_type = 'COMBINED'
st.markdown("**מבחן משולב מתקדם** - 100 שאלות בסיס + הזרקת שאלות מטא")
if st.button("🚀 התחל מבחן משולב", key=f"combined_{st.session_state.run_id}"):
# 1. טעינה מפורשת של הנתונים
all_qs_df = load_questions_data()

# 2. בניית ה-100 המקוריות (60 HEXACO + 40 אמינות)
hex_pool = get_balanced_questions(all_qs_df, 60)
int_pool = get_integrity_questions(40)
for q in hex_pool: q['origin'] = 'HEXACO'
for q in int_pool: q['origin'] = 'INTEGRITY'

combined_list = []
for i in range(10):
combined_list.extend(hex_pool[i*6:(i+1)*6])
combined_list.extend(int_pool[i*4:(i+1)*4])

# 3. הזרקת שאלות מטא (בנוסף ל-100)
if 'is_stress_meta' in all_qs_df.columns:
# המרה למספר וסינון
all_qs_df['is_stress_meta'] = pd.to_numeric(all_qs_df['is_stress_meta'], errors='coerce').fillna(0)
meta_qs_df = all_qs_df[all_qs_df['is_stress_meta'] == 1]

if not meta_qs_df.empty:
meta_list = meta_qs_df.to_dict('records')
# בוחר 10 שאלות מטא להזרקה
num_to_inject = min(10, len(meta_list))
meta_to_inject = random.sample(meta_list, num_to_inject)

for mq in meta_to_inject:
mq['origin'] = 'INTEGRITY'
# הזרקה במיקום אקראי (החל משאלה 10)
insert_pos = random.randint(10, len(combined_list) - 5)
combined_list.insert(insert_pos, mq)

# 4. עדכון ה-Session וריצה (שים לב: אין דריסה של combined_list כאן)
st.session_state.questions = combined_list
st.session_state.current_q = 0
st.session_state.step = 'QUIZ'
st.session_state.start_time = time.time()
st.rerun()

with tab_archive:
history = get_db_history(name_input)
if history:
for i, entry in enumerate(history):
with st.expander(f"📅 מבדק מיום {entry.get('test_date')} בשעה {entry.get('test_time')}"):
st.plotly_chart(get_radar_chart(entry['results']), key=f"hist_chart_{i}_{st.session_state.run_id}", width="stretch")
if st.button(f"🔍 הצג ניתוח AI מלא", key=f"view_rep_btn_{i}"):
@st.dialog(f"דוח מפורט - מבדק מיום {entry.get('test_date')}", width="large")
def show_modal(data):
st.write(f"### חוות דעת מומחי AI עבור {name_input}")
reps = data.get("ai_report", ["אין נתונים", "אין נתונים"])
t_gem, t_cld = st.tabs(["Gemini Analysis", "Claude Expert"])
with t_gem: st.markdown(f'<div class="ai-report-box">{reps[0]}</div>', unsafe_allow_html=True)
with t_cld: st.markdown(f'<div class="claude-report-box">{reps[1]}</div>', unsafe_allow_html=True)
show_modal(entry)
else: 
st.info("לא נמצאו מבדקים קודמים עבורך.")

show_copyright()

elif st.session_state.step == 'QUIZ':
st_autorefresh(interval=1000, key="quiz_refresh")
q_idx = st.session_state.current_q

if q_idx < len(st.session_state.questions):
q_data = st.session_state.questions[q_idx]
elapsed = time.time() - st.session_state.start_time

# --- NEW ADDITION: התראת זמן בזמן אמת ---
if elapsed > 8:
st.markdown('<div class="time-warning">⚠️ שים לב: עליך לענות במהירות! היסוס יתר נרשם במערכת.</div>', unsafe_allow_html=True)

st.progress(q_idx / len(st.session_state.questions))
c_left, c_right = st.columns([1,1])
c_left.write(f"שאלה **{q_idx + 1}** מתוך {len(st.session_state.questions)}")
c_right.write(f"⏱️ זמן לשאלה: **{int(elapsed)}** שניות")

st.markdown(f'<div class="question-text">{q_data["q"]}</div>', unsafe_allow_html=True)

options = [("בכלל לא", 1), ("לא מסכים", 2), ("נייטרלי", 3), ("מסכים", 4), ("מסכים מאוד", 5)]
cols = st.columns(5)
for i, (label, val) in enumerate(options):
if cols[i].button(label, key=f"ans_{q_idx}_{val}_{st.session_state.run_id}"):
record_answer(val, q_data); st.rerun()

if q_idx > 0:
if st.button("⬅️ חזור לשאלה הקודמת", key=f"back_btn_{st.session_state.run_id}"):
st.session_state.current_q -= 1
if st.session_state.responses: st.session_state.responses.pop()
st.rerun()
else:
st.session_state.step = 'RESULTS'; st.rerun()
show_copyright()

elif st.session_state.step == 'RESULTS':
st.markdown(f'# 📊 דוח ניתוח אישיות - {st.session_state.user_name}')

resp_df = pd.DataFrame(st.session_state.responses)
hex_data = resp_df[resp_df.get('origin', 'HEXACO') == 'HEXACO'] if 'origin' in resp_df.columns else resp_df
int_data = resp_df[resp_df.get('origin', '') == 'INTEGRITY'] if 'origin' in resp_df.columns else pd.DataFrame()

df_raw, summary_df = process_results(hex_data.to_dict('records') if not hex_data.empty else st.session_state.responses)
trait_scores = summary_df.set_index('trait')['final_score'].to_dict()

m1, m2, m3, m4 = st.columns(4) # --- NEW ADDITION: m4 ---
fit_score = calculate_medical_fit(summary_df)
m1.metric("🎯 התאמה לרפואה", f"{fit_score}%")

# --- NEW ADDITION: הצגת מדד היסוס בתוצאות ---
m4.metric("⏳ מדד היסוס", st.session_state.hesitation_count)

if not int_data.empty and INTEGRITY_AVAILABLE:
df_int_raw, int_summary = process_integrity_results(int_data.to_dict('records'))
reliability_score = calculate_reliability_score(df_int_raw)
contradictions = detect_contradictions(df_int_raw)

try:
int_scores = int_summary.set_index(int_summary.columns[0])[int_summary.columns[-1]].to_dict()
except:
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

# --- תצוגת גרפים מותאמת לסוג המבחן ---
if st.session_state.test_type == 'INTEGRITY':
st.subheader("📊 ניתוח מדדי אמינות ויושרה")
if not int_data.empty and INTEGRITY_AVAILABLE:
st.plotly_chart(get_radar_chart(int_scores), width='content', key=f"int_only_radar_{st.session_state.run_id}")
else:
st.info("לא נמצאו נתוני אמינות להצגה")

elif st.session_state.test_type == 'HEXACO':
c1, c2 = st.columns(2)
with c1:
st.subheader("פרופיל אישיות HEXACO")
st.plotly_chart(get_radar_chart(trait_scores), width='content', key=f"hex_only_radar_{st.session_state.run_id}")
with c2:
st.subheader("השוואת נורמות (Bar Chart)")
st.plotly_chart(get_comparison_chart(trait_scores), width='content', key=f"hex_only_bar_{st.session_state.run_id}")

elif st.session_state.test_type == 'COMBINED':
c1, c2 = st.columns(2)
with c1:
st.subheader("פרופיל אישיות HEXACO")
st.plotly_chart(get_radar_chart(trait_scores), width='content', key=f"comb_hex_radar_{st.session_state.run_id}")
with c2:
st.subheader("מדדי אמינות")
if not int_data.empty and INTEGRITY_AVAILABLE:
st.plotly_chart(get_radar_chart(int_scores), width='content', key=f"comb_int_radar_{st.session_state.run_id}")
else:
st.plotly_chart(get_comparison_chart(trait_scores), width='content', key=f"comb_bar_fallback_{st.session_state.run_id}")

if not int_data.empty and INTEGRITY_AVAILABLE and contradictions:
st.divider()
st.subheader("⚠️ ממצאי עקביות")
critical = [c for c in contradictions if c.get('severity') == 'critical']
high = [c for c in contradictions if c.get('severity') == 'high']

if critical:
st.error(f"🚨 נמצאו {len(critical)} סתירות קריטיות")
for c in critical[:3]:
st.markdown(f"- **{c.get('category')}**: {c.get('message', 'סתירה בתשובות')}")
if high:
st.warning(f"⚠️ נמצאו {len(high)} סתירות חמורות")

st.divider()
st.subheader("📥 שמירת תוצאות והמשך")

# יצירת 3 עמודות
col_pdf, col_excel, col_reset = st.columns(3)

with col_pdf:
# יצירת ה-PDF (קיים אצלך)
pdf_data = create_pdf_report(summary_df, df_raw)
st.download_button(
"📥 הורד דוח PDF מלא", 
pdf_data, 
f"HEXACO_{st.session_state.user_name}.pdf", 
key=f"pdf_dl_{st.session_state.run_id}",
width='content'
)

with col_excel:
if "responses" in st.session_state and st.session_state.responses:
# קבלת התוצאה מהפונקציה
result = create_excel_download(st.session_state.responses)

# בדיקה: האם חזרו נתונים (bytes) או הודעת שגיאה (str)
if isinstance(result, bytes):
st.download_button(
label="📊 הורד פירוט תשובות (Excel)",
data=result,
file_name=f"Answers_{st.session_state.user_name}.xlsx",
mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
key=f"excel_dl_{st.session_state.run_id}",
width="stretch"
)
else:
# כאן יופיע הפירוט המדויק למה זה נכשל
st.error(f"⚠️ יצירת האקסל נכשלה")
with st.expander("לצפייה בפרטי השגיאה הטכנית"):
st.code(result)
st.info("טיפ: וודא שספריית xlsxwriter מותקנת ב-requirements.txt")
else:
st.warning("אין נתונים זמינים להורדה")

with col_reset:
if st.button("🏁 סיום וחזרה לתפריט", key=f"finish_reset_{st.session_state.run_id}", width='content'):
current_name = st.session_state.user_name
for key in list(st.session_state.keys()): del st.session_state[key]
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
st.session_state.user_name,
trait_scores,
st.session_state.reliability_score,
st.session_state.contradictions,
hist
)
elif st.session_state.test_type == 'INTEGRITY' and INTEGRITY_AVAILABLE:
gem_rep, cld_rep = get_integrity_ai_analysis(
st.session_state.user_name,
st.session_state.reliability_score,
st.session_state.contradictions,
int_scores,
hist
)
else:
gem_rep, cld_rep = get_multi_ai_analysis(st.session_state.user_name, trait_scores, hist)

st.session_state.gemini_report = gem_rep
st.session_state.claude_report = cld_rep

# --- NEW ADDITION: שמירת מדד ההיסוס ב-DB ---
if st.session_state.test_type == 'COMBINED' and not int_data.empty:
try:
save_combined_test_to_db(st.session_state.user_name, trait_scores, int_scores, 
st.session_state.reliability_score, [gem_rep, cld_rep])
except:
save_to_db(st.session_state.user_name, trait_scores, [gem_rep, cld_rep])
elif st.session_state.test_type == 'INTEGRITY' and not int_data.empty:
try:
save_integrity_test_to_db(st.session_state.user_name, int_scores, 
st.session_state.reliability_score, [gem_rep, cld_rep])
except:
save_to_db(st.session_state.user_name, int_scores, [gem_rep, cld_rep])
else:
save_to_db(st.session_state.user_name, trait_scores, [gem_rep, cld_rep])

except Exception as e:
st.error(f"שגיאה בהפקת דוח: {e}")

st.subheader("💡 ניתוח מומחי AI משולב")
rep_tab1, rep_tab2 = st.tabs(["📝 חוות דעת Gemini", "🩺 חוות דעת Claude"])
with rep_tab1: st.markdown(f'<div class="ai-report-box">{st.session_state.gemini_report}</div>', unsafe_allow_html=True)
with rep_tab2: st.markdown(f'<div class="claude-report-box">{st.session_state.claude_report}</div>', unsafe_allow_html=True)

show_copyright()
