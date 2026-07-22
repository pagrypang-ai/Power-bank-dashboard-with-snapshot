from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st


st.set_page_config(page_title="Product Value Dashboard", layout="wide")

BASE_DIR = Path(__file__).parent
CURRENT_DATE = pd.Timestamp.today().date()
BRAND_COLOR_PALETTE = [
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#332288",
    "#88CCEE",
    "#882255",
    "#44AA99",
    "#AA4499",
    "#117733",
    "#DDCC77",
    "#661100",
    "#6699CC",
    "#AA4466",
    "#6A3D9A",
    "#B15928",
    "#1B9E77",
    "#E7298A",
    "#66A61E",
    "#E6AB02",
    "#A6761D",
    "#666666",
    "#E41A1C",
]
DISPLAY_FIELDS = [
    "Brand",
    "Pickup or Not",
    "Sold by",
    "Rating",
    "Number of Reviews",
    "Was Price",
    "Price",
    "Capacity/mAh",
    "Color",
    "Size",
    "Weight",
    "Phone Stand",
    "LED Display",
    "Wired Connect Type",
    "Wireless or Not",
    "Fast Charging Protocol",
    "USB Power (Max)",
    "Warranty",
]


def parse_number(value):
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", "").replace("$", ""))
    return float(match.group(0)) if match else None


def parse_tracking_date(column_name):
    text = str(column_name).strip()
    if not re.match(r"^20\d{2}[-/]\d{1,2}[-/]\d{1,2}$", text):
        return None
    try:
        return pd.to_datetime(text).date()
    except Exception:
        return None


def tracking_date_columns(df):
    columns = []
    for column in df.columns:
        parsed = parse_tracking_date(column)
        if parsed is not None:
            columns.append((column, parsed))
    return sorted(columns, key=lambda item: item[1])


def normalize_brand(value) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    text = re.sub(r"\s+", " ", text).replace("™", "")
    key = text.lower()
    mapping = {
        "mophie": "mophie",
        "mycharge": "myCharge",
        "best buy essentials": "Best Buy essentials",
        "popsockets x anker": "PopSockets X Anker",
        "velvet caviar": "VELVET CAVIAR",
        "torras": "TORRAS",
        "iniu": "INIU",
    }
    return mapping.get(key, text if text else "Unknown")


def normalize_pickup(value) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if "pickup" in text:
        return "Pickup"
    if "online" in text:
        return "Online"
    return "N/A" if not text else str(value).strip().title()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "Pickup or not": "Pickup or Not",
        "Phone stand": "Phone Stand",
        "LED display": "LED Display",
        "Magnetic charging": "Magnetic Charging",
        "Fast charging protocol": "Fast Charging Protocol",
        "USB power (Max)": "USB Power (Max)",
        "URL of Image": "Image URL",
    }
    df = df.rename(columns=rename).copy()
    defaults = {
        "Channel": "Best Buy",
        "Brand": "Unknown",
        "Model Number": "",
        "Image URL": "",
        "Pickup or Not": "",
        "Sold by": "",
        "Rating": "",
        "Number of Reviews": "",
        "Was Price": "",
        "Price": "",
        "Capacity/mAh": "",
        "Color": "",
        "Size": "",
        "Weight": "",
        "Phone Stand": "",
        "LED Display": "",
        "Wired Connect Type": "",
        "Wireless or Not": "",
        "Magnetic Charging": "N/A",
        "Fast Charging Protocol": "",
        "USB Power (Max)": "",
        "Warranty": "",
        "Link": "",
    }
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default
    return df


def status_events(row, date_cols):
    events = []
    for column, event_date in date_cols:
        value = row.get(column)
        if pd.isna(value) or value == "":
            continue
        text = str(value).lower()
        if "add" in text:
            events.append((event_date, "available"))
        if "unavailable" in text or "sold out" in text:
            events.append((event_date, "unavailable"))
    return events


def status_on_date(events, query_date):
    status = "unavailable"
    for event_date, event_status in events:
        if event_date <= query_date:
            status = event_status
    return status


