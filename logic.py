import pandas as pd
from fpdf import FPDF
import re
from datetime import datetime
import numpy as np

# הגדרת הפרופיל האידיאלי
IDEAL_RANGES = {
    'Conscientiousness': (4.3, 4.8),
    'Honesty-Humility': (4.2, 4.9),
    'Agreeableness': (4.0, 4.6),
    'Emotionality': (3.6, 4.1),
    'Extraversion': (3.6, 4.2),
    'Openness to Experience': (3.5, 4.1)
}

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

def get_static_interpretation(trait, score):
    """מחזיר פרשנות מובנית מבוססת טווחים"""
    trait_map = {
        'H': 'Honesty-Humility', 'E': 'Emotionality', 'X': 'Extraversion',
        'A': 'Agreeableness', 'C': 'Conscientiousness', 'O': 'Openness to Experience'
    }
    full_trait = trait_map.get(trait, trait)
    
    if full_trait not in IDEAL_RANGES:
        return "ניתוח כללי של התכונה."

    low_limit, high_limit = IDEAL_RANGES[full_trait]
    
    if score < 3.0:
        return f"⚠️ ציון נמוך משמעותית מהמצופה מרופא. מומלץ לבחון האם התשובות שיקפו את המציאות או חוסר הבנה."
    elif score < low_limit:
        return f"הציון מעט נמוך מהטווח האידיאלי ({low_limit}-{high_limit}). כדאי להדגיש חוזקות אחרות בראיון."
    elif score <= high_limit:
        return f"✅ ציון מצוין! נמצא בטווח האידיאלי עבור מועמדים לרפואה."
    else:
        if score >= 4.9:
            return "❗ ציון גבוה מאוד (קרוב ל-5). בוחנים עלולים לחשוד בניסיון 'לייפות' את המציאות (Social Desirability)."
        return f"הציון מעט גבוה מהטווח המומלץ, אך עדיין משקף יכולות טובות."

def calculate_medical_fit(summary_df):
    """מחשב מדד התאמה כללי באחוזים"""
    if summary_df.empty: return 0
    points = 0
    total_traits = len(IDEAL_RANGES)
    
    for _, row in summary_df.iterrows():
        trait = row['trait']
        score = row['final_score']
        if trait in IDEAL_RANGES:
            low, high = IDEAL_RANGES[trait]
            if low <= score <= high:
                points += 1
            elif abs(score - ((low+high)/2)) < 0.7: 
                points += 0.5
                
    return int((points / total_traits) * 100)

def check_response_time(duration):
    """בדיקת תקינות זמן תגובה לשאלה בודדת"""
    if duration < 1.8: return "מהיר מדי"
    if duration > 25: return "איטי מדי"
    return "תקין"

def calculate_reliability_index(df_raw):
    """
    מחשב ציון אמינות כללי (0-100)
    מבוסס על סתירות, מהירות תגובה ודפוסי תשובה
    """
    if df_raw.empty: return 100
    penalty = 0
    
    # 1. קנס על תשובה מהירה מדי (פחות מ-1.5 שניות) - מעיד על חוסר קריאה
    fast_count = len(df_raw[df_raw['time_taken'] < 1.5])
    penalty += (fast_count / len(df_raw)) * 60
    
    # 2. קנס על סתירות פנימיות
    inconsistencies = get_inconsistent_questions(df_raw)
    penalty += len(inconsistencies) * 12
    
    # 3. בדיקת "עקביות יתר" (מענה על אותה ספרה כל הזמן)
    if len(df_raw) > 10:
        std_dev = df_raw['original_answer'].std()
        if std_dev < 0.4: penalty += 40 # ענה כמעט תמיד את אותה תשובה
        
    reliability = max(0, min(100, int(100 - penalty)))
    return reliability

