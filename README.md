🧪 GIS Gym｜空間分析 AI 助教平台
GIS Gym 是一個基於 RAG (Retrieval-Augmented Generation) 技術的智慧教學輔助平台，專為大學「空間分析」與「GIS」課程設計。

透過整合 OpenAI GPT-4o 模型與 LangChain 框架，本平台能讀取課程講義、程式碼 (.R/.Rmd) 與實體圖資 (.shp/.csv)，為學生提供具備「真實資料」的實作練習題目，並提供即時、高品質的自動批改與回饋；同時賦予助教強大的後台分析能力，自動歸納學生學習弱點並生成教學建議。

✨ 核心功能
👨‍🎓 學生端 (Student)
🏋️ 自主練習 (Practice Mode)

AI 出題：根據指定單元 (Unit) 與難度，隨機生成簡答或實作題。

真實圖資注入：題目會直接引用課程資料夾內的實體檔案（如 Shapefile），並提供 📥 下載按鈕，讓學生能進行真實操作，而非空泛理論。

即時批改：使用 GPT-4o 針對學生回答或程式碼進行深度評析，提供分數、優缺點與改進建議。

📝 單元作業 (Assignments)

查看助教發布的每週/單元作業與截止日期。

線上繳交作業，系統自動記錄繳交時間並進行 AI 預評分。

👩‍🏫 助教端 (TA Dashboard)
🤖 AI 教學顧問報告

一鍵掃描指定單元的所有學生作答紀錄。

自動歸納 Top 3 核心弱點。

生成教學加強建議與推薦的期中考題。

📊 學習歷程管理

檢視所有練習與作業紀錄 (SQLite)。

互動式表格：支援篩選單元、學號。

手動加分 (Bonus)：可針對優秀作答給予額外加分與備註。

📂 自動化課程管理

支援自動掃描資料夾結構，生成課程 Metadata。

支援讀取 PDF, Word, R Code, R Markdown 建立向量知識庫。

🏗️ 系統架構與目錄結構
本專案採用 Unit (單元流水號) 結構進行管理（如 01_Data_Analysis），方便依照教學進度彈性調整。
GIS_Gym/
├── app.py                      # 🚀 Streamlit 主程式
├── build_vector_db.py          # 🛠️ [工具] 建立 RAG 向量資料庫 (FAISS)
├── generate_metadata.py        # 🛠️ [工具] 自動生成單元 Metadata (JSON)
├── requirements.txt            # Python 套件依賴
├── learning_history.sqlite     # SQLite 資料庫 (自動生成)
├── GeoGIS_faiss_db/            # FAISS 向量索引 (由 build_vector_db.py 生成)
│
└── lectures/                   # 📚 課程教材庫 (核心資料夾)
    ├── 01_Data_Analysis/       # [範例] 單元 01
    │   ├── metadata.json       # 單元資訊 (由 generate_metadata.py 生成)
    │   ├── materials/          # 講義 (PDF, Docx)
    │   ├── code/               # 程式碼範例 (.R, .Rmd) -> AI 讀這裡學寫 Code
    │   └── data/               # 🌍 真實圖資 (.shp, .csv) -> AI 拿這裡出題
    │       ├── tpe_pop.csv
    │       └── map.shp
    ├── 02_Spatial_Data/
    └── ... (依此類推)