def is_discounted(row) -> bool:
    was = row.get("Was Price Num")
    price = row.get("Price Num")
    return pd.notna(was) and pd.notna(price) and was > price


@st.cache_data(ttl=600)
def load_data(uploaded_file=None, sheet_csv_url=""):
    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".xlsx"):
            raw = pd.read_excel(uploaded_file)
        else:
            raw = pd.read_csv(uploaded_file)
    elif sheet_csv_url:
        raw = pd.read_csv(sheet_csv_url)
    else:
        raw = pd.read_csv(BASE_DIR / "data/product_data_sample.csv")

    df = normalize_columns(raw)
    df["Channel"] = df["Channel"].fillna("Best Buy").astype(str).str.strip()
    df.loc[df["Channel"] == "", "Channel"] = "Best Buy"
    df["Channel Group"] = df["Channel"]
    df["Brand"] = df["Brand"].fillna("").astype(str).str.strip()
    df["Brand Group"] = df["Brand"].apply(normalize_brand)
    df["Pickup Group"] = df["Pickup or Not"].apply(normalize_pickup)
    df["Price Num"] = df["Price"].apply(parse_number)
    df["Was Price Num"] = df["Was Price"].apply(parse_number)
    df["Capacity Num"] = df["Capacity/mAh"].apply(parse_number)
    df["USB Num"] = df["USB Power (Max)"].apply(parse_number)
    df["Capacity Group"] = df["Capacity Num"].apply(lambda x: f"{int(x):,} mAh" if pd.notna(x) else "N/A")
    df["USB Group"] = df["USB Power (Max)"].fillna("N/A").astype(str)
    df["Magnetic Charging Group"] = df["Magnetic Charging"].fillna("N/A").astype(str).str.strip()
    df.loc[df["Magnetic Charging Group"] == "", "Magnetic Charging Group"] = "N/A"
    df["Image Source"] = df["Image URL"].fillna("").astype(str)
    df["Discounted"] = df.apply(is_discounted, axis=1)

    date_cols = tracking_date_columns(df)
    latest_tracking_date = date_cols[-1][1] if date_cols else CURRENT_DATE
    df["Shelf Events"] = df.apply(lambda row: status_events(row, date_cols), axis=1)
    df["Current Shelf Status"] = df["Shelf Events"].apply(lambda events: status_on_date(events, latest_tracking_date))

    capacities = sorted(df["Capacity Num"].dropna().unique())
    rank = {capacity: index + 1 for index, capacity in enumerate(capacities)}
    usb_ranges = df.groupby("Capacity Num")["USB Num"].agg(["min", "max"]).to_dict("index")

    def value_index(row):
        capacity = row["Capacity Num"]
        usb = row["USB Num"]
        if pd.isna(capacity):
            return None
        base = rank[capacity]
        usb_range = usb_ranges.get(capacity, {})
        low, high = usb_range.get("min"), usb_range.get("max")
        if pd.isna(usb) or pd.isna(low) or pd.isna(high) or high == low:
            return float(base)
        return base + ((usb - low) / (high - low)) * 0.8

    df["Value Index"] = df.apply(value_index, axis=1)
    return df, date_cols, latest_tracking_date


def clean_altair_df(df, columns):
    chart_df = df[[column for column in columns if column in df.columns]].copy()
    for column in chart_df.columns:
        if column not in {"Price Num", "Value Index", "Available SKUs", "Pickup SKUs", "Online SKUs", "Discounted SKUs", "Discount Rate"}:
            chart_df[column] = chart_df[column].fillna("").astype(str)
    return chart_df


