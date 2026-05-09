"""
Sales Analytics Dashboard — Streamlit App
Q6 of the Data Analyst Python Assessment.
"""

from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------- Page Setup ----------------
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        [data-testid="stMetricValue"] { font-size: 26px; }
        [data-testid="stMetricLabel"] { font-size: 14px; }
        .block-container { padding-top: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Constants ----------------
REQUIRED_COLUMNS = {
    "Date", "Product", "Region", "Units_Sold",
    "Revenue", "Salesperson", "Channel",
}


# ---------------- Helpers ----------------
@st.cache_data(show_spinner=False)
def load_and_clean(file_bytes: bytes) -> pd.DataFrame:
    """Read every sheet from the uploaded Excel, combine, and clean."""
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None)
    df = pd.concat(sheets.values(), ignore_index=True)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    df = df[df["Revenue"].notna() & (df["Revenue"] != 0)].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).reset_index(drop=True)
    return df


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes for download."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="CleanedData")
    return buffer.getvalue()


# ---------------- Sidebar: Upload ----------------
with st.sidebar:
    st.title("📊 Sales Dashboard")
    st.caption("Interactive analytics on multi-year sales data")
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Upload Sales Excel File",
        type=["xlsx", "xls"],
        help="Excel file with one sheet per year",
    )

# ---------------- Landing State (no upload yet) ----------------
if uploaded_file is None:
    st.title("📊 Sales Analytics Dashboard")
    st.info("👈 Upload your sales Excel file from the sidebar to begin.")
    st.markdown(
        """
        ### What this dashboard does
        - **Cleans & combines** yearly sales sheets into one dataset
        - **Filters** by Year, Region, Product, Salesperson, and Channel
        - **Visualizes** revenue across products, channels, salespeople, and time
        - **Exports** the cleaned dataset as CSV or Excel

        ### Required columns in your file
        `Date`, `Product`, `Region`, `Units_Sold`, `Revenue`, `Salesperson`, `Channel`
        """
    )
    st.stop()

# ---------------- Load & Validate ----------------
try:
    # Double-check uploaded_file is not None for the linter (though st.stop() handles it)
    if uploaded_file is not None:
        df = load_and_clean(uploaded_file.getvalue())
    else:
        st.stop()
except ValueError as e:
    st.error(f"❌ Invalid file format: {e}")
    st.stop()
except Exception as e:
    st.error(f"❌ Could not read the uploaded file: {e}")
    st.stop()

if df.empty:
    st.warning("The uploaded file contains no usable rows after cleaning.")
    st.stop()

# ---------------- Sidebar: Filters ----------------
with st.sidebar:
    st.markdown("### 🔍 Filters")

    years = sorted(df["Date"].dt.year.unique())
    selected_years = st.multiselect("Year", years, default=years)

    regions = sorted(df["Region"].unique())
    selected_regions = st.multiselect("Region", regions, default=regions)

    products = sorted(df["Product"].unique())
    selected_products = st.multiselect("Product", products, default=products)

    salespeople = sorted(df["Salesperson"].unique())
    selected_salespeople = st.multiselect("Salesperson", salespeople, default=salespeople)

    channels = sorted(df["Channel"].unique())
    selected_channels = st.multiselect("Channel", channels, default=channels)

    st.markdown("---")
    st.caption(f"Total records loaded: **{len(df):,}**")

# ---------------- Apply Filters ----------------
filtered = df[
    df["Date"].dt.year.isin(selected_years)
    & df["Region"].isin(selected_regions)
    & df["Product"].isin(selected_products)
    & df["Salesperson"].isin(selected_salespeople)
    & df["Channel"].isin(selected_channels)
]

if filtered.empty:
    st.warning("⚠️ No data matches the selected filters. Try widening them.")
    st.stop()

# ---------------- Header & KPIs ----------------
st.title("📊 Sales Analytics Dashboard")
st.caption(
    f"Showing **{len(filtered):,}** records | "
    f"{filtered['Date'].min():%b %d, %Y} → {filtered['Date'].max():%b %d, %Y}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Total Revenue", f"₹{filtered['Revenue'].sum():,.0f}")
c2.metric("📦 Total Units Sold", f"{int(filtered['Units_Sold'].sum()):,}")
c3.metric("📈 Avg Revenue / Order", f"₹{filtered['Revenue'].mean():,.2f}")
c4.metric("🧾 Transactions", f"{len(filtered):,}")

st.markdown("---")

# ---------------- Tabs ----------------
tab_viz, tab_top, tab_data = st.tabs(
    ["📈 Visualizations", "🏆 Top Products", "📥 Data & Download"]
)

# ---- Tab 1: Visualizations ----
with tab_viz:
    col1, col2 = st.columns(2)

    with col1:
        prod_rev = (
            filtered.groupby("Product")["Revenue"]
            .sum().round(2).reset_index()
            .sort_values("Revenue", ascending=True)
        )
        fig = px.bar(
            prod_rev, x="Revenue", y="Product", orientation="h",
            title="Revenue by Product", text_auto=".2s",
            color="Revenue", color_continuous_scale="Viridis",
        )
        fig.update_layout(coloraxis_showscale=False, height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        ch_rev = filtered.groupby("Channel")["Revenue"].sum().reset_index()
        fig = px.pie(
            ch_rev, names="Channel", values="Revenue",
            title="Revenue by Channel", hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    monthly = (
        filtered.assign(Month=filtered["Date"].dt.to_period("M").astype(str))
        .groupby("Month")["Revenue"].sum().reset_index()
    )
    fig = px.line(
        monthly, x="Month", y="Revenue",
        title="Monthly Revenue Trend", markers=True,
    )
    fig.update_traces(line={"color": "#1f77b4", "width": 2.5})
    fig.update_layout(height=360)
    st.plotly_chart(fig, use_container_width=True)

    sp_rev = filtered.groupby("Salesperson")["Revenue"].sum().reset_index()
    fig = px.treemap(
        sp_rev, path=["Salesperson"], values="Revenue",
        title="Revenue by Salesperson",
        color="Revenue", color_continuous_scale="Blues",
    )
    fig.update_traces(textinfo="label+value+percent root")
    fig.update_layout(height=420, margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 2: Top Products ----
with tab_top:
    st.subheader("🏆 Top 5 Products by Revenue")
    top5 = (
        filtered.groupby("Product")["Revenue"]
        .sum().nlargest(5).round(2).reset_index()
    )
    top5.insert(0, "Rank", range(1, len(top5) + 1))

    st.dataframe(
        top5.style
            .format({"Revenue": "₹{:,.2f}"})
            .background_gradient(subset=["Revenue"], cmap="Greens")
            .hide(axis="index"),
        use_container_width=True,
        height=240,
    )

    st.caption(
        f"Note: dataset contains {filtered['Product'].nunique()} unique products."
    )

# ---- Tab 3: Data & Download ----
with tab_data:
    st.subheader("Cleaned Dataset Preview")
    st.dataframe(filtered.head(200), use_container_width=True, height=400)
    st.caption(f"Showing first 200 of {len(filtered):,} filtered rows.")

    st.markdown("---")
    st.subheader("⬇️ Download Cleaned Data")
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Download as CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="cleaned_sales_data.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "Download as Excel",
            data=to_excel_bytes(filtered),
            file_name="cleaned_sales_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

st.markdown("---")
st.caption("Built with Streamlit + Plotly | Sales Analytics Dashboard")
