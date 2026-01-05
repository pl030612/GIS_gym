import os
import json
import glob
import sqlite3
import random
import re
import docx2txt  # pip install docx2txt
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import altair as alt

from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


# =====================================================
# 0) 參數設定 & 語言包 (Settings & i18n)
# =====================================================

# 各單元截止日期 (可視需求調整)
UNIT_DEADLINES = {
    1: "2025-09-30",
    2: "2025-10-07",
    3: "2025-10-14",
    4: "2025-10-21",
    5: "2025-10-28",
    6: "2025-11-04",
    7: "2025-11-11",
    8: "2025-11-18",
    9: "2025-11-25",
    10: "2025-12-02"
}
DEFAULT_DEADLINE = "2025-12-31"

# 介面翻譯字典 (UI Translations)
TRANSLATIONS = {
    "zh": {
        "page_title": "GIS Gym｜空間分析 AI 助教平台",
        "caption": "自主練習 (Real Data) | 單元作業 (Assignments) | 助教分析 (AI Consultant)",
        "sidebar_user": "👤 使用者設定",
        "label_student_id": "輸入學號",
        "ta_login": "🔒 助教登入",
        "ta_mode": "👨‍🏫 助教模式",
        "btn_login": "登入",
        "btn_logout": "登出",
        "tab_practice": "自主練習",
        "tab_assignment": "單元作業",
        "tab_ta": "助教後台",
        
        # Practice Tab
        "sel_unit": "選擇單元",
        "sel_level": "難度",
        "sel_type": "題型",
        "opt_all": "全部",
        "opt_intro": "入門",
        "opt_adv": "進階",
        "opt_short": "簡答題",
        "opt_coding": "實作題",
        "btn_generate": "產生題目",
        "header_q": "題目",
        "expander_hint": "💡 提示 (Hint)",
        "btn_download_data": "📥 下載練習圖資",
        "placeholder_ans": "輸入答案...",
        "btn_submit": "送出批改",
        "expander_feedback": "批改結果",
        "feedback_score": "🎯 得分：",
        "feedback_pros": "✅ 優點",
        "feedback_cons": "⚠️ 弱點",
        "feedback_sug": "💡 建議",
        
        # Assignment Tab
        "no_assign_file": "📂 目前沒有掃描到任何作業檔案 (homework/assignment*.docx)。",
        "sel_assign_unit": "選擇作業單元",
        "header_assign_desc": "作業說明",
        "label_deadline": "📅 截止期限:",
        "header_assign_data": "📂 相關圖資下載",
        "no_data_file": "（此單元無實體檔案可供下載）",
        "msg_submitted": "✅ 已繳交。分數：",
        "btn_submit_assign": "繳交 Unit {} 作業",
        
        # TA Tab
        "header_ta_report": "AI 教學顧問報告",
        "btn_gen_report": "生成分析報告",
        "header_prac_history": "自主練習紀錄 (Practice)",
        "btn_dl_csv": "📥 下載紀錄 (.csv)",
        "header_assign_history": "作業繳交檢視 (Submissions)",
        "col_weakness": "弱點",
        "msg_no_data": "無資料",
        "msg_edit_bonus": "編輯加分: ID {} ({})",
        "btn_update": "更新"
    },
    "en": {
        "page_title": "GIS Gym | Spatial Analysis AI Tutor",
        "caption": "Self-Practice (Real Data) | Assignments | TA Analysis",
        "sidebar_user": "👤 User Settings",
        "label_student_id": "Student ID",
        "ta_login": "🔒 TA Login",
        "ta_mode": "👨‍🏫 TA Mode",
        "btn_login": "Login",
        "btn_logout": "Logout",
        "tab_practice": "Practice",
        "tab_assignment": "Assignments",
        "tab_ta": "TA Dashboard",
        
        # Practice Tab
        "sel_unit": "Unit",
        "sel_level": "Level",
        "sel_type": "Type",
        "opt_all": "All",
        "opt_intro": "Introductory",
        "opt_adv": "Advanced",
        "opt_short": "Short Answer",
        "opt_coding": "Practical (R Code)",
        "btn_generate": "Generate Question",
        "header_q": "Question",
        "expander_hint": "💡 Hint",
        "btn_download_data": "📥 Download Data",
        "placeholder_ans": "Your answer...",
        "btn_submit": "Submit for Grading",
        "expander_feedback": "Feedback Result",
        "feedback_score": "🎯 Score:",
        "feedback_pros": "✅ Strengths",
        "feedback_cons": "⚠️ Weaknesses",
        "feedback_sug": "💡 Suggestions",
        
        # Assignment Tab
        "no_assign_file": "📂 No assignment files found (homework/assignment*.docx).",
        "sel_assign_unit": "Select Unit",
        "header_assign_desc": "Instructions",
        "label_deadline": "📅 Deadline:",
        "header_assign_data": "📂 Related Datasets",
        "no_data_file": "(No files available for this unit)",
        "msg_submitted": "✅ Submitted. Score:",
        "btn_submit_assign": "Submit Unit {} Assignment",
        
        # TA Tab
        "header_ta_report": "AI Consultant Report",
        "btn_gen_report": "Generate Report",
        "header_prac_history": "Practice History",
        "btn_dl_csv": "📥 Download (.csv)",
        "header_assign_history": "Assignment Submissions",
        "col_weakness": "Weaknesses",
        "msg_no_data": "No Data",
        "msg_edit_bonus": "Edit Bonus: ID {} ({})",
        "btn_update": "Update"
    }
}


