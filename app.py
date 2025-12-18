import os
import json
import glob
import sqlite3
import random
import re
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
# 3) SQLite 初始化 (欄位已更新為 unit_id)
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. 練習紀錄表 (week -> unit_id)
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

    # 3. 作業繳交紀錄表 (week -> unit_id)
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
# 4) 資料載入與掃描 (配合流水號目錄結構)
# =====================================================
@st.cache_data(show_spinner=False)
def load_all_metadata():
    # 掃描 lectures 下所有 metadata.json
    files = glob.glob(os.path.join(LECTURES_DIR, "**", "metadata.json"), recursive=True)
    out = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                # 兼容處理：如果 json 裡還是寫 week，我們把它讀為 unit_id
                if "week" in data and "unit_id" not in data:
                    data["unit_id"] = data["week"]
                out.append(data)
        except:
            pass
    return out

all_metadata = load_all_metadata()
# 取得所有可用單元 ID
units_available = sorted({m.get("unit_id") for m in all_metadata if "unit_id" in m})
unit_options = [str(u) for u in units_available]

# --- [UPDATED] 掃描真實資料檔 (依流水號資料夾) ---
def get_unit_files(unit_id: int):
    """
    回傳該單元資料夾 (如 01_Data_Analysis/data) 下的 GIS 相關檔案
    """
    if not os.path.exists(LECTURES_DIR):
        return []

    # 1. 尋找對應 unit_id 的資料夾 (例如找開頭是 "01_" 或 "1_")
    target_folder_name = None
    for folder_name in os.listdir(LECTURES_DIR):
        # Regex 匹配開頭數字
        match = re.match(r"^(\d+)[_]", folder_name)
        if match:
            if int(match.group(1)) == unit_id:
                target_folder_name = folder_name
                break
    
    if not target_folder_name:
        return []

    # 2. 進入該資料夾下的 data 目錄
    data_dir = os.path.join(LECTURES_DIR, target_folder_name, "data")
    
    files_list = []
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.lower().endswith(('.shp', '.shx', '.dbf', '.csv', '.tif', '.geojson', '.zip', '.txt')):
                files_list.append({
                    "name": f,
                    "path": os.path.join(data_dir, f)
                })
    return files_list


# --- 模擬作業資料 (Assignment DB) ---
# Key 改為 Unit ID
ASSIGNMENTS_DB = {
    3: {
        "id": 103,
        "title": "Unit 3 作業：空間資料結構解析",
        "description": "請說明 Vector 與 Raster 資料結構在儲存空間與運算效能上的主要差異，並舉一個實際案例說明何時該選用 Raster。",
        "deadline": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    },
    4: {
        "id": 104,
        "title": "Unit 4 作業：座標系統實作",
        "description": "請使用 R 的 `sf` 套件，寫出一段將 TWD97 (EPSG:3826) 轉換為 WGS84 (EPSG:4326) 的程式碼，並解釋為何需要進行座標轉換。",
        "deadline": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    }
}


# =====================================================
# 5) FAISS 與 RAG 核心
# =====================================================
def ensure_vectorstore_loaded():
    if "vectorstore" in st.session_state and st.session_state["vectorstore"] is not None:
        return st.session_state["vectorstore"]
    if not os.path.exists(FAISS_DIR):
        return None
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
    
    # 搜尋相似文件
    docs = vs.similarity_search(query, k=20)
    
    # [UPDATED] 依照 unit_id 過濾
    if unit_id is not None:
        # 注意：需確保 build_vector_db.py 寫入的是 "unit_id"
        # 若是舊的 db 寫的是 "week"，這裡要改為 d.metadata.get("week")
        docs = [d for d in docs if d.metadata.get("unit_id") == unit_id]
    
    docs = docs[:k]
    
    # 格式化輸出
    parts = []
    for d in docs:
        uid = d.metadata.get('unit_id', '?')
        content = d.page_content
        parts.append(f"[Unit {uid}] {content}")
        
    return "\n\n".join(parts)


