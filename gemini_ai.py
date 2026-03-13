import streamlit as st
import requests
import json
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime

# זכויות יוצרים לניתאי מלכה

# --- 1. הגדרות ליבה וטווחים פסיכומטריים (ניתוח פערים) ---
TRAIT_DICT = {
    "Honesty-Humility": "כנות וענווה (H)",
    "Emotionality": "רגשיות (E)",
    "Extraversion": "מוחצנות (X)",
    "Agreeableness": "נעימות (A)",
    "Conscientiousness": "מצפוניות (C)",
    "Openness to Experience": "פתיחות (O)"
}

IDEAL_DOCTOR = {
    "Honesty-Humility": 4.55,
    "Emotionality": 3.85,
    "Extraversion": 3.9,
    "Agreeableness": 4.3,
    "Conscientiousness": 4.55,
    "Openness to Experience": 3.8
}

TRAIT_RANGES = {
    "Honesty-Humility": {"critical_low": 3.5, "optimal_low": 4.2, "optimal_high": 4.9, "critical_high": 5.0},
    "Emotionality": {"critical_low": 2.8, "optimal_low": 3.6, "optimal_high": 4.1, "critical_high": 4.5},
    "Extraversion": {"critical_low": 2.5, "optimal_low": 3.6, "optimal_high": 4.2, "critical_high": 4.8},
    "Agreeableness": {"critical_low": 3.2, "optimal_low": 4.0, "optimal_high": 4.6, "critical_high": 5.0},
    "Conscientiousness": {"critical_low": 3.8, "optimal_low": 4.3, "optimal_high": 4.8, "critical_high": 5.0},
    "Openness to Experience": {"critical_low": 2.8, "optimal_low": 3.5, "optimal_high": 4.1, "critical_high": 4.7}
}

# --- פונקציות עזר: חילוץ נתונים מוגן מקריסות ---
def _extract_float(val):
    try:
        if hasattr(val, 'iloc'): return float(val.iloc[0])
        if hasattr(val, 'item'): return float(val.item())
        if isinstance(val, (list, tuple)): return float(val[0])
        return float(val)
    except Exception:
        return 0.0

def _parse_to_simple_dict(data):
    res = {}
    try:
        if isinstance(data, pd.DataFrame):
            t_col = next((c for c in data.columns if str(c).lower() in ['trait', 'category']), None)
            s_col = next((c for c in data.columns if str(c).lower() in ['avg_score', 'mean', 'score']), None)
            if t_col and s_col:
                for _, row in data.iterrows():
                    res[str(row[t_col])] = _extract_float(row[s_col])
            else:
                for idx, row in data.iterrows():
                    res[str(idx)] = _extract_float(row.iloc[0])
            return res
        if isinstance(data, dict):
            t_col = data.get('trait', data.get('Trait', data.get('category')))
            s_col = data.get('avg_score', data.get('Mean', data.get('score')))
            if isinstance(t_col, dict) and isinstance(s_col, dict):
                for k, v in t_col.items(): res[str(v)] = _extract_float(s_col.get(k, 0))
                return res
            for k, v in data.items(): res[str(k)] = _extract_float(v)
            return res
    except Exception:
        pass
    return {}