# =====================================================
# 1) Streamlit 基本設定
# =====================================================
st.set_page_config(page_title="GIS Gym", page_icon="🧪", layout="wide")

# 初始化語言設定
if "language" not in st.session_state:
    st.session_state["language"] = "zh"

# 取得當前語言包
T = TRANSLATIONS[st.session_state["language"]]

st.title(f"🧪 {T['page_title']}")
st.caption(T['caption'])


# =====================================================
# 2) OpenAI API Key & Client
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
# 3) 路徑設定
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LECTURES_DIR = os.path.join(BASE_DIR, "lectures")
FAISS_DIR = os.path.join(BASE_DIR, "GeoGIS_faiss_db")
DB_PATH = os.path.join(BASE_DIR, "learning_history.sqlite")


# =====================================================
# 4) SQLite 初始化
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
# 5) 資料載入：Metadata、真實檔案、Word作業
# =====================================================
@st.cache_data(show_spinner=False)
def load_all_metadata():
    if not os.path.exists(LECTURES_DIR): return []
    files = glob.glob(os.path.join(LECTURES_DIR, "**", "metadata.json"), recursive=True)
    out = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
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

@st.cache_data(ttl=900, show_spinner="Scanning assignments...")
def scan_assignments_from_files(lang_code):
    """
    動態掃描 Word 作業檔 (支援多語系)
    lang_code: 'zh' 或 'en'
    邏輯：若 lang='en'，優先找 *_en.docx，找不到則 fallback 找 .docx
    """
    assignments_db = {}
    if not os.path.exists(LECTURES_DIR): return {}

    folders = sorted([f for f in os.listdir(LECTURES_DIR) if os.path.isdir(os.path.join(LECTURES_DIR, f))])
    
    for folder in folders:
        match = re.match(r"^(\d+)[_]", folder)
        if not match: continue
        unit_id = int(match.group(1))
        
        folder_path = os.path.join(LECTURES_DIR, folder)
        sub_assign_dir = os.path.join(folder_path, "assignments")
        
        search_dirs = []
        if os.path.exists(sub_assign_dir): search_dirs.append(sub_assign_dir)
        search_dirs.append(folder_path)
        
        target_file = None
        
        # 遍歷搜尋目錄
        for d in search_dirs:
            if not os.path.exists(d): continue
            files = os.listdir(d)
            
            # 1. 嘗試尋找精確匹配 (例如 homework_en.docx)
            if lang_code == 'en':
                for f in files:
                    if (f.lower().startswith("homework") or f.lower().startswith("assignment")) and "_en.docx" in f.lower():
                        target_file = os.path.join(d, f)
                        break
            
            # 2. 如果沒找到 (或不是 en)，找一般檔案 (fallback)
            if not target_file:
                for f in files:
                    if (f.lower().startswith("homework") or f.lower().startswith("assignment")) and f.endswith(".docx") and "_en.docx" not in f.lower():
                        target_file = os.path.join(d, f)
                        break
            
            if target_file: break
        
        if target_file:
            try:
                content = docx2txt.process(target_file)
                deadline = UNIT_DEADLINES.get(unit_id, DEFAULT_DEADLINE)
                assignments_db[unit_id] = {
                    "id": 1000 + unit_id,
                    "title": f"Unit {unit_id}", # Title 簡化，內容在 description
                    "description": content if content.strip() else "(Empty File)",
                    "deadline": deadline 
                }
            except Exception as e:
                print(f"Error reading docx {target_file}: {e}")
                
    return assignments_db

