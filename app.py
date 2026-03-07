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
            port=st.secrets["db_port"],
            sslmode="require"
        )
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="SRBA Inventory", layout="wide", page_icon="logo.png")

# --- 3. HEADER ---
col_logo, col_title = st.columns([0.15, 0.85], vertical_alignment="center") 
with col_logo:
    st.image("logo.png", width=100) 
with col_title:
    st.title("Stok Gudang PT Sumber Rejeki Berkat Abadi")

# --- 4. DATA FETCHING ---
conn = get_connection()
if conn:
    # Pull only the columns created in the new table
    df_raw = pd.read_sql('SELECT item_name, brand, current_stock, unit_type, last_updated FROM inventory ORDER BY last_updated DESC', conn)

# --- 5. MAIN DISPLAY (ALWAYS VISIBLE) ---
# This section is now outside any password checks
if not df_raw.empty:
    df = df_raw.rename(columns={
        'item_name': 'Nama Barang', 'brand': 'Brand',
        'current_stock': 'Sisa Barang', 'unit_type': 'Satuan Barang',
        'last_updated': 'Update Data'
    })
    
    df['Status'] = df['Sisa Barang'].apply(lambda x: "📦 RE-ORDER" if x <= 10 else "✅ STOCK SAFE")
    search = st.text_input("🔍 Search Name or Brand:")
    df_display = df[['Nama Barang', 'Brand', 'Sisa Barang', 'Satuan Barang', 'Status', 'Update Data']]
    
    if search:
        mask = df_display['Nama Barang'].str.contains(search, case=False) | df_display['Brand'].str.contains(search, case=False)
        st.dataframe(df_display[mask], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("The warehouse is currently empty. Use the Admin Portal on the left to add items.")

st.divider()

# --- 6. ADMIN PORTAL (CONTROLS ACTIONS ONLY) ---
st.sidebar.header("🔒 Admin Portal")
password = st.sidebar.text_input("Enter Admin Password:", type="password")

if password:
    if password == st.secrets["admin_password"]:
        # --- EVERYTHING IN HERE IS FOR ADMIN ONLY ---
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
                    # Updated to Makassar Time (GMT+8)
                    cur.execute("""
                        UPDATE inventory 
                        SET current_stock = %s, 
                            last_updated = CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Makassar' 
                        WHERE item_name = %s AND brand = %s
                    """, (new_qty, sel_name, sel_brand))
                    conn.commit()
                    st.sidebar.success(f"✅ Updated {sel_name}!")
                    st.rerun()
            else:
                st.sidebar.warning("No items to update yet.")
        
        else:
            st.sidebar.subheader("Add New Item")
            add_n = st.sidebar.text_input("Item Name")
            add_b = st.sidebar.text_input("Brand")
            add_s = st.sidebar.number_input("Initial Stock", min_value=0)
            add_u = st.sidebar.selectbox("Unit", ["Box", "Pcs", "Tube", "Pack", "Botol", "Buah"])
            
            if st.sidebar.button("Save New Item"):
                if add_n and add_b:
                    cur = conn.cursor()
                    
                    # 1. Check if this specific item name and brand already exist
                    cur.execute("SELECT item_name, brand FROM inventory WHERE item_name = %s AND brand = %s", (add_n, add_b))
                    existing = cur.fetchone()
                    
                    if existing:
                        # 2. Show the warning if it is already available
                        st.sidebar.error(f"⚠️ Data '{add_n}' with Brand '{add_b}' is already available.")
                        st.sidebar.warning("Please just update the stock in the 'Update Stock' menu instead.")
                    else:
                        # 3. If it is truly new, save it with Makassar Time
                        cur.execute("""
                            INSERT INTO inventory (item_name, brand, current_stock, unit_type, last_updated) 
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Makassar')
                        """, (add_n, add_b, add_s, add_u))
                        conn.commit()
                        st.sidebar.success("✨ New item added successfully!")
                        st.rerun()
                else:
                    st.sidebar.warning("Please fill in both Item Name and Brand.")
        
    else:
        # --- EVERYTHING IN HERE IS FOR VISITORS ---
        st.sidebar.error("Your Password is Wrong")
        st.sidebar.info("Logged in as Visitor")
