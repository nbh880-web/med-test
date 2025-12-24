# ... (כל ה-imports וה-CSS הקיימים שלך) ...
from gemini_ai import get_ai_analysis, get_comparison_chart, get_history

# --- מסכי האפליקציה ---

if st.session_state.step == 'HOME':
    st.title("🏥 מערכת סימolציה HEXACO - הכנה למס\"ר")
    st.session_state.user_name = st.text_input("הכנס את שמך המלא:", st.session_state.user_name)
    
    if st.session_state.user_name:
        # הוספת טאבים לארכיון ומבחן חדש
        tab_new, tab_archive = st.tabs(["📝 מבחן חדש", "📜 ארכיון אישי"])
        
        with tab_new:
            all_qs_df = load_questions()
            st.write(f"שלום {st.session_state.user_name}, בחר סימולציה להתחלה:")
            col1, col2, col3 = st.columns(3)
            if col1.button("⏳ תרגול מהיר (36)"):
                st.session_state.questions = get_balanced_questions(all_qs_df, 36)
                st.session_state.step = 'QUIZ'; st.session_state.start_time = time.time(); st.rerun()
            if col2.button("📋 סימולציה רגילה (120)"):
                st.session_state.questions = get_balanced_questions(all_qs_df, 120)
                st.session_state.step = 'QUIZ'; st.session_state.start_time = time.time(); st.rerun()
            if col3.button("🔍 סימולציה מלאה (300)"):
                st.session_state.questions = get_balanced_questions(all_qs_df, 300)
                st.session_state.step = 'QUIZ'; st.session_state.start_time = time.time(); st.rerun()

        with tab_archive:
            st.subheader(f"היסטוריית תרגול: {st.session_state.user_name}")
            history = get_history(st.session_state.user_name)
            if not history:
                st.info("טרם נשמרו מבחנים בארכיון.")
            for entry in history:
                with st.expander(f"סימולציה מ- {entry.get('timestamp').strftime('%d/%m/%y %H:%M')}"):
                    st.plotly_chart(get_comparison_chart(entry['results']), use_container_width=True)
                    st.markdown(f'<div class="ai-report-box">{entry["ai_report"]}</div>', unsafe_allow_html=True)

# ... (שלב ה-QUIZ נשאר זהה) ...

elif st.session_state.step == 'RESULTS':
    st.title(f"📊 דוח הכנה למס\"ר - {st.session_state.user_name}")
    df_raw, summary_df = process_results(st.session_state.responses)
    trait_scores = summary_df.set_index('trait')['final_score'].to_dict()

    # הצגת הגרף ההשוואתי החדש
    st.subheader("📊 השוואה לפרופיל היעד")
    st.plotly_chart(get_comparison_chart(trait_scores), use_container_width=True)

    # ... (המשך הצגת הטבלה והעקביות הקיימים שלך) ...

    if st.button("צור ניתוח AI והכנה למס\"ר"):
        with st.spinner("המאמן האישי מנתח את התוצאות..."):
            ai_data = summary_df.to_string()
            report_text = get_ai_analysis(st.session_state.user_name, trait_scores)
            st.markdown("### 💡 טיפים והכנה למס\"ר:")
            st.markdown(f'<div class="ai-report-box">{report_text}</div>', unsafe_allow_html=True)
            # ... (המשך ה-PDF שלך) ...
