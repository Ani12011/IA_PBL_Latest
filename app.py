# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.figure_factory as ff

# --- PAGE SETUP ---
st.set_page_config(page_title="Comprehensive Sales Analytics Dashboard", layout="wide")

st.title("📊 Sales Analytics Dashboard")
st.markdown("""
Welcome to the all-in-one analytics dashboard!  
Explore every possible insight about your sales, products, customers, and channels, powered by interactive controls.  
**All visuals focus on analyzing and predicting Total Sale Value.**
""")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_excel("IA_PBL_DA_GJ25NS045_AnishAggarwal.xlsx")
    # Standardize column names for code consistency
    df.columns = [c.strip().replace(" ", "") for c in df.columns]
    return df

df = load_data()
if df.empty:
    st.warning("Excel file not found or is empty!")
    st.stop()

# --- FILTERS SIDEBAR ---
st.sidebar.header("Filter Data")
locations = st.sidebar.multiselect("Select Location(s)", options=df['Location'].unique(), default=list(df['Location'].unique()))
products = st.sidebar.multiselect("Select Product Variant(s)", options=df['ProductVariant'].unique(), default=list(df['ProductVariant'].unique()))
channels = st.sidebar.multiselect("Select Channel(s)", options=df['Channel'].unique(), default=list(df['Channel'].unique()))
genders = st.sidebar.multiselect("Select Gender(s)", options=df['Gender'].unique(), default=list(df['Gender'].unique()))
payment_types = st.sidebar.multiselect("Select Payment Type(s)", options=df['PaymentType'].unique(), default=list(df['PaymentType'].unique()))
age_range = st.sidebar.slider("Select Age Range", int(df['Age'].min()), int(df['Age'].max()), (int(df['Age'].min()), int(df['Age'].max())))
feedback_range = st.sidebar.slider("Feedback Score Range", int(df['FeedbackScore'].min()), int(df['FeedbackScore'].max()), (int(df['FeedbackScore'].min()), int(df['FeedbackScore'].max())))
unit_range = st.sidebar.slider("Unit Purchased Range", int(df['UnitPurchased'].min()), int(df['UnitPurchased'].max()), (int(df['UnitPurchased'].min()), int(df['UnitPurchased'].max())))

df_filtered = df[
    (df['Location'].isin(locations)) &
    (df['ProductVariant'].isin(products)) &
    (df['Channel'].isin(channels)) &
    (df['Gender'].isin(genders)) &
    (df['PaymentType'].isin(payment_types)) &
    (df['Age'].between(age_range[0], age_range[1])) &
    (df['FeedbackScore'].between(feedback_range[0], feedback_range[1])) &
    (df['UnitPurchased'].between(unit_range[0], unit_range[1]))
]

# --- TABS FOR THEMATIC SECTIONS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overall KPIs", 
    "Demographic Analysis", 
    "Product & Channel Analysis", 
    "Feedback & Sales", 
    "Payment Analysis",
    "Advanced Correlations"
])

