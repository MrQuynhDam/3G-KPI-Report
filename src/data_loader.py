import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data
def process_data(file_input):
    df = pd.read_csv(file_input, thousands=",")
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]

    def _clean_num(series):
        if series.dtype == object or str(series.dtype).startswith("str"):
            return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")
        return pd.to_numeric(series, errors="coerce")

    # Map tên cột linh hoạt từ file CSV đầu vào
    alias_map = {
        "DateTime": ["DateTime", "Thời gian", "Time", "timestamp"],
        "Date": ["Date", "Ngày"],
        "Hour": ["Giờ", "Hour", "hour"],
        "Site Name": ["Site Name", "Site", "Tên Site", "NodeB Name", "NodeB"],
        "Tên đối tượng": ["Tên đối tượng", "Tên CELL", "Cell Name", "Cell", "Tên Cell", "Object Name", "CellId"],
        "TRAFFIC": ["TRAFFIC", "Traffic", "CS Traffic", "Traffic (Erl)"],
        "SOFTHOSR": ["SOFTHOSR", "Soft HO SR (%)", "Soft Handover SR (%)", "Soft HO SR"],
        "CALLVOLUME": ["CALLVOLUME", "Call Volume", "CS Call Volume", "Calls"],
        "DCR": ["DCR", "CS Drop Rate (%)", "Drop Call Rate (%)", "CS Voice Drop Rate (%)"],
        "CSSR": ["CSSR", "CS CSSR (%)", "Call Setup Success Rate (%)", "CS Voice CSSR (%)"],
        "CSCONGES": ["CSCONGES", "CS Congestion Rate (%)", "Congestion Rate (%)", "CS Congestion (%)"]
    }

    for std_col, aliases in alias_map.items():
        if std_col not in df.columns:
            for alias in aliases:
                if alias in df.columns:
                    df.rename(columns={alias: std_col}, inplace=True)
                    break

    # Tự động trích xuất Site Name từ Tên Cell nếu không có cột Site Name
    cell_col_name = "Tên đối tượng" if "Tên đối tượng" in df.columns else ("Cell Name" if "Cell Name" in df.columns else None)
    if "Site Name" not in df.columns and cell_col_name:
        extracted_site = df[cell_col_name].astype(str).str.extract(r'3G_([A-Za-z0-9]{6})')[0]
        df["Site Name"] = extracted_site.fillna(df[cell_col_name])

    # Bóc tách Freqband (Sóng mang M1, M4...) và Cell Type (VNP vs MORAN)
    if cell_col_name and cell_col_name in df.columns:
        cell_s = df[cell_col_name].astype(str).str.strip()
        is_moran = cell_s.str.upper().str.startswith("VNP-")
        core = cell_s.where(~is_moran, cell_s.str[4:])
        extracted_fb = core.str.extract(r'3G_[A-Za-z0-9]{6}([A-Za-z][0-9]?)')[0]
        df["Freqband"] = extracted_fb.fillna("N/A")
        df["Cell Type"] = np.where(is_moran, "MORAN", "VNP")

    # Xử lý Ngày / Giờ / DateTime
    if "Date" in df.columns:
        df["Date_dt"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df["Date"] = df["Date_dt"].dt.date
    else:
        df["Date_dt"] = pd.Timestamp.now()
        df["Date"] = df["Date_dt"].dt.date

    has_hour = False
    if "Hour" in df.columns:
        hr = pd.to_numeric(df["Hour"].astype(str).str.extract(r"(\d{1,2})")[0], errors="coerce")
        if hr.notnull().any():
            df["Hour"] = hr.fillna(0).astype(int)
            has_hour = True
        else:
            df["Hour"] = 0
    else:
        df["Hour"] = 0

    if "DateTime" not in df.columns:
        df["DateTime"] = pd.to_datetime(df["Date_dt"].astype(str) + " " + df["Hour"].astype(str) + ":00:00", errors="coerce")

    df["_has_hour_col"] = has_hour

    # Làm sạch các chỉ số KPI chính
    kpi_cols = ["TRAFFIC", "SOFTHOSR", "CALLVOLUME", "DCR", "CSSR", "CSCONGES"]
    for col in kpi_cols:
        if col in df.columns:
            df[col] = _clean_num(df[col])

    return df


def aggregate_kpis(df_in, group_cols):
    """Gom nhóm + tính trung bình có trọng số theo TRAFFIC (Erlang)."""
    if isinstance(group_cols, str):
        group_cols = [group_cols]
    group_cols = list(group_cols)

    TR, CV = 'TRAFFIC', 'CALLVOLUME'
    cols = df_in.columns

    nan_s = pd.Series(np.nan, index=df_in.index)
    tr_vol = df_in[TR] if TR in cols else nan_s
    cv_vol = df_in[CV] if CV in cols else nan_s

    tmp = {'_tr': tr_vol, '_cv': cv_vol}
    mean_cols = {}
    spec = {'_tr': 'sum', '_cv': 'sum'}

    def add_weighted(key, x, weight):
        valid = x.notna() & weight.notna() & (weight > 0)
        tmp[f'{key}__n'] = (x * weight).where(valid)
        tmp[f'{key}__d'] = weight.where(valid)
        spec[f'{key}__n'] = 'sum'
        spec[f'{key}__d'] = 'sum'
        mean_cols[f'{key}__m'] = x
        spec[f'{key}__m'] = 'mean'

    pct_kpis = [k for k in ['CSSR', 'DCR', 'SOFTHOSR', 'CSCONGES'] if k in cols]
    for k in pct_kpis:
        add_weighted(f'p::{k}', df_in[k], tr_vol)

    work = pd.concat([df_in[group_cols], pd.DataFrame(tmp), pd.DataFrame(mean_cols)], axis=1)
    agg = work.groupby(group_cols, sort=True).agg(spec)

    res = pd.DataFrame(index=agg.index)
    if TR in cols: res[TR] = agg['_tr']
    if CV in cols: res[CV] = agg['_cv']

    for k in pct_kpis:
        d = agg[f'p::{k}__d']
        weighted = np.where(d > 0, agg[f'p::{k}__n'] / d.where(d > 0), agg[f'p::{k}__m'])
        res[k] = pd.Series(weighted, index=agg.index)

    return res.reset_index()


def calc_weighted_avg(df_in, kpi_col, weight_col="TRAFFIC"):
    if kpi_col not in df_in.columns:
        return 0.0

    if weight_col in df_in.columns:
        valid_mask = df_in[kpi_col].notnull() & df_in[weight_col].notnull() & (df_in[weight_col] > 0)
        df_valid = df_in[valid_mask]
        total_weight = df_valid[weight_col].sum()
        if total_weight > 0:
            return (df_valid[kpi_col] * df_valid[weight_col]).sum() / total_weight

    df_valid = df_in[df_in[kpi_col].notnull()]
    return df_valid[kpi_col].mean() if not df_valid.empty else 0.0
