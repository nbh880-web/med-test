import pandas as pd
from fpdf import FPDF
import re
from datetime import datetime

# הגדרת הפרופיל האידיאלי (לפי הסיכום שבנינו)
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
    """מחזיר פרשנות מובנית מבוססת טווחים (העוגנים הפסיכולוגיים)"""
    # התאמת שמות אם מגיעים בקיצור
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
            elif abs(score - ((low+high)/2)) < 0.7: # חריגה קלה
                points += 0.5
                
    return int((points / total_traits) * 100)

def check_response_time(duration):
    if duration < 1.8: return "מהיר מדי"
    if duration > 25: return "איטי מדי"
    return "תקין"

def analyze_consistency(df):
    inconsistency_alerts = []
    if df.empty or 'trait' not in df.columns: return inconsistency_alerts
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
    inconsistencies = []
    if df_raw.empty: return []
    for trait in df_raw['trait'].unique():
        trait_qs = df_raw[df_raw['trait'] == trait]
        for i in range(len(trait_qs)):
            for j in range(i + 1, len(trait_qs)):
                q1 = trait_qs.iloc[i]; q2 = trait_qs.iloc[j]
                if abs(q1['final_score'] - q2['final_score']) >= 2.5:
                    inconsistencies.append({
                        'trait': trait, 'q1_text': q1['question'],
                        'q1_ans': q1['original_answer'], 'q2_text': q2['question'],
                        'q2_ans': q2['original_answer']
                    })
    return inconsistencies

def process_results(user_responses):
    df = pd.DataFrame(user_responses)
    if df.empty: return df, pd.DataFrame()
    df['time_status'] = df['time_taken'].apply(check_response_time)
    summary = df.groupby('trait').agg({'final_score': 'mean', 'time_taken': 'mean'}).reset_index()
    summary['final_score'] = summary['final_score'].round(2)
    return df, summary

def fix_heb(text):
    if not text: return " "
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-]', '', str(text))
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    try:
        pdf.add_font('Assistant', '', 'Assistant.ttf')
        font_main = 'Assistant'
    except:
        font_main = 'Helvetica'

    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font(font_main, size=22)
    pdf.cell(180, 15, txt=fix_heb("דוח תוצאות HEXACO - הכנה לרפואה"), ln=True, align='C')
    
    # הוספת מדד ההתאמה ל-PDF
    fit_score = calculate_medical_fit(summary_df)
    pdf.set_font(font_main, size=14)
    pdf.cell(180, 10, txt=fix_heb(f"מדד התאמה משוער לפרופיל רופא: {fit_score}%"), ln=True, align='C')
    pdf.ln(5)

    col_w = 60
    pdf.set_font(font_main, size=12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(col_w, 10, fix_heb("סטטוס"), 1, 0, 'C', True)
    pdf.cell(col_w, 10, fix_heb("ציון"), 1, 0, 'C', True)
    pdf.cell(col_w, 10, fix_heb("תכונה"), 1, 1, 'C', True)

    for _, row in summary_df.iterrows():
        pdf.cell(col_w, 10, fix_heb("מעובד"), 1, 0, 'C')
        pdf.cell(col_w, 10, str(row['final_score']), 1, 0, 'C')
        pdf.cell(col_w, 10, fix_heb(str(row['trait'])), 1, 1, 'C')

    return bytes(pdf.output())