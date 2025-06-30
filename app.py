# app.py – Robust, one‑file Streamlit dashboard
# ---------------------------------------------
# • Auto‑cleans column names (trims, lowercase, removes spaces/punctuation)
# • Works even if the sheet uses “Unit Purchased”, “unit_purchased”, etc.
# • Uses only safe names from that point onward.

import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# ---------- PAGE CONFIG ----------
st.set_page_config("Comprehensive Sales Analytics", layout="wide")

st.title("📊 Sales Analytics Dashboard")
st.write(
    "Explore every possible factor that affects **Total Sale Value**. "
    "Use the filters in the sidebar to slice and dice the data instantly."
)

# ---------- DATA LOADER ----------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)

    # --- Standardise column names: lower‑case, strip, remove spaces & non‑alphanumerics
    clean_cols = (
        df.columns.str.strip()                                 # trim
                 .str.lower()                                  # lower‑case
                 .str.replace(r"[\\s\\-]+", "", regex=True)    # remove spaces/dashes
                 .str.replace(r"[^0-9a-z_]", "", regex=True)   # drop any other symbols
    )
    df.columns = clean_cols

    # Make sure numeric columns are numeric
    for col in ["age", "unitpurchased", "feedbackscore", "totalsalevalue"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=["totalsalevalue"])  # keep only rows with valid target

df = load_data("IA_PBL_DA_GJ25NS045_AnishAggarwal.xlsx")

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Filter Panel")

def multiselect_with_all(label, series):
    options = series.dropna().unique().tolist()
    default = st.sidebar.multiselect(label, options, options)
    return default or options  # if user clears all, treat as "select all"

locations     = multiselect_with_all("Location",      df["location"])
products      = multiselect_with_all("Product Variant", df["productvariant"])
channels      = multiselect_with_all("Channel",       df["channel"])
genders       = multiselect_with_all("Gender",        df["gender"])
payment_types = multiselect_with_all("Payment Type",  df["paymenttype"])

age_min, age_max = int(df["age"].min()), int(df["age"].max())
age_range = st.sidebar.slider("Age Range", age_min, age_max, (age_min, age_max))

unit_min, unit_max = int(df["unitpurchased"].min()), int(df["unitpurchased"].max())
unit_range = st.sidebar.slider("Unit Purchased Range", unit_min, unit_max, (unit_min, unit_max))

fb_min, fb_max = int(df["feedbackscore"].min()), int(df["feedbackscore"].max())
fb_range = st.sidebar.slider("Feedback Score Range", fb_min, fb_max, (fb_min, fb_max))

# ---------- APPLY FILTERS ----------
mask = (
    df["location"].isin(locations)
    & df["productvariant"].isin(products)
    & df["channel"].isin(channels)
    & df["gender"].isin(genders)
    & df["paymenttype"].isin(payment_types)
    & df["age"].between(*age_range)
    & df["unitpurchased"].between(*unit_range)
    & df["feedbackscore"].between(*fb_range)
)

df_filt = df.loc[mask].copy()

# ---------- TAB LAYOUT ----------
tabs = st.tabs(
    [
        "Overall KPIs",
        "Demographics",
        "Products & Channels",
        "Feedback Impact",
        "Payment Analysis",
        "Correlations / Deep‑dive",
    ]
)

# ---------- TAB 1 : KPIs ----------
with tabs[0]:
    st.subheader("🚀 High‑level KPIs")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Sale Value", f"${df_filt.totalsalevalue.sum():,.2f}")
    k2.metric("Average per Order", f"${df_filt.totalsalevalue.mean():,.2f}")
    k3.metric("Transactions", f"{len(df_filt):,}")
    k4.metric("Avg Feedback", f"{df_filt.feedbackscore.mean():.2f}")

    st.markdown("### Sale Value Distribution")
    st.plotly_chart(
        px.histogram(df_filt, x="totalsalevalue", nbins=30, title="Histogram of Sale Values"),
        use_container_width=True,
    )

