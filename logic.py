"""
Mednitai — HEXACO Logic
=======================
"""

import pandas as pd
import numpy as np
import io
import os

IDEAL_RANGES = {
    'Conscientiousness':       (4.3, 4.8),
    'Honesty-Humility':        (4.2, 4.9),
    'Agreeableness':           (4.0, 4.6),
    'Emotionality':            (3.6, 4.1),
    'Extraversion':            (3.6, 4.2),
    'Openness to Experience':  (3.5, 4.1)
}


def calculate_score(answer, reverse_value):
    try:
        score = int(answer)
        rev = str(reverse_value).strip().lower()
        if rev in ['true', '1', '1.0', 'yes', 't', 'ת', 'אמת']:
            score = 6 - score
        return max(1, min(5, score))
    except (ValueError, TypeError):
        return 3


def process_results(user_responses):
    if not user_responses:
        return pd.DataFrame(), pd.DataFrame()

    records = []
    for r in user_responses:
        score = calculate_score(r.get('answer', 3), r.get('reverse', False))
        records.append({
            'question': r.get('question', ''),
            'answer': r.get('answer', 3),
            'score': score,
            'response_time': r.get('response_time', 0),
            'trait': r.get('trait', ''),
            'reverse': r.get('reverse', False),
        })

    df_raw = pd.DataFrame(records)
    if df_raw.empty or 'trait' not in df_raw.columns:
        return df_raw, pd.DataFrame()

    summary = df_raw.groupby('trait').agg(
        avg_score=('score', 'mean'),
        avg_time=('response_time', 'mean'),
        std_score=('score', 'std'),
        q_count=('score', 'count')
    ).reset_index()
    summary.rename(columns={'trait': 'Trait', 'avg_score': 'Mean'}, inplace=True)
    return df_raw, summary


def calculate_medical_fit(summary_df):
    if summary_df is None or summary_df.empty:
        return 0
    try:
        total, count = 0, 0
        t_col = 'Trait' if 'Trait' in summary_df.columns else 'trait'
        s_col = 'Mean' if 'Mean' in summary_df.columns else 'avg_score'

        for _, row in summary_df.iterrows():
            trait = row.get(t_col, '')
            score = float(row.get(s_col, 0))
            if trait in IDEAL_RANGES:
                low, high = IDEAL_RANGES[trait]
                if low <= score <= high:
                    fit = 100
                else:
                    gap = min(abs(score - low), abs(score - high))
                    fit = max(0, 100 - gap * 40)
                total += fit
                count += 1
        return round(total / count) if count else 0
    except Exception:
        return 0


def calculate_reliability_index(df_raw):
    if df_raw is None or df_raw.empty:
        return 100
    try:
        score = 100.0
        if 'response_time' in df_raw.columns:
            score -= (df_raw['response_time'] < 1.4).sum() * 2
        score -= len(get_inconsistent_questions(df_raw)) * 5
        if 'trait' in df_raw.columns and 'score' in df_raw.columns:
            for trait in df_raw['trait'].unique():
                ts = df_raw[df_raw['trait'] == trait]['score']
                if len(ts) > 2 and ts.std() < 0.35:
                    score -= 8
        return max(0, min(100, round(score)))
    except Exception:
        return 50


def get_inconsistent_questions(df_raw):
    result = []
    if df_raw is None or df_raw.empty:
        return result
    try:
        if 'trait' not in df_raw.columns or 'score' not in df_raw.columns:
            return result
        for trait in df_raw['trait'].unique():
            tdf = df_raw[df_raw['trait'] == trait]
            scores = tdf['score'].values
            questions = tdf['question'].values
            for i in range(len(scores)):
                for j in range(i + 1, len(scores)):
                    if abs(scores[i] - scores[j]) >= 2.5:
                        result.append({
                            'trait': trait, 'gap': abs(scores[i] - scores[j]),
                            'severity': 'high',
                            'message': f"סתירה ב-{trait}: פער {abs(scores[i] - scores[j]):.1f}"
                        })
    except Exception:
        pass
    return result


def analyze_consistency(df):
    alerts = []
    if df is None or df.empty:
        return alerts
    try:
        if 'response_time' in df.columns:
            fast = (df['response_time'] < 1.4).sum()
            if fast > 5:
                alerts.append({'level': 'red', 'message': f'{fast} תשובות מהירות מדי'})
            elif fast > 2:
                alerts.append({'level': 'orange', 'message': f'{fast} תשובות מהירות'})
        if 'trait' in df.columns and 'score' in df.columns:
            for trait in df['trait'].unique():
                ts = df[df['trait'] == trait]['score']
                if len(ts) > 3 and ts.std() < 0.35:
                    alerts.append({'level': 'orange', 'message': f'תשובות מונוטוניות ב-{trait}'})
        incons = get_inconsistent_questions(df)
        if len(incons) > 3:
            alerts.append({'level': 'red', 'message': f'{len(incons)} סתירות'})
        elif incons:
            alerts.append({'level': 'blue', 'message': f'{len(incons)} סתירות קלות'})
    except Exception:
        pass
    return alerts


def create_pdf_report(summary_df, raw_responses):
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()

        font_path = "Assistant.ttf"
        if os.path.exists(font_path):
            pdf.add_font("Assistant", "", font_path, uni=True)
            pdf.set_font("Assistant", size=14)
        else:
            pdf.set_font("Helvetica", size=14)

        pdf.cell(0, 10, "Mednitai HEXACO Report", ln=True, align='C')
        pdf.ln(10)

        if summary_df is not None and hasattr(summary_df, 'iterrows'):
            t_col = 'Trait' if 'Trait' in summary_df.columns else 'trait'
            s_col = 'Mean' if 'Mean' in summary_df.columns else 'avg_score'
            pdf.set_font_size(11)
            for _, row in summary_df.iterrows():
                pdf.cell(0, 8, f"{row.get(t_col, '')}: {row.get(s_col, 0):.2f}", ln=True)

        pdf.ln(5)
        if raw_responses:
            df = pd.DataFrame(raw_responses) if isinstance(raw_responses, list) else raw_responses
            if not df.empty:
                rel = calculate_reliability_index(df)
                pdf.cell(0, 8, f"Reliability Score: {rel}", ln=True)

        return pdf.output()
    except Exception:
        return None


