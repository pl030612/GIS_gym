import os
import json
import glob
import sqlite3
import random
import re
import docx2txt  # 需 pip install docx2txt
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import altair as alt

from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


# =====================================================
# 0) Streamlit 基本設定
# =====================================================
st.set_page_config(page_title="GIS Gym - 空間分析 AI 助教", page_icon="🧪", layout="wide")
st.title("🧪 GIS Gym｜空間分析 AI 助教平台")
st.caption("自主練習 (Real Data) ⮕ 單元作業 (Assignments) ⮕ 助教分析 (AI Consultant)")


# =====================================================
# 1) OpenAI API Key & Client
# =====================================================
def get_openai_key():
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    return os.getenv("OPENAI_API_KEY")

OPENAI_API_KEY = get_openai_key()
if not OPENAI_API_KEY:
    st.error("❌ 找不到 OPENAI_API_KEY，請檢查 Secrets 設定。")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)


# =====================================================
# 2) 路徑設定
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LECTURES_DIR = os.path.join(BASE_DIR, "lectures")
FAISS_DIR = os.path.join(BASE_DIR, "GeoGIS_faiss_db")
DB_PATH = os.path.join(BASE_DIR, "learning_history.sqlite")


# =====================================================
# 3) SQLite 初始化 (Unit ID 架構)
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. 練習紀錄表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            student_id TEXT,
            unit_id INTEGER,
            topic TEXT,
            question TEXT,
            score INTEGER,
            level TEXT,
            feedback_json TEXT
        )
    """)
    
    # 2. 練習加分表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bonus_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id INTEGER UNIQUE,
            bonus INTEGER DEFAULT 0,
            note TEXT,
            updated_at TEXT,
            FOREIGN KEY(history_id) REFERENCES learning_history(id)
        )
    """)

    # 3. 作業繳交紀錄表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            student_id TEXT,
            unit_id INTEGER,
            answer TEXT,
            score INTEGER,
            feedback_json TEXT,
            timestamp TEXT
        )
    """)
    
    conn.commit()
    conn.close()

init_db()


# =====================================================
# 4) 資料載入：Metadata、真實檔案、Word作業(含快取)
# =====================================================
@st.cache_data(show_spinner=False)
def load_all_metadata():
    """讀取所有單元的 metadata.json"""
    if not os.path.exists(LECTURES_DIR): return []
    files = glob.glob(os.path.join(LECTURES_DIR, "**", "metadata.json"), recursive=True)
    out = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                # 相容性處理
                if "week" in data and "unit_id" not in data:
                    data["unit_id"] = data["week"]
                out.append(data)
        except:
            pass
    return out

all_metadata = load_all_metadata()
units_available = sorted({m.get("unit_id") for m in all_metadata if "unit_id" in m})
unit_options = [str(u) for u in units_available]

def get_unit_files(unit_id: int):
    """回傳該單元資料夾下的 GIS 真實檔案 (.shp, .csv 等)"""
    if not os.path.exists(LECTURES_DIR): return []

    target_folder = None
    for folder in os.listdir(LECTURES_DIR):
        match = re.match(r"^(\d+)[_]", folder)
        if match and int(match.group(1)) == unit_id:
            target_folder = folder
            break
    
    if not target_folder: return []

    data_dir = os.path.join(LECTURES_DIR, target_folder, "data")
    files_list = []
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.lower().endswith(('.shp', '.shx', '.dbf', '.csv', '.tif', '.geojson', '.zip', '.txt')):
                files_list.append({
                    "name": f,
                    "path": os.path.join(data_dir, f)
                })
    return files_list

# 🔥 效能關鍵：ttl=900 (15分鐘快取)
@st.cache_data(ttl=900, show_spinner="正在掃描作業檔案...")
def scan_assignments_from_files():
    """動態掃描 Word 作業檔"""
    assignments_db = {}
    if not os.path.exists(LECTURES_DIR): return {}

    folders = sorted([f for f in os.listdir(LECTURES_DIR) if os.path.isdir(os.path.join(LECTURES_DIR, f))])
    
    for folder in folders:
        match = re.match(r"^(\d+)[_]", folder)
        if not match: continue
        unit_id = int(match.group(1))
        
        folder_path = os.path.join(LECTURES_DIR, folder)
        target_file = None
        sub_assign_dir = os.path.join(folder_path, "assignments")
        
        search_dirs = []
        if os.path.exists(sub_assign_dir): search_dirs.append(sub_assign_dir)
        search_dirs.append(folder_path)
            
        for d in search_dirs:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                if (f.lower().startswith("homework") or f.lower().startswith("assignment")) and f.endswith(".docx"):
                    target_file = os.path.join(d, f)
                    break
            if target_file: break
        
        if target_file:
            try:
                content = docx2txt.process(target_file)
                assignments_db[unit_id] = {
                    "id": 1000 + unit_id,
                    "title": f"Unit {unit_id} 作業：{os.path.basename(target_file)}",
                    "description": content if content.strip() else "（檔案內容為空）",
                    "deadline": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
                }
            except Exception as e:
                print(f"Error reading docx {target_file}: {e}")
                
    return assignments_db

ASSIGNMENTS_DB = scan_assignments_from_files()


# =====================================================
# 5) FAISS 與 RAG 核心
# =====================================================
def ensure_vectorstore_loaded():
    if "vectorstore" in st.session_state and st.session_state["vectorstore"] is not None:
        return st.session_state["vectorstore"]
    if not os.path.exists(FAISS_DIR): return None
    try:
        with st.spinner("⏳ 正在載入向量資料庫..."):
            embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
            vs = FAISS.load_local(FAISS_DIR, embeddings, allow_dangerous_deserialization=True)
            st.session_state["vectorstore"] = vs
            return vs
    except Exception as e:
        st.error(f"向量庫載入失敗: {e}")
        return None

def _retrieve_context(query: str, unit_id: int | None, k: int = 8) -> str:
    vs = ensure_vectorstore_loaded()
    if vs is None: return ""
    
    docs = vs.similarity_search(query, k=20)
    if unit_id is not None:
        docs = [d for d in docs if d.metadata.get("unit_id") == unit_id or d.metadata.get("week") == unit_id]
    
    docs = docs[:k]
    parts = [f"[Unit {d.metadata.get('unit_id', '?')}] {d.page_content}" for d in docs]
    return "\n\n".join(parts)


# =====================================================
# 6) AI 功能：GPT-4o (出題/批改/分析)
# =====================================================
def generate_practice_question_real_data(level: str, qtype: str, unit_id: int | None) -> dict:
    q_str = f"Unit {unit_id}" if unit_id else ""
    seed = f"{q_str} 空間分析 {qtype} {level}"
    context = _retrieve_context(seed, unit_id=unit_id)
    
    styles = [
        "**角色扮演**：設定學生為資料分析師，解決特定業主問題。",
        "**除錯挑戰**：描述一個分析流程，請學生用資料實作並驗證。",
        "**比較分析**：請學生用同一份資料嘗試兩種不同參數或方法。"
    ]
    selected_style = random.choice(styles)
    
    if qtype == "實作題":
        real_files = get_unit_files(unit_id) if unit_id else []
        file_names_str = ", ".join([f['name'] for f in real_files]) if real_files else "無 (請自行假設虛擬資料)"
        
        system_instruction = f"""
        你必須從提供的「真實檔案列表」中選擇一個檔案來設計操作任務。
        真實檔案列表: [{file_names_str}]
        """
        target_file_instruction = "AI選擇的檔案名稱(必須完全符合列表)"
    
    else:
        system_instruction = """
        這是一道「觀念簡答題」。
        ❌ 請勿要求學生操作任何特定檔案。
        ❌ 請勿提及特定的檔名 (如 .shp)。
        ✅ 請專注於測試學生對該單元空間分析概念的理解。
        """
        target_file_instruction = "None"

    # [UPDATED] 修改 System Prompt，加入 "hint" 欄位
    system_prompt = f"""
    你是頂尖的空間分析助教。請使用 GPT-4o 的強大邏輯來出題。
    目前的題型任務是：【{qtype}】。難度：{level}。
    
    {system_instruction}
    
    請以 JSON 格式回傳，務必包含 hint (提示) 欄位：
    {{
        "question_content": "題目內容(Markdown)，請勿在題目中直接寫出提示或答案...",
        "hint": "給學生的引導提示(Markdown)，例如『考慮使用 st_buffer 函數...』，但不要直接給答案。",
        "target_filename": "{target_file_instruction}",
        "style_used": "{selected_style}"
    }}
    """
    
    user_prompt = f"請設計題目。[參考講義] {context}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"question_content": f"出題錯誤: {e}", "target_filename": None, "style_used": "Error", "hint": ""}


def grade_submission(question_text: str, student_answer: str, unit_id: int | None) -> dict:
    context = _retrieve_context(question_text, unit_id=unit_id, k=10)
    prompt = f"""
    [角色] 嚴格的空間分析助教。
    [題目] {question_text}
    [學生回答] {student_answer}
    [講義依據] {context}
    
    請以 JSON 回傳批改：
    {{
      "score": (0-10),
      "level": "Excellent/Good/Fair/Poor",
      "strengths": ["優點..."],
      "weaknesses": ["缺點..."],
      "suggestions": ["建議..."]
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"score": 0, "weaknesses": ["系統錯誤"], "suggestions": [str(e)]}

def generate_weakness_report(unit_id: int):
    conn = sqlite3.connect(DB_PATH)
    df_p = pd.read_sql("SELECT feedback_json FROM learning_history WHERE unit_id=?", conn, params=(unit_id,))
    df_a = pd.read_sql("SELECT feedback_json FROM submissions WHERE unit_id=?", conn, params=(unit_id,))
    conn.close()
    
    feedbacks = pd.concat([df_p['feedback_json'], df_a['feedback_json']]).dropna()
    if feedbacks.empty: return "⚠️ 該單元尚無足夠數據。"

    all_weaknesses = []
    for json_str in feedbacks:
        try:
            data = json.loads(json_str)
            if 'weaknesses' in data: all_weaknesses.extend(data['weaknesses'])
        except: pass
    
    if not all_weaknesses: return "⚠️ 數據中找不到弱點紀錄。"

    weakness_text = "\n".join(all_weaknesses[:60])
    prompt = f"""
    你是教學顧問。以下是 Unit {unit_id} 學生常犯錯誤列表：
    {weakness_text}
    
    請使用 GPT-4o 製作 Markdown 報告：
    1. **🚨 Top 3 核心弱點**
    2. **👨‍🏫 教學加強建議**
    3. **📝 推薦考題 (2題)**
    """
    with st.spinner("🤖 AI 正在撰寫分析報告..."):
        r = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content


# =====================================================
# 7) DB Log Functions
# =====================================================
def log_practice(sid, uid, q, fb):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO learning_history (timestamp, student_id, unit_id, question, score, level, feedback_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), sid, uid, q, fb.get('score'), fb.get('level'), json.dumps(fb, ensure_ascii=False)))
    conn.commit()
    conn.close()

