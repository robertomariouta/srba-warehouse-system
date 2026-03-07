import streamlit as st
import psycopg2
import pandas as pd

# --- 1. SETTINGS & LOGO ---
st.set_page_config(page_title="SRBA Warehouse", layout="wide")
st.image("logo.png", width=150)
st.title("Stok Gudang PT Sumber Rejeki Berkat Abadi")

# --- 2. DATABASE CONNECTION ---
def get_connection():
    return psycopg2.connect(
        host=st.secrets["db_host"],
        database=st.secrets["db_name"],
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        port=st.secrets["db_port"],
        sslmode="require"
    )

conn = get_connection()

# --- 3. LOAD DATA ---
query = "SELECT item_name, brand, current_stock, unit_type, last_updated FROM inventory ORDER BY last_updated DESC"
df_raw = pd.read_sql(query, conn)

# --- 4. SEARCH & DISPLAY ---
search = st.text_input("🔍 Search Name or Brand:")
df_display = df_raw.copy()

if search:
    df_display = df_raw[
        (df_raw['item_name'].str.contains(search, case=False)) | 
        (df_raw['brand'].str.contains(search, case=False))
    ]

# Rename for Indonesian Labels
df_display.columns = ["Nama Barang", "Brand", "Sisa Barang", "Satuan Barang", "Update Data"]

# Status Logic
def get_status(stock):
    return "📦 RE-ORDER" if stock <= 0 else "✅ STOCK SAFE"

df_display["Status"] = df_display["Sisa Barang"].apply(get_status)
st.table(df_display[["Nama Barang", "Brand", "Sisa Barang", "Satuan Barang", "Status", "Update Data"]])

# --- 5. ADMIN PORTAL ---
st.sidebar.header("🔒 Admin Portal")
password = st.sidebar.text_input("Enter Admin Password:", type="password")

if password:
    if password == st.secrets["admin_password"]:
        st.sidebar.success("Logged in as Admin")
        st.sidebar.divider()
        
        task = st.sidebar.radio("Choose Action:", ["📝 Update Stock", "➕ Add New Item"])

        if task == "📝 Update Stock":
            if not df_raw.empty:
                st.sidebar.subheader("Update Inventory")
                brands = sorted(df_raw['brand'].unique())
                sel_brand = st.sidebar.selectbox("Choose Brand", brands)
                names = df_raw[df_raw['brand'] == sel_brand]['item_name'].tolist()
                sel_name = st.sidebar.selectbox("Choose Item Name", names)
                current_qty = df_raw[(df_raw['brand'] == sel_brand) & (df_raw['item_name'] == sel_name)]['current_stock'].values[0]
                
                st.sidebar.info(f"Last Stock: **{current_qty}**")
                new_qty = st.sidebar.number_input("Input New Stock", min_value=0, value=int(current_qty))
                
                if st.sidebar.button("Update Now"):
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE inventory 
                        SET current_stock = %s, 
                            last_updated = CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Makassar' 
                        WHERE item_name = %s AND brand = %s
                    """, (new_qty, sel_name, sel_brand))
                    conn.commit()
                    st.rerun()
        else:
            st.sidebar.subheader("Add New Item")
            add_n = st.sidebar.text_input("Item Name")
            add_b = st.sidebar.text_input("Brand")
            add_s = st.sidebar.number_input("Initial Stock", min_value=0)
            add_u = st.sidebar.selectbox("Unit", ["Box", "Pcs", "Tube", "Pack", "Botol", "Buah"])
            
            if st.sidebar.button("Save New Item"):
                if add_n:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO inventory (item_name, brand, current_stock, unit_type, last_updated) 
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Makassar')
                    """, (add_n, add_b, add_s, add_u))
                    conn.commit()
                    st.rerun()
    else:
        st.sidebar.error("Your Password is Wrong")
        st.sidebar.info("Logged in as Visitor")
