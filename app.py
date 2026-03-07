import streamlit as st
import psycopg2
import pandas as pd

# --- 1. DATABASE CONNECTION ---
def get_connection():
    try:
        return psycopg2.connect(
            host=st.secrets["db_host"],
            database=st.secrets["db_name"],
            user=st.secrets["db_user"],
            password=st.secrets["db_password"],
            port=st.secrets["db_port"]
        )
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="SRBA Inventory", layout="wide", page_icon="logo.png")

# --- 3. HEADER ---
col1, col2 = st.columns([0.15, 0.85], vertical_alignment="center") 
with col1:
    st.image("logo.png", width=100) 
with col2:
    st.title("Stok Gudang PT Sumber Rejeki Berkat Abadi")

# --- 4. FETCH & PROCESS DATA (The "Option B" Fix) ---
conn = get_connection()
if conn:
    # Pull raw data from the 'inventory' table
    df = pd.read_sql('SELECT * FROM inventory', conn)
    conn.close()

    if not df.empty:
        # STEP A: Rename columns to stop the KeyError
        df = df.rename(columns={
            'item_name': 'Nama Barang',
            'brand': 'Brand',
            'current_stock': 'Sisa Barang',
            'unit_type': 'Satuan Barang',
            'last_updated': 'Update Data'
        })

        # STEP B: The Status Formula (Fixes ValueError at Line 56)
        def check_status(row):
            try:
                current = float(row['Sisa Barang'])
                # Uses hidden 'min_required' from Neon Backend
                minimum = float(row.get('min_required', 10)) 
                return "📦 RE-ORDER" if current <= minimum else "✅ STOCK SAFE"
            except:
                return "⚠️ DATA ERROR"

        # Apply row-by-row (axis=1 is the key!)
        df['Status'] = df.apply(check_status, axis=1)

        # STEP C: Frontend Filter (Hides min_required/location_code)
        display_cols = ['Nama Barang', 'Brand', 'Sisa Barang', 'Satuan Barang', 'Status', 'Update Data']
        df_display = df[display_cols]
        
        # Sort by Date
        df_display['Update Data'] = pd.to_datetime(df_display['Update Data'])
        df_display = df_display.sort_values(by='Update Data', ascending=False)

        # --- 5. SEARCH & DASHBOARD ---
        search = st.text_input("🔍 Search Name or Brand:", placeholder="Type and press ENTER...")
        
        if search:
            mask = df_display['Nama Barang'].str.contains(search, case=False, na=False) | \
                   df_display['Brand'].str.contains(search, case=False, na=False)
            df_final = df_display[mask]
        else:
            df_final = df_display

        st.dataframe(df_final, use_container_width=True, hide_index=True)
    else:
        st.info("Table is currently empty. Add data via Admin Portal or Neon.")

# --- 6. ADMIN PORTAL (SIDEBAR) ---
st.sidebar.header("🔒 Admin Portal")
password = st.sidebar.text_input("Enter Admin Password:", type="password")

if password == st.secrets["admin_password"]:
    st.sidebar.success("Logged in as Admin")
    # (Your existing Add/Update logic remains here, just ensure it uses 'inventory' table)
elif password != "":
    st.sidebar.warning("❌ Wrong password.")
else:
    st.sidebar.info("Please enter password to edit.")