def create_excel_download(responses):
    try:
        if not responses:
            return "אין נתונים"
        df = pd.DataFrame(responses)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Responses', index=False)
            ws = writer.sheets['Responses']
            for i, col in enumerate(df.columns):
                width = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                ws.set_column(i, i, min(width, 40))
        return output.getvalue()
    except Exception as e:
        return f"שגיאה: {e}"


def get_balanced_questions(df, total_limit=60):
    if df is None or df.empty:
        return []
    try:
        trait_col = None
        for col in ['trait', 'Trait', 'category']:
            if col in df.columns:
                trait_col = col
                break
        if not trait_col:
            return df.head(total_limit).to_dict('records')

        traits = df[trait_col].unique()
        per_trait = max(1, total_limit // len(traits))
        parts = []
        for trait in traits:
            tdf = df[df[trait_col] == trait]
            parts.append(tdf.sample(n=min(per_trait, len(tdf))))

        result = pd.concat(parts)
        remaining = total_limit - len(result)
        if remaining > 0:
            leftover = df[~df.index.isin(result.index)]
            if not leftover.empty:
                result = pd.concat([result, leftover.sample(n=min(remaining, len(leftover)))])

        return result.sample(frac=1).reset_index(drop=True).to_dict('records')
    except Exception:
        return df.head(total_limit).to_dict('records')


# ============================================================
# Dynamic WPM Threshold
# ============================================================
def calculate_dynamic_wpm_threshold(question_text):
    """
    Calculate minimum reasonable reading time for a question.
    Based on average reading speed of ~200 WPM (Hebrew is slightly slower).
    Hebrew WPM ~150. Adding 1 second for decision-making.

    Returns: minimum seconds to read + decide.
    Too fast = below this threshold = suspicious.
    """
    try:
        words = len(str(question_text).split())
        # Hebrew reading: ~150 words per minute = 2.5 words per second
        reading_time = words / 2.5
        # Minimum 1.2 seconds even for very short questions
        # Add 0.8 seconds for cognitive processing (choosing answer)
        threshold = max(1.2, reading_time + 0.8)
        return round(threshold, 2)
    except Exception:
        return 1.4  # Fallback


# ============================================================
# Fatigue Index
# ============================================================
def calculate_fatigue_index(responses):
    """
    Compare first third vs last third of test.
    Measures:
    - Response time increase (slowing down)
    - Score variance increase (less consistent)
    - Speed of last 10% vs first 10%

    Returns 0-100 (0=no fatigue, 100=severe fatigue).
    """
    if not responses or len(responses) < 9:
        return 0

    try:
        n = len(responses)
        third = n // 3

        first_third = responses[:third]
        last_third = responses[-third:]

        fatigue_score = 0

        # ---- 1. Response time comparison ----
        first_times = [r.get('response_time', 0) for r in first_third if r.get('response_time', 0) > 0]
        last_times = [r.get('response_time', 0) for r in last_third if r.get('response_time', 0) > 0]

        if first_times and last_times:
            avg_first = sum(first_times) / len(first_times)
            avg_last = sum(last_times) / len(last_times)

            if avg_first > 0:
                # Significant slowdown = fatigue
                time_ratio = avg_last / avg_first
                if time_ratio > 1.5:
                    fatigue_score += 30  # Major slowdown
                elif time_ratio > 1.2:
                    fatigue_score += 15  # Moderate slowdown
                # Or significant speedup (rushing to finish)
                elif time_ratio < 0.6:
                    fatigue_score += 25  # Rushing at end
                elif time_ratio < 0.8:
                    fatigue_score += 10

        # ---- 2. Score variance comparison ----
        first_scores = [r.get('answer', 3) for r in first_third]
        last_scores = [r.get('answer', 3) for r in last_third]

        if len(first_scores) > 2 and len(last_scores) > 2:
            first_std = np.std(first_scores)
            last_std = np.std(last_scores)

            # Less variance at end = fatigue (defaulting to middle)
            if last_std < first_std * 0.5 and first_std > 0.5:
                fatigue_score += 20  # Much less variance
            elif last_std < first_std * 0.7 and first_std > 0.5:
                fatigue_score += 10

            # Or much more variance (careless)
            if last_std > first_std * 1.8 and last_std > 1.0:
                fatigue_score += 15

        # ---- 3. Last 10% speed check ----
        last_10pct = responses[-max(1, n // 10):]
        last_10_times = [r.get('response_time', 0) for r in last_10pct if r.get('response_time', 0) > 0]

        if last_10_times and first_times:
            avg_last_10 = sum(last_10_times) / len(last_10_times)
            avg_first_time = sum(first_times) / len(first_times)

            if avg_first_time > 0 and avg_last_10 < avg_first_time * 0.4:
                fatigue_score += 20  # Extremely rushed at end

        # ---- 4. Monotone answers at end ----
        if len(last_scores) > 5:
            # Check if last answers are all the same
            unique_last = len(set(last_scores[-min(10, len(last_scores)):]))
            if unique_last <= 2:
                fatigue_score += 15  # Almost no variation

        return min(100, max(0, fatigue_score))

    except Exception:
        return 0