def render_value_matrix(df, date_cols):
    title_col, mode_col = st.columns([3, 1])
    with title_col:
        st.title("Product Value Matrix")
    with mode_col:
        display_mode = st.radio("Point Display", ["Product Image", "Brand Color"], horizontal=True)

    all_dates = [item[1] for item in date_cols]
    min_date = min(all_dates) if all_dates else date(2024, 1, 1)
    max_date = max(max(all_dates), CURRENT_DATE) if all_dates else CURRENT_DATE
    query_date = st.sidebar.date_input("Query Date", max_date, min_value=min_date, max_value=max_date)
    if isinstance(query_date, tuple):
        query_date = query_date[0]

    df = df.copy()
    df["Availability on Query Date"] = df["Shelf Events"].apply(lambda events: status_on_date(events, query_date))
    channels = st.sidebar.multiselect("Channel", sorted(df["Channel Group"].dropna().unique()), default=sorted(df["Channel Group"].dropna().unique()))
    brands = st.sidebar.multiselect("Brand", sorted(df["Brand Group"].dropna().unique()), default=sorted(df["Brand Group"].dropna().unique()))
    pickup = st.sidebar.multiselect("Pickup or Not", sorted(df["Pickup Group"].dropna().unique()), default=sorted(df["Pickup Group"].dropna().unique()))
    availability = st.sidebar.multiselect("Availability on Query Date", ["available", "unavailable"], default=["available", "unavailable"])
    magnetic = st.sidebar.multiselect("Magnetic Charging", sorted(df["Magnetic Charging Group"].dropna().unique()), default=sorted(df["Magnetic Charging Group"].dropna().unique()))
    capacity = st.sidebar.multiselect("Capacity", sorted(df["Capacity Group"].dropna().unique()), default=sorted(df["Capacity Group"].dropna().unique()))
    usb = st.sidebar.multiselect("USB Power", sorted(df["USB Group"].dropna().unique()), default=sorted(df["USB Group"].dropna().unique()))

    mask = (
        df["Channel Group"].isin(channels)
        & df["Brand Group"].isin(brands)
        & df["Pickup Group"].isin(pickup)
        & df["Availability on Query Date"].isin(availability)
        & df["Magnetic Charging Group"].isin(magnetic)
        & df["Capacity Group"].isin(capacity)
        & df["USB Group"].isin(usb)
    )
    plot_df = df.loc[mask & df["Price Num"].notna() & df["Value Index"].notna() & (df["Image Source"] != "")].copy()

    with st.expander("Debug: products not shown in scatter plot"):
        debug_df = df.copy()
        debug_df["In Filter"] = mask
        debug_df["Has Price Num"] = debug_df["Price Num"].notna()
        debug_df["Has Value Index"] = debug_df["Value Index"].notna()
        debug_df["Has Image Source"] = debug_df["Image Source"].astype(str).str.strip() != ""
        debug_df["Shown In Plot"] = (
            debug_df["In Filter"]
            & debug_df["Has Price Num"]
            & debug_df["Has Value Index"]
            & debug_df["Has Image Source"]
        )

        st.write(
            "Products not shown in scatter plot",
            debug_df.loc[
                ~debug_df["Shown In Plot"],
                [
                    "Channel",
                    "Brand",
                    "Model Number",
                    "Price",
                    "Price Num",
                    "Capacity/mAh",
                    "Capacity Num",
                    "USB Power (Max)",
                    "USB Num",
                    "Image Source",
                    "In Filter",
                    "Has Price Num",
                    "Has Value Index",
                    "Has Image Source",
                ],
            ],
        )

    col1, col2, col3, col4 = st.columns(4)    

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Shown Products", f"{len(plot_df):,}")
    col2.metric("Available on Query Date", f"{plot_df['Availability on Query Date'].eq('available').sum():,}")
    col3.metric("Median Price", "N/A" if plot_df.empty else f"${plot_df['Price Num'].median():,.2f}")
    col4.metric(
        "Capacity Range",
        "N/A" if plot_df.empty else f"{int(plot_df['Capacity Num'].min()):,}-{int(plot_df['Capacity Num'].max()):,} mAh",
    )

    tooltip = [alt.Tooltip(f"{field}:N", title=field) for field in DISPLAY_FIELDS]
    chart_columns = list(dict.fromkeys(["Price Num", "Value Index", "Image Source", "Link", "Brand Group", *DISPLAY_FIELDS]))
    chart_df = clean_altair_df(plot_df, chart_columns)
    x_axis = alt.X("Price Num:Q", title="Price ($)", scale=alt.Scale(zero=False))
    y_axis = alt.Y("Value Index:Q", title="Product Value (Capacity + Output Power Max)")

    if display_mode == "Product Image":
        chart = (
            alt.Chart(chart_df)
            .mark_image(width=46, height=46)
            .encode(x=x_axis, y=y_axis, url="Image Source:N", href="Link:N", tooltip=tooltip)
            .properties(height=720)
            .interactive()
        )
    else:
        brand_domain = sorted(df["Brand Group"].dropna().astype(str).unique())
        brand_range = [BRAND_COLOR_PALETTE[index % len(BRAND_COLOR_PALETTE)] for index, _ in enumerate(brand_domain)]
        base_chart = alt.Chart(chart_df).encode(x=x_axis, y=y_axis)
        point_chart = base_chart.mark_circle(size=170, opacity=0.92, stroke="#ffffff", strokeWidth=1.5).encode(
            color=alt.Color("Brand Group:N", title="Brand", scale=alt.Scale(domain=brand_domain, range=brand_range)),
            href="Link:N",
            tooltip=tooltip,
        )
        label_chart = base_chart.mark_text(
            align="center",
            baseline="top",
            dy=12,
            fontSize=10,
            fontWeight="normal",
            color="#1f2933",
            opacity=0.46,
        ).encode(text="Brand Group:N")
        chart = (point_chart + label_chart).properties(height=720).interactive()

    st.altair_chart(chart, use_container_width=True)


