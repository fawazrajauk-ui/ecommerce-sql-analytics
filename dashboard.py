import streamlit as st
from pathlib import Path
import subprocess
import sys

if not Path("ecommerce.duckdb").exists():
    with st.spinner("Preparing retail analytics database..."):
        subprocess.run(
            [sys.executable, "setup_database.py"],
            check=True
        )

import duckdb
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="E-Commerce Analytics",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def load_data():
    con = duckdb.connect("ecommerce.duckdb", read_only=True)
    df = con.execute("""
        SELECT
            invoice_no,
            invoice_date,
            customer_id,
            country,
            quantity,
            revenue
        FROM clean_sales
    """).df()
    con.close()
    return df

df = load_data()

st.title("E-Commerce Analytics Dashboard")
st.caption(
    "Online Retail Dataset | December 2010 – December 2011"
)

st.sidebar.header("Filters")

min_date = df["invoice_date"].min().date()
max_date = df["invoice_date"].max().date()

date_range = st.sidebar.date_input(
    "Transaction date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) != 2:
    st.info("Select both a start and end date.")
    st.stop()

start_date, end_date = date_range

filtered = df[
    (df["invoice_date"].dt.date >= start_date)
    & (df["invoice_date"].dt.date <= end_date)
].copy()

revenue = filtered["revenue"].sum()
orders = filtered["invoice_no"].nunique()
customers = filtered["customer_id"].nunique()
avg_order = revenue / orders if orders else 0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Gross Sales", f"£{revenue:,.0f}")
col2.metric("Orders", f"{orders:,}")
col3.metric("Identified Customers", f"{customers:,}")
col4.metric("Average Order Value", f"£{avg_order:,.2f}")

overview_tab, product_tab, customer_tab, retention_tab = st.tabs(["Sales Overview", "Product Analytics", "Customer Segmentation", "Customer Retention"])

with overview_tab:
    st.divider()
    st.subheader("Monthly Revenue")

    monthly = (
        filtered.assign(
            month=filtered["invoice_date"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby("month", as_index=False)["revenue"]
        .sum()
    )

    fig = px.line(
        monthly,
        x="month",
        y="revenue",
        markers=True,
        labels={
            "month": "Month",
            "revenue": "Gross Sales (£)"
        },
        template="plotly_white"
    )

    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=9),
        hovertemplate="%{x|%b %Y}<br>£%{y:,.0f}<extra></extra>"
    )

    fig.update_layout(
        yaxis_tickprefix="£",
        yaxis_tickformat=",.0f",
        margin=dict(l=20, r=20, t=20, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Gross positive-line sales exclude cancellations, returns "
    "and non-positive prices. December 2011 is incomplete."
)


with product_tab:
    st.subheader("Top Merchandise Products")

    con = duckdb.connect("ecommerce.duckdb", read_only=True)
    products = con.execute("""
        SELECT
            invoice_date,
            stock_code,
            description,
            invoice_no,
            quantity,
            revenue
        FROM merchandise_sales
    """).df()
    con.close()

    products = products[
        (products["invoice_date"].dt.date >= start_date)
        & (products["invoice_date"].dt.date <= end_date)
    ]

    ranking = (
        products.groupby("stock_code", as_index=False)
        .agg(
            product=("description", "first"),
            revenue=("revenue", "sum"),
            units=("quantity", "sum"),
            orders=("invoice_no", "nunique")
        )
    )

    metric = st.selectbox(
        "Rank products by",
        ["Revenue", "Units Sold", "Orders"]
    )

    metric_col = {
        "Revenue": "revenue",
        "Units Sold": "units",
        "Orders": "orders"
    }[metric]

    top = ranking.nlargest(10, metric_col).sort_values(metric_col)

    fig_products = px.bar(
        top,
        x=metric_col,
        y="product",
        orientation="h",
        color=metric_col,
        color_continuous_scale="Blues",
        title=f"Top 10 Products by {metric}",
        template="plotly_white",
        labels={
            "product": "",
            metric_col: metric
        }
    )

    fig_products.update_layout(
        height=600,
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    st.plotly_chart(fig_products, use_container_width=True)

    st.dataframe(
        ranking.sort_values(metric_col, ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Merchandise rankings exclude selected administrative "
        "stock codes. Classification is approximate."
    )


with customer_tab:
    st.subheader("RFM Customer Segmentation")

    st.info(
        "Customer segments are calculated using the full historical "
        "dataset, rather than the selected date range."
    )

    con = duckdb.connect("ecommerce.duckdb", read_only=True)

    segments = con.execute("""
        SELECT
            segment,
            COUNT(*) AS customers,
            ROUND(SUM(monetary_gbp), 2) AS total_spending,
            ROUND(AVG(monetary_gbp), 2) AS avg_spending,
            ROUND(AVG(frequency), 2) AS avg_orders
        FROM customer_rfm_scored
        GROUP BY segment
        ORDER BY total_spending DESC
    """).df()

    con.close()

    metric = st.selectbox(
        "Compare customer segments by",
        ["Total Spending", "Customer Count", "Average Spending"]
    )

    metric_col = {
        "Total Spending": "total_spending",
        "Customer Count": "customers",
        "Average Spending": "avg_spending"
    }[metric]

    chart_data = segments.sort_values(metric_col)

    fig_segments = px.bar(
        chart_data,
        x=metric_col,
        y="segment",
        orientation="h",
        color="segment",
        title=f"Customer Segments by {metric}",
        labels={
            "segment": "",
            metric_col: metric
        },
        template="plotly_white"
    )

    fig_segments.update_layout(
        height=480,
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    st.plotly_chart(fig_segments, use_container_width=True)

    st.subheader("Segment Breakdown")

    segments["customer_share_pct"] = (
        segments["customers"]
        / segments["customers"].sum() * 100
    ).round(1)

    segments["spending_share_pct"] = (
        segments["total_spending"]
        / segments["total_spending"].sum() * 100
    ).round(1)

    st.dataframe(
        segments,
        use_container_width=True,
        hide_index=True
    )

    champions = segments[
        segments["segment"] == "Champions"
    ].iloc[0]

    st.success(
        f"Champions represent "
        f"{champions['customer_share_pct']:.1f}% of customers "
        f"but account for "
        f"{champions['spending_share_pct']:.1f}% "
        f"of identified historical spending."
    )


with retention_tab:
    st.subheader("Customer Cohort Retention")

    st.markdown(
        "Each row represents customers grouped by their **first "
        "observed purchase month**. Each column shows the percentage "
        "who purchased again in that relative month."
    )

    months = st.slider(
        "Months to display",
        min_value=3,
        max_value=12,
        value=6
    )

    con = duckdb.connect("ecommerce.duckdb", read_only=True)

    retention = con.execute("""
        SELECT
            STRFTIME(cohort_month, '%Y-%m') AS cohort,
            months_since_first,
            retention_pct,
            cohort_size
        FROM cohort_retention
        ORDER BY cohort_month, months_since_first
    """).df()

    con.close()

    matrix = retention.pivot(
        index="cohort",
        columns="months_since_first",
        values="retention_pct"
    )

    matrix = matrix.reindex(columns=range(months + 1))

    last_complete_month = pd.Period("2011-11", freq="M")

    for cohort in matrix.index:
        cohort_period = pd.Period(cohort, freq="M")
        max_age = (
            last_complete_month.ordinal
            - cohort_period.ordinal
        )

        for age in matrix.columns:
            if age > max_age:
                matrix.loc[cohort, age] = float("nan")

    import plotly.graph_objects as go

    heatmap = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=[f"Month {i}" for i in matrix.columns],
            y=matrix.index.tolist(),
            colorscale="Teal",
            zmin=0,
            zmax=100,
            text=matrix.round(1).values,
            texttemplate="%{text:.1f}%",
            textfont=dict(size=11),
            hovertemplate=(
                "Cohort: %{y}<br>"
                "Period: %{x}<br>"
                "Retention: %{z:.2f}%"
                "<extra></extra>"
            ),
            colorbar=dict(title="Retention %")
        )
    )

    heatmap.update_layout(
        height=650,
        template="plotly_white",
        xaxis_title="Months Since First Observed Purchase",
        yaxis_title="Customer Cohort",
        yaxis_autorange="reversed",
        margin=dict(l=30, r=30, t=30, b=30)
    )

    st.plotly_chart(heatmap, use_container_width=True)

    st.caption(
        "Month 0 is 100% by definition. Blank cells indicate "
        "incomplete observation windows. December 2011 is excluded "
        "from follow-up because only nine days are available."
    )

    st.subheader("Retention Data")

    st.dataframe(
        matrix.round(2),
        use_container_width=True
    )
