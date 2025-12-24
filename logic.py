import pandas as pd
from fpdf import FPDF
import re
from datetime import datetime

def calculate_score(answer, reverse_value):
    """מחשב ציון סופי לפי עמודת ה-reverse מהאקסל"""
    try:
        # טיפול במגוון פורמטים (TRUE/FALSE, 0/1, מחרוזת)
        rev_str = str(reverse_value).strip().upper()
        is_reverse = rev_str in ["TRUE", "1", "YES", "T"]
        
        if is_reverse:
            return 6 - int(answer)
        return int(answer)
    except:
        return int(answer)

def check_response_time(duration):
    """בדיקה אם זמן התגובה תקין או חשוד (בשניות)"""
    if duration < 1.8:
        return "מהיר מדי"
    if duration > 25:
        return "איטי מדי"
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
                inconsistency_alerts.append({
                    "text": f"חוסר עקביות חמור בתכונת {trait} (פער של {score_range:.1f})",
                    "level": "red"
                })
            elif score_range >= 2.2:
                inconsistency_alerts.append({
                    "text": f"חוסר עקביות בינוני בתכונת {trait} (פער של {score_range:.1f})",
                    "level": "orange"
                })
    return inconsistency_alerts

def get_inconsistent_questions(df_raw):
    """מאתרת זוגות ספציפיים של שאלות מאותה תכונה שהתשובות עליהן סותרות"""
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
                        'trait': trait,
                        'q1_text': q1['question'],
                        'q1_ans': q1['original_answer'],
                        'q2_text': q2['question'],
                        'q2_ans': q2['original_answer']
                    })
    return inconsistencies

def process_results(user_responses):
    """מעבד את התשובות לדאטה-פרים מסודר ומחשב ממוצעים"""
    df = pd.DataFrame(user_responses)
    if df.empty:
        return df, pd.DataFrame()
        
    df['time_status'] = df['time_taken'].apply(check_response_time)
    
    summary = df.groupby('trait').agg({
        'final_score': 'mean',
        'time_taken': 'mean'
    }).reset_index()
    
    summary['final_score'] = summary['final_score'].round(2)
    return df, summary

def fix_heb(text):
    """הופכת טקסט עברית ל-RTL ויזואלית ל-PDF ומנקה תווים בעייתיים"""
    if not text: return ""
    # ניקוי תווים שעלולים לשבור את הפונט ב-PDF
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-]', '', str(text))
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    """מפיק דוח PDF תואם fpdf2 עם הגנות שגיאה"""
    # יצירת אובייקט PDF (ב-fpdf2 אין צורך בפרמטרים מיוחדים ל-UTF8, זה מובנה)
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    
    # ניסיון טעינת פונט - חשוב מאוד לעברית!
    try:
        pdf.add_font('Assistant', '', 'Assistant.ttf')
        font_main = 'Assistant'
    except:
        # אם הקובץ Assistant.ttf לא קיים בתיקייה, נשתמש ב-Arial כברירת מחדל
        font_main = 'Helvetica' # Helvetica היא ברירת מחדל בטוחה ב-fpdf2

    # --- דף 1: סיכום מנהלים ---
    pdf.add_page()
    pdf.set_font(font_main, size=24)
    # שימוש ב-multi_cell או cell עם טקסט הפוך
    pdf.cell(0, 20, txt=fix_heb("דוח הכנה למבחני מסר - HEXACO"), ln=True, align='C')
    
    pdf.set_font(font_main, size=12)
    curr_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 10, txt=fix_heb(f"תאריך ביצוע: {curr_time}"), ln=True, align='C')
    pdf.ln(10)
    
    # כותרות טבלה
    pdf.set_font(font_main, size=14)
    pdf.set_fill_color(30, 144, 255) # כחול
    pdf.set_text_color(255, 255, 255)
    
    # סדר העמודות מימין לשמאל ב-PDF
    pdf.cell(60, 12, fix_heb("תכונת אישיות"), 1, 0, 'C', True)
    pdf.cell(60, 12, fix_heb("ציון"), 1, 0, 'C', True)
    pdf.cell(60, 12, fix_heb("סטטוס יעד"), 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font_main, size=12)
    for _, row in summary_df.iterrows():
        score = row['final_score']
        status = "תקין" if 3.5 <= score <= 4.5 else "דורש שיפור"
        pdf.cell(60, 10, fix_heb(str(row['trait'])), 1, 0, 'R')
        pdf.cell(60, 10, f"{score:.2f}", 1, 0, 'C')
        pdf.cell(60, 10, fix_heb(status), 1, 1, 'C')

    # --- דף 2: ניתוח סתירות פנימיות ---
    df_raw = pd.DataFrame(raw_responses)
    inconsistencies = get_inconsistent_questions(df_raw)
    
    if inconsistencies:
        pdf.add_page()
        pdf.set_font(font_main, size=18)
        pdf.cell(0, 15, txt=fix_heb("ניתוח סתירות פנימיות"), ln=True, align='R')
        pdf.ln(5)
        pdf.set_font(font_main, size=11)
        
        for pair in inconsistencies:
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 10, txt=fix_heb(f"סתירה בתכונת: {pair['trait']}"), ln=True, align='R')
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 8, txt=fix_heb(f"שאלה 1: {pair['q1_text']} (תשובה: {pair['q1_ans']})"), align='R')
            pdf.multi_cell(0, 8, txt=fix_heb(f"שאלה 2: {pair['q2_text']} (תשובה: {pair['q2_ans']})"), align='R')
            pdf.ln(2)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)

    return bytes(pdf.output())
