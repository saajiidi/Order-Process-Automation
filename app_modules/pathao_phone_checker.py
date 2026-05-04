"""
Pathao Phone Checker Module
Check customer delivery history and reliability from Pathao records.
"""

import streamlit as st
import pandas as pd
import re
import requests
import time
from datetime import datetime
import os


def standardize_phone(phone: str) -> str:
    """Standardize phone number to BD format."""
    if not phone or pd.isna(phone):
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if digits.startswith('880'):
        return '+' + digits
    elif digits.startswith('01') and len(digits) == 11:
        return '+88' + digits
    return digits


def render_pathao_phone_checker():
    st.markdown(
        """
        <style>
        .pc-header{
            background:linear-gradient(90deg,#ef4444,#f97316);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        .pc-sub{color:#94a3b8;font-size:.9rem;margin-bottom:1.2rem;}
        </style>
        <div class="pc-header">🚚 Pathao Phone Checker</div>
        <div class="pc-sub">Search and validate customer delivery history from Pathao records</div>
        """,
        unsafe_allow_html=True
    )

    try:
        pathao_secrets = st.secrets.get("pathao", {})
        client_id = st.secrets.get("PATHAO_CLIENT_ID", "") or pathao_secrets.get("client_id", "")
        client_secret = st.secrets.get("PATHAO_CLIENT_SECRET", "") or pathao_secrets.get("client_secret", "")
        username = st.secrets.get("PATHAO_USERNAME", "") or pathao_secrets.get("username", "")
        password = st.secrets.get("PATHAO_PASSWORD", "") or pathao_secrets.get("password", "")
    except Exception:
        client_id, client_secret, username, password = "", "", "", ""
        
    has_secrets = bool(client_id and client_secret and username and password)

    tab_file, tab_api, tab_bulk, tab_wc_sync = st.tabs(["📂 Check from File (CSV/Excel)", "🔌 Check via API", "📦 Bulk API Check", "🔄 WC Order Sync"])

    with tab_file:
        st.markdown("#### Upload Pathao Export File")
        st.caption("Upload your Pathao orders export to quickly search for a customer's past delivery success rate.")
        
        uploaded_file = st.file_uploader("Upload Pathao Orders Export", type=['csv', 'xlsx', 'xls'], key="pathao_checker_file")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, dtype=str)
                else:
                    df = pd.read_excel(uploaded_file, dtype=str)
                    
                # Attempt to find phone and status columns
                phone_col = next((c for c in df.columns if any(k in c.lower() for k in ['phone', 'mobile', 'contact', 'recipient_phone'])), None)
                status_col = next((c for c in df.columns if any(k in c.lower() for k in ['status', 'state', 'order_status'])), None)
                
                if not phone_col:
                    st.error("Could not auto-detect a Phone Number column. Please ensure your file has a 'Phone' or 'Mobile' column.")
                    st.write("Available columns:", list(df.columns))
                else:
                    df['_std_phone'] = df[phone_col].apply(standardize_phone)
                    st.success(f"✅ Loaded {len(df):,} records successfully.")
                    
                    st.divider()
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        search_phone = st.text_input("🔍 Enter Phone Number to Search", placeholder="e.g. 01712345678")
                    
                    if search_phone:
                        std_search = standardize_phone(search_phone)
                        if not std_search:
                            std_search = search_phone

                        results = df[df['_std_phone'].str.contains(std_search, na=False) | df[phone_col].str.contains(search_phone, na=False)]
                        
                        if len(results) > 0:
                            st.markdown(f"**Found {len(results)} order(s) for this number.**")
                            
                            if status_col:
                                st.markdown("##### Delivery Status Ratio")
                                status_counts = results[status_col].value_counts()
                                cols = st.columns(min(len(status_counts), 4) or 1)
                                for i, (status, count) in enumerate(status_counts.items()):
                                    cols[i % 4].metric(status, count)
                            
                            st.dataframe(results.drop(columns=['_std_phone']), use_container_width=True, hide_index=True)
                        else:
                            st.warning("No orders found for this phone number in the uploaded dataset.")
                            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")

    with tab_api:
        st.markdown("#### Check Customer via Pathao Live API")
        st.info("Query Pathao's servers directly. Requires valid Pathao Merchant API credentials.")
        
        try:
            pathao_secrets = st.secrets.get("pathao", {})
            def_cid = st.secrets.get("PATHAO_CLIENT_ID", "") or pathao_secrets.get("client_id", "")
            def_csec = st.secrets.get("PATHAO_CLIENT_SECRET", "") or pathao_secrets.get("client_secret", "")
            def_user = st.secrets.get("PATHAO_USERNAME", "") or pathao_secrets.get("username", "")
            def_pass = st.secrets.get("PATHAO_PASSWORD", "") or pathao_secrets.get("password", "")
        except Exception:
            def_cid, def_csec, def_user, def_pass = "", "", "", ""
            
        has_secrets = bool(def_cid and def_csec and def_user and def_pass)
        if has_secrets:
            st.success("✅ Pathao API credentials loaded from secrets.toml")

        with st.expander("API Configuration", expanded=not has_secrets):
            c1, c2 = st.columns(2)
            with c1:
                client_id = st.text_input("Client ID", value=def_cid, type="password", key="pathao_cid")
                client_secret = st.text_input("Client Secret", value=def_csec, type="password", key="pathao_csec")
            with c2:
                username = st.text_input("Username (Email)", value=def_user, key="pathao_user")
                password = st.text_input("Password", value=def_pass, type="password", key="pathao_pass")
            
        api_phone = st.text_input("📱 Phone Number to Check", placeholder="e.g. 01712345678", key="pathao_api_phone")
        
        if st.button("🚀 Check via API", type="primary"):
            if not (client_id and client_secret and username and password and api_phone):
                st.error("Please fill in all API credentials and the phone number.")
            else:
                with st.spinner("Authenticating and Connecting to Pathao API..."):
                    try:
                        token_resp = requests.post(
                            "https://api-hermes.pathao.com/aladdin/api/v1/issue-token",
                            json={"client_id": client_id, "client_secret": client_secret, "username": username, "password": password, "grant_type": "password"},
                            timeout=10
                        )
                        
                        if token_resp.status_code == 200:
                            token = token_resp.json().get("access_token")
                            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
                            orders_resp = requests.get(f"https://api-hermes.pathao.com/aladdin/api/v1/orders?search={api_phone}", headers=headers, timeout=15)
                            
                            if orders_resp.status_code == 200:
                                data = orders_resp.json().get("data", {}).get("data", [])
                                if data:
                                    st.success(f"✅ Found {len(data)} order(s) for this phone number.")
                                    df_api = pd.DataFrame(data)
                                    st.dataframe(df_api, use_container_width=True, hide_index=True)
                                else:
                                    st.warning("No orders found for this phone number in your Pathao account.")
                            elif orders_resp.status_code in [401, 403]:
                                st.error("⚠️ The Pathao access token is invalid or has expired. Please verify your API credentials and permissions.")
                            else:
                                st.error(f"Failed to fetch orders. Pathao API responded with status {orders_resp.status_code}")
                        else:
                            try:
                                err_details = token_resp.json().get("error_description", "Please check your credentials.")
                            except Exception:
                                err_details = "Please check your credentials."
                            st.error(f"⚠️ Failed to authenticate (Status {token_resp.status_code}). {err_details}")
                    except Exception as e:
                        st.error(f"Network error occurred: {str(e)}")

    with tab_bulk:
        st.markdown("#### Bulk Customer Validation via Pathao API")
        st.info("Check delivery success rates for multiple phone numbers at once.")
        
        if not has_secrets:
            st.warning("⚠️ Pathao API credentials are missing from `secrets.toml`. Please add them to enable bulk checking.")
        else:
            source = st.radio("Select Data Source", ["Upload File", "WooCommerce Data (Session)"], horizontal=True)
            
            phones_to_check = []
            
            if source == "Upload File":
                bulk_file = st.file_uploader("Upload Customers List", type=['csv', 'xlsx', 'xls'], key="pathao_bulk_file")
                if bulk_file:
                    try:
                        if bulk_file.name.endswith('.csv'):
                            bulk_df = pd.read_csv(bulk_file, dtype=str)
                        else:
                            bulk_df = pd.read_excel(bulk_file, dtype=str)
                            
                        phone_col = next((c for c in bulk_df.columns if any(k in c.lower() for k in ['phone', 'mobile', 'contact', 'recipient_phone'])), None)
                        
                        selected_phone_col = st.selectbox("Select Phone Column", options=bulk_df.columns, index=list(bulk_df.columns).index(phone_col) if phone_col else 0)
                        if selected_phone_col:
                            phones_to_check = bulk_df[selected_phone_col].dropna().unique().tolist()
                            st.success(f"Found {len(phones_to_check):,} unique phone numbers.")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
            else:
                wc_df = st.session_state.get("wc_customers_data")
                if wc_df is not None and not wc_df.empty:
                    if "billing_phone" in wc_df.columns:
                        phones_to_check = wc_df["billing_phone"].dropna().unique().tolist()
                        st.success(f"✅ Loaded {len(phones_to_check):,} unique phones from WooCommerce session.")
                    else:
                        st.error("No 'billing_phone' column found in WooCommerce data.")
                else:
                    st.warning("No WooCommerce data found. Please run the WooCommerce Extraction module first, or use File Upload.")
                    
            if phones_to_check:
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    max_check = st.number_input("Max numbers to check (API Limit Prevention)", min_value=1, max_value=len(phones_to_check), value=min(50, len(phones_to_check)))
                
                if st.button("🚀 Start Bulk API Check", type="primary"):
                    phones_to_check = [standardize_phone(p) for p in phones_to_check[:max_check]]
                    phones_to_check = [p for p in phones_to_check if p]
                    
                    with st.spinner("Authenticating with Pathao API..."):
                        try:
                            token_resp = requests.post(
                                "https://api-hermes.pathao.com/aladdin/api/v1/issue-token",
                                json={"client_id": client_id, "client_secret": client_secret, "username": username, "password": password, "grant_type": "password"},
                                timeout=10
                            )
                            
                            if token_resp.status_code == 200:
                                token = token_resp.json().get("access_token")
                                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
                                
                                results = []
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                for i, phone in enumerate(phones_to_check):
                                    status_text.text(f"Checking {i+1}/{len(phones_to_check)}: {phone}")
                                    try:
                                        orders_resp = requests.get(f"https://api-hermes.pathao.com/aladdin/api/v1/orders?search={phone}", headers=headers, timeout=10)
                                        if orders_resp.status_code == 200:
                                            data = orders_resp.json().get("data", {}).get("data", [])
                                            
                                            total_orders = len(data)
                                            delivered_count = sum(1 for order in data if str(order.get('order_status', '')).lower() == 'delivered')
                                            cancelled_count = sum(1 for order in data if str(order.get('order_status', '')).lower() in ['cancelled', 'returned', 'return'])
                                            
                                            success_rate = (delivered_count / total_orders * 100) if total_orders > 0 else 0
                                            
                                            results.append({
                                                "Phone": phone,
                                                "Total Orders": total_orders,
                                                "Delivered": delivered_count,
                                                "Returned/Cancelled": cancelled_count,
                                                "Success Rate (%)": round(success_rate, 2)
                                            })
                                    except Exception:
                                        pass
                                        
                                    progress_bar.progress((i + 1) / len(phones_to_check))
                                    time.sleep(0.2)
                                    
                                status_text.text("✅ Bulk check completed!")
                                
                                if results:
                                    res_df = pd.DataFrame(results)
                                    st.dataframe(res_df.sort_values("Total Orders", ascending=False), use_container_width=True, hide_index=True)
                                    
                                    csv = res_df.to_csv(index=False).encode('utf-8')
                                    st.download_button("⬇️ Download Results (CSV)", data=csv, file_name="pathao_bulk_check_results.csv", mime="text/csv")
                                else:
                                    st.warning("No results retrieved.")
                            else:
                                st.error("Failed to authenticate. Please check your credentials.")
                        except Exception as e:
                            st.error(f"Error during bulk check: {e}")

    with tab_wc_sync:
        st.markdown("#### WooCommerce & Pathao Order Sync")
        st.info("Fetch recent WooCommerce orders and cross-reference their live delivery status on Pathao.")
        
        wc_url = os.getenv("WC_STORE_URL", "")
        wc_key = os.getenv("WC_CONSUMER_KEY", "")
        wc_sec = os.getenv("WC_CONSUMER_SECRET", "")
        try:
            if not wc_url: wc_url = st.secrets.get("WC_STORE_URL", "")
            if not wc_key: wc_key = st.secrets.get("WC_CONSUMER_KEY", "")
            if not wc_sec: wc_sec = st.secrets.get("WC_CONSUMER_SECRET", "")
            
            wc_secrets = st.secrets.get("woocommerce", {})
            if not wc_url: wc_url = wc_secrets.get("store_url", "")
            if not wc_key: wc_key = wc_secrets.get("consumer_key", "")
            if not wc_sec: wc_sec = wc_secrets.get("consumer_secret", "")
        except Exception:
            pass
            
        if not has_secrets:
            st.warning("⚠️ Pathao API credentials are missing from `secrets.toml`. Please add them to enable live syncing.")
        elif not (wc_url and wc_key and wc_sec):
            st.warning("⚠️ WooCommerce API credentials are missing from `secrets.toml`. Please add them to enable live syncing.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                days_back = st.number_input("Days to fetch from WooCommerce", min_value=1, max_value=60, value=7)
            with c2:
                wc_status = st.selectbox("WooCommerce Order Status", ["any", "processing", "completed", "on-hold", "pending"], index=0)
            
            if st.button("🔄 Fetch & Sync Status", type="primary", key="sync_wc_pathao"):
                from app_modules.wc_live_source import load_from_woocommerce
                
                # Clear cache to guarantee a fresh fetch from WooCommerce
                load_from_woocommerce.clear()
                
                with st.spinner("Fetching orders from WooCommerce..."):
                    try:
                        wc_df, _, _ = load_from_woocommerce(
                            store_url=wc_url,
                            consumer_key=wc_key,
                            consumer_secret=wc_sec,
                            days_back=days_back,
                            status=wc_status
                        )
                        
                        if wc_df.empty:
                            st.warning("No WooCommerce orders found for the selected criteria.")
                        else:
                            st.success(f"Fetched {len(wc_df)} line items from WooCommerce.")
                            orders_df = wc_df.groupby("Order ID").agg({
                                "Date": "first",
                                "Customer Name": "first",
                                "Phone": "first",
                                "Total Amount": "sum"
                            }).reset_index()
                            
                            st.info(f"Checking Pathao status for {len(orders_df)} unique orders...")
                            
                            token_resp = requests.post(
                                "https://api-hermes.pathao.com/aladdin/api/v1/issue-token",
                                json={"client_id": client_id, "client_secret": client_secret, "username": username, "password": password, "grant_type": "password"},
                                timeout=10
                            )
                            
                            if token_resp.status_code == 200:
                                token = token_resp.json().get("access_token")
                                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
                                
                                pathao_statuses = []
                                pathao_consignment = []
                                
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                for i, row in orders_df.iterrows():
                                    order_id = str(row["Order ID"])
                                    phone = str(row["Phone"])
                                    
                                    status_text.text(f"Checking Order {order_id}...")
                                    p_status = "Not Found"
                                    p_cons = "N/A"
                                    
                                    try:
                                        resp = requests.get(f"https://api-hermes.pathao.com/aladdin/api/v1/orders?search={order_id}", headers=headers, timeout=10)
                                        data = resp.json().get("data", {}).get("data", []) if resp.status_code == 200 else []
                                            
                                        if not data and phone:
                                            std_phone = standardize_phone(phone)
                                            if std_phone:
                                                resp = requests.get(f"https://api-hermes.pathao.com/aladdin/api/v1/orders?search={std_phone}", headers=headers, timeout=10)
                                                data = resp.json().get("data", {}).get("data", []) if resp.status_code == 200 else []
                                                
                                        if data:
                                            match = next((o for o in data if str(order_id) in str(o.get('merchant_order_id', ''))), None)
                                            if not match:
                                                match = data[0]
                                                
                                            p_status = str(match.get('order_status', 'Unknown')).title()
                                            p_cons = str(match.get('consignment_id', 'N/A'))
                                    except Exception:
                                        pass
                                        
                                    pathao_statuses.append(p_status)
                                    pathao_consignment.append(p_cons)
                                    
                                    progress_bar.progress((i + 1) / len(orders_df))
                                    time.sleep(0.1)
                                    
                                status_text.text("✅ Sync completed!")
                                
                                orders_df["Pathao Status"] = pathao_statuses
                                orders_df["Consignment ID"] = pathao_consignment
                                
                                def color_status(val):
                                    if val == 'Delivered': return 'color: #10b981; font-weight: bold'
                                    elif val in ['Cancelled', 'Returned', 'Return']: return 'color: #ef4444; font-weight: bold'
                                    elif val == 'Not Found': return 'color: #94a3b8'
                                    else: return 'color: #f59e0b'
                                
                                try:
                                    styled_df = orders_df.style.map(color_status, subset=['Pathao Status'])
                                except AttributeError:
                                    styled_df = orders_df.style.applymap(color_status, subset=['Pathao Status'])
                                    
                                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                                
                                csv = orders_df.to_csv(index=False).encode('utf-8')
                                st.download_button("⬇️ Download Synced Orders (CSV)", data=csv, file_name=f"wc_pathao_sync_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
                                
                            else:
                                st.error("Failed to authenticate with Pathao API. Check credentials.")
                    except Exception as e:
                        st.error(f"Error during sync: {e}")