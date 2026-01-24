import pandas as pd
from fpdf import FPDF
import re
from datetime import datetime
import numpy as np
import random
import io

# 1. הגדרת הפרופיל האידיאלי (TRAIT_RANGES)
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
        # תמיכה רחבה בערכי Boolean שונים מהאקסל
        is_reverse = rev_str in ["TRUE", "1", "YES", "T", "ת", "אמת"]
        val = int(answer)
        if is_reverse:
            return 6 - val
        return val
    except (ValueError, TypeError):
        # במקרה של תקלה בנתון, נחזיר ערך נייטרלי (3)
        return 3

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
    """חישוב מדד התאמה משופר - מחשב פערים (Gap Analysis)"""
    if summary_df is None or summary_df.empty: return 0
    total_penalty = 0
    traits_found = 0
    
    for _, row in summary_df.iterrows():
        trait = row['trait']
        score = row['final_score']
        if trait in IDEAL_RANGES:
            traits_found += 1
            low, high = IDEAL_RANGES[trait]
            if score < low:
                total_penalty += (low - score) * 1.2
            elif score > high:
                total_penalty += (score - high) * 0.5
                
    if traits_found == 0: return 0
    fit_score = 100 - (total_penalty * 15)
    return int(max(0, min(100, fit_score)))

def check_response_time(duration):
    """בדיקת תקינות זמן תגובה לשאלה בודדת"""
    if duration < 1.8: return "מהיר מדי"
    if duration > 25: return "איטי מדי"
    return "תקין"

def get_inconsistent_questions(df_raw):
    """זיהוי שאלות סותרות עם לוגיקת סף דינמית"""
    inconsistencies = []
    if df_raw is None or df_raw.empty: return []
    
    for trait in df_raw['trait'].unique():
        trait_qs = df_raw[df_raw['trait'] == trait]
        for i in range(len(trait_qs)):
            for j in range(i + 1, len(trait_qs)):
                q1 = trait_qs.iloc[i]
                q2 = trait_qs.iloc[j]
                diff = abs(q1['final_score'] - q2['final_score'])
                if diff >= 2.5:
                    inconsistencies.append({
                        'trait': trait, 
                        'q1_text': q1.get('question', q1.get('q', 'שאלה')),
                        'q1_ans': q1.get('original_answer', q1['final_score']), 
                        'q2_text': q2.get('question', q2.get('q', 'שאלה')),
                        'q2_ans': q2.get('original_answer', q2['final_score']), 
                        'diff': round(diff, 2)
                    })
    return inconsistencies

def calculate_reliability_index(df_raw):
    """ציון אמינות (0-100) - שדרוג: נוספו משקולות סטטיסטיות"""
    if df_raw is None or df_raw.empty: return 100
    penalty = 0
    
    # 1. קנס על מהירות (משקולת גבוהה)
    fast_count = len(df_raw[df_raw['time_taken'] < 1.4])
    penalty += (fast_count / len(df_raw)) * 70 
    
    # 2. סתירות פנימיות
    inconsistencies = get_inconsistent_questions(df_raw)
    penalty += len(inconsistencies) * 15
    
    # 3. דפוס תשובה מונוטוני (SD נמוך מאוד)
    if len(df_raw) > 15:
        std_dev = df_raw['final_score'].std()
        if std_dev < 0.35: penalty += 45
        elif std_dev < 0.5: penalty += 20
        
    return int(max(0, min(100, 100 - penalty)))

def analyze_consistency(df):
    """ניתוח עקביות ומגמות זמן"""
    inconsistency_alerts = []
    if df is None or df.empty or 'trait' not in df.columns: return inconsistency_alerts
    
    avg_time = df['time_taken'].mean()
    if avg_time < 2.2:
        inconsistency_alerts.append({"text": "קצב מענה מהיר מהממוצע - דורש בדיקת אמינות", "level": "orange"})
    elif avg_time > 15:
        inconsistency_alerts.append({"text": "מענה איטי במיוחד - ייתכן ניסיון לניתוח יתר", "level": "blue"})

    for trait in df['trait'].unique():
        trait_data = df[df['trait'] == trait]
        if len(trait_data) >= 2:
            score_range = trait_data['final_score'].max() - trait_data['final_score'].min()
            if score_range >= 3:
                inconsistency_alerts.append({"text": f"סתירה חמורה בתכונת {trait}", "level": "red"})
            elif score_range >= 2.1:
                inconsistency_alerts.append({"text": f"חוסר עקביות ב-{trait}", "level": "orange"})
    return inconsistency_alerts

def process_results(user_responses):
    """מעבד את התשובות ומוסיף נתוני זמן ואמינות"""
    df = pd.DataFrame(user_responses)
    if df.empty: return df, pd.DataFrame()
    
    df['time_status'] = df['time_taken'].apply(check_response_time)
    
    summary = df.groupby('trait').agg({
        'final_score': 'mean', 
        'time_taken': 'mean'
    }).reset_index()
    
    # חישוב עקביות פנימית לתכונה
    std_by_trait = df.groupby('trait')['final_score'].std().fillna(0)
    summary['consistency_score'] = summary['trait'].map(lambda x: round((1 - (std_by_trait[x] / 4)).clip(0, 1), 2))
    
    summary['final_score'] = summary['final_score'].round(2)
    summary['avg_time'] = summary['time_taken'].round(1)
    
    return df, summary

