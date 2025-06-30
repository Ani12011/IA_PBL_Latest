# app.py – ultra‑robust Streamlit dashboard
# ----------------------------------------
# Handles messy column names, prevents KeyErrors, and
# shows clear messages if the workbook structure is wrong.

import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# ───────────────────────────────────────────── PAGE CONFIG
st.set_page_config("Sales Analytics Dashboard", layout="wide")
st.title("📊 Comprehensive Sales Analytics Dashboard")

# ───────────────────────────────────────────── HELPERS
def slugify(col: str) -> str:
    """lower, strip, remove non‑alnum characters → 'totalsalevalue' etc."""
    col = re.sub(r"[\\s\\-]+", "", col.strip().lower())
    return re.sub(r"[^0-9a-z_]", "", col)

def find_col(df: pd.DataFrame, synonyms: list[str]) -> str | None:
    """Return first column whose *slugified* name contains any synonym token(s)."""
    for raw in df.columns:
        slug = slugify(raw)
        for syn in synonyms:
            if syn in slug:
                return raw
    return None

def load_and_clean(path: str) -> pd.DataFrame:
    # read file
    df = pd.read_excel(path)

    # map raw → canonical names
    mapping = {}

    expect = {
        "age":           ["age"],
        "gender":        ["gender", "sex"],
        "location":      ["location", "city", "region", "state"],
        "productvariant":["productvariant", "variant", "sku", "product"],
        "unitpurchased": ["unitpurchased", "units", "quantity", "qty"],
        "feedbackscore": ["feedbackscore", "feedback", "rating", "satisfaction"],
        "channel":       ["channel", "saleschannel", "purchasechannel"],
        "paymenttype":   ["paymenttype", "paymentmethod", "payment", "paytype"],
        "totalsalevalue":["totalsalevalue", "totalsales", "salesvalue", "totalsale"],
    }

    for canon, syns in expect.items():
        raw = find_col(df, syns)
        if raw:
            mapping[raw] = canon

    df = df.rename(columns=mapping)

    # verify mandatory columns
    missing = [c for c in expect if c not in df.columns]
    if missing:
        st.error(
            "❌ The following required column(s) were not found in the Excel file "
            f"after normalisation: **{', '.join(missing)}**.\\n"
            "Please check the header names and try again."
        )
        st.stop()

    # ensure numeric columns truly numeric
    for col in ["age", "unitpurchased", "feedbackscore", "totalsalevalue"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # drop rows with no target value
    df = df.dropna(subset=["totalsalevalue"])

    return df

# ───────────────────────────────────────────── LOAD DATA
DATA_PATH = "IA_PBL_DA_GJ25NS045_AnishAggarwal.xlsx"
df = load_and_clean(DATA_PATH)

# ───────────────────────────────────────────── SIDEBAR FILTERS
st.sidebar.header("🔎 Filter Panel")

def ms(label, col_name):
    opts = df[col_name].dropna().unique().tolist()
    sel  = st.sidebar.multiselect(label, opts, default=opts)
    return sel or opts  # treat empty as "select all"

locs   = ms("Location",      "location")
prods  = ms("Product Variant","productvariant")
chns   = ms("Channel",       "channel")
gends  = ms("Gender",        "gender")
pays   = ms("Payment Type",  "paymenttype")

age_rng  = st.sidebar.slider("Age Range", int(df.age.min()), int(df.age.max()),
                             (int(df.age.min()), int(df.age.max())))
unit_rng = st.sidebar.slider("Units Purchased Range",
                             int(df.unitpurchased.min()), int(df.unitpurchased.max()),
                             (int(df.unitpurchased.min()), int(df.unitpurchased.max())))
fb_rng   = st.sidebar.slider("Feedback Score Range",
                             int(df.feedbackscore.min()), int(df.feedbackscore.max()),
                             (int(df.feedbackscore.min()), int(df.feedbackscore.max())))

mask = (
    df.location.isin(locs)        &
    df.productvariant.isin(prods) &
    df.channel.isin(chns)         &
    df.gender.isin(gends)         &
    df.paymenttype.isin(pays)     &
    df.age.between(*age_rng)      &
    df.unitpurchased.between(*unit_rng) &
    df.feedbackscore.between(*fb_rng)
)
df_filt = df.loc[mask].copy()

# ───────────────────────────────────────────── TAB SET‑UP
tabs = st.tabs([
    "KPIs", "Demographics", "Products & Channels",
    "Feedback Impact", "Payment Insights", "Correlations"
])

# ───────────────────────────────────────────── TAB 1 : KPIs
with tabs[0]:
    st.subheader("📌 Top‑line KPIs (filtered)")
    a, b, c, d = st.columns(4)
    a.metric("Total Sale Value",  f"${df_filt.totalsalevalue.sum():,.2f}")
    b.metric("Avg per Order",     f"${df_filt.totalsalevalue.mean():,.2f}")
    c.metric("Transactions",      f"{len(df_filt):,}")
    d.metric("Avg Feedback",      f"{df_filt.feedbackscore.mean():.2f}")

    st.plotly_chart(
        px.histogram(df_filt, x="totalsalevalue", nbins=30,
                     title="Distribution of Total Sale Values"),
        use_container_width=True
    )

# ───────────────────────────────────────────── TAB 2 : DEMOGRAPHICS
with tabs[1]:
    st.subheader("👥 Demographic Drivers")
    age_bins = pd.cut(
        df_filt.age,
        bins=[0,20,30,40,50,60,100],
        labels=["≤20", "21‑30", "31‑40", "41‑50", "51‑60", "60+"]
    )
    df_filt["agegroup"] = age_bins

    st.plotly_chart(
        px.bar(
            df_filt.groupby("agegroup", observed=True).totalsalevalue.sum().reset_index(),
            x="agegroup", y="totalsalevalue", text_auto=".2s",
            title="Total Sales by Age Group"
        ),
        use_container_width=True
    )
    st.plotly_chart(
        px.bar(
            df_filt.groupby("gender").totalsalevalue.sum().reset_index(),
            x="gender", y="totalsalevalue", text_auto=".2s", color="gender",
            title="Sales by Gender"
        ),
        use_container_width=True
    )

# ───────────────────────────────────────────── TAB 3 : PRODUCTS & CHANNELS
with tabs[2]:
    st.subheader("📦 Products & 📡 Channels")

    st.plotly_chart(
        px.bar(
            df_filt.groupby("productvariant").totalsalevalue.sum().reset_index(),
            x="productvariant", y="totalsalevalue", text_auto=".2s",
            color="productvariant", title="Sales by Product Variant"
        ),
        use_container_width=True
    )
    st.plotly_chart(
        px.pie(
            df_filt, names="channel", values="totalsalevalue",
            hole=0.4, title="Channel Contribution to Sales"
        ),
        use_container_width=True
    )

    heat = pd.pivot_table(
        df_filt, values="totalsalevalue",
        index="productvariant", columns="channel",
        aggfunc="sum", fill_value=0
    )
    st.plotly_chart(
        px.imshow(heat, text_auto=True, aspect="auto",
                  title="Product‑Channel Heatmap (Total Sales)"),
        use_container_width=True
    )

# ───────────────────────────────────────────── TAB 4 : FEEDBACK
with tabs[3]:
    st.subheader("⭐ Feedback Impact")

    st.plotly_chart(
        px.scatter(
            df_filt, x="feedbackscore", y="totalsalevalue",
            size="unitpurchased", color="productvariant",
            hover_data=["channel", "location"],
            title="Feedback Score vs Total Sale Value"
        ),
        use_container_width=True
    )
    st.plotly_chart(
        px.box(
            df_filt, x="feedbackscore", y="totalsalevalue", points="all",
            title="Sale Value Distribution across Feedback Scores"
        ),
        use_container_width=True
    )

# ───────────────────────────────────────────── TAB 5 : PAYMENT
with tabs[4]:
    st.subheader("💳 Payment Insights")
    st.plotly_chart(
        px.bar(
            df_filt.groupby("paymenttype").totalsalevalue.sum().reset_index(),
            x="paymenttype", y="totalsalevalue", color="paymenttype",
            text_auto=".2s", title="Sales by Payment Type"
        ),
        use_container_width=True
    )

# ───────────────────────────────────────────── TAB 6 : CORRELATIONS
with tabs[5]:
    st.subheader("📈 Correlation Matrix & Scatter")

    num_cols = ["age", "unitpurchased", "feedbackscore", "totalsalevalue"]
    corr = df_filt[num_cols].corr()
    st.plotly_chart(
        px.imshow(corr, text_auto=True, aspect="auto", title="Correlation Matrix"),
        use_container_width=True
    )

    st.markdown("#### Custom Scatter Plot")
    x = st.selectbox("X‑axis", num_cols, index=0)
    y = st.selectbox("Y‑axis", num_cols, index=3)
    colour = st.selectbox("Colour by", ["productvariant", "channel", "gender", "location"])
    st.plotly_chart(
        px.scatter(df_filt, x=x, y=y, color=colour, size="unitpurchased",
                   hover_data=["paymenttype"], title=f"{y} vs {x} (colour: {colour})"),
        use_container_width=True
    )

st.success("✅ Dashboard ready — use the sidebar filters to explore!")