# =====================================================
# 6) AI 功能：出題 / 批改 / 報告
# =====================================================
def generate_practice_question_real_data(level: str, qtype: str, unit_id: int | None) -> dict:
    # 1. 檢索講義
    q_str = f"Unit {unit_id}" if unit_id else ""
    seed = f"{q_str} 空間分析 {qtype} {level}"
    context = _retrieve_context(seed, unit_id=unit_id)
    
    # 2. 掃描真實檔案
    real_files = []
    if unit_id:
        real_files = get_unit_files(unit_id)
    file_names_str = ", ".join([f['name'] for f in real_files]) if real_files else "無 (請自行假設虛擬資料)"

    # 3. 風格設定
    styles = [
        "**角色扮演**：設定學生為資料分析師，解決特定業主問題。",
        "**除錯挑戰**：描述一個分析流程，請學生用資料實作並驗證。",
        "**比較分析**：請學生用同一份資料嘗試兩種不同參數或方法。"
    ]
    selected_style = random.choice(styles)

    # 4. Prompt
    system_prompt = f"""
    你是頂尖的空間分析助教。請使用 GPT-4o 的強大邏輯來出題。
    你必須從提供的「真實檔案列表」中選擇一個檔案來設計「實作題」。
    
    真實檔案列表: [{file_names_str}]
    
    請以 JSON 格式回傳，欄位如下：
    {{
        "question_content": "題目內容(Markdown)...",
        "target_filename": "AI選擇的檔案名稱(必須完全符合列表)",
        "style_used": "{selected_style}"
    }}
    """
    
    if qtype == "實作題":
        if not real_files:
            user_prompt = f"目前沒有實體檔案，請設計一個通用的實作題。\n[參考講義]{context}"
        else:
            user_prompt = f"""
            【題型：實作題】難度：{level}
            請從檔案列表中挑選一個最適合的檔案，設計一個 GIS 操作任務。
            題目必須明確指出要使用哪個檔案，以及要達成什麼分析目標。
            [參考講義] {context}
            """
    else:
        user_prompt = f"""
        【題型：簡答題】難度：{level}
        請參考檔案列表中的資料特性（例如欄位或空間分布）來設計情境題，但不要求實際操作。
        [參考講義] {context}
        """

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
        return {
            "question_content": f"出題發生錯誤: {str(e)}",
            "target_filename": None,
            "style_used": "Error"
        }

def grade_submission(question_text: str, student_answer: str, unit_id: int | None) -> dict:
    context = _retrieve_context(question_text, unit_id=unit_id, k=10)
    prompt = f"""
    [角色] 你是嚴格的空間分析助教。
    [題目] {question_text}
    [學生回答] {student_answer}
    [講義依據] {context}
    
    請以 JSON 回傳批改結果：
    {{
      "score": (0-10),
      "level": "Excellent/Good/Fair/Poor",
      "strengths": ["優點1",...],
      "weaknesses": ["缺點1",...],
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
    # 1. 撈取該單元所有練習與作業的 feedback
    conn = sqlite3.connect(DB_PATH)
    # [UPDATED] SQL 查詢 unit_id
    df_p = pd.read_sql("SELECT feedback_json FROM learning_history WHERE unit_id=?", conn, params=(unit_id,))
    df_a = pd.read_sql("SELECT feedback_json FROM submissions WHERE unit_id=?", conn, params=(unit_id,))
    conn.close()
    
    feedbacks = pd.concat([df_p['feedback_json'], df_a['feedback_json']]).dropna()
    
    if feedbacks.empty:
        return "⚠️ 該單元尚無足夠的數據，無法進行分析。"

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
    
    請使用 GPT-4o 分析並製作一份 Markdown 報告：
    1. **🚨 Top 3 核心弱點**：歸納學生最不熟的概念。
    2. **👨‍🏫 教學加強建議**：助教在該單元教學時該重講什麼？
    3. **📝 推薦考題 (2題)**：針對這些弱點，設計 2 題考題 (附簡易參考答案)。
    """
    
    with st.spinner("🤖 AI 正在閱讀所有學生的作業並撰寫分析報告..."):
        r = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
    return r.choices[0].message.content


