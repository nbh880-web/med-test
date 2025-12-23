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
    """معבד את התשובות לדאטה-פרים מסודר"""
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
    """מנקה תווים בעייתיים והופכת טקסט עברית ל-RTL ויזואלי"""
    if not text or not isinstance(text, str):
        return ""
    
    # 1. ניקוי תווים ששוברים את ה-PDF
    clean_text = re.sub(r'[*#_]', '', text)
    
    # 2. החלפת ירידות שורה ברווחים למניעת שגיאות עימוד
    clean_text = clean_text.replace('\n', ' ').replace('\r', ' ')
    
    # 3. צמצום רווחים כפולים
    clean_text = " ".join(clean_text.split())
    
    # 4. הפיכת סדר האותיות (עברית ויזואלית)
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses, ai_report):
    """מפיק דו"ח PDF מעוצב"""
    pdf = FPDF()
    pdf.add_page()
    
    try:
        pdf.add_font('HebrewFont', '', 'Assistant.ttf', uni=True)
        pdf.set_font('HebrewFont', size=16)
    except:
        pdf.set_font("Arial", size=16)

    # כותרת
    pdf.cell(0, 15, txt=fix_heb("דוח סיכום סימולציה - הכנה לרפואה"), ln=True, align='C')
    pdf.ln(5)
    
    # טבלת סיכום
    pdf.set_font('HebrewFont', size=12)
    w_trait, w_score, w_range = 80, 50, 50
    
    pdf.cell(w_trait, 10, fix_heb("תכונה"), border=1, align='C')
    pdf.cell(w_score, 10, fix_heb("ציון"), border=1, align='C')
    pdf.cell(w_range, 10, fix_heb("עומד בטווח"), border=1, align='C')
    pdf.ln()
    
    for _, row in summary_df.iterrows():
        score = row['final_score']
        in_range = "כן" if 3.5 <= score <= 4.5 else "לא"
        pdf.cell(w_trait, 10, fix_heb(str(row['trait'])), border=1, align='R')
        pdf.cell(w_score, 10, f"{score:.2f}", border=1, align='C')
        pdf.cell(w_range, 10, fix_heb(in_range), border=1, align='C')
        pdf.ln()
    
    pdf.ln(10)

    # ניתוח AI
    pdf.set_font('HebrewFont', size=14)
    pdf.cell(0, 10, txt=fix_heb("ניתוח AI מקצועי:"), ln=True, align='R')
    pdf.set_font('HebrewFont', size=11)
    
    ai_text = ai_report if ai_report else "לא הופק ניתוח"
    pdf.multi_cell(0, 8, txt=fix_heb(ai_text), align='R')
    
    # פירוט תשובות (עמוד חדש)
    pdf.add_page()
    pdf.set_font('HebrewFont', size=14)
    pdf.cell(0, 10, txt=fix_heb("פירוט תשובות מלא:"), ln=True, align='R')
    pdf.ln(5)
    
    for i, resp in enumerate(raw_responses):
        q_clean = resp['question'][:90] + "..." if len(resp['question']) > 90 else resp['question']
        q_line = f"{i+1}. {q_clean}"
        ans_line = f"תשובה: {resp['original_answer']} | זמן: {resp['time_taken']:.1f} שניות"
        
        pdf.set_font('HebrewFont', size=10)
        pdf.multi_cell(0, 7, txt=fix_heb(q_line), align='R')
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 7, txt=fix_heb(ans_line), align='R')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        
    return pdf.output(dest='S')
