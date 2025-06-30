# app.py — fuzzy‑matching header normalisation + Streamlit dashboard
# -----------------------------------------------------------------
# Requirements: streamlit pandas numpy plotly openpyxl (for future Excel)

import os, re, difflib
import pandas as pd, numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config("Sales Analytics Dashboard", layout="wide")
st.title("📊 Comprehensive Sales Analytics Dashboard")

# 1️⃣ LOAD CSV -------------------------------------------------------------
DATA_FILE = "IA_dataset.csv"

if not os.path.exists(DATA_FILE):
    st.error(f"❌ `{DATA_FILE}` not found. Place it beside app.py and restart.")
    st.stop()

df_raw = pd.read_csv(DATA_FILE)

# 2️⃣ SLUGIFY HEADERS ------------------------------------------------------
def slug(text: str) -> str:
    """lower‑case, trim, replace whitespace/dashes, drop non‑alnum"""
    text = re.sub(r"[\\s\\-]+", "", text.strip().lower())
    return re.sub(r"[^0-9a-z]", "", text)

orig_cols = list(df_raw.columns)
slug_map  = {slug(c): c for c in orig_cols}          # slug → original
df        = df_raw.copy()
df.columns = [slug(c) for c in df.columns]           # work on slug headers

# 3️⃣ REQUIRED CANONICAL NAMES + SYNONYMS ---------------------------------
REQUIRED = {
    "age",
    "gender",
    "location",
    "productvariant",
    "unitspurchased",
    "feedbackscore",
    "channel",
    "paymenttype",
    "totalsalevalue",   # will be calculated if absent
}

SYNONYM_GROUPS = {
    "unitspurchased": ["unitpurchased", "units", "quantity", "qty"],
    "feedbackscore":  ["feedback", "rating", "satisfaction"],
    "totalsalevalue": ["totalsale", "salesvalue", "totalsales"],
}

# Add synonym slugs to REQUIRED set for fuzzy search
all_targets = set(REQUIRED)
for target, alts in SYNONYM_GROUPS.items():
    all_targets.update(alts)

# 4️⃣ FUZZY‑MATCH HEADERS --------------------------------------------------
matched = {}          # canonical → existing slug column
missing = set(REQUIRED)

for canon in REQUIRED:
    # list of candidate slugs to try (canonical + synonyms)
    candidates = [canon] + SYNONYM_GROUPS.get(canon, [])
    found = None
    # exact slug match first
    for cand in candidates:
        if cand in df.columns:
            found = cand
            break
    # fuzzy (Levenshtein) match second
    if not found:
        close = difflib.get_close_matches(canon, df.columns, n=1, cutoff=0.75)
        if close:
            found = close[0]
    # record result
    if found:
        matched[canon] = found
        missing.discard(canon)

# 5️⃣ HANDLE totalsalevalue CALCULATION -----------------------------------
if "totalsalevalue" in missing:
    # try compute from units × price
    units_col = matched.get("unitspurchased") or difflib.get_close_matches(
        "unitspurchased", df.columns, n=1, cutoff=0.75
    )
    price_col = "unitprice" if "unitprice" in df.columns else None
    if units_col and price_col:
        if isinstance(units_col, list): units_col = units_col[0]
        df["totalsalevalue"] = (
            pd.to_numeric(df[units_col], errors="coerce") *
            pd.to_numeric(df[price_col], errors="coerce")
        )
        matched["totalsalevalue"] = "totalsalevalue"
        missing.discard("totalsalevalue")

# 6️⃣ FINAL VALIDATION -----------------------------------------------------
if missing:
    st.error(
        "❌ Still missing required column(s) even after fuzzy matching: "
        f"**{', '.join(sorted(missing))}**"
    )
    st.write("Columns detected after slugification:", list(df.columns))
    st.stop()

# 7️⃣ RENAME matched columns to canonical names ---------------------------
df = df.rename(columns={v: k for k, v in matched.items()})

# Coerce numeric columns
for col in ["age", "unitspurchased", "feedbackscore", "totalsalevalue"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df.dropna(subset=["totalsalevalue"], inplace=True)

# 8️⃣ SIDEBAR FILTERS ------------------------------------------------------
st.sidebar.header("🔎 Filters")

def multiselect_all(label, column):
    opts = df[column].dropna().unique().tolist()
    sel  = st.sidebar.multiselect(label, opts, default=opts)
    return sel or opts

locations = multiselect_all("Location", "location")
products  = multiselect_all("Product Variant", "productvariant")
channels  = multiselect_all("Channel", "channel")
genders   = multiselect_all("Gender", "gender")
payments  = multiselect_all("Payment Type", "paymenttype")

age_range   = st.sidebar.slider("Age Range", int(df.age.min()), int(df.age.max()),
                                (int(df.age.min()), int(df.age.max())))
unit_range  = st.sidebar.slider("Units Purchased",
                                int(df.unitspurchased.min()), int(df.unitspurchased.max()),
                                (int(df.unitspurchased.min()), int(df.unitspurchased.max())))
fb_range    = st.sidebar.slider("Feedback Score",
                                int(df.feedbackscore.min()), int(df.feedbackscore.max()),
                                (int(df.feedbackscore.min()), int(df.feedbackscore.max())))

mask = (
    df.location.isin(locations) &
    df.productvariant.isin(products) &
    df.channel.isin(channels) &
    df.gender.isin(genders) &
    df.paymenttype.isin(payments) &
    df.age.between(*age_range) &
    df.unitspurchased.between(*unit_range) &
    df.feedbackscore.between(*fb_range)
)
df_f = df.loc[mask].copy()

# 9️⃣ DASHBOARD ------------------------------------------------------------
tabs = st.tabs(
    ["KPIs", "Demographics", "Products & Channels",
     "Feedback", "Payment", "Correlations"]
)

with tabs[0]:
    st.subheader("📌 High‑level KPIs")
    a,b,c,d = st.columns(4)
    a.metric("Total Sale Value", f"${df_f.totalsalevalue.sum():,.2f}")
    b.metric("Avg per Order",    f"${df_f.totalsalevalue.mean():,.2f}")
    c.metric("Transactions",     f"{len(df_f):,}")
    d.metric("Avg Feedback",     f"{df_f.feedbackscore.mean():.2f}")
    st.plotly_chart(
        px.histogram(df_f, x="totalsalevalue", nbins=30,
                     title="Total Sale Value Distribution"),
        use_container_width=True
    )

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

with tabs[2]:
    st.subheader("📦 Products & 📡 Channels")
    st.plotly_chart(
        px.bar(df_f.groupby("productvariant").totalsalevalue.sum().reset_index(),
               x="productvariant", y="totalsalevalue", text_auto=".2s",
               color="productvariant", title="Sales by Product Variant"),
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
                  title="Product‑Channel Heatmap"),
        use_container_width=True
    )

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

with tabs[4]:
    st.subheader("💳 Payment Insights")
    st.plotly_chart(
        px.bar(df_f.groupby("paymenttype").totalsalevalue.sum().reset_index(),
               x="paymenttype", y="totalsalevalue", color="paymenttype",
               text_auto=".2s", title="Sales by Payment Type"),
        use_container_width=True
    )

with tabs[5]:
    st.subheader("📈 Correlations")
    num_cols = ["age","unitspurchased","feedbackscore","totalsalevalue"]
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

st.success("✅ Dashboard loaded — explore with the sidebar filters!")

