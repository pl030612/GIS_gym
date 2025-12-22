# -----------------------------------------------------
# Tab 3: 助教後台
# -----------------------------------------------------
if st.session_state["is_ta"] and len(tabs) > 2:
    with tabs[2]:
        # 1. AI 報告
        with st.container(border=True):
            st.markdown("### AI 教學顧問報告") 
            ana_unit = st.selectbox("分析單元", unit_options, key="ana_unit")
            if st.button("生成分析報告"):
                if ana_unit:
                    report = generate_weakness_report(int(ana_unit))
                    st.markdown(report)
        
        st.markdown("---")
        
        # 2. 練習紀錄 (Practice)
        st.markdown("### 自主練習紀錄 (Practice)") 
        df = read_history_join_bonus()
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載練習紀錄 (.csv)", csv, "practice_history.csv", "text/csv")
            
            f_unit = st.multiselect("篩選單元 (練習)", sorted(df['unit_id'].dropna().unique()), key="f_unit_prac")
            if f_unit: df = df[df['unit_id'].isin(f_unit)]
            
            event = st.dataframe(df, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", height=300)
            
            if len(event.selection.rows) > 0:
                row = df.iloc[event.selection.rows[0]]
                st.info(f"編輯加分: ID {row['id']} ({row['student_id']})")
                with st.form("bonus"):
                    c1, c2 = st.columns([1, 3])
                    nb = c1.number_input("Bonus", value=int(row['bonus']))
                    nn = c2.text_input("Note", value=str(row['bonus_note'] or ""))
                    if st.form_submit_button("更新"):
                        upsert_bonus(int(row['id']), nb, nn)
                        st.rerun()
        else:
            st.info("無練習資料")

        st.markdown("---")

        # 3. 作業繳交紀錄 (Assignment Submissions)
        st.markdown("### 作業繳交檢視 (Submissions)") 
        df_sub = read_submissions_all()
        if not df_sub.empty:
            csv_sub = df_sub.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載作業紀錄 (.csv)", csv_sub, "assignment_submissions.csv", "text/csv")

            f_unit_sub = st.multiselect("篩選單元 (作業)", sorted(df_sub['unit_id'].dropna().unique()), key="f_unit_sub")
            if f_unit_sub: df_sub = df_sub[df_sub['unit_id'].isin(f_unit_sub)]

            # [UPDATED] 手動指定欄位順序，將 timestamp 移到最前，並隱藏 id/assignment_id
            target_order = ["timestamp", "student_id", "unit_id", "score", "answer"]
            
            # 防呆機制：確保這些欄位真的存在於資料中 (避免資料庫結構不同步時報錯)
            display_cols = [c for c in target_order if c in df_sub.columns]
            
            st.dataframe(df_sub[display_cols], use_container_width=True, hide_index=True, height=300)
        else:
            st.info("目前尚無作業繳交紀錄。")