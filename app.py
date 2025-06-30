# app.py — ultra‑robust header matcher + dashboard
# ------------------------------------------------
# Works with:
#   • IA_dataset.csv in repo (auto‑loaded)
#   • Any uploaded CSV/Excel (via sidebar)
#   • Raw‑GitHub URL fallback (optional)
#
# Prereqs: streamlit pandas numpy openpyxl plotly

import io, os, re, urllib.request as urlreq
import pandas as pd, numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config("Sales Analytics Dashboard", layout="wide")
st.title("📊 Comprehensive Sales Analytics Dashboard")

# ─── FILE SOURCES ─────────────────────────────────────────────────────────
LOCAL_FILE = "IA_dataset.csv"  # your GitHub‑hosted default
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/<user>/<repo>/<branch>/IA_dataset.csv"
    # ^— replace with your real raw‑file URL OR leave as‑is if you have LOCAL_FILE
)

uploaded = st.sidebar.file_uploader(
    "⬆️ Upload CSV or Excel (optional)", type=["csv", "xlsx", "xls"]
)

def choose_file():
    if uploaded is not None:
        st.sidebar.success(f"Using uploaded: {uploaded.name}")
        return uploaded

    if os.path.exists(LOCAL_FILE):
        st.sidebar.success(f"Using repo file: {LOCAL_FILE}")
        return open(LOCAL_FILE, "rb")

    try:
        st.sidebar.info("Downloading dataset from GitHub …")
        data = urlreq.urlopen(GITHUB_RAW_URL).read()
        st.sidebar.success("Downloaded from GitHub raw URL")
        return io.BytesIO(data)
    except Exception:
        st.error(
            "❌ Cannot find **IA_dataset.csv** locally or at the GitHub URL, "
            "and no file was uploaded. Please fix one of those sources."
        )
        st.stop()

file_obj = choose_file()

# ─── FLEXIBLE HEADER NORMALISATION ───────────────────────────────────────
def slug(txt: str) -> str:
    """Lower, trim, remove non‑alphanumerics → slug key."""
    txt = re.sub(r"[\\s\\-]+", "", txt.strip().lower())
    return re.sub(r"[^0-9a-z]", "", txt)

# Required canonical names
REQ = {
    "age":            ["age"],
    "gender":         ["gender", "sex"],
    "location":       ["location", "city", "state", "region"],
    "productvariant": ["productvariant", "product", "sku", "variant"],
    "unitspurchased": ["unitspurchased", "unitpurchased", "units", "quantity", "qty"],
    "unitprice":      ["unitprice", "priceperunit", "unitcost"],
    "feedbackscore":  ["feedbackscore", "feedback", "rating", "satisfaction"],
    "channel":        ["channel", "saleschannel", "purchasechannel"],
    "paymenttype":    ["paymenttype", "paymentmethod", "payment"],
    "totalsalevalue": ["totalsalevalue", "totalsale", "salesvalue", "totalsales"],
}

