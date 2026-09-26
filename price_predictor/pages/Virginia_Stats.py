import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Virginia Housing Market Overview", layout="wide")


@st.cache_data
def load_data():
    df = pd.read_csv("cleaning/cleaned_housing_data.csv")
    df = df[(df["price"] > 0) & (df["price"] <= 3_000_000)].copy()
    df["city"] = df["city"].str.strip().str.lower().str.title()
    df["city"] = df["city"].replace({"Mc Lean": "McLean", "Mclean": "McLean"})
    return df[df["property_type"].isin(["Single Family", "Townhouse", "Condo", "Multi-Family", "Ranch"])]


df = load_data()

st.title("Virginia Housing Market Overview")
st.caption(f"Based on {len(df):,} residential listings across {df['city'].nunique()} Virginia cities")

# --- top metrics ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Listings",      f"{len(df):,}")
c2.metric("Statewide Median",    f"${df['price'].median():,.0f}")
c3.metric("Average Price",       f"${df['price'].mean():,.0f}")
c4.metric("Typical Range",       f"${df['price'].quantile(0.10):,.0f} - ${df['price'].quantile(0.90):,.0f}")

st.divider()

# --- most expensive / most affordable cities ---
city_stats = (
    df.groupby("city")
    .agg(median_price=("price", "median"), count=("price", "count"))
    .query("count >= 30")
)

col_exp, col_cheap = st.columns(2)

with col_exp:
    st.subheader("Most Expensive Cities")
    top = city_stats.nlargest(15, "median_price").sort_values("median_price")
    fig = px.bar(
        top.reset_index(), x="median_price", y="city", orientation="h",
        labels={"median_price": "Median Price", "city": ""},
        color="median_price", color_continuous_scale="Reds",
    )
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=0, b=0), height=420)
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

with col_cheap:
    st.subheader("Most Affordable Cities")
    bottom = city_stats.nsmallest(15, "median_price").sort_values("median_price", ascending=False)
    fig = px.bar(
        bottom.reset_index(), x="median_price", y="city", orientation="h",
        labels={"median_price": "Median Price", "city": ""},
        color="median_price", color_continuous_scale="Blues",
    )
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=0, b=0), height=420)
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- property type + price distribution ---
col_type, col_dist = st.columns(2)

with col_type:
    st.subheader("Median Price by Property Type")
    type_stats = (
        df.groupby("property_type")
        .agg(median_price=("price", "median"), count=("price", "count"))
        .reset_index()
        .sort_values("median_price")
    )
    fig = px.bar(
        type_stats, x="median_price", y="property_type", orientation="h",
        labels={"median_price": "Median Price", "property_type": ""},
        color="median_price", color_continuous_scale="Greens",
        hover_data={"count": True},
    )
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=0, b=0), height=280)
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)

with col_dist:
    st.subheader("Price Distribution")
    fig = px.histogram(
        df[df["price"] <= 1_500_000],
        x="price", nbins=60,
        labels={"price": "Listing Price", "count": "Listings"},
        color_discrete_sequence=["#4a86c8"],
    )
    fig.update_layout(margin=dict(l=0, r=10, t=0, b=0), height=280, bargap=0.05)
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    fig.update_yaxes(title="Listings")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- most listed cities ---
st.subheader("Cities with the Most Listings")
top_cities = df["city"].value_counts().head(20).reset_index()
top_cities.columns = ["city", "count"]
fig = px.bar(
    top_cities, x="city", y="count",
    labels={"city": "", "count": "Listings"},
    color="count", color_continuous_scale="Purples",
)
fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=0, b=0), height=320)
fig.update_yaxes(title="Listings")
st.plotly_chart(fig, use_container_width=True)
