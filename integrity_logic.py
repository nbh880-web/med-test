"""
Mednitai — Integrity Logic
===========================
שאלות אמינות, סתירות, ציונים.
"""

import pandas as pd
import numpy as np
import random
import streamlit as st

INTEGRITY_CATEGORIES = {
    'theft', 'academic', 'termination', 'gambling', 'drugs',
    'whistleblowing', 'feedback', 'teamwork', 'unethical',
    'polygraph', 'regret', 'honesty_meta'
}

NEGATIVE_TRAITS = {'theft', 'drugs', 'gambling', 'unethical', 'termination', 'academic'}
POSITIVE_TRAITS = {'whistleblowing', 'feedback', 'teamwork'}
META_CYCLE = ['polygraph', 'regret', 'honesty_meta']


@st.cache_data
def _load_integrity_csv():
    """Try multiple paths for the CSV file."""
    import os
    candidates = ["integrity_questions.csv", "data/integrity_questions.csv", "./integrity_questions.csv"]
    for path in candidates:
        if os.path.exists(path):
            try:
                return pd.read_csv(path)
            except Exception:
                continue
    st.error("שגיאה בטעינת שאלות אמינות: הקובץ integrity_questions.csv לא נמצא")
    return pd.DataFrame()


def get_integrity_questions(count=140):
    """
    Load and structure integrity questions.
    - Separate into regular / control / meta banks
    - Inject meta every 15 questions (polygraph -> regret -> honesty_meta)
    - Meta questions get is_stress_meta = 1 (int)
    - Control questions injected at random positions
    """
    df = _load_integrity_csv()
    if df.empty:
        return []

    try:
        # Determine category column
        cat_col = None
        for col in ['category', 'Category', 'trait']:
            if col in df.columns:
                cat_col = col
                break
        if not cat_col:
            return df.head(count).to_dict('records')

        # Determine control column
        ctrl_col = None
        for col in ['main_control', 'is_control', 'control']:
            if col in df.columns:
                ctrl_col = col
                break

        # Separate banks
        meta_categories = set(META_CYCLE)
        meta_df = df[df[cat_col].isin(meta_categories)]

        if ctrl_col:
            control_df = df[
                (df[ctrl_col].astype(str).str.strip().str.lower().isin(['1', '1.0', 'true', 'yes']))
                & (~df[cat_col].isin(meta_categories))
            ]
            regular_df = df[
                (~df[cat_col].isin(meta_categories))
                & (~df.index.isin(control_df.index))
            ]
        else:
            control_df = pd.DataFrame()
            regular_df = df[~df[cat_col].isin(meta_categories)]

        # Sample regular questions
        regular_needed = count - (count // 15) - min(10, len(control_df))
        if len(regular_df) >= regular_needed:
            regular_sample = regular_df.sample(n=regular_needed)
        else:
            regular_sample = regular_df

        questions = regular_sample.to_dict('records')

        # Inject meta questions every 15
        meta_index = 0
        meta_records = meta_df.to_dict('records') if not meta_df.empty else []
        inject_positions = list(range(14, len(questions), 15))

        for pos in reversed(inject_positions):
            if meta_records:
                # Cycle through meta categories
                target_cat = META_CYCLE[meta_index % len(META_CYCLE)]
                candidates = [m for m in meta_records if m.get(cat_col) == target_cat]
                if candidates:
                    chosen = random.choice(candidates)
                else:
                    chosen = random.choice(meta_records)

                chosen['is_stress_meta'] = 1  # int, not bool!
                questions.insert(min(pos, len(questions)), chosen)
                meta_index += 1

        # Inject control questions at random positions
        if not control_df.empty:
            control_sample = control_df.sample(n=min(10, len(control_df)))
            for _, ctrl in control_sample.iterrows():
                ctrl_dict = ctrl.to_dict()
                pos = random.randint(0, len(questions))
                questions.insert(pos, ctrl_dict)

        # Ensure is_stress_meta exists on all
        for q in questions:
            if 'is_stress_meta' not in q:
                q['is_stress_meta'] = 0

        return questions[:count]

    except Exception as e:
        return df.head(count).to_dict('records')


def calculate_integrity_score(answer, reverse):
    """Same as HEXACO calculate_score."""
    try:
        score = int(answer)
        rev = str(reverse).strip().lower()
        if rev in ['true', '1', '1.0', 'yes', 't', 'ת', 'אמת']:
            score = 6 - score
        return max(1, min(5, score))
    except (ValueError, TypeError):
        return 3


def detect_contradictions(responses_df):
    """
    Part 1: Gap >= 3 in same category -> severity: high
    Part 2: Control questions with gap >= 2 -> severity: critical
    Part 3: SD > 0.8 in meta questions -> severity: high
    """
    contradictions = []
    if responses_df is None or responses_df.empty:
        return contradictions

    try:
        cat_col = None
        for col in ['category', 'trait']:
            if col in responses_df.columns:
                cat_col = col
                break
        if not cat_col or 'score' not in responses_df.columns:
            return contradictions

        # Part 1: Same category contradictions
        for cat in responses_df[cat_col].unique():
            cat_df = responses_df[responses_df[cat_col] == cat]
            scores = cat_df['score'].values
            questions = cat_df['question'].values if 'question' in cat_df.columns else [''] * len(scores)

            for i in range(len(scores)):
                for j in range(i + 1, len(scores)):
                    if abs(scores[i] - scores[j]) >= 3:
                        contradictions.append({
                            'type': 'category_contradiction',
                            'category': cat,
                            'gap': abs(scores[i] - scores[j]),
                            'severity': 'high',
                            'message': f"סתירה בקטגוריית {cat}: פער {abs(scores[i] - scores[j]):.0f}"
                        })

        # Part 2: Control questions (if identifiable)
        if 'main_control' in responses_df.columns or 'is_control' in responses_df.columns:
            ctrl_col = 'main_control' if 'main_control' in responses_df.columns else 'is_control'
            ctrl_df = responses_df[
                responses_df[ctrl_col].astype(str).str.strip().str.lower().isin(['1', '1.0', 'true'])
            ]
            if len(ctrl_df) > 1:
                scores = ctrl_df['score'].values
                for i in range(len(scores)):
                    for j in range(i + 1, len(scores)):
                        if abs(scores[i] - scores[j]) >= 2:
                            contradictions.append({
                                'type': 'control_contradiction',
                                'gap': abs(scores[i] - scores[j]),
                                'severity': 'critical',
                                'message': f"סתירה בשאלות בקרה: פער {abs(scores[i] - scores[j]):.0f}"
                            })

        # Part 3: Meta SD
        is_meta_col = 'is_stress_meta'
        if is_meta_col in responses_df.columns:
            meta_df = responses_df[
                responses_df[is_meta_col].astype(str).str.strip().str.lower().isin(['1', '1.0', 'true'])
            ]
            if len(meta_df) > 1 and 'score' in meta_df.columns:
                if meta_df['score'].std() > 0.8:
                    contradictions.append({
                        'type': 'meta_inconsistency',
                        'severity': 'high',
                        'message': f"חוסר עקביות בשאלות מטא (SD={meta_df['score'].std():.2f})"
                    })

    except Exception:
        pass

    return contradictions


def calculate_reliability_score(responses_df):
    """
    Reliability 0-100 with penalties for:
    critical contradictions (35), high (15), speed (<5s), monotone, extremes, polygraph resistance
    """
    if responses_df is None or responses_df.empty:
        return 100

    try:
        score = 100.0
        contradictions = detect_contradictions(responses_df)

        for c in contradictions:
            if c.get('severity') == 'critical':
                score -= 35
            elif c.get('severity') == 'high':
                score -= 15

        # Speed penalty
        if 'response_time' in responses_df.columns:
            fast = (responses_df['response_time'] < 5).sum()
            score -= fast * 1.5

        # Monotone
        if 'score' in responses_df.columns:
            if responses_df['score'].std() < 0.3:
                score -= 15

        # Extreme answers
        if 'score' in responses_df.columns:
            extreme = ((responses_df['score'] == 1) | (responses_df['score'] == 5)).sum()
            ratio = extreme / len(responses_df)
            if ratio > 0.7:
                score -= 20

        # Polygraph resistance
        cat_col = None
        for col in ['category', 'trait']:
            if col in responses_df.columns:
                cat_col = col
                break
        if cat_col:
            poly_df = responses_df[responses_df[cat_col] == 'polygraph']
            if not poly_df.empty and 'score' in poly_df.columns:
                if poly_df['score'].mean() < 2:
                    score -= 10

        return max(0, min(100, round(score)))
    except Exception:
        return 50


def process_integrity_results(user_responses):
    """
    Process integrity responses.
    Output: (df_raw, summary_df)
    """
    if not user_responses:
        return pd.DataFrame(), pd.DataFrame()

    records = []
    for r in user_responses:
        score = calculate_integrity_score(r.get('answer', 3), r.get('reverse', False))
        records.append({
            'question': r.get('question', ''),
            'answer': r.get('answer', 3),
            'score': score,
            'response_time': r.get('response_time', 0),
            'category': r.get('category', r.get('trait', '')),
            'is_stress_meta': r.get('is_stress_meta', 0),
            'reverse': r.get('reverse', False),
        })

    df_raw = pd.DataFrame(records)
    if df_raw.empty or 'category' not in df_raw.columns:
        return df_raw, pd.DataFrame()

    summary = df_raw.groupby('category').agg(
        avg_score=('score', 'mean'),
        score_std=('score', 'std'),
        q_count=('score', 'count'),
        avg_time=('response_time', 'mean')
    ).reset_index()

    return df_raw, summary


def get_integrity_interpretation(score):
    if score >= 92:
        return "גבוה מאוד — עקביות ואמינות מצוינת"
    elif score >= 80:
        return "גבוה — אמינות טובה"
    elif score >= 65:
        return "בינוני — יש מקום לשיפור"
    elif score >= 45:
        return "נמוך — נדרשת תשומת לב"
    else:
        return "קריטי — ציון אמינות נמוך מאוד"


def get_category_risk_level(category_id, avg_score):
    """
    negative traits: high score = risk
    positive traits: high score = good
    """
    if category_id in NEGATIVE_TRAITS:
        if avg_score > 3.5:
            return 'high_risk'
        elif avg_score > 2.5:
            return 'medium_risk'
        else:
            return 'low_risk'
    elif category_id in POSITIVE_TRAITS:
        if avg_score > 3.5:
            return 'positive'
        elif avg_score > 2.5:
            return 'neutral'
        else:
            return 'concern'
    else:
        return 'neutral'
