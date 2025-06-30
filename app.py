# app.py — slug‑based header normalisation + streamlined dashboard
# ---------------------------------------------------------------
# Author‑proof: works as long as headers *contain* the key words
# (UnitsPurchased / Total Sale Value etc.), regardless of spaces/case.

import os, re, pandas as pd, numpy as np, streamlit as st, plotly.express as px

st.set_page_config("Sales Analytics Dashboard", layout="wide")
st.title("📊 Comprehensive Sales Analytics Dashboard")

# ──────────────────────────────── 1. Load the CSV  ─────────────────────────────
DATA_FILE = "IA_dataset.csv"

if not os.path.exists(DATA_FILE):
    st.error(f"❌ `{DATA_FILE}` not found. Place the file next to `app.py` and restart.")
    st.stop()

df_raw = pd.read_csv(DATA_FILE)

# ─────────────────────────────── 2. Slugify headers  ───────────────────────────
def slug(txt: str) -> str:
    """lower‑case, strip, drop non‑alphanumerics → safe key"""
    txt = re.sub(r"[\\s\\-]+", "", txt.strip().lower())
    return re.sub(r"[^0-9a-z]", "", txt)

df = df_raw.copy()
df.columns = [slug(c) for c in df.columns]

# ────────────────────────────── 3. Column dictionary  ──────────────────────────
# Canonical slugs we expect
REQ = {
    "age": "age",
    "gender": "gender",
    "location": "location",
    "productvariant": "productvariant",
    "unitspurchased": "unitspurchased",        # from “UnitsPurchased”
    "unitprice": "unitprice",                  # if present
    "feedbackscore": "feedbackscore",
    "channel": "channel",
    "paymenttype": "paymenttype",
    "totalsalevalue": "totalsalevalue",        # from “Total Sale Value”
}

# 3.a  Compute TotalSaleValue if missing but Units × Price exist
if "totalsalevalue" not in df.columns and {"unitspurchased", "unitprice"} <= set(df.columns):
    df["totalsalevalue"] = (
        pd.to_numeric(df["unitspurchased"], errors="coerce")
        * pd.to_numeric(df["unitprice"], errors="coerce")
    )

# 3.b  Verify required columns
missing = [c for c in REQ.values() if c not in df.columns]
if missing:
    st.error(
        "❌ Required column(s) missing even after header normalisation: "
        f"**{', '.join(missing)}**"
    )
    st.write("Columns detected after slugification:", list(df.columns))
    st.stop()

# 3.c  Make sure numeric columns are numeric
for nc in ["age", "unitspurchased", "feedbackscore", "totalsalevalue"]:
    df[nc] = pd.to_numeric(df[nc], errors="coerce")

df.dropna(subset=["totalsalevalue"], inplace=True)

# ─────────────────────────────── 4. Sidebar filters  ───────────────────────────
st.sidebar.header("🔎 Filters")

def multi(label, column):
    opts = df[column].dropna().unique().tolist()
    sel  = st.sidebar.multiselect(label, opts, default=opts)
    return sel or opts  # if user clears, treat as “all”

locs  = multi("Location",        "location")
prods = multi("Product Variant", "productvariant")
chns  = multi("Channel",         "channel")
gnds  = multi("Gender",          "gender")
pays  = multi("Payment Type",    "paymenttype")

age_rng  = st.sidebar.slider("Age",
                             int(df.age.min()), int(df.age.max()),
                             (int(df.age.min()), int(df.age.max())))
unit_rng = st.sidebar.slider("Units Purchased",
                             int(df.unitspurchased.min()), int(df.unitspurchased.max()),
                             (int(df.unitspurchased.min()), int(df.unitspurchased.max())))
fb_rng   = st.sidebar.slider("Feedback Score",
                             int(df.feedbackscore.min()), int(df.feedbackscore.max()),
                             (int(df.feedbackscore.min()), int(df.feedbackscore.max())))

mask = (
    df.location.isin(locs)
    & df.productvariant.isin(prods)
    & df.channel.isin(chns)
    & df.gender.isin(gnds)
    & df.paymenttype.isin(pays)
    & df.age.between(*age_rng)
    & df.unitspurchased.between(*unit_rng)
    & df.feedbackscore.between(*fb_rng)
)
df_f = df.loc[mask].copy()

# ─────────────────────────────── 5. Dashboard tabs  ────────────────────────────
tabs = st.tabs(
    ["KPIs", "Demographics", "Products & Channels",
     "Feedback Impact", "Payment Insights", "Correlations"]
)