# 根據當前語言載入作業
ASSIGNMENTS_DB = scan_assignments_from_files(st.session_state["language"])


# =====================================================
# 6) FAISS 與 RAG 核心
# =====================================================
def ensure_vectorstore_loaded():
    if "vectorstore" in st.session_state and st.session_state["vectorstore"] is not None:
        return st.session_state["vectorstore"]
    if not os.path.exists(FAISS_DIR): return None
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
        vs = FAISS.load_local(FAISS_DIR, embeddings, allow_dangerous_deserialization=True)
        st.session_state["vectorstore"] = vs
        return vs
    except Exception as e:
        st.error(f"VectorStore Error: {e}")
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
# 7) AI 功能：GPT-4o (雙語版)
# =====================================================
def generate_practice_question_real_data(level: str, qtype: str, unit_id: int | None, lang: str) -> dict:
    q_str = f"Unit {unit_id}" if unit_id else ""
    seed = f"{q_str} spatial analysis {qtype} {level}"
    context = _retrieve_context(seed, unit_id=unit_id)
    
    # 雙語技能對照表
    SKILLS_DB = {
        "zh": {
            1: ["資料讀取與檢視 (st_read, glimpse)", "基礎繪圖 (plot, tmap)", "屬性篩選 (filter, select)"],
            2: ["座標系統轉換 (st_transform)", "CRS 定義與檢查 (st_crs)", "屬性資料處理 (mutate, group_by)"],
            3: ["幾何計算 (st_area, st_length)", "空間資料輸出 (st_write)", "向量資料裁切 (st_crop)"],
            4: ["緩衝區分析 (st_buffer)", "幾何中心點 (st_centroid)", "邊界方框 (st_bbox)"],
            5: ["疊圖分析/交集 (st_intersection)", "聯集與差異 (st_union, st_difference)", "空間篩選 (st_filter)"],
            6: ["空間連結 (st_join)", "屬性合併 (left_join)", "點位計數 (Point in Polygon)"],
            7: ["距離矩陣計算 (st_distance)", "最近鄰分析 (Nearest Neighbor)", "環域分析"],
            8: ["密度分析 (Kernel Density)", "熱區圖繪製", "網格分析 (Grid Analysis)"],
            9: ["空間自相關 (Moran's I)", "熱點分析 (Hot Spot Analysis)", "空間權重矩陣"],
            10: ["進階地圖視覺化 (Interactive Maps)", "三維空間分析", "綜合應用"]
        },
        "en": {
            1: ["Data Loading & Inspection (st_read, glimpse)", "Basic Plotting (plot, tmap)", "Attribute Filtering (filter, select)"],
            2: ["CRS Transformation (st_transform)", "CRS Definition (st_crs)", "Attribute Manipulation (mutate, group_by)"],
            3: ["Geometry Calculation (st_area, st_length)", "Data Export (st_write)", "Vector Clipping (st_crop)"],
            4: ["Buffer Analysis (st_buffer)", "Centroids (st_centroid)", "Bounding Box (st_bbox)"],
            5: ["Intersection/Overlay (st_intersection)", "Union & Difference (st_union, st_difference)", "Spatial Filter (st_filter)"],
            6: ["Spatial Join (st_join)", "Attribute Join (left_join)", "Point in Polygon"],
            7: ["Distance Matrix (st_distance)", "Nearest Neighbor Analysis", "Ring Analysis"],
            8: ["Kernel Density Estimation", "Heatmap Visualization", "Grid Analysis"],
            9: ["Spatial Autocorrelation (Moran's I)", "Hot Spot Analysis", "Spatial Weights Matrix"],
            10: ["Interactive Maps", "3D Spatial Analysis", "Comprehensive Application"]
        }
    }
    
    # 選擇對應語言的技能池
    unit_skills = SKILLS_DB.get(lang, SKILLS_DB["zh"])

    if unit_id and unit_id in unit_skills:
        current_skills = unit_skills[unit_id]
        selected_method = random.choice(current_skills)
    else:
        all_skills = [item for sublist in unit_skills.values() for item in sublist]
        selected_method = random.choice(all_skills)

    # 雙語 System Prompt 設定
    if lang == "en":
        sys_role = "You are an expert GIS Teaching Assistant. Use GPT-4o logic to create questions."
        core_point = f"🔥 **Core Concept: {selected_method}**"
        r_rules = """
        ⚠️ Hard Constraints:
        1. Implementation must be in **R language** (sf, terra, tmap, tidyverse).
        2. 🚫 Do NOT mention 'ArcGIS', 'QGIS' or generic 'GIS software'.
        3. Guide students to write R code.
        """
        task_instruction = f"Task Type: {qtype}. Difficulty: {level}."
        hint_label = "hint"
        q_content_label = "question_content"
        target_file_label = "target_filename"
        json_req = "Please respond in JSON format:"
    else:
        sys_role = "你是頂尖的空間分析助教。請使用 GPT-4o 的強大邏輯來出題。"
        core_point = f"🔥 **本次題目核心考點：{selected_method}**"
        r_rules = """
        ⚠️ 嚴格限制：
        1. 實作內容必須限定使用 **R 語言** (例如使用 sf, terra, tmap, tidyverse 等套件)。
        2. 🚫 禁止提及 "ArcGIS", "QGIS" 或通用的 "GIS 軟體" 字眼。
        3. 題目應引導學生寫出 R 程式碼來解決問題。
        """
        task_instruction = f"目前的題型任務是：【{qtype}】。難度：{level}。"
        hint_label = "hint"
        q_content_label = "question_content"
        target_file_label = "target_filename"
        json_req = "請以 JSON 格式回傳："

    # 實作題/簡答題指令區分 (中英通用邏輯，微調文字即可，這裡簡化處理)
    real_files = get_unit_files(unit_id) if unit_id else []
    file_names_str = ", ".join([f['name'] for f in real_files]) if real_files else "None"

    if qtype in ["實作題", "Practical (R Code)"]:
        system_instruction = f"""
        You must choose a file from the list to design a task: [{file_names_str}]
        {r_rules}
        """
        target_file_instruction = "AI selected filename (must be from list)"
    else:
        system_instruction = f"""
        Conceptual Short Answer Question.
        ❌ Do not ask for file operations.
        ✅ Focus on spatial analysis concepts.
        """
        target_file_instruction = "None"

    system_prompt = f"""
    {sys_role}
    {task_instruction}
    {core_point}
    
    {system_instruction}
    
    {json_req}
    {{
        "{q_content_label}": "Question content (Markdown)...",
        "{hint_label}": "Hint for students...",
        "{target_file_label}": "{target_file_instruction}"
    }}
    """
    
    user_prompt = f"Design a question. [Context] {context}"

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
        return {"question_content": f"Error: {e}", "target_filename": None, "hint": ""}


