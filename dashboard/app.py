"""
Retail Inventory and Sales Intelligence System - Dashboard
Reads the views created in Neon PostgreSQL (schema: retail) and shows them
as cards, tables and charts.

Run:  streamlit run app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

st.set_page_config(
    page_title="Retail Inventory & Sales Intelligence",
    page_icon="📦",
    layout="wide",
)

# ----------------------------------------------------------------------
# Database connection
# ----------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL not found. Create a .env file and paste your Neon connection string.")
    st.stop()


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


@st.cache_data(ttl=60)
def load(view_name: str) -> pd.DataFrame:
    """Read one view from the retail schema."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM retail.{view_name}"), conn)


try:
    reorder = load("v_reorder_list")
    stock = load("v_stock_status")
    valuation = load("v_inventory_valuation")
    daily = load("v_daily_sales")
    monthly = load("v_monthly_revenue")
    performance = load("v_product_performance")
except Exception as e:
    st.error("Could not connect to the database. Check your DATABASE_URL in the .env file.")
    st.exception(e)
    st.stop()

# ----------------------------------------------------------------------
# Sidebar filter
# ----------------------------------------------------------------------
st.sidebar.title("Filters")
stores = sorted(stock["store_name"].unique())
selected = st.sidebar.selectbox("Store", ["All stores"] + stores)

if st.sidebar.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()


def by_store(df: pd.DataFrame) -> pd.DataFrame:
    return df if selected == "All stores" else df[df["store_name"] == selected]


reorder_f = by_store(reorder)
stock_f = by_store(stock)
valuation_f = by_store(valuation)
daily_f = by_store(daily)

# ----------------------------------------------------------------------
# Header + KPI cards
# ----------------------------------------------------------------------
st.title("📦 Retail Inventory & Sales Intelligence")
st.caption(f"Showing: {selected}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Sales", f"Rs {daily_f['total_revenue'].sum():,.0f}")
c2.metric("Invoices", f"{int(daily_f['total_invoices'].sum())}")
c3.metric("Stock Value (cost)", f"Rs {valuation_f['stock_value_at_cost'].sum():,.0f}")
c4.metric("Items to Reorder", f"{len(reorder_f)}")
c5.metric("Out of Stock", f"{int((reorder_f['priority'] == 'OUT OF STOCK').sum())}")

st.divider()

# ----------------------------------------------------------------------
# Reorder list (most important section)
# ----------------------------------------------------------------------
st.subheader("🔔 Products to Reorder")

if reorder_f.empty:
    st.success("All products are above their reorder level.")
else:
    icons = {"OUT OF STOCK": "🔴 OUT OF STOCK", "CRITICAL": "🟠 CRITICAL", "REORDER": "🟡 REORDER"}
    show = reorder_f.copy()
    show["priority"] = show["priority"].map(icons)
    show = show.rename(
        columns={
            "store_name": "Store",
            "sku": "SKU",
            "product_name": "Product",
            "supplier_name": "Supplier",
            "lead_time_days": "Lead Time (days)",
            "quantity_on_hand": "In Stock",
            "reorder_level": "Reorder Level",
            "qty_already_on_order": "Already Ordered",
            "suggested_order_qty": "Suggested Qty",
            "estimated_cost": "Est. Cost (Rs)",
            "priority": "Priority",
        }
    )
    st.dataframe(show, hide_index=True)
    st.download_button(
        "Download reorder list (CSV)",
        reorder_f.to_csv(index=False).encode("utf-8"),
        file_name="reorder_list.csv",
        mime="text/csv",
    )

st.divider()

# ----------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Stock Status")
    status_count = stock_f["stock_status"].value_counts().reset_index()
    status_count.columns = ["Status", "Count"]
    fig = px.pie(
        status_count,
        names="Status",
        values="Count",
        hole=0.45,
        color="Status",
        color_discrete_map={
            "OK": "#2e9e5b",
            "REORDER": "#f2c14e",
            "CRITICAL": "#f28c28",
            "OUT OF STOCK": "#d64545",
        },
    )
    st.plotly_chart(fig)

with right:
    st.subheader("Daily Sales")
    day = daily_f.groupby("sale_day", as_index=False)["total_revenue"].sum()
    fig = px.line(day, x="sale_day", y="total_revenue", markers=True,
                  labels={"sale_day": "Date", "total_revenue": "Revenue (Rs)"})
    st.plotly_chart(fig)

left, right = st.columns(2)

with left:
    st.subheader("Top Selling Products (all stores)")
    top = performance.sort_values("revenue", ascending=False).head(10)
    fig = px.bar(top, x="revenue", y="product_name", orientation="h",
                 labels={"revenue": "Revenue (Rs)", "product_name": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig)

with right:
    st.subheader("Stock Value per Store")
    val = valuation_f.melt(
        id_vars="store_name",
        value_vars=["stock_value_at_cost", "stock_value_at_retail"],
        var_name="Type", value_name="Value",
    )
    val["Type"] = val["Type"].map(
        {"stock_value_at_cost": "At cost", "stock_value_at_retail": "At retail price"}
    )
    fig = px.bar(val, x="store_name", y="Value", color="Type", barmode="group",
                 labels={"store_name": "Store", "Value": "Value (Rs)"})
    st.plotly_chart(fig)

st.subheader("Product Performance (units sold, revenue, profit)")
st.dataframe(performance, hide_index=True)

with st.expander("Full stock status (all products)"):
    st.dataframe(stock_f, hide_index=True)

with st.expander("Monthly revenue"):
    st.dataframe(monthly, hide_index=True)
