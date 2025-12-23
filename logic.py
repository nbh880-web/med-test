import pandas as pd
from fpdf import FPDF
import re

def calculate_score(answer, reverse_value):
    is_reverse = str(reverse_value).strip().upper() == "TRUE"
    return (6 - answer) if is_reverse else answer

def check_response_time(duration):
    if duration < 1.5: return "מהיר מדי"
    if duration > 20: return "איטי מדי"
    return "תקין"

def process_results(user_responses):
    df = pd.DataFrame(user_responses)
    summary = df.groupby('trait')['final_score'].mean().reset_index()
    return df, summary

def fix_heb(text):
    if not text or not isinstance(text, str):
        return ""
    # ניקוי תווים שעלולים לשבור את חישוב הרווח ב-PDF
    clean_text = re.sub(r'[*\#_]', '', text) 
    clean_text = clean_text.replace('\n', ' ').strip()
    # הפיכת סדר האותיות לעברית ויזואלית
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses, ai_report):
    pdf = FPDF()
    pdf.add_page()
    
    try:
        pdf.add_font('HebrewFont', '', 'Assistant.ttf', uni=True)
        pdf.set_font('HebrewFont', size=16)
    except:
        pdf.set_font("Arial", size=16)

    # כותרת
    pdf.cell(0, 10, txt=fix_heb("דוח סיכום סימולציה - הכנה לרפואה"), ln=True, align='C')
    pdf.ln(10)
    
    # טבלה עם עמודות ברוחב קבוע ובטוח
    pdf.set_font('HebrewFont', size=12)
    pdf.cell(60, 10, fix_heb("תכונה"), border=1, align='C')
    pdf.cell(50, 10, fix_heb("ציון"), border=1, align='C')
    pdf.cell(60, 10, fix_heb("בטווח?"), border=1, align='C')
    pdf.ln()
    
    for _, row in summary_df.iterrows():
        score = row['final_score']
        pdf.cell(60, 10, fix_heb(str(row['trait'])), border=1, align='R')
        pdf.cell(50, 10, f"{score:.2f}", border=1, align='C')
        pdf.cell(60, 10, fix_heb("כן" if 3.5 <= score <= 4.5 else "לא"), border=1, align='C')
        pdf.ln()
    
    pdf.ln(10)
    pdf.set_font('HebrewFont', size=14)
    pdf.cell(0, 10, txt=fix_heb("ניתוח AI:"), ln=True, align='R')
    pdf.set_font('HebrewFont', size=11)
    
    # שימוש ב-multi_cell עם רוחב 0 כדי למנוע את שגיאת ה-Space
    pdf.multi_cell(0, 8, txt=fix_heb(ai_report), align='R')
    
    return pdf.output(dest='S')