def grade_submission(question_text: str, student_answer: str, unit_id: int | None, lang: str) -> dict:
    context = _retrieve_context(question_text, unit_id=unit_id, k=10)
    
    if lang == "en":
        prompt = f"""
        [Role] Strict but fair GIS TA (R Language Expert).
        [Question] {question_text}
        [Answer] {student_answer}
        [Context] {context}
        
        Respond in JSON:
        {{
          "score": (0-10),
          "level": "Excellent/Good/Fair/Poor",
          "strengths": ["Point 1", "Point 2"],
          "weaknesses": ["Point 1", "Point 2"],
          "suggestions": ["Suggestion 1", "Suggestion 2"]
        }}
        
        ⚠️ Criteria:
        1. Give **10 points** if the answer is correct and logical. Do not be stingy.
        2. Focus on R syntax and spatial logic correctness.
        """
    else:
        prompt = f"""
        [角色] 嚴格但公正的空間分析助教 (R 語言專家)。
        [題目] {question_text}
        [學生回答] {student_answer}
        [講義依據] {context}
        
        請以 JSON 回傳批改結果：
        {{
          "score": (0-10),
          "level": "Excellent/Good/Fair/Poor",
          "strengths": ["優點1", "優點2"],
          "weaknesses": ["缺點1", "缺點2"],
          "suggestions": ["建議1", "建議2"]
        }}
        
        ⚠️ 評分標準：
        1. 若回答完全正確、邏輯清晰且符合題目要求，請給予 **10 分**，不要吝嗇。
        2. 若程式碼語法正確但邏輯有小瑕疵，給 8-9 分。
        3. 專注於 R 語法與空間邏輯的正確性。
        """
        
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"score": 0, "weaknesses": ["System Error"], "suggestions": [str(e)]}

