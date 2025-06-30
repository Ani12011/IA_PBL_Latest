# app.py — beautiful, fault‑tolerant sales dashboard
# --------------------------------------------------
import os, re, difflib
import pandas as pd, numpy as np
import streamlit as st
import plotly.express as px

# ────────────────────────────────── PAGE CONFIG & CSS ─────────────────────────
st.set_page_config("✨ Sales Analytics Pro ✨", layout="wide")
STYLES = """
<style>
/* Global body tweaks */
html, body, [class*="css"]  { font-family: "Montserrat", sans-serif; }
h1, h2, h3 { color:#183153; }
h6 { text-transform:uppercase; letter-spacing:1px; font-size:.7rem; }
section.main > div { padding-top:1rem; }

/* Sidebar */
<style>
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(145deg,#eff4ff,#d8e4ff);
    color:#001037;
}
</style>
/* Hide the default Streamlit footer & menu */
#MainMenu, footer {visibility: hidden;}
</style>
"""
st.markdown(STYLES, unsafe_allow_html=True)

st.title("✨ Sales Analytics Pro")

# ────────────────────────────────── helper: slug & fuzzy match ────────────────
def slug(text: str) -> str:
    text = re.sub(r"[\\s\\-]+", "", text.strip().lower())
    return re.sub(r"[^0-9a-z]", "", text)

# canon → synonym slugs
REQ = {
    "age": [],
    "gender": ["sex"],
    "location": ["city", "state", "region"],
    "productvariant": ["product", "sku", "variant"],
    "unitspurchased": ["units", "quantity", "qty"],
    "unitprice": ["priceperunit", "unitcost"],
    "feedbackscore": ["feedback", "rating", "satisfaction"],
    "channel": ["saleschannel", "purchasechannel"],
    "paymenttype": ["paymentmethod", "payment"],
    "totalsalevalue": ["totalsales", "totalsale", "salesvalue"],
}

DATA = "IA_dataset.csv"
if not os.path.exists(DATA):
    st.error("**IA_dataset.csv** not found next to app.py. Add it and restart.")
    st.stop()

raw = pd.read_csv(DATA)
slug_cols = {slug(c): c for c in raw.columns}            # slug → original
df = raw.copy()
df.columns = [slug(c) for c in df.columns]               # work on slugs

# fuzzy header repair
mapping = {}
for canon, alts in REQ.items():
    pool = [canon] + alts
    found = None
    # exact slug match
    for p in pool:
        if p in df.columns:
            found = p; break
    # fuzzy match (≥ 0.7 similarity)
    if not found:
        close = difflib.get_close_matches(canon, df.columns, n=1, cutoff=0.7)
        found = close[0] if close else None
    if found:
        mapping[found] = canon
df = df.rename(columns=mapping)

# auto‑compute TotalSaleValue if still missing
if "totalsalevalue" not in df.columns and {"unitspurchased", "unitprice"} <= set(df.columns):
    df["totalsalevalue"] = (
        pd.to_numeric(df["unitspurchased"], errors="coerce") *
        pd.to_numeric(df["unitprice"], errors="coerce")
    )

missing = [c for c in REQ if c not in df.columns]
if missing:
    st.error("🚨 Missing columns after repair: " + ", ".join(missing))
    st.stop()

