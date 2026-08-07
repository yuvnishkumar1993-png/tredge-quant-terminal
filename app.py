import streamlit as st
import pandas as pd
import os

# --- 📁 DYNAMIC CSV MASTER LOADER ---
@st.cache_data(ttl=60)
def load_dynamic_csv_master():
    """
    Automatically detects and loads any uploaded CSV file 
    (Scrip Master or Market Watch files) from the workspace.
    """
    possible_files = [
        "api-scrip-master.csv",
        "MW-All-Indices-08-Aug-2026.csv",
        "MW-FO-stock_fut-08-Aug-2026.csv"
    ]
    
    # Check if any new CSV file is present in the current directory
    for file in os.listdir("."):
        if file.endswith(".csv") and file not in possible_files:
            possible_files.insert(0, file)

    for path in possible_files:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, low_memory=False)
                df.columns = [str(col).strip().upper() for col in df.columns]
                return df, path
            except:
                continue
                
    return pd.DataFrame(), "None"

# लोड करें और साइडबार में लाइव स्टेटस दिखाएं
df_master, active_file = load_dynamic_csv_master()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📂 Data Pipeline Status")
if active_file != "None":
    st.sidebar.success(f"🟢 Active Source:\n`{active_file}`")
else:
    st.sidebar.error("🔴 No CSV Database Found!")