# =====================================================
# 7) 資料庫寫入 (Log Functions)
# =====================================================
def log_practice(sid, uid, q, fb):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # [UPDATED] 寫入 unit_id
    cur.execute("""
        INSERT INTO learning_history (timestamp, student_id, unit_id, question, score, level, feedback_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), sid, uid, q, fb.get('score'), fb.get('level'), json.dumps(fb, ensure_ascii=False)))
    conn.commit()
    conn.close()

def log_assignment_submission(assign_id, sid, uid, ans, fb):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # [UPDATED] 寫入 unit_id
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
    # [UPDATED] 查詢 unit_id
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
# 8) 助教權限管理
# =====================================================
with st.sidebar:
    st.header("👤 使用者設定")
    if "student_id" not in st.session_state: st.session_state["student_id"] = ""
    st.session_state["student_id"] = st.text_input("輸入學號 (Student ID)", value=st.session_state["student_id"])
    
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


# =====================================================
# UI 主介面 (Tabs)
# =====================================================
tabs_list = ["🏋️ 自主練習區", "📝 單元作業區"]
if st.session_state["is_ta"]:
    tabs_list.append("📊 助教後台 (分析)")

tabs = st.tabs(tabs_list)

# -----------------------------------------------------
# Tab 1: 自主練習 (Real Data Injection)
# -----------------------------------------------------
with tabs[0]:
    st.subheader("🏋️ 空間分析自主練習 (含實體資料)")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        # [UPDATED] UI 改為單元
        unit_str = c1.selectbox("選擇單元", ["全部"] + unit_options, key="p_unit")
        unit_val = int(unit_str) if unit_str != "全部" else None
        
        lvl = c2.selectbox("難度", ["入門", "進階"], key="p_lvl")
        qty = c3.selectbox("題型", ["簡答題", "實作題"], key="p_qty")
        
        if c4.button("🎲 GPT-4o 出題", type="primary", use_container_width=True):
            with st.spinner("AI 正在檢索講義並尋找合適的圖資..."):
                q_data = generate_practice_question_real_data(lvl, qty, unit_val)
                st.session_state["pq_data"] = q_data
                st.session_state["pq_meta"] = f"{unit_str} | {lvl} | {qty}"
    
    if "pq_data" in st.session_state:
        q_data = st.session_state["pq_data"]
        q_content = q_data.get("question_content", "")
        target_file = q_data.get("target_filename")
        style = q_data.get("style_used", "")

        st.markdown(f"### 📌 題目 [{st.session_state['pq_meta']}]")
        st.caption(f"風格：{style}")
        st.info(q_content)

        # 下載按鈕 (Real Data)
        if target_file and target_file != "None":
            # [UPDATED] 呼叫 get_unit_files
            files = get_unit_files(unit_val) if unit_val else []
            file_path = next((f['path'] for f in files if f['name'] == target_file), None)
            
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as fp:
                    st.download_button(
                        label=f"📥 下載練習圖資 ({target_file})",
                        data=fp,
                        file_name=target_file,
                        mime="application/octet-stream"
                    )
            else:
                if unit_val: st.warning(f"⚠️ 題目提到的檔案 '{target_file}' 未在單元 {unit_val} 資料夾中找到。")
        
        # 作答區
        sid = st.session_state["student_id"]
        ans = st.text_area("作答區", height=150, key="p_ans", disabled=not sid, placeholder="請先輸入學號..." if not sid else "輸入答案或程式碼...")
        
        if st.button("送出批改 (GPT-4o)", key="p_sub", disabled=not ans):
            with st.spinner("批改中..."):
                fb = grade_submission(q_content, ans, unit_val)
                log_practice(sid, unit_val, q_content, fb)
                st.success(f"分數: {fb.get('score')}")
                with st.expander("查看完整評語", expanded=True):
                    st.json(fb)

# -----------------------------------------------------
# Tab 2: 單元作業 (Assignments)
# -----------------------------------------------------
with tabs[1]:
    st.subheader("📝 單元作業繳交")
    
    # [UPDATED] UI 顯示 Unit
    target_unit = st.selectbox("選擇作業單元", options=sorted(ASSIGNMENTS_DB.keys()), format_func=lambda x: f"Unit {x}")
    assignment = ASSIGNMENTS_DB.get(target_unit)
    
    if assignment:
        st.markdown(f"### {assignment['title']}")
        st.caption(f"📅 截止期限: {assignment['deadline']}")
        st.info(assignment['description'])
        
        sid = st.session_state["student_id"]
        
        if not sid:
            st.warning("請先在側邊欄輸入學號以檢視繳交狀態。")
        else:
            prev_sub = get_student_submission(sid, assignment['id'])
            
            if prev_sub:
                score, fb_json = prev_sub
                st.success(f"✅ 已繳交。分數：{score} / 10")
                with st.expander("查看上次批改結果"):
                    st.json(json.loads(fb_json))
                st.write("**如需重交，請在下方重新輸入：**")
            
            assign_ans = st.text_area("作業作答區", height=250, key=f"assign_ans_{target_unit}")
            
            if st.button(f"繳交 Unit {target_unit} 作業", type="primary", disabled=not assign_ans):
                with st.spinner("作業上傳與自動批改中..."):
                    fb = grade_submission(assignment['description'], assign_ans, target_unit)
                    log_assignment_submission(assignment['id'], sid, target_unit, assign_ans, fb)
                    st.balloons()
                    st.success(f"繳交成功！AI 預評分：{fb.get('score')}")
                    st.rerun()
    else:
        st.info("該單元目前沒有發布作業。")

# -----------------------------------------------------
# Tab 3: 助教後台 (Analysis Dashboard)
# -----------------------------------------------------
if st.session_state["is_ta"] and len(tabs) > 2:
    with tabs[2]:
        st.subheader("📊 助教管理後台")
        
        # 1. AI 弱點分析
        with st.container(border=True):
            st.markdown("### 🤖 AI 教學顧問報告 (GPT-4o)")
            # [UPDATED] UI 改為單元
            ana_unit_str = st.selectbox("分析單元", unit_options, key="ana_unit")
            if st.button("生成弱點分析報告", type="primary"):
                if ana_unit_str:
                    report = generate_weakness_report(int(ana_unit_str))
                    st.markdown(report)
                else:
                    st.warning("請選擇單元")

        st.markdown("---")

        # 2. 數據表與加分
        st.markdown("### 📝 作答紀錄與加分")
        df = read_history_join_bonus()
        if not df.empty:
            # 簡單篩選 (Unit)
            f_unit = st.multiselect("篩選單元", sorted(df['unit_id'].dropna().unique()))
            if f_unit: df = df[df['unit_id'].isin(f_unit)]
            
            event = st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                height=300
            )
            
            if len(event.selection.rows) > 0:
                idx = event.selection.rows[0]
                row = df.iloc[idx]
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