# 5.1  KPIs
with tabs[0]:
    st.subheader("📌 High‑level KPIs (filtered)")
    a,b,c,d = st.columns(4)
    a.metric("Total Sale Value", f"${df_f.totalsalevalue.sum():,.2f}")
    b.metric("Avg per Order",    f"${df_f.totalsalevalue.mean():,.2f}")
    c.metric("Transactions",     f"{len(df_f):,}")
    d.metric("Avg Feedback",     f"{df_f.feedbackscore.mean():.2f}")
    st.plotly_chart(
        px.histogram(df_f, x="totalsalevalue", nbins=30,
                     title="Distribution of Total Sale Values"),
        use_container_width=True
    )

# 5.2  Demographics
with tabs[1]:
    st.subheader("👥 Demographic Impact")
    age_bins = pd.cut(df_f.age, bins=[0,20,30,40,50,60,100],
                      labels=["≤20","21‑30","31‑40","41‑50","51‑60","60+"])
    df_f["agegroup"] = age_bins
    st.plotly_chart(
        px.bar(df_f.groupby("agegroup", observed=True).totalsalevalue.sum().reset_index(),
               x="agegroup", y="totalsalevalue", text_auto=".2s",
               title="Sales by Age Group"),
        use_container_width=True
    )
    st.plotly_chart(
        px.bar(df_f.groupby("gender").totalsalevalue.sum().reset_index(),
               x="gender", y="totalsalevalue", color="gender", text_auto=".2s",
               title="Sales by Gender"),
        use_container_width=True
    )

# 5.3  Products & Channels
with tabs[2]:
    st.subheader("📦 Products & 📡 Channels")
    st.plotly_chart(
        px.bar(df_f.groupby("productvariant").totalsalevalue.sum().reset_index(),
               x="productvariant", y="totalsalevalue", color="productvariant",
               text_auto=".2s", title="Sales by Product Variant"),
        use_container_width=True
    )
    st.plotly_chart(
        px.pie(df_f, names="channel", values="totalsalevalue",
               hole=0.4, title="Channel Contribution to Sales"),
        use_container_width=True
    )
    heat = pd.pivot_table(df_f, values="totalsalevalue",
                          index="productvariant", columns="channel",
                          aggfunc="sum", fill_value=0)
    st.plotly_chart(
        px.imshow(heat, text_auto=True, aspect="auto",
                  title="Product‑Channel Heatmap (Total Sales)"),
        use_container_width=True
    )

# 5.4  Feedback Impact
with tabs[3]:
    st.subheader("⭐ Feedback vs Sales")
    st.plotly_chart(
        px.scatter(df_f, x="feedbackscore", y="totalsalevalue",
                   size="unitspurchased", color="productvariant",
                   hover_data=["channel","location"],
                   title="Feedback Score vs Total Sale Value"),
        use_container_width=True
    )
    st.plotly_chart(
        px.box(df_f, x="feedbackscore", y="totalsalevalue",
               points="all", title="Sale Value by Feedback Score"),
        use_container_width=True
    )

# 5.5  Payment Insights
with tabs[4]:
    st.subheader("💳 Payment Insights")
    st.plotly_chart(
        px.bar(df_f.groupby("paymenttype").totalsalevalue.sum().reset_index(),
               x="paymenttype", y="totalsalevalue", color="paymenttype",
               text_auto=".2s", title="Sales by Payment Type"),
        use_container_width=True
    )

# 5.6  Correlations
with tabs[5]:
    st.subheader("📈 Correlation Matrix & Scatter")
    num_cols = ["age", "unitspurchased", "feedbackscore", "totalsalevalue"]
    st.plotly_chart(
        px.imshow(df_f[num_cols].corr(), text_auto=True, aspect="auto",
                  title="Correlation Matrix"),
        use_container_width=True
    )
    st.markdown("#### Custom Scatter")
    x = st.selectbox("X‑axis", num_cols, index=0)
    y = st.selectbox("Y‑axis", num_cols, index=3)
    colour = st.selectbox("Colour by", ["productvariant","channel","gender","location"])
    st.plotly_chart(
        px.scatter(df_f, x=x, y=y, color=colour, size="unitspurchased",
                   hover_data=["paymenttype"],
                   title=f"{y} vs {x} (colour: {colour})"),
        use_container_width=True
    )

st.success("✅ Dashboard ready — explore with the sidebar filters!")