# numeric coercion
for col in ["age","unitspurchased","feedbackscore","totalsalevalue"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df.dropna(subset=["totalsalevalue"], inplace=True)

# ────────────────────────────────── SIDEBAR NAV & FILTERS ─────────────────────
st.sidebar.header("🔎  Filters")
pages = [
    "🏠 Overview",
    "👥 Demographics",
    "📦 Products & Channels",
    "⭐ Feedback Impact",
    "💳 Payment Insights",
    "📈 Correlations"
]
page = st.sidebar.radio("Go to", pages, index=0)

def ms(label,c):
    opts = sorted(df[c].dropna().unique())
    sel = st.sidebar.multiselect(label, opts, default=opts)
    return sel or opts

loc     = ms("Location",        "location")
prod    = ms("Product Variant", "productvariant")
chan    = ms("Channel",         "channel")
gend    = ms("Gender",          "gender")
pay     = ms("Payment Type",    "paymenttype")
age_rng = st.sidebar.slider("Age",  int(df.age.min()), int(df.age.max()),
                            (int(df.age.min()), int(df.age.max())))
unit_rng= st.sidebar.slider("Units Purchased",
                            int(df.unitspurchased.min()), int(df.unitspurchased.max()),
                            (int(df.unitspurchased.min()), int(df.unitspurchased.max())))
fb_rng  = st.sidebar.slider("Feedback Score",
                            int(df.feedbackscore.min()), int(df.feedbackscore.max()),
                            (int(df.feedbackscore.min()), int(df.feedbackscore.max())))

mask = (
    df.location.isin(loc) & df.productvariant.isin(prod) & df.channel.isin(chan) &
    df.gender.isin(gend) & df.paymenttype.isin(pay) &
    df.age.between(*age_rng) & df.unitspurchased.between(*unit_rng) &
    df.feedbackscore.between(*fb_rng)
)
data = df.loc[mask].copy()

# metric cards helper
def card(label, value, color="#ffffff"):
    st.markdown(
        f"""
        <div style="background:{color};padding:14px 25px;border-radius:12px;
                    box-shadow:2px 2px 6px rgba(0,0,0,.07);text-align:center;">
            <h6>{label}</h6><h3>{value}</h3>
        </div>""",
        unsafe_allow_html=True,
    )

# ────────────────────────────────── DASHBOARDS ───────────────────────────
if page == "🏠 Overview":
    c1,c2,c3,c4 = st.columns(4)
    card("Total Sales", f"${data.totalsalevalue.sum():,.0f}", "#d5e8d4")
    with c2: card("Average / Order", f"${data.totalsalevalue.mean():,.0f}", "#e1d5e7")
    with c3: card("Transactions", f"{len(data):,}", "#f8cecc")
    with c4: card("Avg Feedback", f"{data.feedbackscore.mean():.2f}", "#dae8fc")
    st.markdown("### Sale Value Distribution")
    st.plotly_chart(
        px.histogram(data, x="totalsalevalue", nbins=40,
                     template="plotly_white",
                     color_discrete_sequence=["#6fa8dc"]),
        use_container_width=True,
    )

elif page == "👥 Demographics":
    st.header("Age & Gender Dynamics")
    bins = pd.cut(data.age, bins=[0,20,30,40,50,60,100],
                  labels=["≤20","21‑30","31‑40","41‑50","51‑60","60+"])
    data["agegroup"] = bins
    st.plotly_chart(
        px.bar(data.groupby("agegroup", observed=True).totalsalevalue.sum().reset_index(),
               x="agegroup", y="totalsalevalue",
               color="agegroup", template="plotly_white",
               color_discrete_sequence=px.colors.qualitative.Pastel,
               text_auto=".2s"),
        use_container_width=True)
    st.plotly_chart(
        px.violin(data, y="age", x="gender", color="gender", box=True, points="all",
                  template="plotly_white",
                  color_discrete_sequence=px.colors.qualitative.Set2),
        use_container_width=True)

elif page == "📦 Products & Channels":
    st.header("Product & Channel Performance")
    col1,col2 = st.columns([2,1])
    with col1:
        st.plotly_chart(
            px.bar(data.groupby("productvariant").totalsalevalue.sum().sort_values().reset_index(),
                   x="totalsalevalue", y="productvariant",
                   orientation="h", template="plotly_white",
                   color="productvariant",
                   color_discrete_sequence=px.colors.qualitative.Safe,
                   text_auto=".2s"),
            use_container_width=True)
    with col2:
        st.plotly_chart(
            px.pie(data, names="channel", values="totalsalevalue",
                   template="plotly_white", hole=.5,
                   color_discrete_sequence=px.colors.qualitative.Pastel),
            use_container_width=True)
    # heatmap
    pv = pd.pivot_table(
        data, values="totalsalevalue",
        index="productvariant", columns="channel",
        aggfunc="sum", fill_value=0
    )
    st.plotly_chart(
        px.imshow(pv, text_auto=True, aspect="auto",
                  color_continuous_scale="Blues",
                  template="plotly_white"),
        use_container_width=True)

elif page == "⭐ Feedback Impact":
    st.header("Feedback Analysis")
    st.plotly_chart(
        px.scatter(data, x="feedbackscore", y="totalsalevalue",
                   size="unitspurchased", color="productvariant",
                   template="plotly_white",
                   color_discrete_sequence=px.colors.qualitative.Vivid,
                   hover_data=["location","channel"]),
        use_container_width=True)
    st.plotly_chart(
        px.box(data, x="feedbackscore", y="totalsalevalue", points="all",
               color="feedbackscore", template="plotly_white",
               color_discrete_sequence=px.colors.sequential.Mint),
        use_container_width=True)

elif page == "💳 Payment Insights":
    st.header("Payment Method Preferences")
    st.plotly_chart(
        px.bar(data.groupby("paymenttype").totalsalevalue.sum().reset_index(),
               x="paymenttype", y="totalsalevalue", text_auto=".2s",
               color="paymenttype", template="plotly_white",
               color_discrete_sequence=px.colors.qualitative.Pastel2),
        use_container_width=True)
    st.plotly_chart(
        px.sunburst(data, path=["paymenttype","channel","productvariant"],
                    values="totalsalevalue",
                    template="plotly_white",
                    color="paymenttype",
                    color_discrete_sequence=px.colors.qualitative.Pastel2),
        use_container_width=True)

elif page == "📈 Correlations":
    st.header("Relationships & Patterns")
    num = ["age","unitspurchased","feedbackscore","totalsalevalue"]
    st.plotly_chart(
        px.imshow(data[num].corr(), text_auto=True, aspect="auto",
                  color_continuous_scale="RdBu",
                  template="plotly_white"),
        use_container_width=True)
    st.markdown("#### Pairwise Scatter")
    X = st.selectbox("X", num, 0)
    Y = st.selectbox("Y", num, 3)
    clr = st.selectbox("Colour by", ["productvariant","channel","gender","location"])
    st.plotly_chart(
        px.scatter(data, x=X, y=Y, color=clr, size="unitspurchased",
                   template="plotly_white",
                   color_discrete_sequence=px.colors.qualitative.Bold,
                   hover_data=["paymenttype"]),
        use_container_width=True)

st.caption("Built with 🧡 Streamlit & Plotly — © 2025")
