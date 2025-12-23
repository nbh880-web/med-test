import pandas as pd
from fpdf import FPDF
import re

def calculate_score(answer, reverse_value):
    """מחשב ציון סופי לפי עמודת ה-reverse מהאקסל"""
    try:
        is_reverse = str(reverse_value).strip().upper() == "TRUE"
        if is_reverse:
            return 6 - answer
        return answer
    except:
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
    if df.empty:
        return df, pd.DataFrame()
        
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

def fix_heb(text):
    """הופכת טקסט עברית ל-RTL ויזואלי ומנקה תווים בעייתיים"""
    if not text:
        return ""
    # ניקוי תווים שעלולים לשבור את הפונט ב-PDF
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-]', '', str(text))
    # הפיכת סדר האותיות לעברית ויזואלית
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    """מפיק דוח תוצאות ודף נספח תשובות (ללא ה-AI)"""
    pdf = FPDF()
    
    # --- דף 1: דף תוצאות מסוכם (להדפסה) ---
    pdf.add_page()
    try:
        pdf.add_font('HebrewFont', '', 'Assistant.ttf', uni=True)
        pdf.set_font('HebrewFont', size=20)
    except:
        pdf.set_font("Arial", size=20)

    # כותרת
    pdf.cell(0, 20, txt=fix_heb("דוח תוצאות סימולציית HEXACO - הכנה לרפואה"), ln=True, align='C')
    pdf.ln(10)
    
    # טבלת ציונים מעוצבת
    pdf.set_font('HebrewFont', size=14)
    pdf.set_fill_color(240, 240, 240) # צבע רקע לכותרות הטבלה
    
    w_trait, w_score, w_range = 80, 50, 50
    pdf.cell(w_range, 12, fix_heb("עומד בטווח"), 1, 0, 'C', True)
    pdf.cell(w_score, 12, fix_heb("ציון"), 1, 0, 'C', True)
    pdf.cell(w_trait, 12, fix_heb("תכונה"), 1, 1, 'C', True)
    
    pdf.set_font('HebrewFont', size=12)
    for _, row in summary_df.iterrows():
        score = row['final_score']
        in_range = "כן" if 3.5 <= score <= 4.5 else "לא"
        
        pdf.cell(w_range, 10, fix_heb(in_range), 1, 0, 'C')
        pdf.cell(w_score, 10, f"{score:.2f}", 1, 0, 'C')
        pdf.cell(w_trait, 10, fix_heb(str(row['trait'])), 1, 1, 'R')
    
    # --- דף 2 והלאה: נספח תשובות מלא ---
    pdf.add_page()
    pdf.set_font('HebrewFont', size=16)
    pdf.cell(0, 15, txt=fix_heb("נספח: פירוט שאלות ותשובות"), ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_font('HebrewFont', size=10)
    for i, resp in enumerate(raw_responses):
        # בדיקה אם צריך לרדת עמוד
        if pdf.get_y() > 270:
            pdf.add_page()
            
        # הדפסת השאלה
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, txt=fix_heb(f"{i+1}. {resp['question']}"), align='R')
        
        # הדפסת התשובה
        pdf.set_text_color(100, 100, 100)
        ans_line = f"תשובה: {resp['original_answer']} | זמן: {resp['time_taken']:.1f} שניות"
        pdf.cell(0, 7, txt=fix_heb(ans_line), ln=True, align='R')
        pdf.ln(2)

    # יצוא ל-bytes עם טיפול בפורמט
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, bytearray):
        return bytes(pdf_output)
    return pdf_output
