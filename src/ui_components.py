import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data_loader import calc_weighted_avg, aggregate_kpis
from src.pdf_generator import generate_pdf_report

def render_kpi_cards(filtered_df):
    """Hiển thị 6 thẻ KPI chính cho 3G."""
    s_tr = filtered_df.get("TRAFFIC", pd.Series([0]))
    s_cv = filtered_df.get("CALLVOLUME", pd.Series([0]))
    s_cssr = filtered_df.get("CSSR", pd.Series([0]))
    s_dcr = filtered_df.get("DCR", pd.Series([0]))
    s_soft = filtered_df.get("SOFTHOSR", pd.Series([0]))
    s_cong = filtered_df.get("CSCONGES", pd.Series([0]))

    def render_card(cat, title, val, tgt, min_v, max_v, remark, stt="good"):
        s_low = stt.lower()
        html_str = (
            f'<div class="kpi-card"><div class="kpi-hdr"><div>'
            f'<div class="kpi-cat">{cat}</div><div class="kpi-ttl">{title}</div></div>'
            f'<span class="kpi-bdg bdg-{s_low}">{stt.upper()}</span></div>'
            f'<div class="kpi-body"><span class="kpi-val val-{s_low}">{val}</span>'
            f'<span class="kpi-tgt">Target: {tgt}</span></div>'
            f'<div class="kpi-ftr"><span>Min: {min_v} Max: {max_v}</span>'
            f'<span>{remark}</span></div></div>'
        )
        st.markdown(html_str, unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        v = s_tr.sum()
        render_card("Traffic", "CS Traffic", f"{v:,.2f} Erl", "N/A", f"{s_tr.min():.1f}", f"{s_tr.max():.1f}", "Tổng lưu lượng CS", "EXCELLENT")
    with c2:
        v = s_cv.sum()
        render_card("Call Volume", "Call Volume", f"{v:,.0f}", "N/A", f"{s_cv.min():.0f}", f"{s_cv.max():.0f}", "Tổng cuộc gọi", "EXCELLENT")
    with c3:
        v = calc_weighted_avg(filtered_df, "CSSR")
        render_card("Accessibility", "Call Setup SR (CSSR)", f"{v:.2f}%", ">=99.00%", f"{s_cssr.min():.1f}%", f"{s_cssr.max():.1f}%", "Thiết lập cuộc gọi", "GOOD" if v >= 99.0 else "WARNING")
    with c4:
        v = calc_weighted_avg(filtered_df, "DCR")
        render_card("Retainability", "Drop Call Rate (DCR)", f"{v:.3f}%", "<=1.000%", f"{s_dcr.min():.3f}%", f"{s_dcr.max():.3f}%", "Tỷ lệ rớt cuộc gọi", "WARNING" if v > 1.0 else "GOOD")
    with c5:
        v = calc_weighted_avg(filtered_df, "SOFTHOSR")
        render_card("Mobility", "Soft Handover SR", f"{v:.2f}%", ">=99.00%", f"{s_soft.min():.1f}%", f"{s_soft.max():.1f}%", "Chuyển giao mềm 3G", "GOOD" if v >= 99.0 else "WARNING")
    with c6:
        v = calc_weighted_avg(filtered_df, "CSCONGES")
        render_card("Capacity", "CS Congestion Rate", f"{v:.3f}%", "<=0.500%", f"{s_cong.min():.3f}%", f"{s_cong.max():.3f}%", "Tỷ lệ nghẽn thoại CS", "GOOD" if v <= 0.5 else "WARNING")


def render_freqband_section(filtered_df, cell_col):
    """Hiển thị phân bổ Cell, Traffic & Call Volume theo Freqband/Sóng mang."""
    st.subheader("📊 Thống Kê Phân Bổ Cell, Traffic & Call Volume Theo Freqband")

    fb_cell_counts, fb_tf_df, cell_type_counts, fb_type_xtab, fb_cv_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if cell_col and cell_col in filtered_df.columns and "Freqband" in filtered_df.columns:
        _cols = [cell_col, "Freqband"] + (["Cell Type"] if "Cell Type" in filtered_df.columns else [])
        cell_fb_df = filtered_df[_cols].drop_duplicates(subset=[cell_col])

        fb_cell_counts = cell_fb_df["Freqband"].value_counts().reset_index()
        fb_cell_counts.columns = ["Freqband", "Số lượng Cell"]
        fb_cell_counts = fb_cell_counts.sort_values(by="Freqband")

        fb_col1, fb_col2, fb_col3, fb_col4 = st.columns(4)

        # 1. Số lượng Cell theo Freqband
        fig_fb_cell = px.pie(fb_cell_counts, names="Freqband", values="Số lượng Cell", title="<b>Số lượng Cell theo Freqband</b>", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_fb_cell.update_traces(textinfo="label+value+percent", textfont_size=11)
        fig_fb_cell.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=40, b=10))
        with fb_col1: st.plotly_chart(fig_fb_cell, use_container_width=True)

        # 2. Số lượng Cell theo Loại Cell
        if "Cell Type" in cell_fb_df.columns:
            cell_type_counts = cell_fb_df["Cell Type"].value_counts().reset_index()
            cell_type_counts.columns = ["Cell Type", "Số lượng Cell"]
            cell_type_counts = cell_type_counts.sort_values(by="Cell Type", ascending=False)

            fb_type_xtab = pd.crosstab(cell_fb_df["Freqband"], cell_fb_df["Cell Type"])
            for col_type in ["VNP", "MORAN"]:
                if col_type not in fb_type_xtab.columns:
                    fb_type_xtab[col_type] = 0
            fb_type_xtab = fb_type_xtab.reindex(columns=["VNP", "MORAN"], fill_value=0)
            fb_type_xtab["Tổng"] = fb_type_xtab.sum(axis=1)
            fb_type_xtab = fb_type_xtab.sort_index().reset_index()

            fig_ct = px.pie(cell_type_counts, names="Cell Type", values="Số lượng Cell", title="<b>Số lượng Cell theo Loại Cell</b>", hole=0.4, color="Cell Type", color_discrete_map={"VNP": "#3b82f6", "MORAN": "#f59e0b"})
            fig_ct.update_traces(textinfo="label+value+percent", textfont_size=11)
            fig_ct.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=40, b=10))
            with fb_col2: st.plotly_chart(fig_ct, use_container_width=True)

        # 3. CS Traffic (Erl) theo Freqband
        if "TRAFFIC" in filtered_df.columns:
            fb_tf_df = filtered_df.groupby("Freqband")["TRAFFIC"].sum().reset_index().sort_values(by="Freqband")
            fig_fb_tf = px.bar(fb_tf_df, x="Freqband", y="TRAFFIC", text="TRAFFIC", title="<b>CS Traffic (Erl) theo Freqband</b>", color="Freqband", color_discrete_sequence=px.colors.qualitative.Set2)
            fig_fb_tf.update_traces(texttemplate='%{text:,.1f} Erl', textposition='outside')
            fig_fb_tf.update_layout(template="plotly_dark", height=300, showlegend=False, margin=dict(l=10, r=10, t=40, b=10), yaxis_title="Traffic (Erl)", xaxis_title="Freqband")
            with fb_col3: st.plotly_chart(fig_fb_tf, use_container_width=True)

        # 4. Call Volume theo Freqband
        if "CALLVOLUME" in filtered_df.columns:
            fb_cv_df = filtered_df.groupby("Freqband")["CALLVOLUME"].sum().reset_index().sort_values(by="Freqband")
            fig_fb_cv = px.bar(fb_cv_df, x="Freqband", y="CALLVOLUME", text="CALLVOLUME", title="<b>Call Volume theo Freqband</b>", color="Freqband", color_discrete_sequence=px.colors.qualitative.Set3)
            fig_fb_cv.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_fb_cv.update_layout(template="plotly_dark", height=300, showlegend=False, margin=dict(l=10, r=10, t=40, b=10), yaxis_title="Call Volume", xaxis_title="Freqband")
            with fb_col4: st.plotly_chart(fig_fb_cv, use_container_width=True)

        if not fb_type_xtab.empty:
            st.markdown("**Bảng thống kê số lượng Cell, Traffic & Call Volume theo Freqband:**")
            _xt = fb_type_xtab.copy()
            if not fb_tf_df.empty:
                tf_map = dict(zip(fb_tf_df["Freqband"], fb_tf_df["TRAFFIC"]))
                _xt["CS Traffic (Erl)"] = _xt["Freqband"].map(tf_map).round(2)
            if not fb_cv_df.empty:
                cv_map = dict(zip(fb_cv_df["Freqband"], fb_cv_df["CALLVOLUME"]))
                _xt["Call Volume"] = _xt["Freqband"].map(cv_map).round(0)

            total_row = {"Freqband": "Tổng", "VNP": int(_xt["VNP"].sum()), "MORAN": int(_xt["MORAN"].sum()), "Tổng": int(_xt["Tổng"].sum())}
            if "CS Traffic (Erl)" in _xt.columns:
                total_row["CS Traffic (Erl)"] = round(_xt["CS Traffic (Erl)"].sum(), 2)
            if "Call Volume" in _xt.columns:
                total_row["Call Volume"] = int(_xt["Call Volume"].sum())

            df_display = pd.concat([_xt, pd.DataFrame([total_row])], ignore_index=True)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    return fb_cell_counts, fb_tf_df, cell_type_counts, fb_type_xtab, fb_cv_df