def analyze_consistency(df):
    """ניתוח עקביות לפי תכונות והתראות מהירות"""
    inconsistency_alerts = []
    if df.empty or 'trait' not in df.columns: return inconsistency_alerts
    
    # בדיקת זמן ממוצע
    avg_time = df['time_taken'].mean()
    if avg_time < 2.5:
        inconsistency_alerts.append({"text": "קצב מענה מהיר מהממוצע - ייתכן חוסר ריכוז", "level": "orange"})

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
    """מציף זוגות של שאלות שנסתרו מהותית"""
    inconsistencies = []
    if df_raw.empty: return []
    for trait in df_raw['trait'].unique():
        trait_qs = df_raw[df_raw['trait'] == trait]
        for i in range(len(trait_qs)):
            for j in range(i + 1, len(trait_qs)):
                q1 = trait_qs.iloc[i]; q2 = trait_qs.iloc[j]
                # אם הפער בין הציונים הסופיים (אחרי היפוך) גדול מ-2.5
                if abs(q1['final_score'] - q2['final_score']) >= 2.5:
                    inconsistencies.append({
                        'trait': trait, 
                        'q1_text': q1['question'],
                        'q1_ans': q1['original_answer'], 
                        'q2_text': q2['question'],
                        'q2_ans': q2['original_answer'],
                        'diff': round(abs(q1['final_score'] - q2['final_score']), 2)
                    })
    return inconsistencies

def process_results(user_responses):
    """מעבד את התשובות ומוסיף נתוני זמן ואמינות"""
    df = pd.DataFrame(user_responses)
    if df.empty: return df, pd.DataFrame()
    
    df['time_status'] = df['time_taken'].apply(check_response_time)
    
    summary = df.groupby('trait').agg({
        'final_score': 'mean', 
        'time_taken': 'mean'
    }).reset_index()
    
    summary['final_score'] = summary['final_score'].round(2)
    summary['avg_time'] = summary['time_taken'].round(1)
    
    return df, summary

def fix_heb(text):
    """תיקון ויזואלי לעברית ב-PDF"""
    if not text: return " "
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-]', '', str(text))
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    """יצירת דוח PDF הכולל מדדי התאמה ואמינות"""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    try:
        pdf.add_font('Assistant', '', 'Assistant.ttf')
        font_main = 'Assistant'
    except:
        font_main = 'Helvetica'

    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    
    # כותרת
    pdf.set_font(font_main, size=22)
    pdf.cell(180, 15, txt=fix_heb("דוח תוצאות HEXACO - הכנה לרפואה"), ln=True, align='C')
    
    # מדדי על (התאמה ואמינות)
    fit_score = calculate_medical_fit(summary_df)
    rel_score = calculate_reliability_index(raw_responses)
    
    pdf.set_font(font_main, size=14)
    pdf.cell(180, 8, txt=fix_heb(f"מדד התאמה לפרופיל רופא: {fit_score}%"), ln=True, align='C')
    pdf.cell(180, 8, txt=fix_heb(f"מדד אמינות ועקביות מבדק: {rel_score}%"), ln=True, align='C')
    pdf.ln(10)

    # טבלת תוצאות
    col_w = 60
    pdf.set_font(font_main, size=12)
    pdf.set_fill_color(30, 58, 138) # כחול כהה
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_w, 10, fix_heb("זמן ממוצע (ש')"), 1, 0, 'C', True)
    pdf.cell(col_w, 10, fix_heb("ציון"), 1, 0, 'C', True)
    pdf.cell(col_w, 10, fix_heb("תכונה"), 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0)
    for _, row in summary_df.iterrows():
        pdf.cell(col_w, 10, str(row.get('avg_time', 'N/A')), 1, 0, 'C')
        pdf.cell(col_w, 10, str(row['final_score']), 1, 0, 'C')
        pdf.cell(col_w, 10, fix_heb(str(row['trait'])), 1, 1, 'C')

    # הוספת התראות אמינות ל-PDF אם קיימות
    alerts = analyze_consistency(raw_responses)
    if alerts:
        pdf.ln(10)
        pdf.set_font(font_main, size=14, style='B')
        pdf.cell(180, 10, txt=fix_heb("הערות בוחן ואמינות:"), ln=True, align='R')
        pdf.set_font(font_main, size=11)
        for alert in alerts:
            pdf.cell(180, 7, txt=fix_heb(f"• {alert['text']}"), ln=True, align='R')

    return bytes(pdf.output())