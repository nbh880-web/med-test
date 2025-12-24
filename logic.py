import pandas as pd
from fpdf import FPDF
import re
from datetime import datetime

def calculate_score(answer, reverse_value):
    """מחשב ציון סופי לפי עמודת ה-reverse מהאקסל"""
    try:
        # טיפול במגוון פורמטים של ה-CSV (מחרוזת, בוליאני, או ריק)
        rev_str = str(reverse_value).strip().upper()
        is_reverse = rev_str in ["TRUE", "1", "YES", "T"]
        
        if is_reverse:
            return 6 - int(answer)
        return int(answer)
    except:
        return answer

def check_response_time(duration):
    """בדיקה אם זמן התגובה חשוד (בשניות)"""
    if duration < 1.8: # העליתי מעט את הסף ל-1.8 למקצועיות
        return "מהיר מדי"
    if duration > 25:
        return "איטי מדי"
    return "תקין"

def analyze_consistency(df):
    """בקרת עקביות ברמזור: פער 3 אדום, פער 2 כתום"""
    inconsistency_alerts = []
    if df.empty or 'trait' not in df.columns:
        return inconsistency_alerts

    for trait in df['trait'].unique():
        trait_data = df[df['trait'] == trait]
        # נדרשות לפחות 3 שאלות לאותה תכונה כדי לקבוע חוסר עקביות סטטיסטי
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

def process_results(user_responses):
    """מעבד את התשובות לדאטה-פרים מסודר ומחשב ממוצעים"""
    df = pd.DataFrame(user_responses)
    if df.empty:
        return df, pd.DataFrame()
        
    df['time_status'] = df['time_taken'].apply(check_response_time)
    
    # חישוב ממוצעים לכל תכונה
    summary = df.groupby('trait').agg({
        'final_score': 'mean',
        'time_taken': 'mean'
    }).reset_index()
    
    # עיגול ציונים ל-2 ספרות אחרי הנקודה
    summary['final_score'] = summary['final_score'].round(2)
    
    return df, summary

def fix_heb(text):
    """הופכת טקסט עברית ל-RTL ויזואלית ומנקה תווים בעייתיים"""
    if not text:
        return ""
    # ניקוי תווים מיוחדים שעלולים לגרום לקריסת ה-PDF
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-平衡]', '', str(text))
    # היפוך הטקסט (Visual RTL)
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    """מפיק דוח PDF מקצועי ומעוצב"""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    
    # טעינת פונט עברי - וודא ש-Assistant.ttf נמצא בתיקיית השורש
    try:
        pdf.add_font('Assistant', '', 'Assistant.ttf')
        font_main = 'Assistant'
    except:
        font_main = 'Arial'

    # --- דף 1: סיכום מנהלים ---
    pdf.add_page()
    
    # כותרת ראשית
    pdf.set_font(font_main, size=24)
    pdf.cell(0, 20, txt=fix_heb("דוח הכנה למבחני מס\"ר - HEXACO"), ln=True, align='C')
    
    # תאריך הפקת הדוח
    pdf.set_font(font_main, size=12)
    curr_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 10, txt=fix_heb(f"תאריך ביצוע: {curr_time}"), ln=True, align='C')
    pdf.ln(15)
    
    # טבלת ציונים
    pdf.set_font(font_main, size=14)
    pdf.set_fill_color(30, 144, 255) # כחול מקצועי
    pdf.set_text_color(255, 255, 255)
    
    col_width = 60
    pdf.cell(col_width, 12, fix_heb("סטטוס יעד"), 1, 0, 'C', True)
    pdf.cell(col_width, 12, fix_heb("ציון"), 1, 0, 'C', True)
    pdf.cell(col_width, 12, fix_heb("תכונת אישיות"), 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font_main, size=12)
    
    for _, row in summary_df.iterrows():
        score = row['final_score']
        status = "תקין" if 3.5 <= score <= 4.5 else "דורש שיפור"
        
        pdf.cell(col_width, 10, fix_heb(status), 1, 0, 'C')
        pdf.cell(col_width, 10, f"{score:.2f}", 1, 0, 'C')
        pdf.cell(col_width, 10, fix_heb(str(row['trait'])), 1, 1, 'R')
    
    # --- דף 2: פירוט תשובות וזמנים ---
    pdf.add_page()
    pdf.set_font(font_main, size=18)
    pdf.cell(0, 15, txt=fix_heb("פירוט תשובות גולמיות"), ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_font(font_main, size=10)
    for i, resp in enumerate(raw_responses):
        if pdf.get_y() > 260:
            pdf.add_page()
            
        # הדפסת השאלה
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 8, txt=fix_heb(f"{i+1}. {resp['question']}"), align='R')
        
        # הדפסת התשובה וזמן התגובה
        pdf.set_text_color(100, 100, 100)
        ans_info = f"תשובה: {resp['original_answer']} | זמן: {resp['time_taken']:.1f} שניות"
        pdf.cell(0, 6, txt=fix_heb(ans_info), ln=True, align='R')
        pdf.ln(2)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y()) # קו מפריד עדין
        pdf.ln(2)

    return bytes(pdf.output())