# -------- TAB 1: OVERALL KPIs --------
with tab1:
    st.subheader("Overall Business Snapshot")
    st.info("These KPIs give a quick overview of total sales, average sales per order, customer base size, and average feedback. Use sidebar filters to zoom in on any segment.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sale Value", f"${df_filtered['TotalSaleValue'].sum():,.2f}")
    col2.metric("Avg Sale per Order", f"${df_filtered['TotalSaleValue'].mean():,.2f}")
    col3.metric("Total Transactions", df_filtered.shape[0])
    col4.metric("Avg Feedback Score", f"{df_filtered['FeedbackScore'].mean():.2f}")

    st.markdown("#### Sale Value Distribution")
    st.write("This histogram shows how sale values are distributed, helping to spot trends and outliers.")
    fig = px.histogram(df_filtered, x="TotalSaleValue", nbins=30, color_discrete_sequence=['#00BFFF'])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Sale Value by Product Variant")
    fig = px.box(df_filtered, x="ProductVariant", y="TotalSaleValue", color="ProductVariant", points="all")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Sales Breakdown by Channel")
    fig = px.pie(df_filtered, names="Channel", values="TotalSaleValue", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# -------- TAB 2: DEMOGRAPHIC ANALYSIS --------
with tab2:
    st.subheader("Demographic Impact on Sales")
    st.info("Analyze how age, gender, and location influence Total Sale Value. Use filters for deeper dives.")

    st.markdown("#### Sale Value by Age Group")
    age_bins = pd.cut(df_filtered['Age'], bins=[0,20,30,40,50,60,100], labels=['<=20','21-30','31-40','41-50','51-60','60+'])
    df_filtered['AgeGroup'] = age_bins
    fig = px.bar(df_filtered.groupby('AgeGroup', observed=True)['TotalSaleValue'].sum().reset_index(), 
                 x='AgeGroup', y='TotalSaleValue', color='AgeGroup', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Sales by Gender")
    fig = px.bar(df_filtered.groupby('Gender')['TotalSaleValue'].sum().reset_index(), 
                 x='Gender', y='TotalSaleValue', color='Gender', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Sales by Location")
    top_locations = df_filtered['Location'].value_counts().head(10).index
    fig = px.bar(df_filtered[df_filtered['Location'].isin(top_locations)].groupby('Location')['TotalSaleValue'].sum().reset_index(), 
                 x='Location', y='TotalSaleValue', color='Location', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Units Purchased by Age Group & Gender")
    fig = px.box(df_filtered, x='AgeGroup', y='UnitPurchased', color='Gender', points="all")
    st.plotly_chart(fig, use_container_width=True)

# -------- TAB 3: PRODUCT & CHANNEL ANALYSIS --------
with tab3:
    st.subheader("Product and Channel Performance")
    st.info("Track which products and channels drive the highest sales, volume, and customer satisfaction.")

    st.markdown("#### Total Sale Value by Product Variant")
    fig = px.bar(df_filtered.groupby('ProductVariant')['TotalSaleValue'].sum().reset_index(), 
                 x='ProductVariant', y='TotalSaleValue', color='ProductVariant', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Total Sale Value by Channel")
    fig = px.bar(df_filtered.groupby('Channel')['TotalSaleValue'].sum().reset_index(), 
                 x='Channel', y='TotalSaleValue', color='Channel', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Product Variant vs Channel Heatmap")
    st.write("See which products sell best through which channels.")
    pv = pd.pivot_table(df_filtered, values='TotalSaleValue', index='ProductVariant', columns='Channel', aggfunc=np.sum, fill_value=0)
    fig = px.imshow(pv, text_auto=True, aspect='auto', color_continuous_scale='Blues')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Average Feedback Score by Product Variant")
    fig = px.bar(df_filtered.groupby('ProductVariant')['FeedbackScore'].mean().reset_index(), 
                 x='ProductVariant', y='FeedbackScore', color='ProductVariant', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

# -------- TAB 4: FEEDBACK & SALES --------
with tab4:
    st.subheader("Feedback Impact on Sales")
    st.info("Uncover the link between customer feedback, unit purchase, and sale value.")

    st.markdown("#### Sale Value by Feedback Score")
    fig = px.box(df_filtered, x='FeedbackScore', y='TotalSaleValue', points="all", color='FeedbackScore')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Average Sale Value by Feedback Score Group")
    fig = px.bar(df_filtered.groupby('FeedbackScore')['TotalSaleValue'].mean().reset_index(), 
                 x='FeedbackScore', y='TotalSaleValue', color='FeedbackScore', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Feedback Score Distribution")
    fig = px.histogram(df_filtered, x="FeedbackScore", nbins=10, color_discrete_sequence=['#FFA07A'])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Scatter: Feedback Score vs Total Sale Value")
    fig = px.scatter(df_filtered, x='FeedbackScore', y='TotalSaleValue', size='UnitPurchased', color='ProductVariant', hover_data=['Channel', 'Location'])
    st.plotly_chart(fig, use_container_width=True)

# -------- TAB 5: PAYMENT ANALYSIS --------
with tab5:
    st.subheader("Payment Method Trends")
    st.info("Analyze which payment methods drive higher sales, and their demographics.")

    st.markdown("#### Total Sale Value by Payment Type")
    fig = px.bar(df_filtered.groupby('PaymentType')['TotalSaleValue'].sum().reset_index(), 
                 x='PaymentType', y='TotalSaleValue', color='PaymentType', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Average Feedback Score by Payment Type")
    fig = px.bar(df_filtered.groupby('PaymentType')['FeedbackScore'].mean().reset_index(), 
                 x='PaymentType', y='FeedbackScore', color='PaymentType', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Payment Type vs Channel Heatmap")
    pv2 = pd.pivot_table(df_filtered, values='TotalSaleValue', index='PaymentType', columns='Channel', aggfunc=np.sum, fill_value=0)
    fig = px.imshow(pv2, text_auto=True, aspect='auto', color_continuous_scale='Greens')
    st.plotly_chart(fig, use_container_width=True)

# -------- TAB 6: ADVANCED CORRELATIONS & DEEP DIVES --------
with tab6:
    st.subheader("Advanced Analytics & Deep Dives")
    st.info("Uncover hidden relationships and perform ad-hoc group comparisons across all dimensions.")

    st.markdown("#### Correlation Matrix")
    st.write("Shows relationships between numeric features (UnitPurchased, Age, FeedbackScore, TotalSaleValue).")
    numeric_cols = ['Age', 'UnitPurchased', 'FeedbackScore', 'TotalSaleValue']
    corr = df_filtered[numeric_cols].corr()
    fig = px.imshow(corr, text_auto=True, aspect='auto', color_continuous_scale='RdBu', title='Correlation Matrix')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Pairwise Relationships")
    st.write("Explore how two variables jointly impact sales.")
    x_axis = st.selectbox("X-axis", numeric_cols, index=0)
    y_axis = st.selectbox("Y-axis", numeric_cols, index=3)
    color_by = st.selectbox("Color By", ['ProductVariant', 'Channel', 'Gender', 'Location'], index=0)
    fig = px.scatter(df_filtered, x=x_axis, y=y_axis, color=color_by, size='UnitPurchased', hover_data=['PaymentType'])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Pivot Table: Custom Group Analysis")
    group_cols = st.multiselect("Group By (choose 1-2)", ['Age', 'Gender', 'Location', 'ProductVariant', 'Channel', 'PaymentType'], default=['ProductVariant'])
    if group_cols:
        agg_df = df_filtered.groupby(group_cols)['TotalSaleValue'].agg(['count','sum','mean']).reset_index()
        st.dataframe(agg_df)

    st.markdown("#### Boxplot: Sale Value by Any Categorical")
    cat = st.selectbox("Choose Category", ['Gender', 'Location', 'ProductVariant', 'Channel', 'PaymentType'])
    fig = px.box(df_filtered, x=cat, y='TotalSaleValue', color=cat, points="all")
    st.plotly_chart(fig, use_container_width=True)

# --------- END OF DASHBOARD ---------
st.markdown("---")
st.write("💡 *Tip: Use combinations of sidebar filters and tabbed visuals for powerful ad-hoc business analysis!*")

