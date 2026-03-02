import os
import json
import glob
import random
import re
import docx2txt
import smtplib
import gspread
import uuid
import time
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from pathlib import Path
import psutil

import streamlit as st
import pandas as pd
import altair as alt

from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


# =====================================================
# 0) 參數設定 & 語言包 & 單元備註
# =====================================================

GOOGLE_SHEET_NAME = "GIS_Gym_Database" 
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1n-tYLLiwX1-iewjFJSXii2jfTCS1qyyDoAAQO1PD8-Y/edit?usp=sharing"

# 學生白名單
ALLOWED_STUDENTS = [
    "D14228004", "R14228004", "R14228008", "R14228016", "R14228022", 
    "R14228023", "R11228022", "R13228003", "R13228021", "R13341004", 
    "R13343001", "R14521610", "R14521813", "R14622035", "R13847026", 
    "B11103010", "B11106012", "B10107021", "B12204023", "B12204038", 
    "B11204022", "B12208025", "B13208001", "B13208002", "B13208004", 
    "B13208006", "B13208007", "B13208008", "B13208009", "B13208011", 
    "B13208012", "B13208013", "B13208014", "B13208015", "B13208016", 
    "B13208017", "B13208018", "B13208019", "B13208020", "B13208022", 
    "B13208023", "B13208025", "B13208027", "B13208028", "B13208029", 
    "B13208030", "B13208031", "B13208032", "B13208033", "B13208034", 
    "B13208035", "B13208036", "B13208037", "B13208038", "B13208039", 
    "B13302311", "B11103052", "B11208021", "B12103013", "B12208011", 
    "B12208036", "B12208042", "B12208043", "B11208028", "41144042S", 
    "41123113L", "TA2026"
]

# 完整雙語單元備註
UNIT_NOTES = {
    1: {
        "zh": "ℹ️ 本單元圖資編碼為 Big5。",
        "en": "ℹ️ Data encoding for this unit is Big5."
    },
    2: {
        "zh": "ℹ️ 本單元Taiwan_county、Taiwan_temple、Taiwan_town圖資編碼為UTF-8，其餘為 Big5。",
        "en": "ℹ️ Taiwan_county, Taiwan_temple, Taiwan_town are UTF-8. Others are Big5."
    },
    3: {
        "zh": "ℹ️ 本單元圖資編碼為 Big5。",
        "en": "ℹ️ Data encoding for this unit is Big5."
    },
    4: {
        "zh": "ℹ️ 本單元Taiwan_hospital、Taiwan_village、Taiwan_town圖資編碼為UTF-8，其餘為 Big5。",
        "en": "ℹ️ Taiwan_hospital, Taiwan_village, Taiwan_town are UTF-8. Others are Big5."
    },
    5: {
        "zh": "ℹ️ 本單元圖資編碼為 Big5。",
        "en": "ℹ️ Data encoding for this unit is Big5."
    },
    6: {
        "zh": "ℹ️ 本單元School、Tainan_temple_mazhou、Taiwan_temple_mazhou、Taiwan_town圖資編碼為UTF-8，其餘為 Big5。",
        "en": "ℹ️ School, Tainan_temple_mazhou, Taiwan_temple_mazhou, Taiwan_town are UTF-8. Others are Big5."
    },
    7: {
        "zh": "ℹ️ 本單元School、Tainan_temple_mazhou圖資編碼為UTF-8，其餘為 Big5。",
        "en": "ℹ️ School, Tainan_temple_mazhou are UTF-8. Others are Big5."
    },
    8: {
        "zh": "ℹ️ 本單元School、Tainan_temple_mazhou圖資編碼為UTF-8，其餘為 Big5。",
        "en": "ℹ️ School, Tainan_temple_mazhou are UTF-8. Others are Big5."
    },
    9: {
        "zh": "ℹ️ 本單元Dengue_Case、KAOH_toen圖資編碼為UTF-8，其餘為 Big5。",
        "en": "ℹ️ Dengue_Case, KAOH_toen are UTF-8. Others are Big5."
    },
    10: {
        "zh": "ℹ️ 本單元Dengue_Case、KAOH_toen圖資編碼為UTF-8，其餘為 Big5。",
        "en": "ℹ️ Dengue_Case, KAOH_toen are UTF-8. Others are Big5."
    }
}

