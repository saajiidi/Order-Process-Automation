import streamlit as st
import os
import re
import hashlib
import pandas as pd
from app_modules.ui_components import terminal_chat_bubble
from app_modules.error_handler import safe_render
from app_modules.unified_reporting import UnifiedReportGenerator, ReportSection, ReportMetadata

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def _get_data_context():
    """Scans session state for active DataFrames and creates a summary for the AI."""
    context_blocks = []
    df_keys = {
        "unified_customer_df": "Unified Customer Analytics Data",
        "return_insight_df": "Return Insights Data",
        "wc_customers_data": "WooCommerce Customers Data",
        "wc_phone_data": "WooCommerce Phone Extraction",
        "pathao_res_df": "Bulk Order (Pathao) Data",
        "inv_res_data": "Inventory Distribution Data",
        "ce_df": "Customer Extractor Data"
    }
    
    for key, desc in df_keys.items():
        df = st.session_state.get(key)
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            shape = df.shape
            cols = list(df.columns)[:10]  # First 10 cols to save tokens
            context_blocks.append(f"- **{desc}**: {shape[0]} rows. Columns include: {cols}.")
            
    return "Available Datasets in Session:\n" + "\n".join(context_blocks) if context_blocks else "No active datasets loaded by the user yet."


def _execute_ai_code(code: str, context_dfs: dict):
    """Safely executes AI-generated Streamlit/Plotly code."""
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Provide standard data libraries to the executing environment
    local_env = {
        "st": st, "pd": pd, "px": px, "go": go, **context_dfs
    }
    
    try:
        # Execute the code block natively inside the Streamlit app
        with st.container():
            exec(code, local_env)
            
        # Export to Unified Excel Report if AI populated the specific variables
        if "ai_report_df" in local_env and isinstance(local_env["ai_report_df"], pd.DataFrame):
            df = local_env["ai_report_df"]
            title = local_env.get("ai_report_title", "AI Generated Analysis")
            c_type = local_env.get("ai_chart_type", None)
            c_col = local_env.get("ai_chart_col", None)
            c_fig = local_env.get("ai_report_fig", None)
            
            generator = UnifiedReportGenerator(metadata=ReportMetadata(title=title, generated_by="AI Data Pilot"))
            generator.add_section(ReportSection(title="Data Insights", dataframe=df, description="AI Generated Analysis", chart_type=c_type, chart_column=c_col, chart_figure=c_fig))
            
            code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
            st.download_button(
                label=f"📥 Download {title} (Unified Excel)",
                data=generator.generate_excel(),
                file_name=f"{title.replace(' ', '_').lower()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                key=f"ai_export_{code_hash}"
            )
    except Exception as e:
        st.error(f"⚠️ The AI generated invalid code that failed to execute: {e}")
        with st.expander("View Failed Code"):
            st.code(code, language="python")

@safe_render(fallback_message="AI Data Pilot encountered an error.")
def render_ai_data_pilot_tab():
    st.markdown(
        """
        <style>
        .ai-header{
            background:linear-gradient(90deg,#8b5cf6,#d946ef);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            font-size:1.7rem;font-weight:800;margin-bottom:.2rem;
        }
        </style>
        <div class="ai-header">🤖 AI Data Pilot</div>
        """,
        unsafe_allow_html=True
    )
    st.caption("Conversational AI Agent for Data Analytics powered by Llama 3 (via Groq).")
    
    if not GROQ_AVAILABLE:
        st.error("⚠️ The 'groq' Python library is not installed. Please run `pip install groq` in your environment to use the AI Pilot.")
        return

    # Securely retrieve the Groq API key
    groq_api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    
    if not groq_api_key:
        st.warning("⚠️ GROQ API Key not found in `secrets.toml` or environment variables.")
        groq_api_key = st.text_input("Enter your Groq API Key temporarily:", type="password")
        if not groq_api_key:
            return

    client = Groq(api_key=groq_api_key)
    
    # Dynamically inject the dataframe schemas into the AI's awareness
    # Create dictionary of available dataframes for code execution
    df_keys = ["unified_customer_df", "return_insight_df", "wc_customers_data", "wc_phone_data", "pathao_res_df", "inv_res_data", "ce_df"]
    context_dfs = {}
    for k in df_keys:
        df = st.session_state.get(k)
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            context_dfs[k] = df
            
    data_context = _get_data_context()
    
    system_prompt = {
        "role": "system",
        "content": ("You are the DEEN-OPS AI Data Pilot, an advanced analytics assistant built into the Automation Hub Pro platform. "
                    "Provide concise, data-driven, and highly analytical answers. Format your output beautifully using Markdown.\n"
                    "If the user asks to draw a chart, plot, or visualize data, WRITE VALID PYTHON CODE using plotly.express (px) and streamlit (st).\n"
                    "ALWAYS wrap your code in a standard markdown block (```python ... ```).\n"
                    "Assume the pandas DataFrames are ALREADY LOADED in the environment with the EXACT variable names listed below.\n"
                    "IMPORTANT: To allow users to download your analysis, ALWAYS save your final DataFrame to a variable named `ai_report_df`.\n"
                    "Also assign the Plotly figure object to a variable named `ai_report_fig` so it can be exported natively to Excel.\n"
                    "Also assign a string to `ai_report_title` (e.g., 'Top Spenders').\n"
                    "Example output format:\n"
                    "```python\n"
                    "ai_report_title = 'Top Spenders'\n"
                    "ai_report_df = unified_customer_df.head(10)\n"
                    "fig = px.bar(unified_customer_df.head(10), x='primary_name', y='total_spent', title='Top Spenders')\n"
                    "ai_report_fig = fig\n"
                    "st.plotly_chart(fig, use_container_width=True)\n"
                    "```\n\n"
                    f"--- SYSTEM AWARENESS ---\n{data_context}\n\nUse this context to inform the user about what data is currently available to analyze.")
    }
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Initializing DEEN-OPS AI Pilot...\nSystems online. Connected to Llama 3. How can I assist with your data today?"}
        ]
        
    for msg in st.session_state.chat_history:
        if msg["role"] == "assistant":
            terminal_chat_bubble(msg["content"])
            # Re-render any charts generated in past interactions
            code_blocks = re.findall(r"```python\n(.*?)\n```", msg["content"], re.DOTALL)
            for code in code_blocks:
                _execute_ai_code(code, context_dfs)
        else:
            with st.chat_message("user"):
                st.write(msg["content"])
                
    prompt = st.chat_input("Ask me to analyze sales, find anomalies, or generate a report...")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        with st.spinner("Processing through DEEN-OPS Neural Core..."):
            try:
                # Memory Management: Keep system prompt + last 10 messages (5 full exchanges) to prevent max token limit exceptions.
                MAX_HISTORY = 10
                history_to_send = st.session_state.chat_history[-MAX_HISTORY:]
                
                messages = [system_prompt] + [
                    {"role": m["role"], "content": m["content"]} 
                    for m in history_to_send
                ]
                
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="llama3-70b-8192",  # You can switch to "llama3-8b-8192" for even faster/cheaper inference
                    temperature=0.4,
                    max_tokens=1024,
                )
                response_text = chat_completion.choices[0].message.content
            except Exception as e:
                response_text = f"[SYSTEM ERROR] Failed to connect to LLM Core: {str(e)}"
                
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        
        # Render the response and immediately execute any new code generated
        st.rerun()