# --- Cache: Model Discovery ---
@st.cache_resource
def _cached_model_discovery(api_key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            models = [m['name'] for m in res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            for m in models:
                if "1.5-flash" in m: return m
            return models[0] if models else "models/gemini-1.5-flash"
    except Exception:
        pass
    return "models/gemini-1.5-flash"

class HEXACO_Expert_System:
    def __init__(self):
        self.gemini_keys = [
            st.secrets.get("GEMINI_KEY_1", "").strip(),
            st.secrets.get("GEMINI_KEY_2", "").strip(),
            st.secrets.get("GEMINI_KEY_3", "").strip()
        ]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        self.claude_key = st.secrets.get("CLAUDE_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "").strip()

    def _get_model_discovery(self, api_key):
        return _cached_model_discovery(api_key)

    def _call_gemini_safe(self, prompt):
        if not self.gemini_keys:
            return "❌ מפתחות Gemini חסרים בהגדרות ה-Secrets."
        
        errors = []
        for i, key in enumerate(self.gemini_keys, 1):
            model = self._get_model_discovery(key)
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={key}"
                # מוגדר כאן ל-120 שניות
                res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=120)
                
                if res.status_code == 200:
                    data = res.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
                elif res.status_code == 429:
                    errors.append(f"🔑 מפתח #{i}: חריגת מכסה/עומס (429)")
                else:
                    errors.append(f"🔑 מפתח #{i} נדחה על ידי גוגל (קוד {res.status_code}): {res.text}")
            except Exception as e:
                errors.append(f"🔑 מפתח #{i} כשל טכנית: {str(e)}")
                
        return "❌ שגיאת התחברות ל-Gemini. פירוט השגיאות מהשרת:\n\n" + "\n".join(errors)

    def _call_claude(self, prompt):
        if not self.claude_key:
            return "⚠️ מפתח Claude חסר בהגדרות ה-Secrets."

        models_to_try = [
            "claude-opus-4-6",               
            "claude-sonnet-4-20250514",      
            "claude-3-5-sonnet-20241022",    
            "claude-3-5-sonnet-latest"       
        ]

        headers = {
            "x-api-key": self.claude_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        for model_name in models_to_try:
            try:
                payload = {
                    "model": model_name,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}]
                }
                # מוגדר כאן ל-120 שניות כדי שקלוד לא יקרוס ויחתוך את הפעולה באמצע!
                res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)

                if res.status_code == 200:
                    return res.json()['content'][0]['text']
                elif res.status_code == 404:
                    continue
                else:
                    return f"❌ השרת של קלוד סירב למודל {model_name}. (קוד {res.status_code}): {res.text}"
            except Exception as e:
                return f"❌ שגיאה טכנית בחיבור ל-Claude: {str(e)}"

        return "❌ שגיאת 404: אף אחד מהמודלים שניסינו לא זמין בחשבון ה-API שלך בקלוד."

    def calculate_compatibility_score(self, results):
        clean_results = _parse_to_simple_dict(results)
        if not clean_results: return 0
        total = 0
        for trait, score in clean_results.items():
            r = TRAIT_RANGES.get(trait, {})
            if r.get("optimal_low", 0) <= score <= r.get("optimal_high", 5): total += 100
            elif score < r.get("critical_low", 0) or score > r.get("critical_high", 5): total += 30
            else: total += 70
        return int(total / max(1, len(clean_results)))

    def generate_expert_reports(self, name, results, history=[]):
        clean_results = _parse_to_simple_dict(results)
        gaps = []
        for t, s in clean_results.items():
            gaps.append(f"{TRAIT_DICT.get(t, t)}: {_extract_float(s):.2f} (יעד: {IDEAL_DOCTOR.get(t, 'N/A')})")
        gaps_str = "\n".join(gaps)
        
        trend_text = "אין היסטוריה קודמת"
        if history:
            trend_text = "\n".join([f"מבחן מ-{h.get('test_date', 'unknown')}: {h.get('results', '{}')}" for h in history[-3:]])

        gemini_prompt = f"""
        אתה פסיכולוג ארגוני בכיר במיוני רפואה (מס"ר).
        מועמד: {name}
        תוצאות נוכחיות: {json.dumps(clean_results)}
        ניתוח פערים: {gaps_str}
        היסטוריית מגמות: {trend_text}
        כתוב דוח מפורט (לפחות 1200 מילים) בעברית.
        """

        claude_prompt = f"""
        אתה ד"ר רחל גולדשטיין, פסיכולוגית קלינית בכירה המומחית למיון מועמדים לרפואה.
        מועמד: {name}
        תוצאות: {json.dumps(clean_results)}
        נתח את הסיכונים הקליניים והתאמת המועמד למצבי לחץ.
        כתוב דוח מעמיק של 1500 מילים בעברית.
        © זכויות יוצרים לניתאי מלכה.
        """

        return self._call_gemini_safe(gemini_prompt), self._call_claude(claude_prompt)

    def create_radar_chart(self, results):
        clean_results = _parse_to_simple_dict(results)
        if not clean_results: return go.Figure()
        fig = go.Figure()
        cat = [TRAIT_DICT.get(k, k) for k in clean_results.keys()]
        val = list(clean_results.values())
        ideal = [IDEAL_DOCTOR.get(k, 3) for k in clean_results.keys()]
        fig.add_trace(go.Scatterpolar(r=ideal + [ideal[0]] if ideal else [], theta=cat + [cat[0]] if cat else [], fill='toself', name='🎯 יעד', line=dict(color='rgba(46,204,113,0.5)')))
        fig.add_trace(go.Scatterpolar(r=val + [val[0]] if val else [], theta=cat + [cat[0]] if cat else [], fill='toself', name='📊 אתה', line=dict(color='#1e3a8a', width=4)))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 5])), paper_bgcolor='rgba(0,0,0,0)')
        return fig

    def create_comparison_bar_chart(self, results):
        clean_results = _parse_to_simple_dict(results)
        if not clean_results: return go.Figure()
        cat = [TRAIT_DICT.get(k, k) for k in clean_results.keys()]
        val = list(clean_results.values())
        ideal = [IDEAL_DOCTOR.get(k, 3) for k in clean_results.keys()]
        fig = go.Figure(data=[
            go.Bar(name='אתה', x=cat, y=val, marker_color='#1e3a8a'),
            go.Bar(name='יעד רפואי', x=cat, y=ideal, marker_color='rgba(46,204,113,0.5)')
        ])
        fig.update_layout(barmode='group', yaxis=dict(range=[1, 5]), paper_bgcolor='rgba(0,0,0,0)')
        return fig

    def create_token_gauge(self, text):
        tokens = int(len(str(text).split()) * 1.5) if text else 0
        fig = go.Figure(go.Indicator(mode="gauge+number", value=tokens, title={'text': "Tokens"}, gauge={'axis': {'range': [0, 8000]}, 'bar': {'color': "#2ECC71"}}))
        fig.update_layout(height=250)
        return fig

