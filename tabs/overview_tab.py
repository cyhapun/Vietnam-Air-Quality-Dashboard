import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import base64
import os
import textwrap
import html
from utils.helpers import AQI_DEF, POLLS

OV_TIMEFRAME_DELTAS = {
    "24h": pd.Timedelta(hours=24),
    "7 ngày": pd.Timedelta(days=7),
    "30 ngày": pd.Timedelta(days=30),
    "3 tháng": pd.Timedelta(days=90),
}
OV_TIMEFRAME_LABELS = {
    "24h": "24 giờ",
    "7 ngày": "7 ngày",
    "30 ngày": "30 ngày",
    "3 tháng": "3 tháng",
}

POLLUTANT_LEVEL_BANDS = {
    "pm2_5": [12, 35.4, 55.4, 150.4, 250.4],
    "pm10": [54, 154, 254, 354, 424],
    "co": [4400, 9400, 12400, 15400, 30400],
    "so2": [35, 75, 185, 304, 604],
    "no2": [53, 100, 360, 649, 1249],
    "o3": [54, 70, 85, 105, 200],
}

STANDARD_LEVEL_LABELS = [
    "Tốt",
    "Vừa phải",
    "Không lành mạnh cho nhóm nhạy cảm",
    "Không khỏe mạnh",
    "Rất không tốt cho sức khỏe",
    "Nguy hiểm",
]


def _safe_pm25_mean(df):
    """Safely calculates the mean of the PM2.5 column, returning 0.0 if missing or NaN."""
    if "pm2_5" not in df.columns:
        return 0.0
    val = df["pm2_5"].mean()
    return 0.0 if pd.isna(val) else float(val)


def _get_timeframe_selector():
    """Retrieves the active timeframe selection from the session state, defaulting to '24h'."""
    if "ov_time_range" not in st.session_state:
        st.session_state["ov_time_range"] = "24h"
    if st.session_state["ov_time_range"] not in OV_TIMEFRAME_DELTAS:
        st.session_state["ov_time_range"] = "24h"
    return st.session_state["ov_time_range"]


def _filter_df_by_time_range(df, selected_range):
    """Filters a DataFrame to only include records within the selected trailing time range."""
    if df.empty or "timestamp" not in df.columns:
        return df.copy()
    max_ts = df["timestamp"].max()
    if pd.isna(max_ts):
        return df.copy()
    delta = OV_TIMEFRAME_DELTAS.get(selected_range, OV_TIMEFRAME_DELTAS["24h"])
    min_ts = max_ts - delta
    return df[df["timestamp"] >= min_ts].copy()


def _compute_hero_insights(df: pd.DataFrame, avg_aqi: int, current_label: str) -> dict:
    """
    Computes insights for the hero section based on the filtered data.
    This includes health advice, risks for sensitive groups, and identifying the best/worst time slots.
    """
    slot_focus = "Không đủ dữ liệu"
    slot_focus_sub = "Chưa xác định được khung giờ có rủi ro nổi bật."
    if "time_slot" in df.columns and "aqi" in df.columns:
        slot_mean = df.groupby("time_slot", observed=False)["aqi"].mean().dropna().sort_values(ascending=False)
        if not slot_mean.empty:
            slot_focus = str(slot_mean.index[0])
            slot_focus_sub = f"AQI trung bình cao nhất: {slot_mean.iloc[0]:.1f}."

    health_advice_map = {
        "Tốt": "Tiếp tục sinh hoạt bình thường; duy trì theo dõi chất lượng không khí định kỳ.",
        "Vừa phải": "Giảm vận động ngoài trời kéo dài khi không cần thiết, nhất là vào giờ cao điểm.",
        "Không lành mạnh cho nhóm nhạy cảm": "Nhóm nhạy cảm nên hạn chế ra ngoài, ưu tiên khẩu trang lọc bụi mịn khi di chuyển.",
        "Không khỏe mạnh": "Hạn chế hoạt động ngoài trời; cân nhắc dùng khẩu trang N95 khi bắt buộc phải ra ngoài.",
        "Rất không tốt cho sức khỏe": "Ưu tiên ở trong nhà, đóng cửa và dùng máy lọc không khí nếu có.",
        "Nguy hiểm": "Tránh ra ngoài tối đa; theo dõi cảnh báo y tế địa phương và bảo vệ hô hấp nghiêm ngặt.",
    }
    health_advice = health_advice_map.get(current_label, health_advice_map["Nguy hiểm"])

    if avg_aqi <= 50:
        risk_children = "Rủi ro thấp; có thể hoạt động ngoài trời bình thường."
        risk_elderly = "Rủi ro thấp; duy trì theo dõi định kỳ."
    elif avg_aqi <= 100:
        risk_children = "Nhạy cảm nhẹ; giảm thời lượng chơi ngoài trời kéo dài."
        risk_elderly = "Có thể mệt nhẹ nếu phơi nhiễm lâu; nên nghỉ ngắt quãng."
    elif avg_aqi <= 150:
        risk_children = "Nguy cơ kích ứng hô hấp tăng; nên hạn chế ra ngoài lâu."
        risk_elderly = "Tăng nguy cơ khó thở/ho; ưu tiên không gian trong nhà."
    elif avg_aqi <= 200:
        risk_children = "Nguy cơ viêm đường hô hấp rõ rệt; hạn chế tối đa hoạt động ngoài trời."
        risk_elderly = "Nguy cơ đợt cấp bệnh nền cao; tránh phơi nhiễm trực tiếp."
    elif avg_aqi <= 300:
        risk_children = "Mức nguy cơ rất cao; nên ở trong nhà và theo dõi triệu chứng."
        risk_elderly = "Rủi ro rất cao với tim phổi; hạn chế di chuyển ngoài trời."
    else:
        risk_children = "Nguy hiểm; tránh ra ngoài hoàn toàn nếu có thể."
        risk_elderly = "Nguy hiểm; cần bảo vệ hô hấp nghiêm ngặt và theo dõi sát."

    best_slot = "Không đủ dữ liệu"
    best_slot_sub = "Chưa xác định được khung giờ an toàn hơn trong ngày."
    if "time_slot" in df.columns and "aqi" in df.columns:
        slot_min = df.groupby("time_slot", observed=False)["aqi"].mean().dropna().sort_values(ascending=True)
        if not slot_min.empty:
            best_slot = str(slot_min.index[0])
            best_slot_sub = f"AQI trung bình thấp nhất: {slot_min.iloc[0]:.1f}."

    return {
        "slot_focus": slot_focus,
        "slot_focus_sub": slot_focus_sub,
        "health_advice": health_advice,
        "risk_children": risk_children,
        "risk_elderly": risk_elderly,
        "best_slot": best_slot,
        "best_slot_sub": best_slot_sub,
    }


