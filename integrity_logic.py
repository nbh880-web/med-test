"""
לוגיקת מבחן האמינות - זיהוי סתירות ודפוסי שקר
© זכויות יוצרים לניתאי מלכה
"""

import pandas as pd
import numpy as np
import random

# קטגוריות המבחן המלאות
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
    """טוען שאלות אמינות ובוחר את הכמות הנדרשת"""
    try:
        df = pd.read_csv('data/integrity_questions.csv')
    except Exception as e:
        print(f"Error loading questions: {e}")
        return []

    meta_df = df[df['control_type'] == 'meta']
    control_questions = df[df['control_type'] == 'main_control'].to_dict('records')
    regular_questions = df[df['control_type'] == 'none'].to_dict('records')

    meta_banks = {
        'polygraph': meta_df[meta_df['category'] == 'polygraph'].to_dict('records'),
        'regret': meta_df[meta_df['category'] == 'regret'].to_dict('records'),
        'honesty_meta': meta_df[meta_df['category'] == 'honesty_meta'].to_dict('records')
    }

    categories = [
        cat for cat in INTEGRITY_CATEGORIES.keys()
        if cat not in ['polygraph', 'regret', 'honesty_meta']
    ]

    estimated_meta = count // 15
    needed_regular = count - len(control_questions) - estimated_meta
    per_category = max(1, needed_regular // len(categories))

    selected_regular = []
    for category in categories:
        cat_questions = [q for q in regular_questions if q.get('category') == category]
        if cat_questions:
            sample_size = min(len(cat_questions), per_category)
            selected_regular.extend(random.sample(cat_questions, sample_size))

    if len(selected_regular) < needed_regular:
        remaining = needed_regular - len(selected_regular)
        selected_set = {id(q) for q in selected_regular}
        unused = [q for q in regular_questions if id(q) not in selected_set]
        if unused:
            selected_regular.extend(random.sample(unused, min(len(unused), remaining)))

    random.shuffle(selected_regular)

    # בניית רשימה סופית עם מנגנון הזרקה מחזורי
    final_test = []
    meta_order = ['polygraph', 'regret', 'honesty_meta']
    meta_idx = 0

    for i, question in enumerate(selected_regular):
        final_test.append(question)
        if (i + 1) % 15 == 0:
            current_type = meta_order[meta_idx % len(meta_order)]
            bank = meta_banks.get(current_type, [])
            if bank:
                meta_q = random.choice(bank).copy()
                meta_q['is_stress_meta'] = True
                final_test.append(meta_q)
                meta_idx += 1

    for ctrl in control_questions:
        pos = random.randint(0, len(final_test))
        final_test.insert(pos, ctrl)

    return final_test


def calculate_integrity_score(answer, reverse):
    """מחשב ציון לשאלת אמינות בודדת"""
    try:
        rev_str = str(reverse).strip().upper()
        is_reverse = rev_str in ["TRUE", "1", "YES", "T", "Y"]
        val = int(answer)
        return (6 - val) if is_reverse else val
    except (ValueError, TypeError):
        return 3


def detect_contradictions(responses_df):
    """
    מנגנון זיהוי סתירות מורחב:
    1. הצלבה בין שאלות באותה קטגוריה
    2. בדיקת שאלות בקרה מרכזיות
    3. ניתוח סטיית תקן בשאלות מטא
    """
    contradictions = []

    if responses_df is None or responses_df.empty:
        return contradictions

    # חלק א': סתירות בתוך קטגוריות תוכן
    for category in INTEGRITY_CATEGORIES.keys():
        if category in ['polygraph', 'regret', 'honesty_meta']:
            continue
        cat_qs = responses_df[responses_df['category'] == category]
        if len(cat_qs) >= 2:
            scores = cat_qs['final_score'].values
            questions = cat_qs['question'].values if 'question' in cat_qs.columns else ['שאלה'] * len(cat_qs)
            answers = cat_qs['original_answer'].values if 'original_answer' in cat_qs.columns else scores

            for i in range(len(scores)):
                for j in range(i + 1, len(scores)):
                    diff = abs(scores[i] - scores[j])
                    if diff >= 3:
                        contradictions.append({
                            'type': 'category_inconsistency',
                            'category': INTEGRITY_CATEGORIES.get(category, category),
                            'severity': 'high',
                            'diff': int(diff),
                            'q1': questions[i],
                            'q2': questions[j],
                            'ans1': int(answers[i]),
                            'ans2': int(answers[j]),
                            'message': f"נמצא פער של {int(diff)} נקודות בין תשובות באותו נושא"
                        })

    # חלק ב': שאלות בקרה מרכזיות
    if 'control_type' in responses_df.columns:
        control_qs = responses_df[responses_df['control_type'] == 'main_control']
        if len(control_qs) >= 2:
            ctrl_scores = control_qs['final_score'].values
            score_range = max(ctrl_scores) - min(ctrl_scores)
            if score_range >= 2:
                contradictions.append({
                    'type': 'control_breach',
                    'category': 'שאלת בקרה מרכזית',
                    'severity': 'critical',
                    'diff': int(score_range),
                    'message': 'המועמד נתן תשובות סותרות לשאלות זהות לחלוטין'
                })

    # חלק ג': שאלות מטא
    for meta_type in ['polygraph', 'regret', 'honesty_meta']:
        meta_qs = responses_df[responses_df['category'] == meta_type]
        if len(meta_qs) >= 2:
            std_dev = np.std(meta_qs['final_score'].values)
            if std_dev > 0.8:
                contradictions.append({
                    'type': 'meta_inconsistency',
                    'category': INTEGRITY_CATEGORIES.get(meta_type, meta_type),
                    'severity': 'high',
                    'std': float(round(std_dev, 2)),
                    'message': f"חוסר עקביות בדיווח על {INTEGRITY_CATEGORIES[meta_type]}"
                })

    return contradictions


def calculate_reliability_score(responses_df):
    """חישוב מדד האמינות הסופי (0-100)"""
    if responses_df is None or responses_df.empty:
        return 0

    penalty = 0

    # 1. סתירות
    contradictions = detect_contradictions(responses_df)
    critical = len([c for c in contradictions if c.get('severity') == 'critical'])
    high = len([c for c in contradictions if c.get('severity') == 'high'])
    penalty += critical * 35
    penalty += high * 15

    # 2. זמני תגובה
    if 'time_taken' in responses_df.columns:
        num_fast = len(responses_df[responses_df['time_taken'] < 5.0])
        if num_fast > (len(responses_df) * 0.20):
            penalty += (num_fast / len(responses_df)) * 50

    # 3. סטיית תקן כללית (מענה מונוטוני)
    overall_std = np.std(responses_df['final_score'].values)
    if overall_std < 0.3:
        penalty += 60
    elif overall_std < 0.6:
        penalty += 30

    # 4. תשובות קיצוניות
    if 'original_answer' in responses_df.columns:
        n = len(responses_df)
        extreme_5 = len(responses_df[responses_df['original_answer'] == 5]) / n
        extreme_1 = len(responses_df[responses_df['original_answer'] == 1]) / n
        if extreme_5 > 0.75 or extreme_1 > 0.75:
            penalty += 40

    # 5. נכונות לפוליגרף
    poly_qs = responses_df[responses_df['category'] == 'polygraph']
    if not poly_qs.empty:
        avg_poly = poly_qs['original_answer'].mean() if 'original_answer' in poly_qs.columns else 3
        if avg_poly <= 2.0:
            penalty += 25

    return int(max(0, min(100, 100 - penalty)))


def get_integrity_interpretation(score):
    """פרשנות טקסטואלית וצבעונית לציון האמינות"""
    if score >= 92:
        return {'level': 'גבוה מאוד', 'color': '#28a745', 'text': 'התשובות עקביות לחלוטין.'}
    elif score >= 80:
        return {'level': 'גבוה', 'color': '#78d147', 'text': 'רמת אמינות טובה.'}
    elif score >= 65:
        return {'level': 'בינוני', 'color': '#ffc107', 'text': 'רמה גבולית. נמצאו מספר סתירות.'}
    elif score >= 45:
        return {'level': 'נמוך', 'color': '#fd7e14', 'text': 'סתירות רבות ודפוס מענה חשוד.'}
    else:
        return {'level': 'קריטי', 'color': '#dc3545', 'text': 'אזהרה: המבחן אינו אמין.'}


def process_integrity_results(user_responses):
    """מעבד את רשימת התשובות ומייצר DataFrames לסיכום"""
    df_raw = pd.DataFrame(user_responses)
    if df_raw.empty:
        return df_raw, pd.DataFrame()

    summary_df = df_raw.groupby('category').agg({
        'final_score': ['mean', 'std', 'count'],
        'time_taken': 'mean'
    }).reset_index()

    summary_df.columns = ['category', 'avg_score', 'score_std', 'q_count', 'avg_time']
    summary_df['display_name'] = summary_df['category'].map(INTEGRITY_CATEGORIES)
    summary_df = summary_df.round(2)

    return df_raw, summary_df


def get_category_risk_level(category_id, avg_score):
    """קביעת רמת סיכון ספציפית לכל קטגוריה"""
    negative_traits = ['theft', 'drugs', 'unethical', 'gambling', 'academic']
    if category_id in negative_traits:
        if avg_score >= 4.0:
            return {'level': 'סיכון גבוה', 'color': 'red'}
        elif avg_score >= 2.5:
            return {'level': 'סיכון בינוני', 'color': 'orange'}
        return {'level': 'תקין', 'color': 'green'}
    else:
        if avg_score >= 4.0:
            return {'level': 'מצוין', 'color': 'green'}
        elif avg_score >= 2.5:
            return {'level': 'מספק', 'color': 'yellow'}
        return {'level': 'נמוך', 'color': 'red'}