def render_trend_chart(filtered_df, has_hour):
    """Biểu đồ xu hướng kết hợp Traffic & KPI 3G theo Freqband."""
    st.subheader("📈 Biểu Đồ Tương Quan Xu HƯỚNG KPI 3G")

    kpi_dict = {
        "CSSR - Tỷ lệ thiết lập (%)": "CSSR",
        "DCR - Tỷ lệ rớt cuộc gọi (%)": "DCR",
        "SOFTHOSR - Chuyển giao mềm (%)": "SOFTHOSR",
        "CSCONGES - Tỷ lệ nghẽn (%)": "CSCONGES",
        "CALLVOLUME - Số lượng cuộc gọi": "CALLVOLUME",
    }
    avail_kpis = {k: v for k, v in kpi_dict.items() if v in filtered_df.columns}

    if avail_kpis:
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 1])
        with ctrl_col1:
            time_mode = st.radio("⏱ Thời gian:", ["Chỉ theo giờ (24h Avg)", "Theo Ngày & Giờ (Timeline)"], horizontal=True)
        with ctrl_col2:
            sel_kpi_lbl = st.selectbox("🎯 Chọn KPI kết hợp với Traffic:", options=list(avail_kpis.keys()))
        with ctrl_col3:
            if "Freqband" in filtered_df.columns:
                all_fb = sorted(filtered_df["Freqband"].dropna().unique().tolist())
                fb_options = ["Tất cả Freqband"] + all_fb
                sel_fb = st.selectbox("📡 Chọn Freqband:", options=fb_options)
            else:
                sel_fb = "Tất cả Freqband"

        # Lọc dữ liệu theo Freqband đã chọn
        trend_df = filtered_df.copy()
        if sel_fb != "Tất cả Freqband" and "Freqband" in trend_df.columns:
            trend_df = trend_df[trend_df["Freqband"] == sel_fb]

        if trend_df.empty:
            st.warning("⚠️ Không có dữ liệu cho Freqband đã chọn!")
            return

        sel_kpi_col = avail_kpis[sel_kpi_lbl]

        if time_mode == "Chỉ theo giờ (24h Avg)":
            if has_hour and "Hour" in trend_df.columns:
                c_data = aggregate_kpis(trend_df, ["Hour"])
                x_axis = c_data["Hour"]
                x_title = "Giờ trong ngày (0h - 23h)"
            else:
                c_data = aggregate_kpis(trend_df, ["Date"])
                x_axis = pd.to_datetime(c_data["Date"]).dt.strftime("%d/%m")
                x_title = "Ngày"
        else:
            group_cols = [col for col in ["Date", "Hour", "DateTime"] if col in trend_df.columns]
            if not has_hour and "Hour" in group_cols: group_cols.remove("Hour")
            if group_cols:
                c_data = aggregate_kpis(trend_df, group_cols)
                if "DateTime" in c_data.columns:
                    c_data = c_data.sort_values(by="DateTime")
                    fmt_str = "%d/%m %H:00" if has_hour else "%d/%m"
                    c_data["TimeLabel"] = pd.to_datetime(c_data["DateTime"]).dt.strftime(fmt_str)
                elif "Date" in c_data.columns:
                    c_data["TimeLabel"] = pd.to_datetime(c_data["Date"]).dt.strftime("%d/%m")
                else:
                    c_data["TimeLabel"] = c_data["Hour"].astype(str) + ":00"
            else:
                c_data = aggregate_kpis(trend_df, ["Date"])
                c_data["TimeLabel"] = "Timeline"

            x_axis = c_data["TimeLabel"]
            x_title = "Thời Gian (Ngày/Giờ)" if has_hour else "Thời Gian (Ngày)"

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        if "TRAFFIC" in c_data.columns:
            fig.add_trace(go.Bar(x=x_axis, y=c_data["TRAFFIC"], name="Traffic (Erl)", marker_color="rgba(2, 132, 199, 0.5)"), secondary_y=False)
        if sel_kpi_col in c_data.columns:
            fig.add_trace(go.Scatter(x=x_axis, y=c_data[sel_kpi_col], name=sel_kpi_lbl, mode="lines+markers", line=dict(color="#ef4444", width=2.5)), secondary_y=True)

        fb_suffix = f" (Freqband: {sel_fb})" if sel_fb != "Tất cả Freqband" else ""
        fig.update_layout(title_text=f"📊 Biểu đồ Traffic (Erl) và {sel_kpi_lbl}{fb_suffix}", template="plotly_dark", hovermode="x unified", height=420, margin=dict(l=10, r=10, t=40, b=10))
        fig.update_xaxes(title_text=x_title, type="category")
        
        # Định dạng trục Y1 (Traffic) làm tròn 2 số thập phân
        fig.update_yaxes(title_text="CS Traffic (Erl)", secondary_y=False, showgrid=False, tickformat=".2f")
        
        # Định dạng trục Y2 (KPI): Nếu là CALLVOLUME thì để số nguyên, ngược lại làm tròn 2 số thập phân
        kpi_tick_fmt = ",.0f" if sel_kpi_col == "CALLVOLUME" else ".2f"
        fig.update_yaxes(title_text=sel_kpi_lbl, secondary_y=True, showgrid=True, gridcolor="rgba(255,255,255,0.1)", tickformat=kpi_tick_fmt)

        st.plotly_chart(fig, use_container_width=True)