def latest_add_activity(channel_df, date_cols):
    for column, event_date in reversed(date_cols):
        mask = channel_df[column].fillna("").astype(str).str.lower().str.contains("add")
        if mask.any():
            return column, event_date, channel_df.loc[mask].copy()
    return None, None, channel_df.iloc[0:0].copy()


def group_long_tail_counts(series, top_n=10):
    counts = series.value_counts()
    if len(counts) <= top_n:
        return counts.rename_axis("Brand").reset_index(name="Available SKUs")
    head = counts.head(top_n)
    others = pd.Series({"Others": counts.iloc[top_n:].sum()})
    grouped = pd.concat([head, others])
    return grouped.rename_axis("Brand").reset_index(name="Available SKUs")


def build_snapshot(channel_df, date_cols, latest_tracking_date):
    channel_df = channel_df.copy()
    channel_df["Snapshot Status"] = channel_df["Shelf Events"].apply(lambda events: status_on_date(events, latest_tracking_date))
    available = channel_df[channel_df["Snapshot Status"] == "available"].copy()
    total_skus = len(channel_df)
    available_skus = len(available)
    unavailable_skus = total_skus - available_skus
    pickup_skus = int((available["Pickup Group"] == "Pickup").sum())
    pickup_coverage = pickup_skus / available_skus if available_skus else 0

    brand_counts = group_long_tail_counts(available["Brand Group"], top_n=10) if not available.empty else pd.DataFrame(columns=["Brand", "Available SKUs"])
    major_brands = list(available["Brand Group"].value_counts().head(8).index)
    available["Major Brand"] = available["Brand Group"].where(available["Brand Group"].isin(major_brands), "Others")
    pickup_df = (
        available.groupby(["Major Brand", "Pickup Group"]).size().reset_index(name="SKUs")
        if not available.empty
        else pd.DataFrame(columns=["Major Brand", "Pickup Group", "SKUs"])
    )
    discount_df = (
        available.groupby("Brand Group")
        .agg(**{"Available SKUs": ("Brand Group", "size"), "Discounted SKUs": ("Discounted", "sum")})
        .reset_index()
        .rename(columns={"Brand Group": "Brand"})
    )
    if not discount_df.empty:
        discount_df["Discount Rate"] = discount_df["Discounted SKUs"] / discount_df["Available SKUs"]
        discount_df = discount_df.sort_values(["Discounted SKUs", "Available SKUs"], ascending=False).head(10)

    add_col, add_date, new_rows = latest_add_activity(channel_df, date_cols)
    if not new_rows.empty:
        new_table = (
            new_rows.groupby("Brand Group")
            .agg(**{"New SKUs": ("Brand Group", "size"), "Model Numbers": ("Model Number", lambda values: ", ".join([str(v) for v in values if str(v).strip()][:8]))})
            .reset_index()
            .rename(columns={"Brand Group": "Brand"})
            .sort_values(["New SKUs", "Brand"], ascending=[False, True])
        )
    else:
        new_table = pd.DataFrame(columns=["Brand", "New SKUs", "Model Numbers"])

    leaders = available["Brand Group"].value_counts().head(3)
    leader_text = ", ".join(f"{brand} ({count})" for brand, count in leaders.items()) if not leaders.empty else "No available SKUs"
    pickup_text = "pickup-driven" if pickup_coverage >= 0.5 else "online-driven"
    discount_leaders = discount_df[discount_df["Discounted SKUs"] > 0].head(3)
    discount_text = ", ".join(f"{row['Brand']} ({int(row['Discounted SKUs'])})" for _, row in discount_leaders.iterrows()) or "No clear discount signal"
    new_text = (
        ", ".join(f"{row['Brand']} ({int(row['New SKUs'])})" for _, row in new_table.head(3).iterrows())
        if not new_table.empty
        else "No new products"
    )
    insights = [
        f"Brand leadership: {leader_text} lead the available shelf by SKU count.",
        f"Fulfillment mix: this channel is {pickup_text}, with {pickup_coverage:.0%} pickup coverage among available SKUs.",
        f"Commercial signal: price drops are strongest at {discount_text}; newest activity is {new_text}.",
    ]

    raw_brand_values = set(channel_df["Brand"].dropna().astype(str).str.strip())
    std_brand_values = set(channel_df["Brand Group"].dropna().astype(str).str.strip())
    quality_notes = []
    normalized_brand_count = max(0, len(raw_brand_values) - len(std_brand_values))
    if normalized_brand_count:
        quality_notes.append(f"{normalized_brand_count} brand name variant(s) were standardized.")
    missing_price = int(channel_df["Price Num"].isna().sum())
    missing_was_price = int(channel_df["Was Price Num"].isna().sum())
    missing_model = int(channel_df["Model Number"].fillna("").astype(str).str.strip().eq("").sum())
    duplicate_models = int(channel_df[channel_df["Model Number"].notna()].duplicated(["Brand Group", "Model Number"]).sum())
    abnormal_prices = int(((channel_df["Price Num"] <= 0) | ((channel_df["Was Price Num"].notna()) & (channel_df["Price Num"].notna()) & (channel_df["Was Price Num"] < channel_df["Price Num"]))).sum())
    if missing_price:
        quality_notes.append(f"{missing_price} SKU(s) are missing current price.")
    if missing_was_price:
        quality_notes.append(f"{missing_was_price} SKU(s) are missing was price.")
    if missing_model:
        quality_notes.append(f"{missing_model} SKU(s) are missing model number.")
    if duplicate_models:
        quality_notes.append(f"{duplicate_models} duplicate brand/model row(s) detected.")
    if abnormal_prices:
        quality_notes.append(f"{abnormal_prices} abnormal price relationship(s) detected.")

    return {
        "available": available,
        "total_skus": total_skus,
        "available_skus": available_skus,
        "unavailable_skus": unavailable_skus,
        "pickup_skus": pickup_skus,
        "pickup_coverage": pickup_coverage,
        "brand_counts": brand_counts,
        "pickup_df": pickup_df,
        "discount_df": discount_df,
        "new_table": new_table,
        "new_date": add_date,
        "insights": insights,
        "quality_note": " ".join(quality_notes) if quality_notes else "No major data quality issues detected.",
    }