def fix_heb(text):
    """תיקון ויזואלי לעברית ב-PDF"""
    if not text: return " "
    text = str(text)
    clean_text = re.sub(r'[^\u0590-\u05FF0-9\s.,?!:()\-]', '', text)
    return clean_text[::-1]

def create_pdf_report(summary_df, raw_responses):
    """יצירת דוח PDF עם עיצוב מלא"""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    try:
        pdf.add_font('Assistant', '', 'Assistant.ttf', uni=True)
        font_main = 'Assistant'
    except Exception:
        font_main = 'Arial' # Fallback בטוח

    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    
    # עיצוב כותרת ורקע עליון
    pdf.set_fill_color(240, 242, 246)
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font(font_main, size=22)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(180, 20, txt=fix_heb("דוח מבדק אישיות HEXACO - הכנה לרפואה"), ln=True, align='C')
    
    fit_score = calculate_medical_fit(summary_df)
    rel_score = calculate_reliability_index(raw_responses)
    
    pdf.set_font(font_main, size=16)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    pdf.cell(90, 10, fix_heb(f"אמינות מבדק: {rel_score}%"), 0, 0, 'C')
    pdf.cell(90, 10, fix_heb(f"התאמה לרפואה: {fit_score}%"), 0, 1, 'C')
    pdf.ln(10)

    # טבלת תוצאות מעוצבת
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_main, size=12) # הסרת style='B' כי פונטים מקוסטמים לפעמים לא תומכים בו
    
    cols = [("זמן ממוצע", 40), ("סטטוס", 40), ("ציון", 30), ("תכונה", 70)]
    for txt, width in cols:
        pdf.cell(width, 10, fix_heb(txt), 1, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font_main, size=11)
    for _, row in summary_df.iterrows():
        status = "תקין" if 2 < row['avg_time'] < 10 else "חריג"
        pdf.cell(40, 10, str(row['avg_time']), 1, 0, 'C')
        pdf.cell(40, 10, fix_heb(status), 1, 0, 'C')
        pdf.cell(30, 10, str(row['final_score']), 1, 0, 'C')
        pdf.cell(70, 10, fix_heb(row['trait']), 1, 1, 'R')

    # חלק ניתוח איכותני והתראות
    alerts = analyze_consistency(raw_responses)
    if alerts:
        pdf.ln(10)
        pdf.set_font(font_main, size=14)
        pdf.cell(180, 10, txt=fix_heb("ממצאים בולטים באמינות המענה:"), ln=True, align='R')
        pdf.set_font(font_main, size=11)
        for alert in alerts:
            color = (200, 0, 0) if alert['level'] == 'red' else (255, 140, 0)
            pdf.set_text_color(*color)
            pdf.cell(180, 7, txt=fix_heb(f"• {alert['text']}"), ln=True, align='R')

    return bytes(pdf.output())

def get_balanced_questions(df, total_limit):
    """בחירת שאלות מאוזנת עם הגנה ממחסור במאגר"""
    if df.empty: return []
    traits = df['trait'].unique()
    qs_per_trait = total_limit // len(traits)
    selected_qs = []
    for trait in traits:
        trait_qs = df[df['trait'] == trait].to_dict('records')
        count = min(len(trait_qs), qs_per_trait)
        if count > 0:
            selected_qs.extend(random.sample(trait_qs, count))
    
    # השלמה אם לא הגענו למכסה בגלל חוסר בשאלות בתכונות מסוימות
    if len(selected_qs) < total_limit:
        remaining_count = total_limit - len(selected_qs)
        all_unused = [q for q in df.to_dict('records') if q not in selected_qs]
        if all_unused:
            selected_qs.extend(random.sample(all_unused, min(len(all_unused), remaining_count)))
            
    random.shuffle(selected_qs)
    return selected_qs

def create_excel_download(responses):
    try:
        if not responses:
            return None
            
        # יצירת DataFrame
        df = pd.DataFrame(responses)
        
        # מיפוי עמודות אפשריות (תומך גם ב-HEXACO וגם ביושרה)
        column_mapping = {
            'question': 'שאלה',
            'q': 'שאלה',
            'trait': 'קטגוריה',
            'category': 'קטגוריה',
            'original_answer': 'תשובה',
            'answer': 'תשובה',
            'time_taken': 'זמן מענה (שניות)',
            'origin': 'מקור השאלה'
        }
        
        # נשמור רק עמודות שבאמת קיימות ב-DataFrame
        existing_cols = [c for c in column_mapping.keys() if c in df.columns]
        export_df = df[existing_cols].copy()
        
        # שינוי שמות לעברית
        export_df.rename(columns=column_mapping, inplace=True)
        
        # יצירת הקובץ בזיכרון
        buffer = io.BytesIO()
        # שימוש ב-engine ברירת המחדל של pandas כדי למנוע בעיות התקנה
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='תוצאות מבדק')
            
            # עיצוב בסיסי (אופציונלי)
            workbook = writer.book
            worksheet = writer.sheets['תוצאות מבדק']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25) # הרחבת עמודות
                
        return buffer.getvalue()
    except Exception as e:
        print(f"Excel Error: {e}")
        return None