def render_top_traffic_section(filtered_df, site_col, cell_col):
    """Bảng Top High Traffic Site & Cell."""
    st.subheader("🔥 Top N Site & Top N Cell Có Lưu Lượng (Traffic) Cao Nhất")
    tr_col1, tr_col2 = st.columns([2, 1])
    with tr_col1: st.markdown("Lọc danh sách Top Site và Top Cell 3G có lưu lượng CS Traffic (Erlang) lớn nhất.")
    with tr_col2: top_n_traffic = st.number_input("🔢 Nhập số lượng Top N cần xem:", min_value=1, max_value=200, value=10, step=1)

    top_cell_df, top_site_df, cell_agg_all = pd.DataFrame(), pd.DataFrame(), None

    if "TRAFFIC" in filtered_df.columns:
        tab_cell, tab_site = st.tabs(["📱 Top Cell Traffic", "🏢 Top Site Traffic"])
        grp_cols = [c for c in [site_col, cell_col] if c is not None and c in filtered_df.columns]
        if grp_cols:
            cell_agg_all = aggregate_kpis(filtered_df, grp_cols)
            top_cell_df = cell_agg_all.nlargest(int(top_n_traffic), "TRAFFIC")
            with tab_cell:
                st.markdown(f"**Top {top_n_traffic} Cell có lưu lượng cao nhất:**")
                st.dataframe(top_cell_df, use_container_width=True)

        if site_col and site_col in filtered_df.columns:
            top_site_df = aggregate_kpis(filtered_df, [site_col]).nlargest(int(top_n_traffic), "TRAFFIC")
            with tab_site:
                st.markdown(f"**Top {top_n_traffic} Site có lưu lượng cao nhất:**")
                st.dataframe(top_site_df, use_container_width=True)

    return top_cell_df, top_site_df, cell_agg_all


