import pandas as pd

def calculate_score(answer, reverse_value):
    """מחשב ציון סופי לפי עמודת ה-reverse מהאקסל"""
    is_reverse = str(reverse_value).strip().upper() == "TRUE"
    if is_reverse:
        return 6 - answer
    return answer

def check_response_time(duration):
    """בדיקה אם זמן התגובה חשוד"""
    if duration < 1.5:
        return "מהיר מדי"
    if duration > 20:
        return "איטי מדי"
    return "תקין"

def analyze_consistency(df):
    """מזהה סתירות מהותיות בתשובות"""
    inconsistency_alerts = []
    if df.empty:
        return inconsistency_alerts

    for trait in df['trait'].unique():
        trait_data = df[df['trait'] == trait]
        if len(trait_data) > 1:
            score_range = trait_data['final_score'].max() - trait_data['final_score'].min()
            if score_range >= 3:
                inconsistency_alerts.append(f"נמצאה חוסר עקביות בתכונת {trait}")
    return inconsistency_alerts

def process_results(user_responses):
    """מעבד את התשובות לדאטה-פרים מסודר"""
    df = pd.DataFrame(user_responses)
    df['time_status'] = df['time_taken'].apply(check_response_time)
    
    summary = df.groupby('trait').agg({
        'final_score': 'mean',
        'time_taken': 'mean'
    }).reset_index()
    
    return df, summary

def get_profile_match(trait_scores):
    """מנגנון הרמזור מול פרופיל רופא"""
    status = {}
    for trait, score in trait_scores.items():
        if 3.5 <= score <= 4.5:
            status[trait] = "🟢 ירוק"
        elif 3.0 <= score <= 5.0:
            status[trait] = "🟡 צהוב"
        else:
            status[trait] = "🔴 אדום"
    return status
from fpdf import FPDF

def fix_heb(text):
    """הופכת טקסט עברית כדי שיוצג נכון ב-PDF (RTL ויזואלי)"""
    if not text or not isinstance(text, str):
        return ""
    # הפיכת סדר האותיות
    return text[::-1]

def create_pdf_report(summary_df, raw_responses, ai_report):
    pdf = FPDF()
    pdf.add_page()
    
    # טעינת פונט עברי (וודא שהקובץ נמצא ב-GitHub באותו שם)
    # אם שם הקובץ שונה, שנה כאן
    try:
        pdf.add_font('HebrewFont', '', 'Assistant.ttf', uni=True)
        pdf.set_font('HebrewFont', size=16)
    except:
        # ברירת מחדל אם הפונט לא נמצא
        pdf.set_font("Arial", size=16)

    # כותרת
    pdf.cell(200, 10, txt=fix_heb("דוח סיכום סימולציה - הכנה לרפואה"), ln=True, align='C')
    pdf.ln(10)
    
    # 1. טבלת סיכום
    pdf.set_font('HebrewFont', size=12)
    pdf.cell(60, 10, fix_heb("תכונה"), border=1)
    pdf.cell(40, 10, fix_heb("ציון"), border=1)
    pdf.cell(60, 10, fix_heb("בטווח? (3.5-4.5)"), border=1)
    pdf.ln()
    
    for _, row in summary_df.iterrows():
        score = row['final_score']
        in_range = "כן" if 3.5 <= score <= 4.5 else "לא"
        pdf.cell(60, 10, fix_heb(str(row['trait'])), border=1)
        pdf.cell(40, 10, f"{score:.2f}", border=1)
        pdf.cell(60, 10, fix_heb(in_range), border=1)
        pdf.ln()
    
    pdf.ln(10)

    # 2. ניתוח AI
    pdf.set_font('HebrewFont', size=14)
    pdf.cell(200, 10, txt=fix_heb("ניתוח AI מקצועי:"), ln=True)
    pdf.set_font('HebrewFont', size=11)
    # multi_cell מתאים לטקסט ארוך
    pdf.multi_cell(0, 10, txt=fix_heb(ai_report))
    
    # 3. פירוט תשובות
    pdf.add_page()
    pdf.set_font('HebrewFont', size=14)
    pdf.cell(200, 10, txt=fix_heb("פירוט תשובות המשתמש:"), ln=True)
    pdf.set_font('HebrewFont', size=10)
    
    for i, resp in enumerate(raw_responses):
        q_text = f"{i+1}. {resp['question']}"
        ans_info = f"תשובה: {resp['original_answer']} | זמן: {resp['time_taken']:.1f} שניות"
        pdf.multi_cell(0, 8, txt=fix_heb(q_text))
        pdf.multi_cell(0, 8, txt=fix_heb(ans_info), border='B')
        pdf.ln(2)
        
    return pdf.output(dest='S')