def _build_scope_metrics(df, state, selected_range):
    """
    Computes aggregated metrics and trends (1d/7d comparisons) for the selected timeframe.
    Returns a derived state dictionary for rendering the overview dashboard.
    """
    _aqi_meta = state["aqi_meta"]
    _aqi_health_guidance = state["aqi_health_guidance"]
    _fmt_delta = state["fmt_delta"]
    city_col = "city" if "city" in df.columns else "province"
    city_aqi_mean = (
        df.groupby(city_col, observed=False)["aqi"].mean().sort_values(ascending=False)
        if city_col in df.columns
        else pd.Series(dtype=float)
    )
    avg_aqi = int(df["aqi"].mean()) if not df["aqi"].dropna().empty else 0
    avg_pm25 = round(_safe_pm25_mean(df), 1)
    dangerp = round((df["aqi"] > 150).mean() * 100, 1) if len(df) else 0.0
    worst = city_aqi_mean.index[0] if not city_aqi_mean.empty else "N/A"
    selected_delta = OV_TIMEFRAME_DELTAS.get(selected_range, OV_TIMEFRAME_DELTAS["24h"])
    days = max(selected_delta.total_seconds() / 86400.0, 1 / 24)
    cig_n = round(avg_pm25 / 22.0 * days, 1)
    _lbl, _col = _aqi_meta(avg_aqi)
    health_hd, _, _ = _aqi_health_guidance(avg_aqi)
    who_pm25_multi = round(max(avg_pm25, 0.1) / 5.0, 1)
    latest_obs = df["timestamp"].max()

    selected_range_label = OV_TIMEFRAME_LABELS.get(selected_range, selected_range)
    exposure_label = selected_range_label.lower()
    trend_primary_kicker = f"Biến động {selected_range_label}"
    trend_secondary_kicker = f"Xu hướng nội bộ ({selected_range_label})"

    max_ts = df["timestamp"].max()
    delta = OV_TIMEFRAME_DELTAS.get(selected_range, OV_TIMEFRAME_DELTAS["24h"])
    curr_start = max_ts - delta if pd.notna(max_ts) else pd.NaT
    prev_start = curr_start - delta if pd.notna(curr_start) else pd.NaT

    curr_window = df[df["timestamp"] >= curr_start] if pd.notna(curr_start) else df.iloc[0:0]
    prev_window = (
        df[(df["timestamp"] >= prev_start) & (df["timestamp"] < curr_start)]
        if pd.notna(prev_start)
        else df.iloc[0:0]
    )

    if not curr_window.empty and not prev_window.empty:
        aqi_1d_text, aqi_1d_color = _fmt_delta(curr_window["aqi"].mean(), prev_window["aqi"].mean())
        pm_1d_text, pm_1d_color = _fmt_delta(
            curr_window["pm2_5"].mean(), prev_window["pm2_5"].mean(), " µg"
        )
    elif len(curr_window) >= 2:
        # Fallback: compare two halves in current window when there is no previous window.
        curr_sorted = curr_window.sort_values("timestamp")
        half_idx = max(1, len(curr_sorted) // 2)
        first_half_curr = curr_sorted.iloc[:half_idx]
        second_half_curr = curr_sorted.iloc[half_idx:]
        if not first_half_curr.empty and not second_half_curr.empty:
            aqi_1d_text, aqi_1d_color = _fmt_delta(
                second_half_curr["aqi"].mean(), first_half_curr["aqi"].mean()
            )
            pm_1d_text, pm_1d_color = _fmt_delta(
                second_half_curr["pm2_5"].mean(), first_half_curr["pm2_5"].mean(), " µg"
            )
        else:
            aqi_1d_text, aqi_1d_color = _fmt_delta(0, None)
            pm_1d_text, pm_1d_color = _fmt_delta(0, None)
    else:
        aqi_1d_text, aqi_1d_color = _fmt_delta(0, None)
        pm_1d_text, pm_1d_color = _fmt_delta(0, None)

    if not curr_window.empty and pd.notna(curr_start):
        mid_ts = curr_start + (delta / 2)
        first_half = curr_window[curr_window["timestamp"] < mid_ts]
        second_half = curr_window[curr_window["timestamp"] >= mid_ts]
        if not first_half.empty and not second_half.empty:
            aqi_7d_text, aqi_7d_color = _fmt_delta(
                second_half["aqi"].mean(), first_half["aqi"].mean()
            )
            pm_7d_text, pm_7d_color = _fmt_delta(
                second_half["pm2_5"].mean(), first_half["pm2_5"].mean(), " µg"
            )
        else:
            aqi_7d_text, aqi_7d_color = _fmt_delta(0, None)
            pm_7d_text, pm_7d_color = _fmt_delta(0, None)
    else:
        aqi_7d_text, aqi_7d_color = _fmt_delta(0, None)
        pm_7d_text, pm_7d_color = _fmt_delta(0, None)

    daily_trend = df.groupby("date", observed=False)[["aqi", "pm2_5"]].mean().sort_index()

    rank_up_line = "Chưa đủ dữ liệu để so sánh thứ hạng ngày gần nhất."
    rank_down_line = ""
    if len(daily_trend) >= 2 and city_col in df.columns:
        last_date = daily_trend.index[-1]
        prev_date = daily_trend.index[-2]
        city_day = df.groupby(["date", city_col], observed=False)["aqi"].mean().reset_index()
        now_rank = (
            city_day[city_day["date"] == last_date]
            .sort_values("aqi", ascending=False)[city_col]
            .tolist()
        )
        prv_rank = (
            city_day[city_day["date"] == prev_date]
            .sort_values("aqi", ascending=False)[city_col]
            .tolist()
        )
        all_rank_cities = sorted(set(now_rank) | set(prv_rank))
        fallback_rank = len(all_rank_cities) + 1
        rank_now_map = {city: i + 1 for i, city in enumerate(now_rank)}
        rank_prev_map = {city: i + 1 for i, city in enumerate(prv_rank)}

        shift_rows = []
        for city in all_rank_cities:
            shift = rank_prev_map.get(city, fallback_rank) - rank_now_map.get(
                city, fallback_rank
            )
            if shift != 0:
                shift_rows.append((city, shift))

        up_moves = sorted(
            [r for r in shift_rows if r[1] > 0], key=lambda x: x[1], reverse=True
        )[:2]
        down_moves = sorted([r for r in shift_rows if r[1] < 0], key=lambda x: x[1])[:2]
        if up_moves:
            rank_up_line = " · ".join([f"{c} (+{s})" for c, s in up_moves])
        if down_moves:
            rank_down_line = " · ".join([f"{c} ({s})" for c, s in down_moves])

    derived_state = dict(state)
    derived_state.update(
        {
            "avg_aqi": avg_aqi,
            "avg_pm25": avg_pm25,
            "dangerp": dangerp,
            "worst": worst,
            "days": days,
            "cig_n": cig_n,
            "_lbl": _lbl,
            "_col": _col,
            "health_hd": health_hd,
            "who_pm25_multi": who_pm25_multi,
            "latest_obs": latest_obs,
            "aqi_1d_text": aqi_1d_text,
            "aqi_1d_color": aqi_1d_color,
            "pm_1d_text": pm_1d_text,
            "pm_1d_color": pm_1d_color,
            "aqi_7d_text": aqi_7d_text,
            "aqi_7d_color": aqi_7d_color,
            "pm_7d_text": pm_7d_text,
            "pm_7d_color": pm_7d_color,
            "rank_up_line": rank_up_line,
            "rank_down_line": rank_down_line,
            "trend_primary_kicker": trend_primary_kicker,
            "trend_secondary_kicker": trend_secondary_kicker,
            "exposure_label": exposure_label,
            "sel": sorted(df[city_col].dropna().unique().tolist()) if city_col in df.columns else [],
            "df": df,
            "plot_city_limit": len(city_aqi_mean),
            "city_priority": city_aqi_mean.index.tolist(),
            "is_city_trimmed": False,
        }
    )
    return derived_state





def _render_pollutant_cards(df):
    """
    Renders individual cards for each secondary pollutant (PM10, O3, NO2, SO2, CO),
    showing their average values and health status based on predefined bands.
    """
    if df.empty: return
    pollutant_meta = {
        "pm2_5": {
            "title": "Vật chất hạt mịn",
            "subtitle": "(PM2.5)",
            "icon_file": "pm25.svg",
            "about": "Bụi siêu mịn có thể đi sâu vào phổi và máu, liên quan mạnh đến bệnh tim mạch và hô hấp.",
        },
        "pm10": {
            "title": "Vật chất hạt mịn",
            "subtitle": "(PM10)",
            "icon_file": "pm10.svg",
            "about": "Hạt bụi kích thước lớn hơn PM2.5, gây kích ứng mắt, mũi và đường hô hấp trên.",
        },
        "co": {
            "title": "Carbon monoxide",
            "subtitle": "(CO)",
            "icon_file": "co.svg",
            "about": "Khí không màu, không mùi sinh ra do đốt cháy không hoàn toàn, ảnh hưởng khả năng vận chuyển oxy của máu.",
        },
        "so2": {
            "title": "Lưu huỳnh dioxide",
            "subtitle": "(SO2)",
            "icon_file": "so2.svg",
            "about": "Khí kích ứng mạnh đường thở, đặc biệt với người hen suyễn và người có bệnh nền hô hấp.",
        },
        "no2": {
            "title": "Nitrogen dioxide",
            "subtitle": "(NO2)",
            "icon_file": "no2.svg",
            "about": "Khí phát sinh từ phương tiện giao thông và đốt nhiên liệu, gây viêm và kích ứng đường hô hấp.",
        },
        "o3": {
            "title": "Ozon",
            "subtitle": "(O3)",
            "icon_file": "o3.svg",
            "about": "Ozon tầng mặt đất hình thành quang hóa, có thể gây ho, khó thở và giảm chức năng phổi.",
        },
    }

    def _pollution_level_text(poll_key, current_val):
        bands = POLLUTANT_LEVEL_BANDS.get(poll_key)
        if not bands or pd.isna(current_val):
            return ("Chưa có ngưỡng tham chiếu", "Không rõ", "#94a3b8", -1)

        idx = 5
        for i, hi in enumerate(bands):
            if float(current_val) <= hi:
                idx = i
                break
        level_label = STANDARD_LEVEL_LABELS[idx]
        level_color = AQI_DEF[idx][3]
        if idx == 0:
            level_text = "Mức tốt - an toàn"
        elif idx == 1:
            level_text = "Mức vừa phải - cần theo dõi"
        elif idx == 2:
            level_text = "Bắt đầu ảnh hưởng nhóm nhạy cảm"
        elif idx == 3:
            level_text = "Ô nhiễm cao - ảnh hưởng sức khỏe"
        elif idx == 4:
            level_text = "Ô nhiễm rất cao"
        else:
            level_text = "Nguy hiểm"
        return level_text, level_label, level_color, idx

    def _pollutant_level_context(poll_key, level_idx):
        if level_idx < 0:
            return (
                "Chưa đủ dữ liệu để kết luận theo mức độ.",
                "Tiếp tục quan trắc thêm trước khi đưa ra khuyến nghị vận hành.",
            )
        poll_name = POLLS.get(poll_key, {}).get("label", poll_key.upper())
        if poll_key in {"pm2_5", "pm10"}:
            if level_idx == 0:
                return (
                    f"Nồng độ {poll_name} đang ở mức tốt, rủi ro phơi nhiễm ngắn hạn thấp.",
                    "Duy trì thông gió tự nhiên và theo dõi định kỳ.",
                )
            if level_idx == 1:
                return (
                    f"Nồng độ {poll_name} ở mức vừa phải, điều kiện nhìn chung còn kiểm soát được.",
                    "Theo dõi thêm vào giờ cao điểm giao thông, nhóm nhạy cảm nên giảm phơi nhiễm kéo dài.",
                )
            if level_idx == 2:
                return (
                    f"{poll_name} tăng rõ so với nền, nhóm nhạy cảm có thể bắt đầu khó chịu đường hô hấp.",
                    "Nhóm nhạy cảm nên giảm thời gian ở ngoài trời kéo dài và đeo khẩu trang lọc bụi.",
                )
            if level_idx == 3:
                return (
                    f"{poll_name} ở mức cao, nguy cơ kích ứng và viêm đường hô hấp tăng ở dân số chung.",
                    "Hạn chế vận động mạnh ngoài trời, ưu tiên không gian trong nhà và lọc không khí.",
                )
            return (
                f"{poll_name} đang ở mức rất cao/nguy hiểm, nguy cơ ảnh hưởng sức khỏe cấp tính tăng mạnh.",
                "Giảm tối đa phơi nhiễm ngoài trời, đóng cửa, lọc không khí và theo dõi cảnh báo liên tục.",
            )
        if poll_key in {"no2", "so2"}:
            if level_idx == 0:
                return (
                    f"{poll_name} đang ở mức tốt, tác động cấp tính lên hô hấp thấp.",
                    "Duy trì theo dõi định kỳ tại khu vực giao thông/công nghiệp.",
                )
            if level_idx == 1:
                return (
                    f"{poll_name} ở mức vừa phải, chưa nghiêm trọng nhưng cần theo dõi chặt hơn.",
                    "Giảm phơi nhiễm gần nguồn thải trong thời gian dài, nhất là với nhóm nhạy cảm.",
                )
            if level_idx == 2:
                return (
                    f"{poll_name} bắt đầu ảnh hưởng nhóm nhạy cảm (hen suyễn, bệnh hô hấp nền).",
                    "Giảm phơi nhiễm trực tiếp gần nguồn thải, hạn chế hoạt động gắng sức ngoài trời.",
                )
            if level_idx == 3:
                return (
                    f"{poll_name} ở mức không khỏe mạnh, nguy cơ kích ứng đường thở tăng rõ rệt.",
                    "Ưu tiên ở trong nhà, cân nhắc khẩu trang phù hợp và tránh trục giao thông dày đặc.",
                )
            return (
                f"{poll_name} đạt mức rất cao/nguy hiểm, có thể gây đợt cấp ở người bệnh hô hấp.",
                "Nhóm nhạy cảm nên ở trong nhà, theo dõi triệu chứng và tuân thủ cảnh báo y tế địa phương.",
            )
        if poll_key == "o3":
            if level_idx == 0:
                return (
                    "Ozon tầng mặt đất đang ở mức tốt, rủi ro ngắn hạn tương đối thấp.",
                    "Có thể sinh hoạt bình thường, vẫn nên theo dõi vào buổi trưa/chiều nắng mạnh.",
                )
            if level_idx == 1:
                return (
                    "Ozon đang ở mức vừa phải, điều kiện còn kiểm soát được nhưng không nên chủ quan.",
                    "Giảm vận động kéo dài ngoài trời vào khung giờ nắng gắt, nhất là nhóm nhạy cảm.",
                )
            if level_idx == 2:
                return (
                    "Ozon tăng, có thể gây khó chịu hô hấp nhẹ ở nhóm nhạy cảm khi hoạt động ngoài trời.",
                    "Giảm vận động mạnh ngoài trời vào khung giờ nắng gắt.",
                )
            if level_idx == 3:
                return (
                    "Ozon ở mức cao, có thể làm giảm chức năng phổi tạm thời ở dân số chung.",
                    "Hạn chế tập luyện ngoài trời, ưu tiên hoạt động trong nhà có thông khí phù hợp.",
                )
            return (
                "Ozon rất cao/nguy hiểm, nguy cơ kích ứng hô hấp diện rộng gia tăng.",
                "Tránh hoạt động ngoài trời không cần thiết, đặc biệt với trẻ em, người già và người có bệnh nền.",
            )
        if level_idx == 0:
            return ("CO đang ở mức tốt, rủi ro cấp tính hiện thấp.", "Đảm bảo thông thoáng không gian kín và duy trì theo dõi định kỳ.")
        if level_idx == 1:
            return ("CO ở mức vừa phải, nhìn chung còn kiểm soát được.", "Tăng thông gió tại không gian kín và hạn chế đứng lâu gần nguồn đốt.")
        if level_idx == 2:
            return ("CO tăng, có thể gây mệt mỏi/đau đầu nhẹ ở môi trường kém thông gió.", "Tăng thông gió, hạn chế đứng lâu gần nguồn đốt và bãi xe kín.")
        if level_idx == 3:
            return ("CO ở mức cao, nguy cơ ảnh hưởng vận chuyển oxy trong máu tăng.", "Tránh vận động mạnh ở nơi bí khí, ưu tiên di chuyển sang khu vực thông thoáng.")
        return ("CO ở mức rất cao/nguy hiểm, cần cảnh giác phơi nhiễm cấp tính.", "Giảm tối đa thời gian ở không gian kín có nguồn đốt, theo dõi cảnh báo và xử lý thông gió ngay.")

    def _svg_data_uri(file_name):
        svg_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "components", file_name))
        try:
            with open(svg_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/svg+xml;base64,{encoded}"
        except Exception:
            return ""

    available_polls = [k for k in pollutant_meta if k in df.columns]
    if not available_polls:
        return

    st.markdown(
        "<div class='card pollutant-card-wrap' style='margin-top:10px'><div class='card-title'><span class='q-tag'>Insights</span>Chỉ số chất ô nhiễm theo thành phần</div>",
        unsafe_allow_html=True,
    )
    ordered = ["pm2_5", "pm10", "co", "so2", "no2", "o3"]
    card_html = []
    for poll_key in ordered:
        if poll_key not in available_polls:
            continue
        meta = pollutant_meta[poll_key]
        series = df[poll_key].dropna()
        if series.empty:
            continue
        current_val = round(series.mean(), 1)
        unit = POLLS[poll_key]["unit"] if poll_key in POLLS else ""
        level_text, current_level_label, current_level_color, level_idx = _pollution_level_text(poll_key, current_val)
        _level_insight, level_recommend = _pollutant_level_context(poll_key, level_idx)
        icon_uri = _svg_data_uri(meta["icon_file"])
        icon_block = (
            f"<img src='{icon_uri}' class='pollutant-icon' alt='{meta['title']}'/>"
            if icon_uri
            else "<div class='pollutant-icon pollutant-icon-fallback'></div>"
        )
        tooltip_html = (
            "<div class='pollutant-tooltip'>"
            f"<div class='pollutant-tooltip-head'>{html.escape(meta['title'])} {html.escape(meta['subtitle'])}</div>"
            "<div class='pollutant-tooltip-row'>"
            "<span class='k'>Chất này là gì?</span>"
            f"<span class='v'>{html.escape(meta['about'])}</span>"
            "</div>"
            "<div class='pollutant-tooltip-row'>"
            "<span class='k'>Mức hiện tại</span>"
            f"<span class='v'><strong>{current_val:g} {html.escape(unit)}</strong> - {html.escape(level_text)} ({html.escape(current_level_label)})</span>"
            "</div>"
            "<div class='pollutant-tooltip-row'>"
            "<span class='k'>Khuyến nghị</span>"
            f"<span class='v'>{html.escape(level_recommend)}</span>"
            "</div>"
            "</div>"
        )
        card_html.append(
            (
                f"<div class='pollutant-mini-card' style='border-left-color:{current_level_color};'>"
                f"<div class='pollutant-mini-left'>{icon_block}</div>"
                "<div class='pollutant-mini-mid'>"
                f"<div class='pollutant-mini-title'>{meta['title']}</div>"
                f"<div class='pollutant-mini-sub'>{meta['subtitle']}</div>"
                "</div>"
                "<div class='pollutant-mini-right'>"
                f"<div class='pollutant-mini-value'>{current_val:g}</div>"
                f"<div class='pollutant-mini-unit'>{unit}</div>"
                "</div>"
                f"{tooltip_html}"
                "</div>"
            )
        )
    st.markdown(f"<div class='pollutant-mini-grid'>{''.join(card_html)}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_overview(state, df_override=None, scope_label="Việt Nam"):
    """
    Renders the complete overview section, including the Hero UI, KPI strip,
    trend grid, and pollutant breakdown cards.
    """
    source_df = df_override if df_override is not None else state.get("df", pd.DataFrame())
    selected_range = _get_timeframe_selector()
    filtered_df = _filter_df_by_time_range(source_df, selected_range)
    if filtered_df.empty:
        st.warning(f"Không có dữ liệu trong khung thời gian {selected_range}.")
        return

    local_state = _build_scope_metrics(filtered_df, state, selected_range)
    globals().update(local_state)
    AQI_DEF = local_state["AQI_DEF"]
    _col = local_state["_col"]
    avg_aqi = local_state["avg_aqi"]
    _lbl = local_state["_lbl"]
    avg_pm25 = local_state["avg_pm25"]
    cig_n = local_state["cig_n"]
    days = local_state["days"]
    worst = local_state["worst"]
    dangerp = local_state["dangerp"]
    aqi_1d_color = local_state["aqi_1d_color"]
    aqi_1d_text = local_state["aqi_1d_text"]
    pm_1d_color = local_state["pm_1d_color"]
    pm_1d_text = local_state["pm_1d_text"]
    aqi_7d_color = local_state["aqi_7d_color"]
    aqi_7d_text = local_state["aqi_7d_text"]
    pm_7d_color = local_state["pm_7d_color"]
    pm_7d_text = local_state["pm_7d_text"]
    trend_primary_kicker = local_state["trend_primary_kicker"]
    trend_secondary_kicker = local_state["trend_secondary_kicker"]
    exposure_label = local_state["exposure_label"]
    rank_up_line = local_state["rank_up_line"]
    rank_down_line = local_state["rank_down_line"]
    health_hd = local_state["health_hd"]
    latest_obs = local_state["latest_obs"]
    who_pm25_multi = local_state["who_pm25_multi"]
    sel = local_state["sel"]
    df = local_state["df"]
    is_city_trimmed = local_state["is_city_trimmed"]
    plot_city_limit = local_state["plot_city_limit"]
    city_priority = local_state["city_priority"]
    vietnam_svg_base64 = local_state.get("vietnam_svg_base64", "")
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    hero_bg_html = ""
    if vietnam_svg_base64:
        hero_bg_html = (
            "<div class='iq-hero-vn-bg' "
            f"style=\"background-image:url('data:image/svg+xml;base64,{vietnam_svg_base64}')\"></div>"
        )



    aqi_reference = [(lo, hi, label) for lo, hi, label, _ in AQI_DEF]
    pm25_warning_map = {
        "Tốt": "Không có cảnh báo đáng kể.",
        "Vừa phải": "Nhóm nhạy cảm nên giảm vận động ngoài trời.",
        "Không lành mạnh cho nhóm nhạy cảm": "Nhóm nhạy cảm tránh hoạt động ngoài trời kéo dài.",
        "Không khỏe mạnh": "Hạn chế ra ngoài, ưu tiên khẩu trang lọc bụi mịn.",
        "Rất không tốt cho sức khỏe": "Tránh hoạt động gắng sức ngoài trời.",
        "Nguy hiểm": "Mọi người nên hạn chế tối đa hoạt động ngoài trời.",
    }
    current_band = next(
        (item for item in aqi_reference if item[0] <= avg_aqi <= item[1]),
        aqi_reference[-1],
    )
    current_pm_warning = pm25_warning_map.get(
        current_band[2], "Theo dõi AQI theo thời gian thực."
    )
    latest_obs_text = (
        latest_obs.strftime("%H:%M · %d/%m/%Y") if pd.notna(latest_obs) else "N/A"
    )
    hero_insights = _compute_hero_insights(df, avg_aqi, _lbl)



    cig_svg = "<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' style='margin-right: 4px; vertical-align: middle; margin-top: -2px;'><path d='M18 12H2v4h16'/><path d='M22 12v4'/><path d='M7 12v4'/><path d='M18 8c0-2.5-2-2.5-2-5'/><path d='M22 8c0-2.5-2-2.5-2-5'/></svg>"

    iqair_hybrid_html = (
        f"<div class='iq-wrap'>"
        f"<div class='iq-live-head'>"
        f"<div class='iq-title'>Live AQI Vietnam · IQAir Hybrid</div>"
        f"<div class='iq-meta'>Cập nhật gần nhất: {latest_obs_text} · Dữ liệu từ bộ cảm biến nội bộ</div>"
        f"</div>"
        f"<div class='iq-card iq-card-hero'>"
        f"{hero_bg_html}"
        f"<div class='iq-hero-content'>"
        f"<div class='iq-hero-kicker'>CHẤT LƯỢNG KHÔNG KHÍ TẠI {scope_label.upper()} TRONG {exposure_label.upper()}</div>"
        f"<div class='iq-hero-row' style='display: flex; align-items: center; gap: 16px;'>"
        f"<div style='display: flex; align-items: baseline; gap: 8px;'>"
        f"<div class='iq-hero-aqi' style='color:{_col}'>{avg_aqi}</div>"
        f"<div class='iq-hero-status'>{_lbl}</div>"
        f"</div>"
        f"<div style='font-size: 1.15rem; color: {aqi_1d_color}; font-weight: 700; white-space: nowrap;'>{aqi_1d_text}</div>"
        f"</div>"
        f"<div style='display: flex; gap: 48px; margin-top: 20px; flex-wrap: wrap; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.15);'>"
        f"<div style='display: flex; flex-direction: column; gap: 6px;'>"
        f"<div style='font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; font-weight: 600;'>Khung giờ đáng chú ý</div>"
        f"<div style='font-size: 1.1rem; font-weight: 600;'>{hero_insights['slot_focus']}</div>"
        f"<div style='font-size: 0.9rem; opacity: 0.9;'>{hero_insights['slot_focus_sub']}</div>"
        f"</div>"
        f"<div style='display: flex; flex-direction: column; gap: 6px;'>"
        f"<div style='font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; font-weight: 600;'>Mức độ tiếp xúc</div>"
        f"<div style='font-size: 1.1rem; font-weight: 600; display: flex; align-items: center;'>{cig_svg} Tương đương {cig_n} điếu thuốc lá</div>"
        f"<div style='font-size: 0.9rem; opacity: 0.9;'>Trong thời gian {exposure_label}</div>"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(iqair_hybrid_html, unsafe_allow_html=True)
    _render_pollutant_cards(df)

    if is_city_trimmed:
        st.caption(
            f"Hiển thị Top {plot_city_limit}/{len(city_priority)} khu vực theo AQI trung bình cho các biểu đồ theo Tỉnh/thành để giữ bố cục gọn."
        )


def render(df):
    """
    Main entry point for the Overview Tab.
    Loads the global context and builds interactive timeline charts for AQI and PM2.5.
    """
    ctx = st.session_state.get("dashboard_context", {})
    if ctx is None:
        st.error("Thiếu ngữ cảnh dashboard.")
        st.stop()
    globals().update(ctx)
    selected_range = st.session_state.get("ov_time_range", "24h")
    df = _filter_df_by_time_range(df, selected_range)


    if df.empty:
        st.info(f"Không có dữ liệu để hiển thị bản đồ/xếp hạng trong khung {selected_range}.")
        return

    map_col, donut_col = st.columns([2.2, 1.2], gap="small")
    city_geo = (
        df.groupby("city", observed=False)
        .agg(
            lat=("lat", "mean"),
            lon=("lon", "mean"),
            aqi=("aqi", "mean"),
            pm2_5=("pm2_5", "mean"),
            n=("aqi", "size"),
        )
        .reset_index()
        .dropna(subset=["lat", "lon"])
    )
    city_geo["aqi_lbl"] = pd.cut(
        city_geo["aqi"],
        bins=[-np.inf, 50, 100, 150, 200, 300, np.inf],
        labels=[x[2] for x in AQI_DEF],
        include_lowest=True,
    ).fillna(AQI_DEF[-1][2])
    city_geo["marker_size"] = (city_geo["pm2_5"].clip(lower=8) * 0.7).clip(
        lower=8, upper=28
    )
    aqi_cap = AQI_DEF[-1][1]
    # Build a smooth AQI gradient by interpolating between AQI_DEF color anchors.
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _mix_color(c1, c2, t):
        r1, g1, b1 = _hex_to_rgb(c1)
        r2, g2, b2 = _hex_to_rgb(c2)
        return _rgb_to_hex(
            (
                int(r1 + (r2 - r1) * t),
                int(g1 + (g2 - g1) * t),
                int(b1 + (b2 - b1) * t),
            )
        )

    color_stops = [(0, AQI_DEF[0][3])] + [(hi, col) for _, hi, _, col in AQI_DEF]
    aqi_colorscale = []
    smooth_steps = 4
    for i in range(len(color_stops) - 1):
        v1, c1 = color_stops[i]
        v2, c2 = color_stops[i + 1]
        for s in range(smooth_steps):
            t = s / smooth_steps
            v = v1 + (v2 - v1) * t
            aqi_colorscale.append([v / aqi_cap, _mix_color(c1, c2, t)])
    aqi_colorscale.append([1.0, AQI_DEF[-1][3]])

    fig_map = go.Figure(
        go.Scattermapbox(
            lat=city_geo["lat"],
            lon=city_geo["lon"],
            mode="markers",
            text=city_geo["city"],
            marker=dict(
                size=city_geo["marker_size"],
                color=city_geo["aqi"],
                colorscale=aqi_colorscale,
                cmin=0,
                cmax=aqi_cap,
                opacity=0.84,
                colorbar=dict(
                    title="AQI",
                    thickness=10,
                    tickfont=dict(size=8),
                    tickvals=[(lo + hi) / 2 for lo, hi, _, _ in AQI_DEF],
                    ticktext=[
                        f"{lo}-{hi}: {lbl}" if hi < AQI_DEF[-1][1] else f"{lo}+: {lbl}"
                        for lo, hi, lbl, _ in AQI_DEF
                    ],
                    x=1.01,
                ),
            ),
            customdata=np.stack(
                [city_geo["aqi_lbl"], city_geo["pm2_5"].round(1), city_geo["n"]],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "AQI TB: %{marker.color:.1f} (%{customdata[0]})<br>"
                "PM2.5 TB: %{customdata[1]} µg/m³<br>"
                "Số quan trắc: %{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig_map.update_layout(
        mapbox=dict(
            style="carto-positron",
            center=dict(
                lat=float(city_geo["lat"].mean()), lon=float(city_geo["lon"].mean())
            ),
            zoom=4.2,
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                x=0.01,
                y=0.99,
                xanchor="left",
                yanchor="top",
                showactive=False,
                bgcolor="rgba(255,255,255,0.94)",
                bordercolor="rgba(148,163,184,0.65)",
                borderwidth=1,
                pad=dict(r=6, t=2, b=2, l=2),
                buttons=[
                    dict(
                        label="↺",
                        method="relayout",
                        args=[
                            {
                                "mapbox.center.lat": float(city_geo["lat"].mean()),
                                "mapbox.center.lon": float(city_geo["lon"].mean()),
                                "mapbox.zoom": 4.2,
                            }
                        ],
                    )
                ],
            )
        ],
        margin=dict(l=2, r=2, t=6, b=2),
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro", size=10, color="#334155"),
    )
    with map_col:
        st.markdown(
            '<div class="card"><div class="card-title"><span class="q-tag">Overview</span>Bản đồ AQI theo khu vực</div><div class="card-sub">Màu sắc biểu diễn AQI trung bình, kích thước điểm phản ánh PM2.5.</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            fig_map,
            width="stretch",
            config={"displayModeBar": False, "scrollZoom": True},
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with donut_col:
        st.markdown(
            '<div class="card donut-card"><div class="card-title"><span class="q-tag">Overview</span>Cơ cấu mức AQI</div><div class="card-sub">Phân bố tỷ trọng các mức chất lượng không khí.</div>',
            unsafe_allow_html=True,
        )
        band_dist = (
            df["aqi_lbl"]
            .value_counts(normalize=True)
            .reindex([x[2] for x in AQI_DEF])
            .fillna(0)
            * 100
        )
        dominant_idx = band_dist.values.argmax()
        dominant_label = band_dist.index[dominant_idx]
        dominant_pct = band_dist.values[dominant_idx]
        dominant_color = AQI_DEF[dominant_idx][3]
        pull_vals = [0.04] * len(band_dist)
        pull_vals[dominant_idx] = 0.10
        fig_dn = go.Figure(
            go.Pie(
                labels=band_dist.index,
                values=band_dist.round(2),
                hole=0.55,
                pull=pull_vals,
                marker=dict(
                    colors=[x[3] for x in AQI_DEF],
                    line=dict(width=2.5, color="#ffffff"),
                ),
                textinfo="percent",
                textfont=dict(size=14, color="#ffffff", family="Be Vietnam Pro"),
                textposition="inside",
                insidetextorientation="horizontal",
                hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
                direction="clockwise",
                sort=False,
                rotation=90,
            )
        )
        fig_dn.update_layout(
            annotations=[
                dict(
                    text=f"<b style='font-size:1.6rem;color:{dominant_color}'>{dominant_pct:.0f}%</b>"
                    f"<br><span style='font-size:.72rem;color:#64748b'>{dominant_label}</span>",
                    x=0.5,
                    y=0.5,
                    font_size=12,
                    showarrow=False,
                )
            ]
        )
        ml(fig_dn, h=310, margin=dict(l=10, r=10, t=14, b=10), showlegend=False)
        st.plotly_chart(
            fig_dn, width="stretch", config={"displayModeBar": False}
        )
        legend_items = "".join(
            f"<span class='donut-legend-item'><span class='donut-legend-dot' style='background:{c}'></span>{lbl}</span>"
            for _, _, lbl, c in AQI_DEF
        )
        st.markdown(
            f"<div class='donut-legend'>{legend_items}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    rank_now = city_geo.sort_values("aqi", ascending=False).head(8).copy()
    rank_clean = city_geo.sort_values("aqi", ascending=True).head(8).copy()

    def _aqi_badge(val):
        _, badge_col = aqi_meta(float(val))
        badge_text = "#ffffff" if float(val) >= 151 else "#0f172a"
        return badge_col, badge_text

    def _rows_html(rank_df):
        rows = []
        for idx, row in enumerate(rank_df.itertuples(index=False), start=1):
            badge_col, badge_text = _aqi_badge(row.aqi)
            highlight_cls = " ov-live-row-top" if idx == 1 else ""
            rows.append(
                f"<div class='ov-live-row{highlight_cls}'>"
                f"<div class='ov-live-col ov-live-no'>{idx}</div>"
                f"<div class='ov-live-col ov-live-city'><span class='ov-flag-icon'>★</span> {row.city}</div>"
                f"<div class='ov-live-col ov-live-aqi'><span class='ov-aqi-pill' style='background:{badge_col};color:{badge_text}'>{row.aqi:.0f}</span></div>"
                "</div>"
            )
        return "".join(rows)


    with st.expander("Bảng xếp hạng trực tiếp các Tỉnh/thành", expanded=False):
        rank_left, rank_right = st.columns(2, gap="small")
        with rank_left:
            st.markdown(
                f"""
                <div class="ov-live-card">
                    <div class="ov-live-head">Xếp hạng trực tiếp các tỉnh/thành ô nhiễm nhất</div>
                    <div class="ov-live-sub">Xếp hạng các Tỉnh/thành ô nhiễm nhất tại Việt Nam theo thời gian thực</div>
                    <div class="ov-live-table-head">
                        <div>#</div><div>Tỉnh/thành</div><div>AQI Mỹ</div>
                    </div>
                    {_rows_html(rank_now)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with rank_right:
            st.markdown(
                f"""
                <div class="ov-live-card">
                    <div class="ov-live-head">Xếp hạng trực tiếp các tỉnh/thành trong lành nhất</div>
                    <div class="ov-live-sub">Xếp hạng các tỉnh/thành trong lành nhất tại Việt Nam theo thời gian thực</div>
                    <div class="ov-live-table-head">
                        <div>#</div><div>Tỉnh/thành</div><div>AQI Mỹ</div>
                    </div>
                    {_rows_html(rank_clean)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ══════════════════════════════════════════════