def render_worst_cells_and_pdf(filtered_df, site_col, cell_col, cell_agg_all, top_site_df, top_cell_df, fb_cell_counts, fb_tf_df, cell_type_counts, fb_type_xtab, fb_cv_df, sel_dates, sel_sites, has_hour):
    """Bảng Worst Cells Matrix & Xuất Báo Cáo PDF cho 3G."""
    st.subheader("⚠️ Danh Sách Worst N Cells Theo Chỉ Số KPI 3G")

    if cell_col and cell_col in filtered_df.columns:
        kpi_options_dict = {
            "CSSR Thấp (Call Setup Success Rate)": ("CSSR", True),
            "DCR Cao (Drop Call Rate)": ("DCR", False),
            "SOFTHOSR Thấp (Soft Handover SR)": ("SOFTHOSR", True),
            "CSCONGES Cao (CS Congestion Rate)": ("CSCONGES", False),
        }
        available_kpi_options = {lbl: (col, is_asc) for lbl, (col, is_asc) in kpi_options_dict.items() if col in filtered_df.columns}

        if available_kpi_options:
            kpi_col1, kpi_col2 = st.columns([2, 1])
            with kpi_col1: sel_worst_kpi_lbl = st.selectbox("🎯 Chọn KPI cần xem trên giao diện:", options=list(available_kpi_options.keys()))
            with kpi_col2: top_n_worst = st.number_input("🔢 Nhập số lượng Worst Cells (N):", min_value=1, max_value=200, value=10, step=1)

            target_col, sort_ascending = available_kpi_options[sel_worst_kpi_lbl]
            grp_worst_cols = [c for c in [site_col, cell_col] if c is not None and c in filtered_df.columns]

            if grp_worst_cols:
                cell_agg = cell_agg_all if cell_agg_all is not None else aggregate_kpis(filtered_df, grp_worst_cols)
                res_df = (cell_agg.nsmallest(int(top_n_worst), target_col) if sort_ascending else cell_agg.nlargest(int(top_n_worst), target_col)) if target_col in cell_agg.columns else cell_agg.head(int(top_n_worst))

                st.markdown(f"**Danh sách Top {top_n_worst} Worst Cells theo `{sel_worst_kpi_lbl}`:**")
                st.dataframe(res_df, use_container_width=True)

                st.markdown("---")
                st.markdown("### 📄 PDF Report Export")

                s_tr = filtered_df.get("TRAFFIC", pd.Series([0]))
                _pdf_sig = (len(filtered_df), round(float(s_tr.sum()), 3), tuple(map(str, sel_dates)), len(sel_sites))

                if st.button("📑 Tạo Báo Cáo PDF"):
                    with st.spinner("Đang tạo PDF..."):
                        _top = lambda col, asc: (cell_agg.nsmallest(10, col) if asc else cell_agg.nlargest(10, col)) if col in cell_agg.columns else pd.DataFrame()
                        worst10_cssr = _top("CSSR", True)
                        worst10_dcr = _top("DCR", False)
                        worst10_soft = _top("SOFTHOSR", True)
                        worst10_cong = _top("CSCONGES", False)

                        top10_sites_pdf = top_site_df.head(10) if not top_site_df.empty else pd.DataFrame()
                        top10_cells_pdf = top_cell_df.head(10) if not top_cell_df.empty else pd.DataFrame()

                        summary_data = {
                            "tr": s_tr.sum(),
                            "cv": filtered_df.get("CALLVOLUME", pd.Series([0])).sum(),
                            "cssr": calc_weighted_avg(filtered_df, "CSSR"),
                            "dcr": calc_weighted_avg(filtered_df, "DCR"),
                            "soft": calc_weighted_avg(filtered_df, "SOFTHOSR"),
                            "cong": calc_weighted_avg(filtered_df, "CSCONGES"),
                        }

                        timeline_grp = [c for c in ["Date", "Hour", "DateTime"] if c in filtered_df.columns]
                        if not has_hour and "Hour" in timeline_grp: timeline_grp.remove("Hour")

                        if timeline_grp:
                            c_data_timeline = aggregate_kpis(filtered_df, timeline_grp)
                            if "DateTime" in c_data_timeline.columns:
                                c_data_timeline = c_data_timeline.sort_values(by="DateTime")
                                c_data_timeline["TimeLabel"] = pd.to_datetime(c_data_timeline["DateTime"]).dt.strftime("%d/%m %H:00" if has_hour else "%d/%m")
                            elif "Date" in c_data_timeline.columns:
                                c_data_timeline["TimeLabel"] = pd.to_datetime(c_data_timeline["Date"]).dt.strftime("%d/%m")
                            elif "Hour" in c_data_timeline.columns:
                                c_data_timeline["TimeLabel"] = c_data_timeline["Hour"].astype(str) + ":00"
                            else: c_data_timeline["TimeLabel"] = "Timeline"
                        else:
                            c_data_timeline = pd.DataFrame()

                        pdf_buf = generate_pdf_report(
                            summary_data, c_data_timeline, top10_sites_pdf, top10_cells_pdf,
                            worst10_cssr, worst10_dcr, worst10_soft, worst10_cong,
                            fb_cell_counts, fb_tf_df, cell_type_counts, fb_type_xtab, fb_cv_df
                        )
                        st.session_state["pdf_bytes"] = pdf_buf.getvalue()
                        st.session_state["pdf_sig"] = _pdf_sig

                if st.session_state.get("pdf_bytes") is not None:
                    if st.session_state.get("pdf_sig") == _pdf_sig:
                        st.download_button(label="⬇️ Tải Báo Cáo PDF", data=st.session_state["pdf_bytes"], file_name="3G_Network_Health.pdf", mime="application/pdf")
                    else:
                        st.info("Bộ lọc đã thay đổi — bấm 'Tạo Báo Cáo PDF' để tạo lại.")