TRANSLATIONS = {
    "zh": {
        "page_title": "🔮 GIS Gym",
        "sidebar_user": "使用者設定",
        "label_student_id": "輸入學號",
        "ta_login": "助教登入",
        "ta_mode": "助教模式",
        "btn_login": "登入",
        "btn_logout": "登出",
        "tab_practice": "自主練習",
        "tab_assignment": "單元作業",
        "tab_ta": "助教後台",
        "sel_unit": "選擇單元",
        "sel_topic": "主題",
        "sel_level": "難度",
        "sel_type": "題型",
        "opt_all": "全部",
        "opt_intro": "入門",
        "opt_adv": "進階",
        "opt_short": "簡答題",
        "opt_coding": "實作題",
        "btn_generate": "產生題目",
        "header_q": "題目",
        "btn_show_hint": "🔍 查看提示",
        "header_hint": "提示內容",
        "btn_download_data": "下載圖資",
        "placeholder_ans": "輸入答案 (若是實作題請務必包含 R code)...",
        "btn_submit": "送出批改",
        "expander_feedback": "批改結果",
        
        "fb_score": "得分：", 
        "fb_rubric": "評分細項",
        "fb_strengths": "優點 ",
        "fb_weaknesses": "弱點",
        "col_crit": "評分標準",
        "col_pts": "得分",
        "col_max": "配分",
        "col_evi": "評語",
        
        "no_assign_file": "📂 目前沒有掃描到任何作業檔案。",
        "sel_assign_unit": "選擇作業單元",
        "header_assign_desc": "作業說明",
        "header_assign_data": "下載圖資",
        "no_data_file": "（此單元無實體檔案可供下載）",
        "msg_submitted": "已繳交。分數：",
        "btn_submit_assign": "繳交作業",
        "header_ta_report": "AI 教學顧問報告",
        "btn_gen_report": "生成分析報告",
        "header_prac_history": "自主練習紀錄",
        "btn_dl_csv": "下載紀錄 (.csv)",
        "header_assign_history": "作業繳交檢視",
        "msg_no_data": "無資料",
        "link_gsheet": "🔗 前往 Google Sheet 查看原始資料",
        "ta_filter_unit": "篩選單元：",
        "warning_no_id": "⚠️ 請先在左側欄位輸入學號！",
        "warning_not_allowed": "🚫 此學號未授權使用本系統，請聯繫助教。"
    },
    "en": {
        "page_title": "🔮 GIS Gym",
        "sidebar_user": "User Settings",
        "label_student_id": "Student ID",
        "ta_login": "TA Login",
        "ta_mode": "TA Mode",
        "btn_login": "Login",
        "btn_logout": "Logout",
        "tab_practice": "Practice",
        "tab_assignment": "Assignments",
        "tab_ta": "TA Dashboard",
        "sel_unit": "Unit",
        "sel_topic": "Topic",
        "sel_level": "Level",
        "sel_type": "Type",
        "opt_all": "All",
        "opt_intro": "Introductory",
        "opt_adv": "Advanced",
        "opt_short": "Short Answer",
        "opt_coding": "Practical (R Code)",
        "btn_generate": "Generate Question",
        "header_q": "Question",
        "btn_show_hint": "🔍 Show Hint",
        "header_hint": "Hint Content",
        "btn_download_data": "Download Data",
        "placeholder_ans": "Your answer (Must include R code for practical tasks)...",
        "btn_submit": "Submit for Grading",
        "expander_feedback": "Feedback Result",
        
        "fb_score": "Score:",
        "fb_rubric": "Rubric",
        "fb_strengths": "Strengths",
        "fb_weaknesses": "Weaknesses",
        "col_crit": "Criterion",
        "col_pts": "Points",
        "col_max": "Max",
        "col_evi": "Evidence",
        
        "no_assign_file": "No assignment files found.",
        "sel_assign_unit": "Select Unit",
        "header_assign_desc": "Instructions",
        "header_assign_data": "Download Data",
        "no_data_file": "(No files available)",
        "msg_submitted": "Submitted. Score:",
        "btn_submit_assign": "Submit Assignment",
        "header_ta_report": "AI Consultant Report",
        "btn_gen_report": "Generate Report",
        "header_prac_history": "Practice History",
        "btn_dl_csv": "Download (.csv)",
        "header_assign_history": "Assignment Submissions",
        "msg_no_data": "No Data",
        "link_gsheet": "🔗 Go to Google Sheet",
        "ta_filter_unit": "Filter Unit:",
        "warning_no_id": "⚠️ Please enter Student ID in sidebar first!",
        "warning_not_allowed": "🚫 Access Denied. Please contact TA."
    }
}

SKILLS_DB = {
    "zh": {
        1: ["資料讀取與檢視 (st_read)", "基礎繪圖 (plot, tmap)", "屬性篩選 (filter, select)", "t檢定 (t.test)", "機率分布 (Probability Distribution, pbinom)"],
        2: ["座標系統轉換 (st_transform)", "CRS 定義與檢查 (st_crs)", "屬性資料處理 (mutate, group_by)", "繪製面量圖 (tm_shape, tm_polygons)", "繪製統計圖表 (ggplot)"],
        3: ["幾何計算 (st_area)", "距離測量 (st_distance)", "空間連結 (st_join)", "緩衝區分析 (st_buffer)", "幾何中心點 (st_centroid)"],
        4: ["疊圖分析/交集 (st_intersection)", "網格建立 (st_make_grid)", "分群統計 (group_by, summarise)", "邊界方框 (st_bbox)"],
        5: ["計算平均中心點及中位數中心點 (calc_mnc, calc_mdc)", "標準距離偏差 (calc_sdd)", "標準差橢圓 (calc_sde)", "中心地理物件 (calc_cf)"],
        6: ["樣方分析 (quadrat.test)", "變異數與平均值比值 (var, mean, sqrt)", "二項分布 (Binomial distribution, dbinom)"],
        7: ["最近鄰分析 (Nearest Neighbor, nndist)", "G函數 (G(d) function, Gest)", "蒙地卡羅模擬檢定 (Monte Carlo Significance Test)"],
        8: ["F函數 (F(d) function, Fest)", "K函數 (Ripley's K function, Kest)", "邊緣校正 (Border Correction Methods)", "L函數 (L(d) function, Lest)"],
        9: ["空間自相關 (Spatial Autocorrelation)", "全域檢定及局部檢定 (Global & Local Methods)", "空間權重矩陣 (Spatial Weights Matrix)", "熱點分析 (Hot Spot Analysis)", "Moran's I統計量 (moran.test)", "群聚強度檢定 (G-statistics, globalG.test)"],
        10: ["空間相關局部指標 (Local Moran's I, localmoran)", "檢定G*的統計顯著性 (Local G-statistic, localG)", "熱區的統計顯著性校正 (FDR Correction, p.adjust)"]
    },
    "en": {
        1: ["Data Loading & Inspection (st_read)", "Basic Plotting (plot, tmap)", "Attribute Filtering (filter, select)", "T-test (t.test)", "Probability Distribution (pbinom)"],
        2: ["CRS Transformation (st_transform)", "CRS Check (st_crs)", "Attribute Manipulation (mutate, group_by)", "Choropleth Maps (tm_shape)", "Statistical Plots (ggplot)"],
        3: ["Geometry Calculation (st_area)", "Distance Measurement (st_distance)", "Spatial Join (st_join)", "Buffer Analysis (st_buffer)", "Geometric Centroid (st_centroid)"],
        4: ["Intersection (st_intersection)", "Grid Creation (st_make_grid)", "Group Statistics (summarise)", "Bounding Box (st_bbox)"],
        5: ["Mean/Median Center (calc_mnc, calc_mdc)", "Standard Distance Deviation (calc_sdd)", "Standard Deviational Ellipse (calc_sde)", "Central Feature (calc_cf)"],
        6: ["Quadrat Analysis (quadrat.test)", "Variance-Mean Ratio (VMR)", "Binomial Distribution (dbinom)"],
        7: ["Nearest Neighbor (nndist)", "G-function (Gest)", "Monte Carlo Significance Test"],
        8: ["F-function (Fest)", "K-function (Kest)", "Border Correction Methods", "L-function (Lest)"],
        9: ["Spatial Autocorrelation", "Global & Local Analysis Methods", "Spatial Weights Matrix", "Hot Spot Analysis", "Moran's I (moran.test)", "G-statistics (globalG.test)"],
        10: ["Local Moran's I (localmoran)", "Local G-statistic (localG)", "FDR Correction (p.adjust)"]
    }
}