def load_clean(f) -> pd.DataFrame:
    # 1️⃣ read file
    name = getattr(f, "name", "file").lower()
    df_raw = pd.read_excel(f) if name.endswith((".xls", ".xlsx")) else pd.read_csv(f)

    # 2️⃣ slug map of original headers
    slug2raw = {slug(c): c for c in df_raw.columns}

    # 3️⃣ build mapping (partial starts‑with match)
    mapping = {}
    for canon, patterns in REQ.items():
        found = None
        for pat in patterns:
            # look for any slug key that STARTS with our pattern or vice‑versa
            found = next(
                (raw for s, raw in slug2raw.items()
                 if s.startswith(pat) or pat.startswith(s)),
                None
            )
            if found:
                mapping[found] = canon
                break

    df = df_raw.rename(columns=mapping)

    # 4️⃣ compute TotalSaleValue if absent but units & price exist
    if "totalsalevalue" not in df and {"unitspurchased", "unitprice"} <= set(df.columns):
        df["totalsalevalue"] = (
            pd.to_numeric(df["unitspurchased"], errors="coerce") *
            pd.to_numeric(df["unitprice"], errors="coerce")
        )

    # 5️⃣ validate presence
    missing = [c for c in REQ if c not in df.columns]
    if missing:
        st.error(
            "❌ After header normalisation the following column(s) are missing: "
            f"**{', '.join(missing)}**"
        )
        st.write("Original columns detected:", list(df_raw.columns))
        st.stop()

    # 6️⃣ numeric coercion
    for col in ["age", "unitspurchased", "feedbackscore", "totalsalevalue"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
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

locs = ms("Location", "location")
prods = ms("Product Variant", "productvariant")
chns = ms("Channel", "channel")
gnds = ms("Gender", "gender")
pays = ms("Payment Type", "paymenttype")

age_rng  = st.sidebar.slider("Age",  int(df.age.min()), int(df.age.max()),
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

# ─── DASHBOARD ───────────────────────────────────────────────────────────
tabs = st.tabs(["KPIs","Demographics","Products & Channels",
                "Feedback","Payment","Correlations"])

with tabs[0]:
    st.subheader("📌 High‑level KPIs (filtered)")
    a,b,c,d = st.columns(4)
    a.metric("Total Sale Value", f"${df_f.totalsalevalue.sum():,.2f}")
    b.metric("Avg per Order",    f"${df_f.totalsalevalue.mean():,.2f}")
    c.metric("Transactions",     f"{len(df_f):,}")
    d.metric("Avg Feedback",     f"{df_f.feedbackscore.mean():.2f}")
    st.plotly_chart(px.histogram(df_f, x="totalsalevalue", nbins=30,
                                 title="Distribution of Total Sale Values"),
                    use_container_width=True)

with tabs[1]:
    st.subheader("👥 Demographic Impact")
    age_bins = pd.cut(df_f.age, bins=[0,20,30,40,50,60,100],
                      labels=["≤20","21‑30","31‑40","41‑50","51‑60","60+"])
    df_f["agegroup"] = age_bins
    st.plotly_chart(px.bar(df_f.groupby("agegroup", observed=True).totalsalevalue.sum()
                           .reset_index(), x="agegroup", y="totalsalevalue",
                           title="Sales by Age Group", text_auto=".2s"),
                    use_container_width=True)
    st.plotly_chart(px.bar(df_f.groupby("gender").totalsalevalue.sum().reset_index(),
                           x="gender", y="totalsalevalue", color="gender",
                           title="Sales by Gender", text_auto=".2s"),
                    use_container_width=True)

with tabs[2]:
    st.subheader("📦 Products & 📡 Channels")
    st.plotly_chart(px.bar(df_f.groupby("productvariant").totalsalevalue.sum()
                           .reset_index(), x="productvariant", y="totalsalevalue",
                           color="productvariant", text_auto=".2s",
                           title="Sales by Product Variant"),
                    use_container_width=True)
    st.plotly_chart(px.pie(df_f, names="channel", values="totalsalevalue",
                           hole=0.4, title="Channel Contribution to Sales"),
                    use_container_width=True)
    heat = pd.pivot_table(df_f, values="totalsalevalue",
                          index="productvariant", columns="channel",
                          aggfunc="sum", fill_value=0)
    st.plotly_chart(px.imshow(heat, text_auto=True, aspect="auto",
                              title="Product‑Channel Heatmap (Total Sales)"),
                    use_container_width=True)

with tabs[3]:
    st.subheader("⭐ Feedback vs Sales")
    st.plotly_chart(px.scatter(df_f, x="feedbackscore", y="totalsalevalue",
                               size="unitspurchased", color="productvariant",
                               hover_data=["channel","location"],
                               title="Feedback Score vs Total Sale Value"),
                    use_container_width=True)
    st.plotly_chart(px.box(df_f, x="feedbackscore", y="totalsalevalue",
                           points="all", title="Sale Value by Feedback Score"),
                    use_container_width=True)

with tabs[4]:
    st.subheader("💳 Payment Insights")
    st.plotly_chart(px.bar(df_f.groupby("paymenttype").totalsalevalue.sum()
                           .reset_index(), x="paymenttype", y="totalsalevalue",
                           color="paymenttype", text_auto=".2s",
                           title="Sales by Payment Type"),
                    use_container_width=True)

with tabs[5]:
    st.subheader("📈 Correlations")
    num = ["age","unitspurchased","feedbackscore","totalsalevalue"]
    st.plotly_chart(px.imshow(df_f[num].corr(), text_auto=True, aspect="auto",
                              title="Correlation Matrix"),
                    use_container_width=True)
    st.markdown("#### Custom Scatter")
    x = st.selectbox("X‑axis", num, index=0)
    y = st.selectbox("Y‑axis", num, index=3)
    colour = st.selectbox("Colour by", ["productvariant","channel","gender","location"])
    st.plotly_chart(px.scatter(df_f, x=x, y=y, color=colour, size="unitspurchased",
                               hover_data=["paymenttype"],
                               title=f"{y} vs {x} (colour: {colour})"),
                    use_container_width=True)

st.success("✅ Dashboard ready — explore with the sidebar filters!")