def generate_weakness_report(unit_id: int):
    # 此功能較為進階，暫時維持中文或簡單英文，視需求可再擴充
    conn = sqlite3.connect(DB_PATH)
    df_p = pd.read_sql("SELECT feedback_json FROM learning_history WHERE unit_id=?", conn, params=(unit_id,))
    df_a = pd.read_sql("SELECT feedback_json FROM submissions WHERE unit_id=?", conn, params=(unit_id,))
    conn.close()
    
    feedbacks = pd.concat([df_p['feedback_json'], df_a['feedback_json']]).dropna()
    if feedbacks.empty: return "⚠️ No sufficient data."

    all_weaknesses = []
    for json_str in feedbacks:
        try:
            data = json.loads(json_str)
            if 'weaknesses' in data: all_weaknesses.extend(data['weaknesses'])
        except: pass
    
    if not all_weaknesses: return "⚠️ No weaknesses recorded."

    weakness_text = "\n".join(all_weaknesses[:60])
    
    # 根據當前語言選擇 Prompt
    lang = st.session_state["language"]
    if lang == "en":
        prompt = f"""
        You are an Educational Consultant. Analyze the following student weaknesses for Unit {unit_id} (R GIS):
        {weakness_text}
        
        Produce a Markdown report:
        1. **🚨 Top 3 Core Weaknesses**
        2. **👨‍🏫 Teaching Suggestions**
        3. **📝 Recommended Exam Questions (2 questions, R code)**
        """
    else:
        prompt = f"""
        你是教學顧問。以下是 Unit {unit_id} 學生常犯錯誤列表 (R 語言環境)：
        {weakness_text}
        
        請使用 GPT-4o 製作 Markdown 報告：
        1. **🚨 Top 3 核心弱點**
        2. **👨‍🏫 教學加強建議**
        3. **📝 推薦考題 (2題，R語言實作)**
        """
        
    with st.spinner("🤖 AI analyzing..."):
        r = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content


