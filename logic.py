import pandas as pd

def calculate_score(answer, reverse_value):
    """מחשב ציון סופי לפי עמודת ה-reverse מהאקסל"""
    is_reverse = str(reverse_value).strip().upper() == "TRUE"
    if is_reverse:
        return 6 - answer
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
    """מעבד את התשובות לדאטה-פרים מסודר"""
    df = pd.DataFrame(user_responses)
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
    
    from fpdf import FPDF

def create_pdf_report(summary_df, raw_responses, ai_report):
    pdf = FPDF()
    pdf.add_page()
    
    # כותרת ראשית
    pdf.set_font("Arial", 'B', size=16)
    pdf.cell(200, 10, txt="Psychometric Test - Summary Report", ln=True, align='C')
    pdf.ln(10)
    
    # חלק 1: טבלת סיכום תכונות וטווחים
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(60, 10, "Trait", border=1)
    pdf.cell(40, 10, "Score", border=1)
    pdf.cell(60, 10, "Within Range (3.5-4.5)", border=1)
    pdf.ln()
    
    pdf.set_font("Arial", size=12)
    for _, row in summary_df.iterrows():
        score = row['final_score']
        in_range = "YES" if 3.5 <= score <= 4.5 else "NO"
        pdf.cell(60, 10, str(row['trait']), border=1)
        pdf.cell(40, 10, f"{score:.2f}", border=1)
        pdf.cell(60, 10, in_range, border=1)
        pdf.ln()
    
    pdf.ln(10)

    # חלק 2: ניתוח AI
    pdf.set_font("Arial", 'B', size=14)
    pdf.cell(200, 10, "AI Professional Analysis", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 10, ai_report if ai_report else "No AI analysis generated.")
    
    # חלק 3: פירוט כל התשובות של המשתמש
    pdf.add_page()
    pdf.set_font("Arial", 'B', size=14)
    pdf.cell(200, 10, "Full User Responses", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=9)
    for i, resp in enumerate(raw_responses):
        # הצגת השאלה, התשובה והתכונה
        q_text = f"Q{i+1}: {resp['q'][:60]}..."
        ans_text = f"Answer: {resp['answer']} | Trait: {resp['trait']} | Time: {resp['time_taken']:.1f}s"
        pdf.cell(0, 8, q_text, ln=True)
        pdf.cell(0, 8, ans_text, ln=True, border='B')
        pdf.ln(2)
        
    return pdf.output(dest='S')
