import io

import pandas as pd
import plotly.express as px
import streamlit as st

from app_modules.error_handler import log_error
from app_modules.persistence import clear_state_keys, save_state
from app_modules.ui_components import (
    render_action_bar,
    render_reset_confirm,
    render_steps,
    section_card,
)
from app_modules.ui_config import INVENTORY_LOCATIONS
from inventory_modules import core as inv_core


def _read_uploaded(uploaded_file):
    if not uploaded_file:
        return None
    uploaded_file.seek(0)
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def _reset_inventory_state():
    clear_state_keys(["inv_res_data", "inv_active_l", "inv_t_col"])


def _render_upload_summary(master_df, title_col):
    c1, c2 = st.columns(2)
    c1.metric("Master rows", 0 if master_df is None else len(master_df))
    c2.metric("Title column", title_col if title_col else "Not detected")


def render_distribution_tab(search_q, guided: bool = True):
    section_card(
        "Distribution Hub",
        "Analyze stock mapping, monitor low-stock risk, and export pick manifests.",
    )

    if guided:
        step = 0
        if st.session_state.get("inv_res_data") is not None:
            step = 2
        render_steps(["Upload", "Validate", "Analyze", "Export"], step)

    matrix_tab, insights_tab, pick_tab = st.tabs([
        "Matrix Analyzer",
        "Distribution Insights",
        "Actionable Pick List",
    ])

    with matrix_tab:
        st.subheader("Upload and Analyze")
        master_file = st.file_uploader("Master Stock List (required)", type=["xlsx", "csv"], key="inv_up")

        st.caption("Outlet stock files (optional)")
        loc_files = {}
        loc_cols = st.columns(len(INVENTORY_LOCATIONS))
        for i, loc in enumerate(INVENTORY_LOCATIONS):
            with loc_cols[i]:
                uploaded = st.file_uploader(f"{loc}", key=f"inv_l_{loc}", type=["xlsx", "csv"])
                if uploaded:
                    loc_files[loc] = uploaded

        master_df = None
        title_col = None
        sku_col = None
        if master_file:
            try:
                master_df = _read_uploaded(master_file)
                _, _, title_col, sku_col = inv_core.identify_columns(master_df)
                _render_upload_summary(master_df, title_col)
                if not title_col:
                    st.error("Could not detect an item title/name column in the master list.")
                else:
                    st.success("Validation passed. Ready to run analysis.")
            except Exception as exc:
                log_error(exc, context="Inventory Upload")
                st.error("Failed to read master stock list.")

        analyze_clicked, clear_clicked = render_action_bar(
            primary_label="Analyze distribution",
            primary_key="inv_analyze_btn",
            secondary_label="Clear inventory data",
            secondary_key="inv_clear_btn",
        )

        if clear_clicked:
            _reset_inventory_state()
            st.rerun()

        if analyze_clicked:
            if master_df is None or not title_col:
                st.warning("Upload a valid master stock list before analysis.")
            else:
                try:
                    inventory_map, warnings, _, sku_map = inv_core.load_inventory_from_uploads(loc_files)
                    if warnings:
                        for warning in warnings:
                            st.warning(warning)

                    result_df, _ = inv_core.add_stock_columns_from_inventory(
                        master_df,
                        title_col,
                        inventory_map,
                        INVENTORY_LOCATIONS,
                        sku_col,
                        sku_map,
                    )

                    st.session_state.inv_res_data = result_df
                    st.session_state.inv_active_l = INVENTORY_LOCATIONS
                    st.session_state.inv_t_col = title_col
                    save_state()
                    st.success("Distribution analysis complete.")
                except Exception as exc:
                    log_error(exc, context="Inventory Analyze")
                    st.error("Distribution analysis failed.")

        if st.session_state.get("inv_res_data") is not None:
            df = st.session_state.inv_res_data.copy()
            title_key = st.session_state.inv_t_col
            active_locations = st.session_state.inv_active_l

            if search_q:
                df = df[df[title_key].astype(str).str.lower().str.contains(search_q.lower(), na=False)]

            st.dataframe(df, use_container_width=True, hide_index=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Distribution")
            st.download_button(
                "Download distribution report",
                output.getvalue(),
                "Stock_Distribution.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )

    with insights_tab:
        st.subheader("Inventory Health")
        if st.session_state.get("inv_res_data") is None:
            st.info("Run matrix analysis first.")
        else:
            inv_df = st.session_state.inv_res_data
            locs = st.session_state.inv_active_l
            title_key = st.session_state.inv_t_col

            c1, c2 = st.columns(2)
            with c1:
                melted = inv_df.melt(
                    id_vars=[title_key],
                    value_vars=locs,
                    var_name="Location",
                    value_name="Stock",
                )
                heatmap = px.density_heatmap(
                    melted,
                    x="Location",
                    y=title_key,
                    z="Stock",
                    color_continuous_scale="RdYlGn",
                    title="Stock by item and location",
                )
                st.plotly_chart(heatmap, use_container_width=True)

            with c2:
                totals = inv_df[locs].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
                pie = px.pie(values=totals.values, names=totals.index, title="Location stock distribution", hole=0.4)
                st.plotly_chart(pie, use_container_width=True)

            threshold = st.session_state.get("low_stock_threshold", 5)
            total_stock = inv_df[locs].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
            low_stock = inv_df[total_stock < threshold]

            if low_stock.empty:
                st.success("No low-stock items below current safety threshold.")
            else:
                st.warning(f"{len(low_stock)} items are below threshold ({threshold}).")
                st.dataframe(low_stock[[title_key, *locs]], use_container_width=True, hide_index=True)

    with pick_tab:
        st.subheader("Daily Pick Manifest")
        if st.session_state.get("inv_res_data") is None:
            st.info("Run matrix analysis first.")
        else:
            inv_df = st.session_state.inv_res_data
            locs = st.session_state.inv_active_l
            title_key = st.session_state.inv_t_col

            if "Dispatch Suggestion" not in inv_df.columns:
                st.warning("Dispatch Suggestion column not available.")
            else:
                manifest_rows = []
                for loc in locs:
                    loc_df = inv_df[inv_df["Dispatch Suggestion"] == loc]
                    if loc_df.empty:
                        continue
                    _, qty_col, _, _ = inv_core.identify_columns(loc_df)
                    if qty_col and qty_col in loc_df.columns:
                        summary = loc_df.groupby(title_key)[qty_col].sum().reset_index()
                    else:
                        summary = loc_df.groupby(title_key).size().reset_index(name="Quantity")
                        qty_col = "Quantity"

                    summary.columns = ["Item Name", "Pick Quantity"]
                    st.markdown(f"**{loc}**")
                    st.dataframe(summary, use_container_width=True, hide_index=True)

                    for _, row in summary.iterrows():
                        manifest_rows.append({"Location": loc, "Item Name": row["Item Name"], "Quantity": row["Pick Quantity"]})

                if manifest_rows:
                    manifest_df = pd.DataFrame(manifest_rows)
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                        manifest_df.to_excel(writer, index=False, sheet_name="Picking_Manifest")
                    st.download_button(
                        "Download picking manifest",
                        out.getvalue(),
                        "Picking_Manifest.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

    render_reset_confirm("inventory", _reset_inventory_state)
