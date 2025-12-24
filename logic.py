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
    """בקרת עקביות ברמזור: פער 3 אדום, פער 2 כתום"""
    inconsistency_alerts = []
    if df.empty:
        return inconsistency_alerts

    for trait in df['trait'].unique():
        trait_data = df[df['trait'] == trait]
        if len(trait_data) > 1:
            score_range = trait_data['final_score'].max() - trait_data['final_score'].min()
            
            if score_range >= 3:
                inconsistency_alerts.append({
                    "text": f"חוסר עקביות חמור בתכונת {trait} (פער של {score_range:.1f})",
                    "level": "red"
                })
            elif score_range >= 2:
                inconsistency_alerts.append({
                    "text": f"חוסר עקביות בינוני בתכונת {trait} (פער של {score_range:.1f})",
                    "level": "orange"
                })
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
    """מנגנון הרמזור מול פרופיל רופא למבחני מס"ר"""
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
    """הופכת טקסט עברית ל-RTL ויזואלית ומנקה תווים בעייתיים"""
    if not text:
        return ""
    # ניקוי תווים שעלולים לשבור את ה-PDF
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-]', '', str(text))
    # היפוך הטקסט לעברית ויזואלית (נחוץ ב-fpdf)
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    """מפיק דוח PDF מקצועי תואם fpdf2"""
    # יצירת אובייקט PDF בפורמט A4
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    
    # טעינת פונט עברי (חובה שקובץ ה-ttf יהיה בתיקייה הראשית ב-Github)
    try:
        pdf.add_font('Assistant', '', 'Assistant.ttf')
        font_name = 'Assistant'
    except:
        font_name = 'Arial' # גיבוי למקרה שהפונט חסר

    # --- דף 1: סיכום ציונים ---
    pdf.add_page()
    pdf.set_font(font_name, size=24)
    pdf.cell(0, 20, txt=fix_heb("דוח סימולציית HEXACO - הכנה למסר"), ln=True, align='C')
    pdf.ln(10)
    
    # כותרות טבלה
    pdf.set_font(font_name, size=14)
    pdf.set_fill_color(230, 230, 230)
    
    # ב-fpdf2 אנחנו מציירים את הטבלה מימין לשמאל בגלל העברית
    col_width = 60
    pdf.cell(col_width, 12, fix_heb("עומד בטווח"), 1, 0, 'C', True)
    pdf.cell(col_width, 12, fix_heb("ציון"), 1, 0, 'C', True)
    pdf.cell(col_width, 12, fix_heb("תכונה"), 1, 1, 'C', True)
    
    pdf.set_font(font_name, size=12)
    for _, row in summary_df.iterrows():
        score = row['final_score']
        in_range = "כן" if 3.5 <= score <= 4.5 else "לא"
        
        pdf.cell(col_width, 10, fix_heb(in_range), 1, 0, 'C')
        pdf.cell(col_width, 10, f"{score:.2f}", 1, 0, 'C')
        pdf.cell(col_width, 10, fix_heb(str(row['trait'])), 1, 1, 'R')
    
    # --- דף 2: פירוט תשובות ---
    pdf.add_page()
    pdf.set_font(font_name, size=18)
    pdf.cell(0, 15, txt=fix_heb("נספח תשובות מלא"), ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_font(font_name, size=10)
    for i, resp in enumerate(raw_responses):
        if pdf.get_y() > 260: # בדיקת סוף עמוד
            pdf.add_page()
            
        # שאלה
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 8, txt=fix_heb(f"{i+1}. {resp['question']}"), align='R')
        
        # תשובה וזמן
        pdf.set_text_color(80, 80, 80)
        ans_txt = f"תשובה שנבחרה: {resp['original_answer']} | זמן תגובה: {resp['time_taken']:.1f} שניות"
        pdf.cell(0, 6, txt=fix_heb(ans_txt), ln=True, align='R')
        pdf.ln(2)

    # החזרת ה-PDF כ-Bytes
    return bytes(pdf.output())