# ---------- TAB 2 : DEMOGRAPHICS ----------
with tabs[1]:
    st.subheader("🧑‍🤝‍🧑 Demographic Drivers")

    age_bins = pd.cut(
        df_filt["age"], bins=[0, 20, 30, 40, 50, 60, 100],
        labels=["≤20", "21‑30", "31‑40", "41‑50", "51‑60", "60+"]
    )
    df_filt["agegroup"] = age_bins

    st.plotly_chart(
        px.bar(
            df_filt.groupby("agegroup", observed=True)["totalsalevalue"].sum().reset_index(),
            x="agegroup", y="totalsalevalue", text_auto=".2s",
            title="Total Sales by Age Group"
        ),
        use_container_width=True,
    )

    st.plotly_chart(
        px.bar(
            df_filt.groupby("gender")["totalsalevalue"].sum().reset_index(),
            x="gender", y="totalsalevalue", text_auto=".2s", color="gender",
            title="Sales by Gender"
        ),
        use_container_width=True,
    )

# ---------- TAB 3 : PRODUCT & CHANNEL ----------
with tabs[2]:
    st.subheader("📦 Products & 📡 Channels")

    st.plotly_chart(
        px.bar(
            df_filt.groupby("productvariant")["totalsalevalue"].sum().reset_index(),
            x="productvariant", y="totalsalevalue", text_auto=".2s", color="productvariant",
            title="Sales by Product Variant"
        ),
        use_container_width=True,
    )

    st.plotly_chart(
        px.pie(
            df_filt, names="channel", values="totalsalevalue",
            title="Channel Contribution to Sales", hole=0.4
        ),
        use_container_width=True,
    )

    heat = pd.pivot_table(
        df_filt, values="totalsalevalue",
        index="productvariant", columns="channel", aggfunc="sum", fill_value=0
    )
    st.plotly_chart(
        px.imshow(heat, text_auto=True, aspect="auto", title="Product‑Channel Heatmap"),
        use_container_width=True,
    )

# ---------- TAB 4 : FEEDBACK ----------
with tabs[3]:
    st.subheader("⭐ Feedback vs Sales")

    st.plotly_chart(
        px.scatter(
            df_filt, x="feedbackscore", y="totalsalevalue", size="unitpurchased",
            color="productvariant", hover_data=["channel", "location"],
            title="Feedback Score vs Sale Value"
        ),
        use_container_width=True,
    )

    st.plotly_chart(
        px.box(
            df_filt, x="feedbackscore", y="totalsalevalue", points="all",
            title="Sale Value Distribution across Feedback Scores"
        ),
        use_container_width=True,
    )

# ---------- TAB 5 : PAYMENT ----------
with tabs[4]:
    st.subheader("💳 Payment Insights")

    st.plotly_chart(
        px.bar(
            df_filt.groupby("paymenttype")["totalsalevalue"].sum().reset_index(),
            x="paymenttype", y="totalsalevalue", color="paymenttype", text_auto=".2s",
            title="Sales by Payment Type"
        ),
        use_container_width=True,
    )

# ---------- TAB 6 : CORRELATIONS ----------
with tabs[5]:
    st.subheader("🔬 Advanced Correlation Analysis")

    numeric_cols = ["age", "unitpurchased", "feedbackscore", "totalsalevalue"]
    corr = df_filt[numeric_cols].corr()

    st.plotly_chart(
        px.imshow(corr, text_auto=True, aspect="auto", title="Correlation Matrix"),
        use_container_width=True,
    )

    st.markdown("### Custom Scatter")
    x_axis = st.selectbox("X‑axis", numeric_cols, index=0)
    y_axis = st.selectbox("Y‑axis", numeric_cols, index=3)
    colour = st.selectbox("Colour by", ["productvariant", "channel", "gender", "location"])
    st.plotly_chart(
        px.scatter(
            df_filt, x=x_axis, y=y_axis, color=colour, size="unitpurchased",
            hover_data=["paymenttype"], title=f"{y_axis} vs {x_axis} coloured by {colour}"
        ),
        use_container_width=True,
    )

st.success("Dashboard loaded successfully! Use the sidebar to explore.")