def render_shelf_snapshot(df, date_cols, latest_tracking_date):
    st.title("Shelf Snapshot")
    channels = sorted(df["Channel Group"].dropna().astype(str).unique())
    selected_channel = st.selectbox("Channel", channels)
    channel_df = df[df["Channel Group"] == selected_channel].copy()
    snapshot = build_snapshot(channel_df, date_cols, latest_tracking_date)

    st.subheader("Insight Summary")
    insight_cols = st.columns(3)
    for col, insight in zip(insight_cols, snapshot["insights"]):
        col.info(insight)

    kpi_cols = st.columns(6)
    kpi_cols[0].metric("Total SKUs", f"{snapshot['total_skus']:,}")
    kpi_cols[1].metric("Available SKUs", f"{snapshot['available_skus']:,}")
    kpi_cols[2].metric("Pickup SKUs", f"{snapshot['pickup_skus']:,}")
    kpi_cols[3].metric("Pickup Coverage", f"{snapshot['pickup_coverage']:.1%}")
    kpi_cols[4].metric("Unavailable SKUs", f"{snapshot['unavailable_skus']:,}")
    kpi_cols[5].metric("Latest Tracking Date", latest_tracking_date.isoformat())

    st.subheader("Brand Shelf Presence")
    brand_chart_df = snapshot["brand_counts"]
    if brand_chart_df.empty:
        st.warning("No available SKUs for this channel.")
    else:
        chart = (
            alt.Chart(brand_chart_df)
            .mark_bar(color="#2563EB")
            .encode(
                x=alt.X("Available SKUs:Q", title="Available SKUs"),
                y=alt.Y("Brand:N", sort="-x", title="Brand"),
                tooltip=["Brand:N", "Available SKUs:Q"],
            )
            .properties(height=max(300, len(brand_chart_df) * 34))
        )
        st.altair_chart(chart, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Pickup Coverage")
        pickup_df = snapshot["pickup_df"]
        if pickup_df.empty:
            st.caption("No pickup data available.")
        else:
            pickup_chart = (
                alt.Chart(pickup_df)
                .mark_bar()
                .encode(
                    x=alt.X("sum(SKUs):Q", title="SKUs"),
                    y=alt.Y("Major Brand:N", sort="-x", title="Brand"),
                    color=alt.Color("Pickup Group:N", scale=alt.Scale(range=["#0F766E", "#F59E0B", "#667085"])),
                    tooltip=["Major Brand:N", "Pickup Group:N", "SKUs:Q"],
                )
                .properties(height=330)
            )
            st.altair_chart(pickup_chart, use_container_width=True)

    with col2:
        st.subheader("Price Drop Signal")
        discount_df = snapshot["discount_df"]
        if discount_df.empty or not (discount_df["Discounted SKUs"] > 0).any():
            st.caption("No discounted SKUs detected.")
        else:
            discount_chart = (
                alt.Chart(discount_df)
                .mark_bar(color="#DC2626")
                .encode(
                    x=alt.X("Discounted SKUs:Q", title="Discounted SKUs"),
                    y=alt.Y("Brand:N", sort="-x", title="Brand"),
                    tooltip=[
                        "Brand:N",
                        "Available SKUs:Q",
                        "Discounted SKUs:Q",
                        alt.Tooltip("Discount Rate:Q", format=".0%"),
                    ],
                )
                .properties(height=330)
            )
            st.altair_chart(discount_chart, use_container_width=True)

    st.subheader("New Entrants")
    new_date = snapshot["new_date"]
    if snapshot["new_table"].empty:
        st.caption("No new brands or products detected.")
    else:
        st.caption(f"Most recent add activity: {new_date.isoformat() if new_date else 'N/A'}")
        st.dataframe(snapshot["new_table"], use_container_width=True, hide_index=True)

    st.caption(f"Data quality note: {snapshot['quality_note']}")


def main():
    sheet_url = ""
    try:
        sheet_url = st.secrets.get("GOOGLE_SHEET_CSV_URL", "")
    except Exception:
        sheet_url = os.getenv("GOOGLE_SHEET_CSV_URL", "")

    page = st.sidebar.radio("Page", ["Product Value Matrix", "Shelf Snapshot"])
    uploaded = st.sidebar.file_uploader("Data File", type=["csv", "xlsx"])
    df, date_cols, latest_tracking_date = load_data(uploaded, sheet_url)

    if page == "Product Value Matrix":
        render_value_matrix(df, date_cols)
    else:
        render_shelf_snapshot(df, date_cols, latest_tracking_date)


if __name__ == "__main__":
    main()