# =====================================================
# 8) DB Log Functions
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
    SELECT lh.id, lh.timestamp, lh.student_id, lh.unit_id, lh.score, lh.question, lh.feedback_json,
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

def read_submissions_all() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM submissions ORDER BY id DESC", conn)
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
# 9) UI Helper Functions
# =====================================================
def display_feedback_ui(fb, t_dict):
    """
    自訂評分顯示 UI (支援多語系)
    """
    if not fb: return
    
    st.markdown(f"### {t_dict['feedback_score']} {fb.get('score', 0)} / 10")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### {t_dict['feedback_pros']}")
        strengths = fb.get('strengths', [])
        if strengths:
            for i, s in enumerate(strengths, 1):
                st.markdown(f"**{i}.** {s}")
        else:
            st.write("-")
            
    with c2:
        st.markdown(f"#### {t_dict['feedback_cons']}")
        weaknesses = fb.get('weaknesses', [])
        if weaknesses:
            for i, w in enumerate(weaknesses, 1):
                st.markdown(f"**{i}.** {w}")
        else:
            st.write("-")
    
    st.markdown(f"#### {t_dict['feedback_sug']}")
    suggestions = fb.get('suggestions', [])
    if suggestions:
        for i, s in enumerate(suggestions, 1):
            st.markdown(f"**{i}.** {s}")
    else:
        st.write("-")

def extract_weaknesses(val):
    try:
        if not val: return ""
        d = json.loads(val)
        w = d.get("weaknesses", [])
        if isinstance(w, list):
            return "; ".join([f"{i+1}. {x}" for i, x in enumerate(w)])
        return str(w)
    except:
        return ""


# =====================================================
# 10) 助教權限與 Sidebar UI (含語言切換)
# =====================================================
with st.sidebar:
    # 語言切換器 (放在最上面)
    st.markdown("### 🌐 Language")
    lang_choice = st.radio(
        "Select Language:",
        ("繁體中文", "English"),
        index=0 if st.session_state["language"] == "zh" else 1,
        label_visibility="collapsed"
    )
    
    # 更新 Session State
    new_lang = "zh" if lang_choice == "繁體中文" else "en"
    if new_lang != st.session_state["language"]:
        st.session_state["language"] = new_lang
        st.rerun() # 立即刷新頁面以套用新語言

    # 重新載入對應語言的作業 DB
    ASSIGNMENTS_DB = scan_assignments_from_files(st.session_state["language"])

    st.markdown("---")
    
    st.header(T['sidebar_user'])
    if "student_id" not in st.session_state: st.session_state["student_id"] = ""
    st.session_state["student_id"] = st.text_input(T['label_student_id'], value=st.session_state["student_id"])
    
    st.markdown("---")
    if "is_ta" not in st.session_state: st.session_state["is_ta"] = False
    
    if not st.session_state["is_ta"]:
        with st.expander(T['ta_login']):
            u = st.text_input("ID", key="ta_u")
            p = st.text_input("PW", type="password", key="ta_p")
            if st.button(T['btn_login']):
                if u == "ta" and p == "gisgym2025!":
                    st.session_state["is_ta"] = True
                    st.rerun()
                else:
                    st.error("Error")
    else:
        st.success(T['ta_mode'])
        if st.button(T['btn_logout']):
            st.session_state["is_ta"] = False
            st.rerun()

# Tabs
tabs_list = [T['tab_practice'], T['tab_assignment']]
if st.session_state["is_ta"]: tabs_list.append(T['tab_ta'])
tabs = st.tabs(tabs_list)

