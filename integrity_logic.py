"""
לוגיקת מבחן האמינות - זיהוי סתירות ודפוסי שקר
© זכויות יוצרים לניתאי מלכה
"""

import pandas as pd
import numpy as np
import random
from collections import defaultdict

# קטגוריות המבחן
INTEGRITY_CATEGORIES = {
    'theft': 'גניבה ממקומות עבודה',
    'academic': 'יושרה אקדמית',
    'termination': 'פיטורים והתפטרויות',
    'gambling': 'הימורים',
    'drugs': 'סמים ואלכוהול',
    'whistleblowing': 'דיווח על עמיתים',
    'feedback': 'משוב לעמיתים',
    'teamwork': 'עבודת צוות',
    'unethical': 'התנהגות לא אתית',
    'polygraph': 'נכונות לפוליגרף',
    'regret': 'חרטה על תשובות',
    'honesty_meta': 'כנות בשאלון'
}

def get_integrity_questions(count=140):
    """
    טוען שאלות אמינות ובוחר את הכמות הנדרשת
    """
    try:
        df = pd.read_csv('data/integrity_questions.csv')
    except:
        return []
    
    # הפרדה לשאלות מטא ושאלות תוכן
    meta_questions = df[df['control_type'] == 'meta'].to_dict('records')
    control_questions = df[df['control_type'] == 'main_control'].to_dict('records')
    regular_questions = df[df['control_type'] == 'none'].to_dict('records')
    
    # חישוב כמויות
    meta_count = len(meta_questions)  # כל השאלות המטא (15)
    control_count = len(control_questions)  # שאלות הבקרה (3)
    regular_count = count - meta_count - control_count
    
    # בחירת שאלות רגילות מאוזנות
    selected_regular = []
    categories = [cat for cat in INTEGRITY_CATEGORIES.keys() 
                  if cat not in ['polygraph', 'regret', 'honesty_meta']]
    
    per_category = regular_count // len(categories)
    
    for category in categories:
        cat_questions = [q for q in regular_questions if q['category'] == category]
        if cat_questions:
            sample_size = min(len(cat_questions), per_category)
            selected_regular.extend(random.sample(cat_questions, sample_size))
    
    # השלמה אם חסר
    if len(selected_regular) < regular_count:
        remaining = regular_count - len(selected_regular)
        unused = [q for q in regular_questions if q not in selected_regular]
        if unused:
            selected_regular.extend(random.sample(unused, min(len(unused), remaining)))
    
    # איחוד כל השאלות
    all_questions = selected_regular + control_questions + meta_questions
    random.shuffle(all_questions)
    
    return all_questions

def calculate_integrity_score(answer, reverse):
    """מחשב ציון לשאלת אמינות (1-5)"""
    try:
        rev_str = str(reverse).strip().upper()
        is_reverse = rev_str in ["TRUE", "1", "YES", "T"]
        val = int(answer)
        if is_reverse:
            return 6 - val
        return val
    except:
        return 3

def detect_contradictions(responses_df):
    """
    זיהוי סתירות מתקדם:
    1. סתירות בין שאלות באותה קטגוריה
    2. סתירות בשאלת הבקרה המרכזית (3 ווריאציות)
    3. סתירות בשאלות מטא (פוליגרף, חרטה, כנות)
    """
    contradictions = []
    
    if responses_df is None or responses_df.empty:
        return contradictions
    
    # 1. סתירות בקטגוריות רגילות
    for category in INTEGRITY_CATEGORIES.keys():
        if category in ['polygraph', 'regret', 'honesty_meta']:
            continue
            
        cat_questions = responses_df[responses_df['category'] == category]
        
        if len(cat_questions) >= 2:
            scores = cat_questions['final_score'].values
            for i in range(len(scores)):
                for j in range(i + 1, len(scores)):
                    diff = abs(scores[i] - scores[j])
                    if diff >= 3:  # סתירה חמורה
                        contradictions.append({
                            'type': 'category',
                            'category': INTEGRITY_CATEGORIES.get(category, category),
                            'severity': 'high',
                            'diff': diff,
                            'q1': cat_questions.iloc[i]['question'],
                            'q2': cat_questions.iloc[j]['question'],
                            'ans1': cat_questions.iloc[i]['original_answer'],
                            'ans2': cat_questions.iloc[j]['original_answer']
                        })
    
    # 2. בדיקת שאלת הבקרה המרכזית (3 ווריאציות של אותה שאלה)
    control_qs = responses_df[responses_df['control_type'] == 'main_control']
    if len(control_qs) == 3:
        scores = control_qs['final_score'].values
        if max(scores) - min(scores) >= 2:
            contradictions.append({
                'type': 'control',
                'category': 'שאלת בקרה מרכזית',
                'severity': 'critical',
                'diff': max(scores) - min(scores),
                'message': 'שאלה זהה בשלושה ניסוחים קיבלה תשובות שונות'
            })
    
    # 3. בדיקת עקביות שאלות מטא
    for meta_type in ['polygraph', 'regret', 'honesty_meta']:
        meta_qs = responses_df[responses_df['category'] == meta_type]
        if len(meta_qs) >= 3:
            scores = meta_qs['final_score'].values
            std_dev = np.std(scores)
            if std_dev > 1.0:  # חוסר עקביות גבוה
                contradictions.append({
                    'type': 'meta',
                    'category': INTEGRITY_CATEGORIES.get(meta_type, meta_type),
                    'severity': 'high',
                    'std': round(std_dev, 2),
                    'message': f'תשובות לא עקביות בשאלות {INTEGRITY_CATEGORIES[meta_type]}'
                })
    
    return contradictions