# --- פונקציות גלובליות ---
def get_multi_ai_analysis(name, results, history=[]): return HEXACO_Expert_System().generate_expert_reports(name, results, history)
def get_radar_chart(results): return HEXACO_Expert_System().create_radar_chart(results)
def get_comparison_chart(results): return HEXACO_Expert_System().create_comparison_bar_chart(results)
def create_token_gauge(text): return HEXACO_Expert_System().create_token_gauge(text)

def get_integrity_ai_analysis(user_name, reliability_score, contradictions, int_scores, history):
    expert = HEXACO_Expert_System()
    clean_scores = _parse_to_simple_dict(int_scores)
    rel_info = f"מדד אמינות: {reliability_score}%\n"
    if contradictions:
        rel_info += "סתירות שזוהו:\n" + "\n".join([f"- {c.get('message', str(c))}" for c in contradictions])
    prompt = f"אתה פסיכולוג מנתח מבדק אמינות. מועמד: {user_name}\nתוצאות: {json.dumps(clean_scores)}\n{rel_info}\nהיסטוריה: {history}\nכתוב דוח מפורט בעברית."
    return expert._call_gemini_safe(prompt), expert._call_claude(prompt)

def get_combined_ai_analysis(user_name, trait_scores, reliability_score, contradictions, history):
    expert = HEXACO_Expert_System()
    clean_scores = _parse_to_simple_dict(trait_scores)
    rel_info = f"מדד אמינות שאלון: {reliability_score}%\n"
    if contradictions:
        rel_info += "אזהרת עקביות - נמצאו סתירות:\n" + "\n".join([f"- {c.get('message', str(c))}" for c in contradictions])
    prompt = f"אתה פסיכולוג בכיר המנתח מבדק משולב: אישיות (HEXACO) ואמינות. מועמד: {user_name}\nציוני אישיות: {json.dumps(clean_scores)}\n{rel_info}\nכתוב דוח מעמיק בעברית."
    return expert._call_gemini_safe(prompt), expert._call_claude(prompt)