# -----------------------------------------------------
# Tab 1: Practice (自主練習)
# -----------------------------------------------------
with tabs[0]:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1], vertical_alignment="bottom")
        
        # 處理下拉選單的顯示與內部值對應
        unit_str = c1.selectbox(T['sel_unit'], [T['opt_all']] + unit_options, key="p_unit")
        unit_val = int(unit_str) if unit_str != T['opt_all'] else None
        
        lvl_map = {T['opt_intro']: "入門", T['opt_adv']: "進階", "Introductory": "入门", "Advanced": "进阶"} 
        # 上面 map 只是簡單處理，實際上這裡傳給 AI 的要是中文或英文
        # 為了簡化，直接將顯示值傳給 function，function 內部會自動處理
        lvl_display = c2.selectbox(T['sel_level'], [T['opt_intro'], T['opt_adv']], key="p_lvl")
        
        type_display = c3.selectbox(T['sel_type'], [T['opt_short'], T['opt_coding']], key="p_qty")
        
        if c4.button(T['btn_generate'], type="primary", use_container_width=True): 
            with st.spinner("AI thinking..."):
                # 呼叫出題函數，傳入語言參數
                q_data = generate_practice_question_real_data(
                    lvl_display, type_display, unit_val, st.session_state["language"]
                )
                st.session_state["pq_data"] = q_data
                st.session_state["pq_meta"] = f"{unit_str} | {lvl_display} | {type_display}"
                st.session_state["p_ans"] = "" 
                st.session_state["q_counter"] = st.session_state.get("q_counter", 0) + 1
    
    if "pq_data" in st.session_state:
        q_data = st.session_state["pq_data"]
        q_content = q_data.get("question_content", "")
        q_hint = q_data.get("hint", "")
        target_file = q_data.get("target_filename")

        st.markdown(f"### {T['header_q']} [{st.session_state['pq_meta']}]") 
        st.info(q_content)

        if q_hint:
            suffix = "\u200b" * st.session_state.get("q_counter", 0)
            with st.expander(f"{T['expander_hint']}{suffix}", expanded=False):
                st.markdown(q_hint)

        if target_file and target_file != "None" and target_file is not None:
            files = get_unit_files(unit_val) if unit_val else []
            file_path = next((f['path'] for f in files if f['name'] == target_file), None)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as fp:
                    st.download_button(f"{T['btn_download_data']} ({target_file})", fp, target_file)
        
        sid = st.session_state["student_id"]
        ans = st.text_area("Answer", height=150, key="p_ans", disabled=not sid, placeholder=T['placeholder_ans'])
        
        if st.button(T['btn_submit'], key="p_sub", disabled=not ans):
            with st.spinner("Grading..."):
                fb = grade_submission(q_content, ans, unit_val, st.session_state["language"])
                log_practice(sid, unit_val, q_content, fb)
                st.success(f"{T['feedback_score']} {fb.get('score')}")
                with st.expander(T['expander_feedback'], expanded=True): 
                    display_feedback_ui(fb, T)

# -----------------------------------------------------
# Tab 2: Assignments (單元作業)
# -----------------------------------------------------
with tabs[1]:
    if not ASSIGNMENTS_DB:
        st.info(T['no_assign_file'])
    else:
        target_unit = st.selectbox(T['sel_assign_unit'], options=sorted(ASSIGNMENTS_DB.keys()), format_func=lambda x: f"Unit {x}")
        assignment = ASSIGNMENTS_DB.get(target_unit)
        
        if assignment:
            st.markdown(f"### {T['header_assign_desc']}") 
            st.caption(f"{T['label_deadline']} {assignment['deadline']}")
            st.markdown(assignment['description'])
            
            st.markdown(f"#### {T['header_assign_data']}")
            real_files = get_unit_files(target_unit)
            if real_files:
                cols = st.columns(len(real_files)) if len(real_files) < 4 else st.columns(4)
                for i, f in enumerate(real_files):
                    with cols[i % 4]:
                        with open(f['path'], "rb") as fp:
                            st.download_button(f"📥 {f['name']}", fp, f['name'])
            else:
                st.caption(T['no_data_file'])
            
            st.divider()

            sid = st.session_state["student_id"]
            if not sid:
                st.warning(f"Please enter {T['label_student_id']} in sidebar.")
            else:
                prev = get_student_submission(sid, assignment['id'])
                if prev:
                    st.success(f"{T['msg_submitted']} {prev[0]}")
                    with st.expander(T['expander_feedback']): 
                        display_feedback_ui(json.loads(prev[1]), T)
                    st.write("---")
                
                assign_ans = st.text_area("Answer Area", height=250, key=f"assign_ans_{target_unit}")
                if st.button(T['btn_submit_assign'].format(target_unit), type="primary", disabled=not assign_ans):
                    with st.spinner("Submitting..."):
                        fb = grade_submission(assignment['description'], assign_ans, target_unit, st.session_state["language"])
                        log_assignment_submission(assignment['id'], sid, target_unit, assign_ans, fb)
                        st.balloons()
                        st.success(f"Success! Score: {fb.get('score')}")
                        st.rerun()

