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
    
    # --- 5. ADMIN PORTAL ---
    st.sidebar.header("🔒 Admin Portal")
    password = st.sidebar.text_input("Enter Admin Password:", type="password")

    # This is the part we are adding/changing slightly
    if password:
        if password == st.secrets["admin_password"]:
            # --- EVERYTHING IN HERE IS FOR ADMIN ONLY ---
            st.sidebar.success("Logged in as Admin")
            st.sidebar.divider()
        
            # This menu ONLY appears if the password is correct
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
                    cur.execute("UPDATE inventory SET current_stock = %s, last_updated = CURRENT_TIMESTAMP WHERE item_name = %s AND brand = %s", (new_qty, sel_name, sel_brand))
                    conn.commit()
                    st.sidebar.success(f"✅ Updated {sel_name}!")
                    st.rerun()
            else:
                st.sidebar.warning("No items to update yet. Add a new item first!")

        else:
        # --- EVERYTHING IN HERE IS FOR VISITORS ---
        # Because the 'task' menu is NOT in this block, it will vanish!
        st.sidebar.error("Your Password is Wrong")
        st.sidebar.info("Logged in as Visitor")
        
        else:
            st.sidebar.subheader("Add New Item")
            add_n = st.sidebar.text_input("Item Name")
            add_b = st.sidebar.text_input("Brand")
            add_s = st.sidebar.number_input("Initial Stock", min_value=0)
            add_u = st.sidebar.selectbox("Unit", ["Box", "Pcs", "Tube", "Pack", "Botol", "Buah"])
            
            if st.sidebar.button("Save New Item"):
                if add_n == "":
                    st.sidebar.warning("Please enter a name.")
                else:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO inventory (item_name, brand, current_stock, unit_type) VALUES (%s, %s, %s, %s)", (add_n, add_b, add_s, add_u))
                    conn.commit()
                    st.sidebar.success("✨ Added!")
                    st.rerun()

    # --- 6. MAIN DISPLAY (SEARCH & TABLE) ---
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





