# app.py — universal loader + robust dashboard
# -------------------------------------------
# Prereqs:  streamlit  pandas  numpy  openpyxl  plotly

import io, re, os, urllib.request as urlreq
import pandas as pd, numpy as np, streamlit as st, plotly.express as px

st.set_page_config("Sales Analytics Dashboard", layout="wide")
st.title("📊 Comprehensive Sales Analytics Dashboard")

# ╭──────────────────────────────── FILE SOURCES ─────────────────────────╮
LOCAL_FILE      = "IA_dataset.csv"   # if present in repo / deployed app
GITHUB_RAW_URL  = (
    "https://raw.githubusercontent.com/<user>/<repo>/<branch>/IA_dataset.csv"
    # ⇡  🔁  ← replace with the real raw‑file URL from your GitHub repo.
)

uploaded = st.sidebar.file_uploader(
    "⬆️ Upload CSV or Excel (optional) – leave blank to use repo file/GitHub)",
    type=["csv", "xlsx", "xls"]
)

def get_file_obj():
    "Return a readable binary file‑like object."
    if uploaded is not None:
        st.sidebar.success(f"Using uploaded file: {uploaded.name}")
        return uploaded

    # 1️⃣ local file inside repo
    if os.path.exists(LOCAL_FILE):
        st.sidebar.success(f"Using repo file: {LOCAL_FILE}")
        return open(LOCAL_FILE, "rb")

    # 2️⃣ try GitHub raw link
    try:
        st.sidebar.info("Downloading dataset from GitHub …")
        raw_bytes = urlreq.urlopen(GITHUB_RAW_URL).read()
        return io.BytesIO(raw_bytes)
    except Exception as e:
        st.error(
            "❌ Could not locate **IA_dataset.csv** locally nor download it from "
            "GitHub.\n\nPlease either:\n"
            "• Place the file in the repo next to *app.py*,\n"
            "• Correct `GITHUB_RAW_URL` above, **or**\n"
            "• Upload a file via the sidebar."
        )
        st.stop()

file_obj = get_file_obj()

# ╰────────────────────────────────────────────────────────────────────────╯

# ─── HELPER: flexible header match ───────────────────────────────────────
def slug(x: str) -> str:
    x = re.sub(r"[\\s\\-]+", "", x.strip().lower())
    return re.sub(r"[^0-9a-z]", "", x)

WANTED = {
    "age":            ["age"],
    "gender":         ["gender", "sex"],
    "location":       ["location", "city", "region", "state"],
    "productvariant": ["productvariant", "product", "sku", "variant"],
    "unitspurchased": ["unitspurchased","unitpurchased","units","quantity","qty"],
    "unitprice":      ["unitprice","priceperunit","unitcost"],
    "feedbackscore":  ["feedbackscore","feedback","rating","satisfaction"],
    "channel":        ["channel","saleschannel","purchasechannel"],
    "paymenttype":    ["paymenttype","paymentmethod","payment"],
    "totalsalevalue": ["totalsalevalue","totalsale","salesvalue","totalsales"],
}

def load_clean(f) -> pd.DataFrame:
    # auto‑detect format
    name = getattr(f, "name", "file").lower()
    if name.endswith((".xlsx",".xls")):
        df_raw = pd.read_excel(f)
    else:
        df_raw = pd.read_csv(f)

    # map raw → canonical
    mapping, slug_map = {}, {slug(c): c for c in df_raw.columns}
    for canon, frags in WANTED.items():
        raw = next((slug_map[s] for s in frags if s in slug_map), None)
        if raw: mapping[raw] = canon
    df = df_raw.rename(columns=mapping)

    # compute TotalSaleValue if absent but units & price exist
    if "totalsalevalue" not in df.columns and {"unitspurchased","unitprice"} <= set(df.columns):
        df["totalsalevalue"] = (
            pd.to_numeric(df["unitspurchased"], errors="coerce") *
            pd.to_numeric(df["unitprice"],      errors="coerce")
        )

    # final validation
    req = ["age","gender","location","productvariant","unitspurchased",
           "feedbackscore","channel","paymenttype","totalsalevalue"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        st.error("❌ After header normalisation, missing columns:\n\n"
                 f"**{', '.join(missing)}**")
        st.stop()

    # numeric coercion
    for n in ["age","unitspurchased","feedbackscore","totalsalevalue"]:
        df[n] = pd.to_numeric(df[n], errors="coerce")
    df.dropna(subset=["totalsalevalue"], inplace=True)
    return df

df = load_clean(file_obj)
st.write("### Data preview")
st.dataframe(df.head())

# ─── SIDEBAR FILTERS ─────────────────────────────────────────────────────
st.sidebar.header("🔎 Filters")

def ms(label, col):
    opts = df[col].dropna().unique().tolist()
    sel  = st.sidebar.multiselect(label, opts, default=opts)
    return sel or opts

locs  = ms("Location",        "location")
prods = ms("Product Variant", "productvariant")
chns  = ms("Channel",         "channel")
gnds  = ms("Gender",          "gender")
pays  = ms("Payment Type",    "paymenttype")

age_rng  = st.sidebar.slider("Age Range",  int(df.age.min()), int(df.age.max()),
                             (int(df.age.min()), int(df.age.max())))
unit_rng = st.sidebar.slider("Units Purchased",
                             int(df.unitspurchased.min()), int(df.unitspurchased.max()),
                             (int(df.unitspurchased.min()), int(df.unitspurchased.max())))
fb_rng   = st.sidebar.slider("Feedback Score",
                             int(df.feedbackscore.min()), int(df.feedbackscore.max()),
                             (int(df.feedbackscore.min()), int(df.feedbackscore.max())))

mask = (
    df.location.isin(locs) &
    df.productvariant.isin(prods) &
    df.channel.isin(chns) &
    df.gender.isin(gnds) &
    df.paymenttype.isin(pays) &
    df.age.between(*age_rng) &
    df.unitspurchased.between(*unit_rng) &
    df.feedbackscore.between(*fb_rng)
)
df_f = df.loc[mask].copy()

# ─── DASHBOARD TABS ──────────────────────────────────────────────────────
tabs = st.tabs(["KPIs","Demographics","Products & Channels",
                "Feedback","Payment","Correlations"])

# 1️⃣ KPIs
with tabs[0]:
    st.subheader("📌 High‑level KPIs")
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

# 2️⃣ Demographics
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
               x="gender", y="totalsalevalue", text_auto=".2s", color="gender",
               title="Sales by Gender"),
        use_container_width=True
    )

# 3️⃣ Products & Channels
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
                  title="Product‑Channel Heatmap (Total Sales)"),
        use_container_width=True
    )

# 4️⃣ Feedback
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
        px.box(df_f, x="feedbackscore", y="totalsalevalue", points="all",
               title="Sale Value Distribution across Feedback Scores"),
        use_container_width=True
    )

# 5️⃣ Payment
with tabs[4]:
    st.subheader("💳 Payment Insights")
    st.plotly_chart(
        px.bar(df_f.groupby("paymenttype").totalsalevalue.sum().reset_index(),
               x="paymenttype", y="totalsalevalue", color="paymenttype",
               text_auto=".2s", title="Sales by Payment Type"),
        use_container_width=True
    )

# 6️⃣ Correlations
with tabs[5]:
    st.subheader("📈 Correlation Matrix & Scatter")
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

st.success("✅ Dashboard ready — use sidebar filters to explore!")