# -----------------------------------------------------
# Tab 3: TA Dashboard (助教後台)
# -----------------------------------------------------
if st.session_state["is_ta"] and len(tabs) > 2:
    with tabs[2]:
        with st.container(border=True):
            st.markdown(f"### {T['header_ta_report']}") 
            ana_unit = st.selectbox("Unit", unit_options, key="ana_unit")
            if st.button(T['btn_gen_report']):
                if ana_unit:
                    report = generate_weakness_report(int(ana_unit))
                    st.markdown(report)
        
        st.markdown("---")
        
        # Practice History
        st.markdown(f"### {T['header_prac_history']}") 
        df = read_history_join_bonus()
        if not df.empty:
            df["weakness"] = df["feedback_json"].apply(extract_weaknesses)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(T['btn_dl_csv'], csv, "practice_history.csv", "text/csv")
            
            f_unit = st.multiselect("Filter Unit", sorted(df['unit_id'].dropna().unique()), key="f_unit_prac")
            if f_unit: df = df[df['unit_id'].isin(f_unit)]
            
            target_order_prac = ["timestamp", "student_id", "unit_id", "score", "weakness", "question"]
            display_cols_prac = [c for c in target_order_prac if c in df.columns]
            
            event = st.dataframe(df[display_cols_prac], use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", height=300)
            
            if len(event.selection.rows) > 0:
                row = df.iloc[event.selection.rows[0]]
                st.info(T['msg_edit_bonus'].format(row['id'], row['student_id']))
                with st.form("bonus"):
                    c1, c2 = st.columns([1, 3])
                    nb = c1.number_input("Bonus", value=int(row['bonus']))
                    nn = c2.text_input("Note", value=str(row['bonus_note'] or ""))
                    if st.form_submit_button(T['btn_update']):
                        upsert_bonus(int(row['id']), nb, nn)
                        st.rerun()
        else:
            st.info(T['msg_no_data'])

        st.markdown("---")

        # Assignment Submissions
        st.markdown(f"### {T['header_assign_history']}") 
        df_sub = read_submissions_all()
        if not df_sub.empty:
            df_sub["weakness"] = df_sub["feedback_json"].apply(extract_weaknesses)

            csv_sub = df_sub.to_csv(index=False).encode('utf-8-sig')
            st.download_button(T['btn_dl_csv'], csv_sub, "assignment_submissions.csv", "text/csv")

            f_unit_sub = st.multiselect("Filter Unit (Assign)", sorted(df_sub['unit_id'].dropna().unique()), key="f_unit_sub")
            if f_unit_sub: df_sub = df_sub[df_sub['unit_id'].isin(f_unit_sub)]

            target_order = ["timestamp", "student_id", "unit_id", "score", "weakness", "answer"]
            display_cols = [c for c in target_order if c in df_sub.columns]
            
            st.dataframe(df_sub[display_cols], use_container_width=True, hide_index=True, height=300)
        else:
            st.info(T['msg_no_data'])