import io
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, Image
)

from src.config import FONT_NAME, FONT_NAME_BOLD

def generate_pdf_report(summary, hourly_trend_df, top10_sites, top10_cells, worst10_cssr, worst10_dcr, worst10_soft, worst10_cong, fb_cell_counts=None, fb_tf_df=None, cell_type_counts=None, fb_type_xtab=None, fb_cv_df=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []

    t_style = ParagraphStyle("T", fontName=FONT_NAME, fontSize=16, textColor=colors.HexColor("#0f172a"), spaceAfter=6)
    h2_style = ParagraphStyle("H2", fontName=FONT_NAME, fontSize=11, textColor=colors.HexColor("#1e293b"), spaceBefore=8, spaceAfter=4)
    norm_style = ParagraphStyle("N", fontName=FONT_NAME, fontSize=8.5, textColor=colors.HexColor("#334155"))

    now_str = pd.Timestamp.now().strftime("%d/%m/%Y")

    story.append(Paragraph("BÁO CÁO CHẤT LƯỢNG MẠNG 3G", t_style))
    story.append(Paragraph(f"Thời gian xuất báo cáo: {now_str}", norm_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

    # MỤC I. 6 KPI CARDS TỔNG QUAN
    story.append(Paragraph("I. TỔNG QUAN KPI 3G", h2_style))
    story.append(Spacer(1, 4))

    card_t_style = ParagraphStyle('CT', fontName=FONT_NAME, fontSize=7.5, textColor=colors.HexColor('#475569'), leading=9)
    card_v_style = ParagraphStyle('CV', fontName=FONT_NAME, fontSize=13, textColor=colors.HexColor('#0f172a'), leading=15)
    card_s_style = ParagraphStyle('CS', fontName=FONT_NAME, fontSize=6.5, textColor=colors.HexColor('#64748b'), leading=8)

    def create_pdf_card(cat, title, val, target, remark, color_hex="#10b981"):
        p_t = Paragraph(f"<b>{cat.upper()}</b><br/>{title}", card_t_style)
        p_v = Paragraph(f"<font color='{color_hex}'><b>{val}</b></font>", card_v_style)
        p_s = Paragraph(f"<b>Target:</b> {target}<br/><i>{remark}</i>", card_s_style)

        c_tbl = Table([[p_t], [p_v], [p_s]], colWidths=[118])
        c_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]))
        return c_tbl

    cards_row = [
        create_pdf_card("Traffic", "CS Traffic", f"{summary.get('tr',0):,.2f} Erl", "N/A", "Tải tốt", "#0284c7"),
        create_pdf_card("Call Volume", "Call Volume", f"{summary.get('cv',0):,.0f}", "N/A", "Số cuộc gọi", "#0284c7"),
        create_pdf_card("Accessibility", "Call Setup SR", f"{summary.get('cssr',0):.2f}%", ">=99.00%", "Ổn định", "#059669" if summary.get('cssr',0)>=99.0 else "#d97706"),
        create_pdf_card("Retainability", "Drop Call Rate", f"{summary.get('dcr',0):.3f}%", "<=1.000%", "Đạt chuẩn", "#059669" if summary.get('dcr',0)<=1.0 else "#dc2626"),
        create_pdf_card("Mobility", "Soft Handover SR", f"{summary.get('soft',0):.2f}%", ">=99.00%", "Mượt mà", "#059669" if summary.get('soft',0)>=99.0 else "#d97706"),
        create_pdf_card("Capacity", "CS Congestion Rate", f"{summary.get('cong',0):.3f}%", "<=0.500%", "Không nghẽn", "#059669" if summary.get('cong',0)<=0.5 else "#dc2626"),
    ]

    grid_cards = Table([cards_row], colWidths=[124]*6)
    grid_cards.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(grid_cards)
    story.append(Spacer(1, 8))

    # MỤC II. FREQBAND CHARTS (LƯỚI 2x2)
    _has = lambda d: d is not None and not d.empty
    if _has(fb_cell_counts) or _has(fb_tf_df) or _has(cell_type_counts) or _has(fb_cv_df):
        story.append(Paragraph("II. THỐNG KÊ PHÂN BỔ CELL, TRAFFIC VÀ CALL VOLUME THEO FREQBAND", h2_style))
        story.append(Spacer(1, 2))

        fb_img_buf = io.BytesIO()
        fig_fb, ((ax1_fb, ax_ct), (ax2_fb, ax3_fb)) = plt.subplots(2, 2, figsize=(11, 4.2), dpi=150)
        fb_colors = ['#0284c7', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

        def _donut(ax, labels, sizes, cols, title):
            _, texts, autotexts = ax.pie(
                sizes, labels=labels, autopct=lambda p: f"{p:.1f}%", startangle=90,
                colors=cols, wedgeprops=dict(width=0.45, edgecolor='white')
            )
            for t in texts: t.set_fontsize(7)
            for at in autotexts: at.set_fontsize(6.5); at.set_weight('bold')
            ax.set_title(title, fontsize=8, fontweight='bold', pad=4)

        if _has(fb_cell_counts):
            fb_labels = [f"{b} ({n})" for b, n in zip(fb_cell_counts["Freqband"], fb_cell_counts["Số lượng Cell"])]
            _donut(ax1_fb, fb_labels, fb_cell_counts["Số lượng Cell"].tolist(), fb_colors[:len(fb_labels)], "Số lượng Cell theo Freqband")
        else: ax1_fb.axis('off')

        if _has(cell_type_counts):
            ct_cmap = {"VNP": "#3b82f6", "MORAN": "#f59e0b"}
            ct_labels = [f"{t} ({n})" for t, n in zip(cell_type_counts["Cell Type"], cell_type_counts["Số lượng Cell"])]
            ct_cols = [ct_cmap.get(t, '#94a3b8') for t in cell_type_counts["Cell Type"]]
            _donut(ax_ct, ct_labels, cell_type_counts["Số lượng Cell"].tolist(), ct_cols, "Số lượng Cell theo Loại Cell")
        else: ax_ct.axis('off')

        if _has(fb_tf_df):
            fb_bands = fb_tf_df["Freqband"].tolist()
            fb_traffics = fb_tf_df["TRAFFIC"].tolist()
            fb_bars = ax2_fb.bar(fb_bands, fb_traffics, color='#0284c7', width=0.45, alpha=0.85)
            ax2_fb.set_title("Tổng CS Traffic (Erl) theo Freqband", fontsize=8, fontweight='bold', pad=4)
            ax2_fb.set_ylabel("Traffic (Erl)", fontsize=7)
            ax2_fb.tick_params(axis='both', labelsize=6.5)
            ax2_fb.grid(True, linestyle='--', alpha=0.25, axis='y')

            max_tf = max(fb_traffics) if fb_traffics else 1
            ax2_fb.set_ylim(0, max_tf * 1.18)

            for bar in fb_bars:
                yval = bar.get_height()
                ax2_fb.text(bar.get_x() + bar.get_width()/2.0, yval + (max_tf * 0.02), f"{yval:,.1f}", ha='center', va='bottom', fontsize=6, fontweight='bold')
        else: ax2_fb.axis('off')

        if _has(fb_cv_df) and "CALLVOLUME" in fb_cv_df.columns:
            cv_bands = fb_cv_df["Freqband"].tolist()
            cv_vals = fb_cv_df["CALLVOLUME"].tolist()
            cv_bars = ax3_fb.bar(cv_bands, cv_vals, color='#8b5cf6', width=0.45, alpha=0.85)
            ax3_fb.set_title("Tổng Call Volume theo Freqband", fontsize=8, fontweight='bold', pad=4)
            ax3_fb.set_ylabel("Call Volume", fontsize=7)
            ax3_fb.tick_params(axis='both', labelsize=6.5)
            ax3_fb.grid(True, linestyle='--', alpha=0.25, axis='y')

            max_cv = max(cv_vals) if cv_vals else 1
            ax3_fb.set_ylim(0, max_cv * 1.18)

            for bar in cv_bars:
                yval = bar.get_height()
                ax3_fb.text(bar.get_x() + bar.get_width()/2.0, yval + (max_cv * 0.02), f"{yval:,.0f}", ha='center', va='bottom', fontsize=6, fontweight='bold')
        else: ax3_fb.axis('off')

        plt.tight_layout()
        plt.savefig(fb_img_buf, format='png', dpi=150)
        plt.close()
        fb_img_buf.seek(0)
        story.append(Image(fb_img_buf, width=740, height=280))
        story.append(Spacer(1, 4))

        if _has(fb_type_xtab):
            _ps = ParagraphStyle("FBT", fontName=FONT_NAME, fontSize=7.5, textColor=colors.HexColor("#334155"), alignment=1)
            _pw = ParagraphStyle("FBTW", parent=_ps, textColor=colors.white)
            def _c(txt, bold=False, white=False): return Paragraph(f"<b>{txt}</b>" if bold else str(txt), _pw if white else _ps)

            tf_map = dict(zip(fb_tf_df["Freqband"], fb_tf_df["TRAFFIC"])) if _has(fb_tf_df) else {}
            cv_map = dict(zip(fb_cv_df["Freqband"], fb_cv_df["CALLVOLUME"])) if (_has(fb_cv_df) and "CALLVOLUME" in fb_cv_df.columns) else {}
            grand = int(fb_type_xtab["Tổng"].sum()) or 1

            story.append(Paragraph("<b>Thống kê số lượng Cell, CS Traffic & Call Volume theo Freqband và Loại Cell:</b>", norm_style))
            story.append(Spacer(1, 2))
            hdr = ["Freqband", "Cell VNP", "Cell MORAN", "Tổng Cell", "Tỷ lệ (%)", "Traffic (Erl)", "Call Volume"]
            rows = [[_c(h, True, True) for h in hdr]]
            for _, r in fb_type_xtab.iterrows():
                fb = r["Freqband"]
                rows.append([
                    _c(fb), _c(int(r["VNP"])), _c(int(r["MORAN"])), _c(int(r["Tổng"])),
                    _c(f"{r['Tổng'] / grand * 100:.1f}"),
                    _c(f"{tf_map[fb]:,.2f}" if fb in tf_map and pd.notnull(tf_map[fb]) else "-"),
                    _c(f"{cv_map[fb]:,.0f}" if fb in cv_map and pd.notnull(cv_map[fb]) else "-"),
                ])
            tot_tf = sum(v for v in tf_map.values() if pd.notnull(v)) if tf_map else None
            tot_cv = summary.get('cv', 0)
            rows.append([
                _c("Tổng", True), _c(int(fb_type_xtab["VNP"].sum()), True), _c(int(fb_type_xtab["MORAN"].sum()), True),
                _c(grand if grand != 1 or fb_type_xtab["Tổng"].sum() else 0, True), _c("100.0", True),
                _c(f"{tot_tf:,.2f}" if tot_tf is not None else "-", True),
                _c(f"{tot_cv:,.0f}" if tot_cv is not None else "-", True),
            ])
            t_fb = Table(rows, colWidths=[95, 95, 95, 95, 95, 115, 110], hAlign="LEFT")
            t_fb.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0284c7")),
                ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#e2e8f0")),
                ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
                ("TOPPADDING", (0,0), (-1,-1), 2.5),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            story.append(t_fb)
        story.append(Spacer(1, 8))

    # MỤC III. CHARTS XU HƯỚNG
    story.append(Paragraph("III. XU HƯỚNG CÁC CHỈ SỐ KPI CHÍNH", h2_style))
    story.append(Spacer(1, 4))

    if not hourly_trend_df.empty:
        df_chart = hourly_trend_df.copy()
        x_labels = []
        for _, r in df_chart.iterrows():
            if "TimeLabel" in r and pd.notnull(r["TimeLabel"]) and str(r["TimeLabel"]).strip() != "":
                x_labels.append(str(r["TimeLabel"]))
            elif "DateTime" in r and pd.notnull(r["DateTime"]):
                x_labels.append(pd.to_datetime(r["DateTime"]).strftime("%d/%m %H:00"))
            else:
                x_labels.append(f"{int(r.get('Hour', 0)):02d}:00")
        n_pts = len(x_labels)
        step = max(1, n_pts // 24)

        tr_vals = df_chart.get("TRAFFIC", pd.Series([0]*n_pts)).values
        cssr_vals = df_chart.get("CSSR", pd.Series([0]*n_pts)).values
        dcr_vals = df_chart.get("DCR", pd.Series([0]*n_pts)).values
        soft_vals = df_chart.get("SOFTHOSR", pd.Series([0]*n_pts)).values
        cong_vals = df_chart.get("CSCONGES", pd.Series([0]*n_pts)).values

        def make_single_chart(chart_title, bar_vals, line_vals, line_lbl, line_color):
            img_b = io.BytesIO()
            fig, ax = plt.subplots(figsize=(11, 3.2), dpi=150)

            ax.set_xticks(range(0, n_pts, step))
            ax.set_xticklabels([x_labels[i] for i in range(0, n_pts, step)], rotation=30 if n_pts > 15 else 0, ha='right' if n_pts > 15 else 'center', fontsize=6)
            ax.grid(True, linestyle='--', alpha=0.25)

            ax.bar(range(n_pts), bar_vals, color='#0284c7', alpha=0.45, label="Traffic (Erl)", width=0.8)
            ax.set_ylabel("Traffic (Erl)", color='#0284c7', fontweight='bold', fontsize=7.5)
            ax.tick_params(axis='y', labelcolor='#0284c7', labelsize=6.5)

            ax_t = ax.twinx()
            ax_t.plot(range(n_pts), line_vals, color=line_color, marker='o', markersize=2.5, linewidth=1.4, label=line_lbl)
            ax_t.set_ylabel(line_lbl, color=line_color, fontweight='bold', fontsize=7.5)
            ax_t.tick_params(axis='y', labelcolor=line_color, labelsize=6.5)

            ax.set_title(chart_title, fontsize=8.5, fontweight='bold', pad=4)
            plt.tight_layout()
            plt.savefig(img_b, format='png', dpi=150)
            plt.close()
            img_b.seek(0)
            return Image(img_b, width=740, height=215)

        story.append(make_single_chart("Chart 1: Call Setup Success Rate (CSSR %) & CS Traffic (Erl)", tr_vals, cssr_vals, "CSSR (%)", "#10b981"))
        story.append(Spacer(1, 6))
        story.append(make_single_chart("Chart 2: Drop Call Rate (DCR %) & CS Traffic (Erl)", tr_vals, dcr_vals, "DCR (%)", "#ef4444"))
        story.append(Spacer(1, 6))
        story.append(PageBreak())

        story.append(make_single_chart("Chart 3: Soft Handover SR (SOFTHOSR %) & CS Traffic (Erl)", tr_vals, soft_vals, "Soft HO SR (%)", "#059669"))
        story.append(Spacer(1, 6))
        story.append(make_single_chart("Chart 4: CS Congestion Rate (CSCONGES %) & CS Traffic (Erl)", tr_vals, cong_vals, "Congestion (%)", "#d97706"))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # MỤC IV. TOP SITE & WORST CELLS TABLES
    story.append(Paragraph("IV. DANH SÁCH TOP 10 HIGH TRAFFIC SITE & CELL", h2_style))
    story.append(Spacer(1, 4))

    def p_cell(text, is_bold=False, align='left', color_hex='#0f172a'):
        p_st = ParagraphStyle('PC', fontName=FONT_NAME, fontSize=7.5, textColor=colors.HexColor(color_hex), leading=9, alignment=0 if align=='left' else 1)
        return Paragraph(f"<b>{text}</b>" if is_bold else str(text), p_st)

    if not top10_cells.empty:
        story.append(Paragraph("<b>1. Top 10 Cell có Lưu lượng CS Traffic (Erlang) cao nhất:</b>", norm_style))
        story.append(Spacer(1, 2))
        tr_sub = top10_cells.head(10)
        tr_data = [[p_cell("Site Name", True, color_hex='#ffffff'), p_cell("Cell Name", True, color_hex='#ffffff'), p_cell("Traffic (Erl)", True, color_hex='#ffffff'), p_cell("Call Volume", True, color_hex='#ffffff'), p_cell("CSSR (%)", True, color_hex='#ffffff')]]
        for _, row in tr_sub.iterrows():
            tr_data.append([
                p_cell(row.iloc[0] if len(row) > 0 else ""), p_cell(row.iloc[1] if len(row) > 1 else ""),
                p_cell(f"{row.get('TRAFFIC', 0):,.2f}"), p_cell(f"{row.get('CALLVOLUME', 0):,.0f}"),
                p_cell(f"{row.get('CSSR', 0):.2f}%")
            ])
        t_tr = Table(tr_data, colWidths=[130, 180, 110, 110, 110])
        t_tr.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0284c7")), ("BOTTOMPADDING", (0,0), (-1,-1), 3), ("TOPPADDING", (0,0), (-1,-1), 3), ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])]))
        story.append(t_tr)
        story.append(Spacer(1, 8))

    if not top10_sites.empty:
        story.append(Paragraph("<b>2. Top 10 Site có Lưu lượng CS Traffic (Erlang) cao nhất:</b>", norm_style))
        story.append(Spacer(1, 2))
        ts_sub = top10_sites.head(10)
        ts_data = [[p_cell("Site Name", True, color_hex='#ffffff'), p_cell("Traffic (Erl)", True, color_hex='#ffffff'), p_cell("Call Volume", True, color_hex='#ffffff'), p_cell("DCR (%)", True, color_hex='#ffffff')]]
        for _, row in ts_sub.iterrows():
            ts_data.append([
                p_cell(row.iloc[0] if len(row) > 0 else ""),
                p_cell(f"{row.get('TRAFFIC', 0):,.2f}"),
                p_cell(f"{row.get('CALLVOLUME', 0):,.0f}"),
                p_cell(f"{row.get('DCR', 0):.3f}%")
            ])
        t_ts = Table(ts_data, colWidths=[180, 160, 150, 150])
        t_ts.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0369a1")), ("BOTTOMPADDING", (0,0), (-1,-1), 3), ("TOPPADDING", (0,0), (-1,-1), 3), ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])]))
        story.append(t_ts)

    story.append(PageBreak())
    story.append(Paragraph("V. DANH SÁCH WORST 10 CELLS CÁC KPI CHÍNH (CSSR, DCR, SOFTHOSR, CSCONGES)", h2_style))
    story.append(Spacer(1, 4))

    def render_worst_pdf_table(title, df_data, val_col, fmt, bg_color):
        if df_data.empty: return
        story.append(Paragraph(f"<b>{title}</b>", norm_style))
        story.append(Spacer(1, 2))
        w_data = [[p_cell("Site Name", True, color_hex='#ffffff'), p_cell("Cell Name", True, color_hex='#ffffff'), p_cell("Giá trị KPI", True, color_hex='#ffffff'), p_cell("Traffic (Erl)", True, color_hex='#ffffff')]]
        for _, r in df_data.head(10).iterrows():
            w_data.append([
                p_cell(r.get("Site Name", "")),
                p_cell(r.get("Tên đối tượng", r.get("Cell Name", ""))),
                p_cell(fmt.format(r.get(val_col, 0))),
                p_cell(f"{r.get('TRAFFIC', 0):,.2f}")
            ])
        t_out = Table(w_data, colWidths=[180, 220, 170, 170])
        t_out.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor(bg_color)), ("BOTTOMPADDING", (0,0), (-1,-1), 3), ("TOPPADDING", (0,0), (-1,-1), 3), ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])]))
        story.append(t_out)
        story.append(Spacer(1, 8))

    render_worst_pdf_table("1. Worst 10 Cells theo Tỷ lệ Thiết lập Cuộc gọi (CSSR):", worst10_cssr, "CSSR", "{:.2f}%", "#991b1b")
    render_worst_pdf_table("2. Worst 10 Cells theo Tỷ lệ Rớt Cuộc gọi (DCR):", worst10_dcr, "DCR", "{:.3f}%", "#b91c1c")
    render_worst_pdf_table("3. Worst 10 Cells theo Tỷ lệ Chuyển giao Mềm (SOFTHOSR):", worst10_soft, "SOFTHOSR", "{:.2f}%", "#c2410c")
    render_worst_pdf_table("4. Worst 10 Cells theo Tỷ lệ Nghẽn Thoại (CSCONGES):", worst10_cong, "CSCONGES", "{:.3f}%", "#ea580c")

    doc.build(story)
    buf.seek(0)
    return buf