def log_assignment_submission(assign_id, sid, uid, ans, fb):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO submissions (assignment_id, student_id, unit_id, answer, score, feedback_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assign_id, sid, uid, ans, fb.get('score'), json.dumps(fb, ensure_ascii=False), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_student_submission(sid, assign_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT score, feedback_json FROM submissions WHERE student_id=? AND assignment_id=? ORDER BY id DESC LIMIT 1", (sid, assign_id))
    row = cur.fetchone()
    conn.close()
    return row

def read_history_join_bonus() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    q = """
    SELECT lh.id, lh.timestamp, lh.student_id, lh.unit_id, lh.score, lh.question,
           COALESCE(bp.bonus, 0) AS bonus,
           (COALESCE(lh.score, 0) + COALESCE(bp.bonus, 0)) AS total_score,
           bp.note AS bonus_note
    FROM learning_history lh
    LEFT JOIN bonus_points bp ON lh.id = bp.history_id
    ORDER BY lh.id DESC
    """
    df = pd.read_sql(q, conn)
    conn.close()
    return df

def upsert_bonus(history_id, bonus, note):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO bonus_points (history_id, bonus, note, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(history_id) DO UPDATE SET
            bonus=excluded.bonus, note=excluded.note, updated_at=excluded.updated_at
    """, (history_id, bonus, note, now))
    conn.commit()
    conn.close()


# =====================================================
# 8) 助教權限與 UI
# =====================================================
with st.sidebar:
    st.header("👤 使用者設定")
    if "student_id" not in st.session_state: st.session_state["student_id"] = ""
    st.session_state["student_id"] = st.text_input("輸入學號", value=st.session_state["student_id"])
    
    st.markdown("---")
    if "is_ta" not in st.session_state: st.session_state["is_ta"] = False
    
    if not st.session_state["is_ta"]:
        with st.expander("🔒 助教登入"):
            u = st.text_input("帳號", key="ta_u")
            p = st.text_input("密碼", type="password", key="ta_p")
            if st.button("登入"):
                if u == "ta" and p == "gisgym2025!":
                    st.session_state["is_ta"] = True
                    st.rerun()
                else:
                    st.error("錯誤")
    else:
        st.success("👨‍🏫 助教模式")
        if st.button("登出"):
            st.session_state["is_ta"] = False
            st.rerun()

# Tabs
tabs_list = ["🏋️ 自主練習區", "📝 單元作業區"]
if st.session_state["is_ta"]: tabs_list.append("📊 助教後台 (分析)")
tabs = st.tabs(tabs_list)

# -----------------------------------------------------
# Tab 1: 自主練習
# -----------------------------------------------------
with tabs[0]:
    st.subheader("🏋️ 空間分析自主練習 (含實體資料)")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        unit_str = c1.selectbox("選擇單元", ["全部"] + unit_options, key="p_unit")
        unit_val = int(unit_str) if unit_str != "全部" else None
        lvl = c2.selectbox("難度", ["入門", "進階"], key="p_lvl")
        qty = c3.selectbox("題型", ["簡答題", "實作題"], key="p_qty")
        
        if c4.button("🎲 GPT-4o 出題", type="primary", use_container_width=True):
            with st.spinner("AI 正在出題..."):
                q_data = generate_practice_question_real_data(lvl, qty, unit_val)
                st.session_state["pq_data"] = q_data
                st.session_state["pq_meta"] = f"{unit_str} | {lvl} | {qty}"
    
    if "pq_data" in st.session_state:
        q_data = st.session_state["pq_data"]
        q_content = q_data.get("question_content", "")
        q_hint = q_data.get("hint", "") # 抓取 hint
        target_file = q_data.get("target_filename")
        style = q_data.get("style_used", "")

        st.markdown(f"### 📌 題目 [{st.session_state['pq_meta']}]")
        st.caption(f"風格：{style}")
        st.info(q_content)

        # [UPDATED] 提示區塊 - 預設摺疊
        if q_hint:
            with st.expander("💡 需要一點提示嗎？ (Click for Hint)"):
                st.markdown(q_hint)

        if target_file and target_file != "None" and target_file is not None:
            files = get_unit_files(unit_val) if unit_val else []
            file_path = next((f['path'] for f in files if f['name'] == target_file), None)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as fp:
                    st.download_button(f"📥 下載練習圖資 ({target_file})", fp, target_file)
            else:
                if unit_val: st.warning(f"⚠️ 檔案 '{target_file}' 未找到。")
        
        sid = st.session_state["student_id"]
        ans = st.text_area("作答區", height=150, key="p_ans", disabled=not sid, placeholder="請先輸入學號..." if not sid else "輸入答案...")
        
        if st.button("送出批改", key="p_sub", disabled=not ans):
            with st.spinner("批改中..."):
                fb = grade_submission(q_content, ans, unit_val)
                log_practice(sid, unit_val, q_content, fb)
                st.success(f"分數: {fb.get('score')}")
                with st.expander("查看完整評語", expanded=True): st.json(fb)

# -----------------------------------------------------
# Tab 2: 單元作業 (自動掃描 Word)
# -----------------------------------------------------
with tabs[1]:
    st.subheader("📝 單元作業繳交")
    
    if not ASSIGNMENTS_DB:
        st.info("📂 目前沒有掃描到任何作業檔案 (homework/assignment*.docx)。")
    else:
        target_unit = st.selectbox("選擇作業單元", options=sorted(ASSIGNMENTS_DB.keys()), format_func=lambda x: f"Unit {x}")
        assignment = ASSIGNMENTS_DB.get(target_unit)
        
        if assignment:
            st.markdown(f"### {assignment['title']}")
            st.caption(f"📅 截止期限: {assignment['deadline']}")
            with st.expander("📄 作業說明 (從 Word 讀取)", expanded=True):
                st.write(assignment['description'])
            
            sid = st.session_state["student_id"]
            if not sid:
                st.warning("請先在側邊欄輸入學號。")
            else:
                prev = get_student_submission(sid, assignment['id'])
                if prev:
                    st.success(f"✅ 已繳交。分數：{prev[0]}")
                    with st.expander("查看上次批改"): st.json(json.loads(prev[1]))
                    st.write("---")
                
                assign_ans = st.text_area("作業作答區", height=250, key=f"assign_ans_{target_unit}")
                if st.button(f"繳交 Unit {target_unit} 作業", type="primary", disabled=not assign_ans):
                    with st.spinner("繳交並批改中..."):
                        fb = grade_submission(assignment['description'], assign_ans, target_unit)
                        log_assignment_submission(assignment['id'], sid, target_unit, assign_ans, fb)
                        st.balloons()
                        st.success(f"繳交成功！AI 預評分：{fb.get('score')}")
                        st.rerun()

# -----------------------------------------------------
# Tab 3: 助教後台
# -----------------------------------------------------
if st.session_state["is_ta"] and len(tabs) > 2:
    with tabs[2]:
        st.subheader("📊 助教管理後台")
        
        with st.container(border=True):
            st.markdown("### 🤖 AI 教學顧問報告")
            ana_unit = st.selectbox("分析單元", unit_options, key="ana_unit")
            if st.button("生成分析報告"):
                if ana_unit:
                    report = generate_weakness_report(int(ana_unit))
                    st.markdown(report)
        
        st.markdown("---")
        st.markdown("### 📝 作答紀錄與加分")
        df = read_history_join_bonus()
        if not df.empty:
            f_unit = st.multiselect("篩選單元", sorted(df['unit_id'].dropna().unique()))
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
            st.info("無資料")