# =====================================================
# 1) Streamlit 基本設定
# =====================================================
st.set_page_config(page_title="GIS Gym", page_icon="🔮", layout="wide")

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] div.block-container {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if "language" not in st.session_state:
    st.session_state["language"] = "zh"

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

T = TRANSLATIONS[st.session_state["language"]]

st.title(f"{T['page_title']}")


# =====================================================
# 2) OpenAI API
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
# 3) 資料連線與路徑
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LECTURES_DIR = os.path.join(BASE_DIR, "lectures")
FAISS_DIR = os.path.join(BASE_DIR, "GeoGIS_faiss_db")

@st.cache_resource
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Secrets 中找不到 [gcp_service_account] 設定，無法連線 Google Sheets。")
        return None
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Google Sheets 連線失敗: {e}")
        return None

def get_worksheet(sheet_name):
    client = get_gsheet_client()
    if not client: return None
    try:
        sh = client.open_by_url(GOOGLE_SHEET_URL)
        return sh.worksheet(sheet_name)
    except Exception as e:
        st.error(f"❌ 無法開啟試算表分頁 '{sheet_name}'。\n原因: {e}")
        return None

# =====================================================
# 4) 檔案與作業讀取
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
        except: pass
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
            if f.lower().endswith(('.shp', '.shx', '.dbf', '.csv', '.tif', '.geojson', '.zip', '.txt', '.sbx', '.sbn', '.prj', '.cpg', '.xml')):
                files_list.append({
                    "name": f,
                    "path": os.path.join(data_dir, f)
                })
    files_list.sort(key=lambda x: x['name'])
    return files_list

@st.cache_data(ttl=900, show_spinner="Scanning assignments...")
def scan_assignments_from_files(lang_code):
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
        for d in search_dirs:
            if not os.path.exists(d): continue
            files = os.listdir(d)
            if lang_code == 'en':
                for f in files:
                    if (f.lower().startswith("homework") or f.lower().startswith("assignment")) and "_en.docx" in f.lower():
                        target_file = os.path.join(d, f)
                        break
            if not target_file:
                for f in files:
                    if (f.lower().startswith("homework") or f.lower().startswith("assignment")) and f.endswith(".docx") and "_en.docx" not in f.lower():
                        target_file = os.path.join(d, f)
                        break
            if target_file: break
        
        if target_file:
            try:
                content = docx2txt.process(target_file)
                assignments_db[unit_id] = {
                    "id": 1000 + unit_id,
                    "title": f"Unit {unit_id}", 
                    "description": content if content.strip() else "(Empty File)"
                }
            except Exception as e:
                print(f"Error reading docx {target_file}: {e}")
                
    return assignments_db

ASSIGNMENTS_DB = scan_assignments_from_files(st.session_state["language"])

def get_reference_answer(unit_id: int, lang_code: str):
    if not os.path.exists(LECTURES_DIR): return None
    folders = sorted([f for f in os.listdir(LECTURES_DIR) if os.path.isdir(os.path.join(LECTURES_DIR, f))])
    target_folder = None
    for folder in folders:
        match = re.match(r"^(\d+)[_]", folder)
        if match and int(match.group(1)) == unit_id:
            target_folder = folder
            break
    if not target_folder: return None
    
    sub_assign_dir = os.path.join(LECTURES_DIR, target_folder, "assignments")
    search_dirs = [sub_assign_dir] if os.path.exists(sub_assign_dir) else [os.path.join(LECTURES_DIR, target_folder)]
    
    for d in search_dirs:
        if not os.path.exists(d): continue
        files = os.listdir(d)
        target_file = None
        if lang_code == 'en':
            for f in files:
                if f.lower() in ["reference_en.md", "reference_en.txt"]:
                    target_file = os.path.join(d, f)
                    break
        if not target_file:
            for f in files:
                if f.lower() in ["reference.md", "reference.txt"]:
                    target_file = os.path.join(d, f)
                    break
        
        if target_file:
            try:
                with open(target_file, "r", encoding="utf-8") as fh:
                    return fh.read()
            except: pass
    return None

# =====================================================
# 5) RAG 核心
# =====================================================
@st.cache_resource(show_spinner="Loading Knowledge Base...")
def get_global_vectorstore():
    if not os.path.exists(FAISS_DIR): return None
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
        vs = FAISS.load_local(FAISS_DIR, embeddings, allow_dangerous_deserialization=True)
        return vs
    except: return None

def _retrieve_context(query: str, unit_id: int | None, k: int = 8) -> str:
    vs = get_global_vectorstore()
    if vs is None: return ""
    docs = vs.similarity_search(query, k=20)
    if unit_id is not None:
        docs = [d for d in docs if d.metadata.get("unit_id") == unit_id or d.metadata.get("week") == unit_id]
    docs = docs[:k]
    parts = [f"[Unit {d.metadata.get('unit_id', '?')}] {d.page_content}" for d in docs]
    return "\n\n".join(parts)


# =====================================================
# 6) AI 生成與批改
# =====================================================
def generate_practice_question_real_data(level: str, qtype: str, unit_id: int | None, specific_topic: str | None, lang: str) -> dict:
    q_str = f"Unit {unit_id}" if unit_id else ""
    seed = f"{q_str} spatial analysis {qtype} {level}"
    context = _retrieve_context(seed, unit_id=unit_id)
    
    unit_skills_map = SKILLS_DB.get(lang, SKILLS_DB["zh"])
    selected_method = specific_topic if specific_topic and specific_topic != T["opt_all"] else random.choice(unit_skills_map.get(unit_id, ["Spatial Analysis"]))

    real_files = get_unit_files(unit_id) if unit_id else []
    ai_visible_extensions = ('.shp', '.csv', '.tif', '.geojson', '.txt')
    ai_files = [f['name'] for f in real_files if f['name'].lower().endswith(ai_visible_extensions)]
    file_names_str = ", ".join(ai_files) if ai_files else "None"

    is_short_ans = (qtype in ["簡答題", "Short Answer"])

    if lang == "en":
        if is_short_ans:
            sys_role = "You are a GIS expert. Ask a Conceptual Question based on the context."
            system_instruction = f"""
            Design a 'Short Answer' question (Difficulty: {level}) about: {selected_method}.
            ❌ Do NOT ask students to load specific files or write code.
            ✅ Focus on theory, logic, or concept explanation.
            
            JSON Output:
            {{ "question_content": "Write the actual question text here...", "hint": "Explanation of the concept...", "target_filename": "None" }}
            """
        else:
            sys_role = "You are a GIS TA. Create a Practical R Coding task."
            r_rules = "Hard Constraints: 1. Use **R language** (sf, terra). 2. No ArcGIS/QGIS mentions."
            
            system_instruction = f"""
            Design a 'Practical' task (Difficulty: {level}) using files: [{file_names_str}].
            Core Concept: {selected_method}.
            {r_rules}
            
            【Question Design Strategy】
            1. 'question_content':
               - Provide a **Scenario** or **Analytical Goal**.
               - ✅ **MANDATORY**: You MUST explicitly state the filenames to be used (e.g., "Please use 'A.shp' and 'B.csv' to...").
               - ❌ **FORBIDDEN**: Do NOT list numbered steps (1. Read file, 2. Transform...).
               - ❌ **FORBIDDEN**: Do NOT mention specific R function names in the question.
            
            2. 'hint':
               - Provide the detailed step-by-step guide and suggested R functions here.
            
            JSON Output:
            {{ "question_content": "Scenario description with filenames...", "hint": "Step-by-step R guide...", "target_filename": "..." }}
            """
    else:
        if is_short_ans:
            sys_role = "你是 GIS 觀念專家。請根據講義出題。"
            system_instruction = f"""
            請設計一道關於「{selected_method}」的【觀念簡答題】(難度：{level})。
            ❌ 不要要求學生讀取特定檔案或寫程式。
            ✅ 請專注於測試名詞解釋、分析原理或適用情境。
            
            請回傳 JSON：
            {{ "question_content": "請在此寫下題目敘述...", "hint": "觀念解說...", "target_filename": "None" }}
            """
        else:
            sys_role = "你是頂尖的空間分析助教。請設計 R 語言實作題。"
            r_rules = "嚴格限制：1. 必須使用 **R 語言**。 2. 禁止提及 ArcGIS/QGIS。"
            
            system_instruction = f"""
            請根據真實檔案列表: [{file_names_str}] 設計一道【實作題】(難度：{level})。
            核心考點：{selected_method}。
            {r_rules}
            
            【出題策略】
            1. 'question_content' (題目)：
               - 請設計一個「情境」或「分析目標」。
               - ✅ **必須明確指出要使用的檔案名稱** (例如：請使用 'Taipei.shp' 進行分析...)。
               - ❌ **嚴禁**在題目中列出步驟 (如 1. 讀檔 2. 轉座標...)。
               - ❌ **嚴禁**在題目中直接提及 R 函數名稱 (讓學生自己想)。
            
            2. 'hint' (提示)：
               - 這裡才需要提供詳細的 Step-by-step 步驟與建議使用的 R 套件/函數。
            
            請回傳 JSON：
            {{ "question_content": "包含檔案名稱的情境與目標...", "hint": "R 語言詳細解題步驟...", "target_filename": "..." }}
            """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": sys_role + system_instruction}, {"role": "user", "content": f"Context: {context}"}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"question_content": f"Error: {e}", "target_filename": None, "hint": ""}

def grade_submission(question_text: str, student_answer: str, hint_text: str, unit_id: int | None, lang: str, qtype: str = "Practical (R Code)") -> dict:
    context = _retrieve_context(question_text, unit_id=unit_id, k=10)
    is_conceptual = (qtype in ["簡答題", "Short Answer"])
    
    # 1. 絕對的防呆防弊：Python 後台直接比對，防止 AI 幻覺
    if hint_text and hint_text.strip() and student_answer.strip() == hint_text.strip():
        return {
            "score": 0,
            "strengths": [],
            "weaknesses": ["⚠️ 嚴重違規：檢測到完全複製提示內容，請自行撰寫答案。"],
            "rubric_scores": [0, 0, 0],
            "rubric_evidence": ["未提供", "未提供", "未提供"]
        }

    # [FIX v7.7] 新增無效答案檢測 (Garbage Input Check)
    garbage_check_logic = """
    【🚨 STEP 0: GARBAGE/IRRELEVANT INPUT CHECK】
    First, evaluate if the [Student Answer] is a genuine attempt to answer the [Question].
    If the answer is a meaningless placeholder (e.g., "測試", "123", "不知道", "test", "none"), completely off-topic, or lacks any substantive GIS/R content related to the question:
    - Total Score MUST be 0.
    - All rubric_scores MUST be 0.
    - Weakness MUST state: "⚠️ 嚴重缺失：作答內容無意義或與題目完全無關，請認真作答。"
    - STOP GRADING HERE. Do not apply further rubrics.
    """

    if is_conceptual:
        grading_logic = """
        【Grading Rules (Conceptual/Short Answer)】
        1. **No Code Required**: Focus on text explanation and logic.
        2. **Rubric** (Total 10):
           - **Conceptual Accuracy (概念正確性)** [Max 3]
           - **Analytical Logic (分析邏輯與解釋)** [Max 4]
           - **Completeness (完整性與關鍵細節)** [Max 3]
        """
    else:
        grading_logic = """
        【🚨 STEP 1: MANDATORY CODE CHECK (For Practical Tasks)】
        Check if the student answer contains actual R code syntax (e.g., `library`, `st_read`, `<-`, `function`).
        
        **CASE A: NO R CODE FOUND (Only text descriptions/plans)**:
        - **Total Score MUST be <= 4**.
        - **Rubric Guide**:
          * Requirement: 1-2 (Depending on textual understanding).
          * Spatial Logic: 1-2 (Depending on logic).
          * Code Rigor: 0 (No code).
        - Weakness: "嚴重缺失：僅有文字敘述，未撰寫 R 程式碼 (No R code provided)."
        
        **CASE B: CODE FOUND (Normal Grading)**:
        - **Rubric** (Total 10):
           - **Requirement Coverage (需求覆蓋)** [Max 3]
           - **Spatial Logic (空間邏輯)** [Max 4]
           - **Code Rigor (R 程式嚴謹度)** [Max 3]
        """

    final_prompt = f"""
    You are a strict but fair GIS TA. 
    Evaluate the [Student Answer] against the [Question].
    NOTE: Assume the student DID NOT plagiarize. Just grade the content based on the rules below.
    
    {garbage_check_logic}
    
    {grading_logic}
    
    **Language**: MUST use Traditional Chinese (繁體中文).
    
    Response Format (JSON):
    {{
        "score": int (0-10),
        "strengths": ["point 1", "point 2"],
        "weaknesses": ["point 1", "point 2"],
        "rubric_scores": [score_1, score_2, score_3], 
        "rubric_evidence": ["evidence_1", "evidence_2", "evidence_3"]
    }}
    """

    user_content = f"""
    [Question] {question_text}
    [Hint Provided] {hint_text}
    [Student Answer] {student_answer}
    [Context] {context}
    
    Please grade this submission.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"score": 0, "strengths": [], "weaknesses": ["System Error"], "rubric_scores": [0,0,0], "rubric_evidence": [str(e), "", ""]}

def generate_weakness_report(unit_id: int):
    lang = st.session_state["language"]
    df_p = read_history_gsheet()
    df_a = read_submissions_gsheet()
    
    fb_list = []
    weaknesses = []
    low_score_q_p = []
    
    if not df_p.empty and 'unit_id' in df_p.columns:
        df_p['score'] = pd.to_numeric(df_p['score'], errors='coerce').fillna(0)
        unit_df = df_p[(df_p['unit_id'] == unit_id) & (df_p['score'] >= 2)]
        for _, row in unit_df.iterrows():
            try:
                data = json.loads(row['feedback_json'])
                if 'weaknesses' in data: weaknesses.extend(data['weaknesses'])
                if row['score'] < 8:
                    low_score_q_p.append(f"[Score: {row['score']}] {row['question']}")
            except: pass

    if not df_a.empty and 'unit_id' in df_a.columns:
        df_a['score'] = pd.to_numeric(df_a['score'], errors='coerce').fillna(0)
        unit_df_a = df_a[(df_a['unit_id'] == unit_id) & (df_a['score'] >= 2)]
        for _, row in unit_df_a.iterrows():
            try:
                data = json.loads(row['feedback_json'])
                if 'weaknesses' in data: weaknesses.extend(data['weaknesses'])
            except: pass

    if not weaknesses: return "⚠️ No sufficient data."
    
    weakness_text = "\n".join(weaknesses[:60])
    bad_questions = "\n".join(low_score_q_p[:5])
    
    prompt = f"""
    你是教學顧問。分析 Unit {unit_id} 弱點：\n{weakness_text}
    
    【格式要求】
    1. 使用 Markdown (##, ###)。
    2. **標題字體不要太大**，請從 ### (H3) 開始使用。
    3. 內容包含：常見錯誤模式、概念澄清、教學建議。
    4. 最後請附上一個區塊：**「### 🎯 學生答錯率最高的題目範例」**，請參考以下題目列表，挑選 3 題最具代表性的：
    {bad_questions}
    
    請務必使用繁體中文。
    """
    with st.spinner("🤖 AI analyzing..."):
        r = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content


# =====================================================
# 7) 資料庫與日誌系統
# =====================================================
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

def read_history_gsheet() -> pd.DataFrame:
    try:
        ws = get_worksheet("learning_history")
        if ws: return pd.DataFrame(ws.get_all_records())
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 讀取歷史紀錄失敗：{e}")
        return pd.DataFrame()

def read_submissions_gsheet() -> pd.DataFrame:
    try:
        ws = get_worksheet("submissions")
        if ws: return pd.DataFrame(ws.get_all_records())
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 讀取作業紀錄失敗：{e}")
        return pd.DataFrame()

def log_system_usage(action: str):
    try:
        ws = get_worksheet("system_logs")
        if ws:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            ram_gb = round(mem_info.rss / (1024 ** 3), 4)
            row_data = [datetime.now().isoformat(), action, ram_gb]
            ws.append_row(row_data)
    except: pass 

def log_practice(sid, uid, q, fb, duration, used_hint):
    try:
        ws = get_worksheet("learning_history")
        if ws:
            weakness_list = fb.get('weaknesses', [])
            weakness_str = "; ".join(weakness_list) if isinstance(weakness_list, list) else str(weakness_list)
            
            row_data = [
                datetime.now().isoformat(), 
                st.session_state["session_id"],
                str(sid), 
                int(uid) if uid is not None else 0,
                duration,
                str(used_hint),
                q, 
                fb.get('score', 0), 
                get_level_from_score(fb.get('score', 0)), 
                weakness_str,
                json.dumps(fb, ensure_ascii=False)
            ]
            ws.append_row(row_data)
            log_system_usage(f"Practice_Submit_Unit{uid}")
            
    except Exception as e: st.error(f"Log Error: {e}")

    try:
        email_body = f"Student: {sid}\nScore: {fb.get('score')}"
        send_backup_email(f"GIS Gym Practice: {sid}", email_body)
    except: pass

def log_assignment_submission(assign_id, sid, uid, ans, fb):
    try:
        ws = get_worksheet("submissions")
        if ws:
            weakness_list = fb.get('weaknesses', [])
            weakness_str = "; ".join(weakness_list) if isinstance(weakness_list, list) else str(weakness_list)

            row_data = [
                datetime.now().isoformat(), 
                int(assign_id), 
                str(sid), 
                int(uid) if uid is not None else 0, 
                ans, 
                fb.get('score', 0), 
                weakness_str,
                json.dumps(fb, ensure_ascii=False)
            ]
            ws.append_row(row_data)
            log_system_usage(f"Assignment_Submit_Unit{uid}")

    except Exception as e: st.error(f"Log Error: {e}")

    try:
        email_body = f"Student: {sid}\nUnit: {uid}"
        send_backup_email(f"GIS Gym Assignment: {sid}", email_body)
    except: pass

def get_student_submission(sid, assign_id):
    df = read_submissions_gsheet()
    if df.empty: return None
    try:
        df['student_id'] = df['student_id'].astype(str)
        df['assignment_id'] = df['assignment_id'].astype(str)
        filtered = df[(df['student_id'] == str(sid)) & (df['assignment_id'] == str(assign_id))]
        if not filtered.empty:
            last_row = filtered.iloc[-1]
            return (last_row['score'], last_row['feedback_json'])
    except: pass
    return None

def send_backup_email(subject, body):
    if "email" not in st.secrets: return False
    try:
        cfg = st.secrets["email"]
        msg = MIMEMultipart()
        msg['From'] = cfg["sender_email"]
        msg['To'] = cfg["receiver_email"]
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
            server.starttls()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.send_message(msg)
        return True
    except: return False


# =====================================================
# 8) UI Helper
# =====================================================
def get_level_from_score(score):
    try:
        s = int(score)
        if s == 10: return "優秀 (Excellent)"
        elif s >= 8: return "良好 (Good)"
        elif s >= 6: return "及格 (Pass)"
        else: return "待加強 (Needs Improvement)"
    except: return "N/A"

def display_feedback_ui(fb, t_dict, qtype="Practical"):
    if not fb: return
    
    score = fb.get('score', 0)
    level = get_level_from_score(score)
    
    st.markdown(f"### {t_dict['fb_score']} {score} / 10")
    st.caption(f"等級評價: {level}")
    
    st.markdown(f"#### {t_dict['fb_rubric']}")
    
    ai_scores = fb.get('rubric_scores', [0, 0, 0])
    ai_evidence = fb.get('rubric_evidence', ["未提供", "未提供", "未提供"])
    
    while len(ai_scores) < 3: ai_scores.append(0)
    while len(ai_evidence) < 3: ai_evidence.append("未提供")

    is_conceptual = qtype in ["簡答題", "Short Answer"]
    
    if is_conceptual:
        criteria = [
            ("概念正確性 (Conceptual Accuracy)", 3),
            ("分析邏輯與解釋 (Analytical Logic)", 4),
            ("完整性與關鍵細節 (Completeness)", 3)
        ]
    else:
        criteria = [
            ("需求覆蓋 (Requirement)", 3),
            ("空間邏輯 (Spatial Logic)", 4),
            ("R 程式嚴謹度 (Code Rigor)", 3)
        ]

    rubric_data = []
    for i in range(3):
        rubric_data.append({
            t_dict['col_crit']: criteria[i][0],
            t_dict['col_pts']: ai_scores[i],
            t_dict['col_max']: criteria[i][1],
            t_dict['col_evi']: ai_evidence[i]
        })
    
    st.table(pd.DataFrame(rubric_data))
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### {t_dict['fb_strengths']}")
        for s in fb.get('strengths', []): st.markdown(f"- {s}")
    with c2:
        st.markdown(f"#### {t_dict['fb_weaknesses']}")
        for w in fb.get('weaknesses', []): st.markdown(f"- {w}")


# =====================================================
# 9) 主程式 UI
# =====================================================
with st.sidebar:
    lang_choice = st.radio("Select Language:", ("繁體中文", "English"), index=0 if st.session_state["language"] == "zh" else 1, label_visibility="collapsed")
    new_lang = "zh" if lang_choice == "繁體中文" else "en"
    if new_lang != st.session_state["language"]:
        st.session_state["language"] = new_lang
        st.rerun()

    ASSIGNMENTS_DB = scan_assignments_from_files(st.session_state["language"])
    st.divider()
    
    st.header(T['sidebar_user'])
    if "student_id" not in st.session_state: st.session_state["student_id"] = ""
    
    user_input_id = st.text_input(T['label_student_id'], value=st.session_state["student_id"])
    st.session_state["student_id"] = user_input_id
    
    if "ALLOWED_STUDENTS" in globals() and user_input_id:
        if user_input_id not in ALLOWED_STUDENTS:
            st.error(T['warning_not_allowed'])
            st.stop()
    
    st.divider()
    
    if "is_ta" not in st.session_state: st.session_state["is_ta"] = False
    
    if not st.session_state["is_ta"]:
        with st.expander(T['ta_login']):
            u = st.text_input("ID", key="ta_u")
            p = st.text_input("PW", type="password", key="ta_p")
            if st.button(T['btn_login']):
                if u == "ta" and p == "gisgym2025!":
                    st.session_state["is_ta"] = True
                    st.rerun()
                else: st.error("Error")
    else:
        st.success(T['ta_mode'])
        if st.button(T['btn_logout']):
            st.session_state["is_ta"] = False
            st.rerun()
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        app_ram = mem_info.rss / (1024 ** 3)
        st.write(f"System Load: {app_ram:.2f} / 1.0 GB")
        st.progress(min(app_ram / 1.0, 1.0))
        if app_ram > 0.8: st.error("⚠️ High Memory Usage!")

tabs = st.tabs([T['tab_practice'], T['tab_assignment'], T['tab_ta']] if st.session_state["is_ta"] else [T['tab_practice'], T['tab_assignment']])

# --- Tab 1: Practice ---
with tabs[0]:
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([1.5, 2, 1, 1, 1], vertical_alignment="bottom")
        unit_str = c1.selectbox(T['sel_unit'], [T['opt_all']] + unit_options, key="p_unit")
        unit_val = int(unit_str) if unit_str != T['opt_all'] else None
        
        current_skills = SKILLS_DB.get(st.session_state["language"], SKILLS_DB["zh"])
        avail_topics = [T['opt_all']] + current_skills[unit_val] if unit_val and unit_val in current_skills else [T['opt_all']]
        
        topic_display = c2.selectbox(T['sel_topic'], avail_topics, key="p_topic")
        lvl_display = c3.selectbox(T['sel_level'], [T['opt_intro'], T['opt_adv']], key="p_lvl")
        type_display = c4.selectbox(T['sel_type'], [T['opt_short'], T['opt_coding']], key="p_qty")
        
        if c5.button(T['btn_generate'], type="primary", use_container_width=True):
            if not st.session_state.get("student_id", "").strip():
                st.warning(T["warning_no_id"])
            else:
                with st.spinner("AI thinking..."):
                    q_data = generate_practice_question_real_data(lvl_display, type_display, unit_val, topic_display, st.session_state["language"])
                    st.session_state["pq_data"] = q_data
                    st.session_state["pq_meta"] = f"{unit_str} | {lvl_display} | {type_display}"
                    st.session_state["q_start_time"] = time.time()
                    st.session_state["hint_viewed"] = False
                    st.session_state["p_ans"] = ""

    if "pq_data" in st.session_state:
        q_data = st.session_state["pq_data"]
        st.markdown(f"### {T['header_q']} [{st.session_state['pq_meta']}]") 
        st.info(q_data.get("question_content", ""))
        
        if st.button(T['btn_show_hint']):
            st.session_state["hint_viewed"] = True
        
        if st.session_state.get("hint_viewed", False):
            with st.container(border=True):
                st.markdown(f"#### {T['header_hint']}")
                st.markdown(q_data.get("hint", ""))

        is_short_ans = (type_display in [T['opt_short'], "簡答題", "Short Answer"])
        if unit_val and not is_short_ans:
            all_files = get_unit_files(unit_val)
            if all_files:
                with st.expander(f"📂 {T['btn_download_data']}", expanded=False):
                    if unit_val in UNIT_NOTES:
                        note_lang = st.session_state["language"]
                        st.info(UNIT_NOTES[unit_val][note_lang])
                    
                    cols = st.columns(3)
                    for i, f in enumerate(all_files):
                        with cols[i % 3]:
                            with open(f['path'], "rb") as fp:
                                st.download_button(f"{f['name']}", fp, f['name'])
            else: st.warning(T['no_data_file'])
        
        sid = st.session_state["student_id"]
        ans = st.text_area("Answer", height=150, key="p_ans", disabled=not sid, placeholder=T['placeholder_ans'])
        if st.button(T['btn_submit'], key="p_sub", disabled=not ans):
            with st.spinner("Grading..."):
                duration = 0
                if "q_start_time" in st.session_state:
                    duration = int(time.time() - st.session_state["q_start_time"])
                
                fb = grade_submission(q_data.get("question_content", ""), ans, q_data.get("hint", ""), unit_val, st.session_state["language"], qtype=type_display)
                log_practice(sid, unit_val, q_data.get("question_content", ""), fb, duration, st.session_state.get("hint_viewed", False))
                
                display_feedback_ui(fb, T, qtype=type_display)

# --- Tab 2: Assignment ---
with tabs[1]:
    if not ASSIGNMENTS_DB: st.info(T['no_assign_file'])
    else:
        target_unit = st.selectbox(T['sel_assign_unit'], options=sorted(ASSIGNMENTS_DB.keys()))
        assignment = ASSIGNMENTS_DB.get(target_unit)
        if assignment:
            st.markdown(f"### {T['header_assign_desc']}") 
            st.markdown(assignment['description'])
            
            real_files = get_unit_files(target_unit)
            if real_files:
                with st.expander(f"📂 {T['header_assign_data']}", expanded=False):
                    if target_unit in UNIT_NOTES:
                        note_lang = st.session_state["language"]
                        st.info(UNIT_NOTES[target_unit][note_lang])
                        
                    cols = st.columns(3)
                    for i, f in enumerate(real_files):
                        with cols[i % 3]:
                            with open(f['path'], "rb") as fp:
                                st.download_button(f"{f['name']}", fp, f['name'], key=f"assign_dl_{i}")
            
            st.divider()
            sid = st.session_state["student_id"]
            if not sid: st.warning(f"Please enter {T['label_student_id']} in sidebar.")
            else:
                prev = get_student_submission(sid, assignment['id'])
                if prev:
                    st.success(f"{T['msg_submitted']} {prev[0]}")
                    with st.expander(T['expander_feedback']): 
                        display_feedback_ui(json.loads(prev[1]), T, qtype="Practical")
                    
                    ref_ans = get_reference_answer(target_unit, st.session_state["language"])
                    if ref_ans:
                        with st.expander("📝 查看參考解答 (Reference Answer)"):
                            st.markdown(ref_ans)
                
                assign_ans = st.text_area("Answer Area", height=250, key=f"assign_ans_{target_unit}", placeholder="Please paste your R code and explanation here...")
                if st.button(T['btn_submit_assign'], type="primary", disabled=not assign_ans):
                    with st.spinner("Submitting..."):
                        fb = grade_submission(assignment['description'], assign_ans, "", target_unit, st.session_state["language"], qtype="Practical (R Code)")
                        log_assignment_submission(assignment['id'], sid, target_unit, assign_ans, fb)
                        st.balloons()
                        st.rerun()

# --- Tab 3: TA Dashboard ---
if st.session_state["is_ta"] and len(tabs) > 2:
    with tabs[2]:
        with st.container(border=True):
            st.markdown(f"### {T['header_ta_report']}") 
            ana_unit = st.selectbox(T['ta_filter_unit'], unit_options, key="ana_unit")
            if st.button(T['btn_gen_report']):
                if ana_unit:
                    report = generate_weakness_report(int(ana_unit))
                    st.markdown(report)
        
        st.markdown("---")
        st.link_button(T['link_gsheet'], GOOGLE_SHEET_URL)
        
        filter_unit = st.selectbox(T['ta_filter_unit'], [T['opt_all']] + unit_options, key="hist_filter")
        
        st.markdown(f"### {T['header_prac_history']}") 
        df = read_history_gsheet()
        if not df.empty:
            if filter_unit != T['opt_all']:
                df = df[df['unit_id'] == int(filter_unit)]
            
            st.download_button(T['btn_dl_csv'], df.to_csv(index=False).encode('utf-8-sig'), "practice.csv", "text/csv")
            if 'feedback_json' in df.columns:
                df["weakness_parsed"] = df["feedback_json"].apply(extract_weaknesses)
            
            display_cols = [c for c in ['timestamp', 'student_id', 'unit_id', 'score', 'duration_sec', 'used_hint', 'weakness_parsed'] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=300)
        else: st.info(T['msg_no_data'])

        st.markdown("---")
        st.markdown(f"### {T['header_assign_history']}") 
        df_sub = read_submissions_gsheet()
        if not df_sub.empty:
            if filter_unit != T['opt_all']:
                df_sub = df_sub[df_sub['unit_id'] == int(filter_unit)]
                
            st.download_button(T['btn_dl_csv'], df_sub.to_csv(index=False).encode('utf-8-sig'), "submissions.csv", "text/csv")
            if 'feedback_json' in df_sub.columns: 
                df_sub["weakness_parsed"] = df_sub["feedback_json"].apply(extract_weaknesses)
            display_cols_sub = [c for c in ['timestamp', 'student_id', 'unit_id', 'score', 'weakness_parsed', 'answer'] if c in df_sub.columns]
            st.dataframe(df_sub[display_cols_sub], use_container_width=True, hide_index=True, height=300)
        else: st.info(T['msg_no_data'])