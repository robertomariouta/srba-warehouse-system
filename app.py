import streamlit as st
import psycopg2
import pandas as pd

# --- 1. DATABASE CONNECTION (SECURE VERSION) ---
def get_connection():
    try:
        # We tell Python to look into Streamlit's "Vault" (Secrets)
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
st.set_page_config(
    page_title="SRBA Inventory", 
    layout="wide", 
    page_icon="logo.png"  # This updates the browser tab icon
)

# --- 3. PROPORTIONAL HEADER ---
# We use a very small ratio (1 to 10) so the logo stays close to the text
col1, col2 = st.columns([0.15, 0.85], vertical_alignment="center") 

with col1:
    # 60 to 80 pixels is usually the "sweet spot" for title-size logos
    st.image("logo.png", width=100) 

with col2:
    st.title("Stok Gudang PT Sumber Rejeki Berkat Abadi")

# --- 3. FETCH DATA ---
conn = get_connection()
if conn:
    # Pulling from your VIEW for the display
    df = pd.read_sql('SELECT * FROM daily_report', conn)
    conn.close()

    # Sort by the "Update Data" column (Newest first)
    df['Update Data'] = pd.to_datetime(df['Update Data'])
    df = df.sort_values(by='Update Data', ascending=False)

    # --- 4. SIDEBAR ADMIN PANEL ---
    st.sidebar.header("🔒 Admin Portal")
    password = st.sidebar.text_input("Enter Admin Password:", type="password")

    if password == st.secrets["admin_password"]:
        st.sidebar.success("Logged in as Admin")
        
        # PLAN: UPDATE STOCK (Filtered by Brand & Name)
        with st.sidebar.expander("✏️ Update Remaining Stock"):
            unique_brands = sorted(df['Brand'].unique().tolist())
            sel_brand = st.selectbox("1. Select Brand:", unique_brands)
            
            filtered_items = df[df['Brand'] == sel_brand]['Nama Barang'].tolist()
            sel_item = st.selectbox(f"2. Select Item from {sel_brand}:", filtered_items)
           
            # Use 'Sisa Barang' as shown in your debugging list!
            matched_row = df[(df['Nama Barang'] == sel_item) & (df['Brand'] == sel_brand)]

            if not matched_row.empty:
              current_stock_value = matched_row.iloc[0]['Sisa Barang']
            else:
               current_stock_value = 0

            new_val = st.number_input("New Stock Quantity:", min_value=0, value=int(current_stock_value))
           
            if st.button("Update Stock"):
                conn = get_connection()
                if conn:
                    curr = conn.cursor()
                    # CHANGE 'REPLACE_WITH_YOUR_TABLE_NAME' BELOW!
                    query = """
                        UPDATE inventory 
                        SET current_stock = %s, 
                            last_updated = CURRENT_TIMESTAMP
                        WHERE item_name = %s AND brand = %s
                    """
                    curr.execute(query, (new_val, sel_item, sel_brand))
                    conn.commit()
                    curr.close()
                    conn.close()
                    st.toast(f"✅ Updated {sel_item} to {new_val}")
                    st.rerun()

        # PLAN: ADD NEW ITEM (With Duplicate Check)
        with st.sidebar.expander("➕ Add New Inventory"):
            new_name = st.text_input("New Item Name")
            new_brand = st.text_input("New Brand")
            new_qty = st.number_input("Initial Qty", min_value=0)
            
            if st.button("Save New Item"):
                is_duplicate = ((df['Nama Barang'].str.lower() == new_name.lower()) & 
                                (df['Brand'].str.lower() == new_brand.lower())).any()
                
                if is_duplicate:
                    st.error(f"⚠️ Error: {new_name} ({new_brand}) already exists!")
                else:
                    conn = get_connection()
                    if conn:
                        curr = conn.cursor()
                        # CHANGE 'REPLACE_WITH_YOUR_TABLE_NAME' BELOW!
                        # Use the EXACT column names from your pgAdmin 'inventory' table
                        query = "INSERT INTO inventory (item_name, brand, current_stock) VALUES (%s, %s, %s)"
                        curr.execute(query, (new_name, new_brand, new_qty))
                        conn.commit()
                        curr.close()
                        conn.close()
                        st.success("Item Added!")
                        st.rerun()
    
    # VISITOR MODE NOTIFICATION
    elif password != "":
        st.sidebar.warning("❌ Your password is wrong, you're in visitor mode.")
    else:
        st.sidebar.info("Please enter password to edit.")

    # --- 5. MAIN DASHBOARD ---
    search = st.text_input("🔍 Search Name or Brand:", placeholder="Type and press ENTER...")
    
    if search:
        df_display = df[df['Nama Barang'].str.contains(search, case=False) | 
                        df['Brand'].str.contains(search, case=False)]
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True, hide_index=True)

else:
    st.warning("Could not connect to database.")