def calculate_reliability_score(responses_df):
    """
    חישוב ציון אמינות 0-100 מבוסס על:
    1. סתירות בין שאלות
    2. דפוס תשובות מונוטוני
    3. זמן תגובה חשוד
    4. תשובות קיצוניות מדי (כולם 5 או כולם 1)
    5. סטיות תקן נמוכות
    """
    if responses_df is None or responses_df.empty:
        return 0
    
    penalty = 0
    
    # 1. קנס על סתירות
    contradictions = detect_contradictions(responses_df)
    critical_count = len([c for c in contradictions if c.get('severity') == 'critical'])
    high_count = len([c for c in contradictions if c.get('severity') == 'high'])
    
    penalty += critical_count * 30  # סתירה קריטית = -30
    penalty += high_count * 15      # סתירה גבוהה = -15
    
    # 2. קנס על זמן תגובה חשוד (מהיר מדי)
    if 'time_taken' in responses_df.columns:
        fast_count = len(responses_df[responses_df['time_taken'] < 1.5])
        penalty += (fast_count / len(responses_df)) * 40
    
    # 3. קנס על דפוס מונוטוני
    scores = responses_df['final_score'].values
    std_dev = np.std(scores)
    
    if std_dev < 0.3:  # כמעט אותה תשובה לכולם
        penalty += 50
    elif std_dev < 0.6:
        penalty += 25
    
    # 4. קנס על תשובות קיצוניות
    extreme_5 = len(responses_df[responses_df['original_answer'] == 5])
    extreme_1 = len(responses_df[responses_df['original_answer'] == 1])
    
    if extreme_5 / len(responses_df) > 0.7:  # 70%+ תשובות "מסכים מאוד"
        penalty += 35
    if extreme_1 / len(responses_df) > 0.7:  # 70%+ תשובות "בכלל לא"
        penalty += 35
    
    # 5. בדיקת תשובות לשאלות מטא
    # אם ענה "בכלל לא מוכן" לפוליגרף - חשוד מאוד
    poly_qs = responses_df[responses_df['category'] == 'polygraph']
    if not poly_qs.empty:
        avg_poly = poly_qs['original_answer'].mean()
        if avg_poly <= 2:  # ממוצע נמוך = לא מוכן לפוליגרף
            penalty += 40
    
    # חישוב ציון סופי
    reliability = 100 - penalty
    return int(max(0, min(100, reliability)))

def get_integrity_interpretation(score):
    """מחזיר פרשנות לציון האמינות"""
    if score >= 90:
        return {
            'level': 'גבוה מאוד',
            'color': 'green',
            'text': 'התשובות עקביות ואמינות. המועמד ענה בכנות ובאופן מהימן.'
        }
    elif score >= 75:
        return {
            'level': 'גבוה',
            'color': 'lightgreen',
            'text': 'רמת אמינות טובה. קיימות סתירות קלות אך המועמד נראה כנה.'
        }
    elif score >= 60:
        return {
            'level': 'בינוני',
            'color': 'yellow',
            'text': 'יש חשש לחוסר עקביות. מומלץ לבחון היטב את התשובות.'
        }
    elif score >= 40:
        return {
            'level': 'נמוך',
            'color': 'orange',
            'text': 'רמת אמינות נמוכה. נמצאו סתירות משמעותיות בתשובות.'
        }
    else:
        return {
            'level': 'נמוך מאוד',
            'color': 'red',
            'text': 'אזהרה: רמת אמינות קריטית. התשובות לא אמינות וסותרות זו את זו.'
        }

def process_integrity_results(user_responses):
    """מעבד תשובות ומחשב נתונים סטטיסטיים"""
    df = pd.DataFrame(user_responses)
    
    if df.empty:
        return df, pd.DataFrame()
    
    # סיכום לפי קטגוריה
    summary = df.groupby('category').agg({
        'final_score': 'mean',
        'time_taken': 'mean'
    }).reset_index()
    
    summary['category_name'] = summary['category'].map(INTEGRITY_CATEGORIES)
    summary['final_score'] = summary['final_score'].round(2)
    summary['avg_time'] = summary['time_taken'].round(1)
    
    return df, summary

def get_category_risk_level(category, avg_score):
    """מחזיר רמת סיכון לפי קטגוריה"""
    # קטגוריות קריטיות שבהן ציון נמוך = סיכון גבוה
    critical_categories = ['theft', 'drugs', 'unethical', 'academic']
    
    if category in critical_categories:
        if avg_score <= 2.0:  # ענה "כן" על הרבה שאלות רגישות
            return {'level': 'גבוה', 'color': 'red'}
        elif avg_score <= 3.0:
            return {'level': 'בינוני', 'color': 'orange'}
        else:
            return {'level': 'תקין', 'color': 'green'}
    else:
        # קטגוריות כמו feedback, teamwork - ציון גבוה = טוב
        if avg_score >= 4.0:
            return {'level': 'טוב', 'color': 'green'}
        elif avg_score >= 3.0:
            return {'level': 'בינוני', 'color': 'yellow'}
        else:
            return {'level': 'נמוך', 'color': 'red'}
