import pandas as pd
from fpdf import FPDF
import re
from datetime import datetime

def calculate_score(answer, reverse_value):
    """מחשב ציון סופי לפי עמודת ה-reverse מהאקסל"""
    try:
        rev_str = str(reverse_value).strip().upper()
        is_reverse = rev_str in ["TRUE", "1", "YES", "T"]
        if is_reverse:
            return 6 - int(answer)
        return int(answer)
    except:
        return int(answer)

def check_response_time(duration):
    """בדיקה אם זמן התגובה תקין או חשוד"""
    if duration < 1.8: return "מהיר מדי"
    if duration > 25: return "איטי מדי"
    return "תקין"

def analyze_consistency(df):
    """בקרת עקביות כללית ברמת התכונה (רמזור)"""
    inconsistency_alerts = []
    if df.empty or 'trait' not in df.columns:
        return inconsistency_alerts
    for trait in df['trait'].unique():
        trait_data = df[df['trait'] == trait]
        if len(trait_data) >= 3:
            score_range = trait_data['final_score'].max() - trait_data['final_score'].min()
            if score_range >= 3:
                inconsistency_alerts.append({"text": f"חוסר עקביות חמור ב-{trait}", "level": "red"})
            elif score_range >= 2.2:
                inconsistency_alerts.append({"text": f"חוסר עקביות ב-{trait}", "level": "orange"})
    return inconsistency_alerts

def get_inconsistent_questions(df_raw):
    """מאתרת זוגות סותרים של שאלות"""
    inconsistencies = []
    if df_raw.empty: return []
    for trait in df_raw['trait'].unique():
        trait_qs = df_raw[df_raw['trait'] == trait]
        for i in range(len(trait_qs)):
            for j in range(i + 1, len(trait_qs)):
                q1 = trait_qs.iloc[i]
                q2 = trait_qs.iloc[j]
                if abs(q1['final_score'] - q2['final_score']) >= 2.5:
                    inconsistencies.append({
                        'trait': trait, 'q1_text': q1['question'],
                        'q1_ans': q1['original_answer'], 'q2_text': q2['question'],
                        'q2_ans': q2['original_answer']
                    })
    return inconsistencies

def process_results(user_responses):
    """מעבד את התשובות לממוצעים"""
    df = pd.DataFrame(user_responses)
    if df.empty: return df, pd.DataFrame()
    df['time_status'] = df['time_taken'].apply(check_response_time)
    summary = df.groupby('trait').agg({'final_score': 'mean', 'time_taken': 'mean'}).reset_index()
    summary['final_score'] = summary['final_score'].round(2)
    return df, summary

def fix_heb(text):
    """הופכת טקסט עברית ל-RTL ומנקה תווים בעייתיים"""
    if not text: return " "
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-]', '', str(text))
    if not clean_text.strip(): return " "
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    """מפיק דוח PDF עם הגנה מקסימלית משגיאות רינדור"""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    
    try:
        pdf.add_font('Assistant', '', 'Assistant.ttf')
        font_main = 'Assistant'
    except:
        font_main = 'Helvetica'

    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    effective_width = pdf.w - 30 

    # כותרת
    pdf.set_font(font_main, size=22)
    pdf.cell(effective_width, 15, txt=fix_heb("דוח תוצאות HEXACO"), ln=True, align='C')
    pdf.set_font(font_main, size=11)
    pdf.cell(effective_width, 10, txt=fix_heb(f"הופק בתאריך: {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align='C')
    pdf.ln(5)

    # טבלת ציונים
    col_w = effective_width / 3
    pdf.set_font(font_main, size=12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(col_w, 10, fix_heb("סטטוס"), 1, 0, 'C', True)
    pdf.cell(col_w, 10, fix_heb("ציון"), 1, 0, 'C', True)
    pdf.cell(col_w, 10, fix_heb("תכונה"), 1, 1, 'C', True)

    pdf.set_font(font_main, size=11)
    for _, row in summary_df.iterrows():
        score = row['final_score']
        status = "תקין" if 3.5 <= score <= 4.5 else "לבדיקה"
        pdf.cell(col_w, 10, fix_heb(status), 1, 0, 'C')
        pdf.cell(col_w, 10, str(score), 1, 0, 'C')
        pdf.cell(col_w, 10, fix_heb(str(row['trait'])), 1, 1, 'C')

    # סתירות פנימיות
    inconsistencies = get_inconsistent_questions(pd.DataFrame(raw_responses))
    if inconsistencies:
        pdf.ln(10)
        pdf.set_font(font_main, size=16)
        pdf.cell(effective_width, 10, txt=fix_heb("ניתוח סתירות"), ln=True, align='R')
        pdf.ln(2)
        pdf.set_font(font_main, size=10)
        for pair in inconsistencies:
            pdf.set_text_color(200, 0, 0)
            pdf.cell(effective_width, 8, txt=fix_heb(f"תכונה: {pair['trait']}"), ln=True, align='R')
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(effective_width, 6, txt=fix_heb(f"שאלה א: {pair['q1_text']} (תשובה: {pair['q1_ans']})"), align='R')
            pdf.multi_cell(effective_width, 6, txt=fix_heb(f"שאלה ב: {pair['q2_text']} (תשובה: {pair['q2_ans']})"), align='R')
            pdf.ln(2)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(2)

    return bytes(pdf.output())
