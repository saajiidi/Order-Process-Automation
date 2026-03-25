import streamlit as st
import pandas as pd
import requests

def render_whatsapp_api_tab():
    st.subheader("📲 WhatsApp Business API (Beta)")
    st.info("Send bulk messages directly via official WhatsApp API.")
    
    with st.expander("Configuration", expanded=False):
        token = st.text_input("Access Token", type="password")
        phone_id = st.text_input("Phone Number ID")
        template_name = st.text_input("Template Name")
        
    if "wp_preview_df" in st.session_state and st.session_state.wp_preview_df is not None:
        df = st.session_state.wp_preview_df
        st.write(f"Ready to process {len(df)} orders.")
        
        if st.button("Send API Broadcast"):
            st.warning("Direct API broadcasting is in private preview. Contact admin for access.")
    else:
        st.warning("No data found. Upload data in the WhatsApp tab first.")
