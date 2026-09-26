import streamlit as st
import numpy as np
import pandas as pd
import bz2
import pickle

st.set_page_config(page_title="Virginia Home Price Predictor", layout="centered")

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def decompress_pickle(file):
    with bz2.BZ2File(file, "rb") as f:
        return pickle.load(f)


model = decompress_pickle("price_predictor/model_price.pbz2")
city_mapping = decompress_pickle("price_predictor/city_mapping.pbz2")


@st.cache_data
def load_price_stats():
    df = pd.read_csv("cleaning/cleaned_housing_data.csv")
    prices = df["price"][(df["price"] > 0) & (df["price"] <= 3_000_000)]
    return {
        "n": int(prices.shape[0]),
        "median": float(prices.median()),
        "p10": float(prices.quantile(0.10)),
        "p90": float(prices.quantile(0.90)),
    }


@st.cache_data
def load_constraints():
    """
    Build lookup tables from actual listing data so slider bounds reflect
    realistic correlations between beds, baths, and square footage.
    Uses 5th/95th percentiles to avoid outlier distortion.
    """
    df = pd.read_csv("cleaning/cleaned_housing_data.csv")
    df = df[
        (df["price"] > 0) & (df["price"] <= 3_000_000) &
        (df["beds"] >= 1) & (df["beds"] <= 8) &
        (df["baths"] >= 1.0) & (df["baths"] <= 8.0) &
        (df["square_feet"] >= 200) & (df["square_feet"] <= 10_000)
    ].copy()
    df["baths_r"] = (df["baths"] * 2).round() / 2
    df["beds_i"] = df["beds"].round().clip(1, 8).astype(int)

    sqft_by_baths, sqft_by_beds, beds_by_baths, baths_by_beds = {}, {}, {}, {}

    for b, grp in df.groupby("baths_r"):
        if len(grp) < 15:
            continue
        key = round(float(b) * 2) / 2
        sqft_by_baths[key] = (
            max(200, int(grp["square_feet"].quantile(0.05))),
            min(10_000, int(grp["square_feet"].quantile(0.95))),
        )
        beds_by_baths[key] = (
            max(1, int(grp["beds_i"].quantile(0.05))),
            min(8, int(grp["beds_i"].quantile(0.95))),
        )

    for b, grp in df.groupby("beds_i"):
        if len(grp) < 15:
            continue
        key = int(b)
        sqft_by_beds[key] = (
            max(200, int(grp["square_feet"].quantile(0.05))),
            min(10_000, int(grp["square_feet"].quantile(0.95))),
        )
        bath_lo = round(float(grp["baths_r"].quantile(0.05)) * 2) / 2
        bath_hi = round(float(grp["baths_r"].quantile(0.95)) * 2) / 2
        baths_by_beds[key] = (
            max(1.0, float(bath_lo)),
            min(8.0, float(bath_hi)),
        )

    return sqft_by_baths, sqft_by_beds, beds_by_baths, baths_by_beds


def compute_sqft_bounds(baths, beds, sqft_by_baths, sqft_by_beds):
    bk = round(float(baths) * 2) / 2
    lo1, hi1 = sqft_by_baths.get(bk, (200, 10_000))
    lo2, hi2 = sqft_by_beds.get(int(beds), (200, 10_000))
    lo = max(lo1, lo2)
    hi = min(hi1, hi2)
    if hi - lo < 400:
        lo = min(lo1, lo2)
        hi = max(hi1, hi2)
    lo = int((lo // 100) * 100)
    hi = int(((hi + 99) // 100) * 100)
    if hi <= lo:
        hi = lo + 2_000
    return lo, hi


features_property = [
    "city_encoded", "beds", "baths", "square_feet", "acres", "year_built",
    "days_on_market", "hoa_per_month",
    "property_type_Townhouse", "property_type_Condo", "property_type_Single Family",
    "property_type_Multi-Family", "property_type_Ranch",
]

st.title("Virginia Home Price Predictor")

with st.expander("Key Insights"):
    price_stats = load_price_stats()
    insights_df = pd.DataFrame([
        {"Insight": "Baseline error (before tuning)", "Detail": "About $180 error predicting price per square foot"},
        {"Insight": "Error after city encoding + log transform", "Detail": "Reduced to about $37.52"},
        {"Insight": "City/land encoding impact", "Detail": "Cut prediction error by about 50% across all three models"},
        {"Insight": "Log-transform impact", "Detail": "Cut error a further 20-30%"},
        {"Insight": "Most influential features", "Detail": "Square footage, number of baths, city-encoded price, property type"},
        {"Insight": f"Median listing price (n={price_stats['n']:,})", "Detail": f"${price_stats['median']:,.0f}"},
        {"Insight": "Typical price range (10th-90th percentile)", "Detail": f"${price_stats['p10']:,.0f} - ${price_stats['p90']:,.0f}"},
    ])
    st.dataframe(insights_df, hide_index=True, width="stretch")

city = st.text_input("Enter a Virginia City").strip().lower().title()

if city and city in city_mapping:
    city_encoded = city_mapping[city]

    sqft_by_baths, sqft_by_beds, beds_by_baths, baths_by_beds = load_constraints()

    # initialize session state on first load
    for k, v in [("va_baths", 2.0), ("va_beds", 3), ("va_sqft", 1_500)]:
        if k not in st.session_state:
            st.session_state[k] = v

    baths_cur = float(st.session_state["va_baths"])
    beds_cur  = int(st.session_state["va_beds"])

    # compute dynamic bounds from current values
    beds_lo,  beds_hi  = beds_by_baths.get(round(baths_cur * 2) / 2, (1, 8))
    baths_lo, baths_hi = baths_by_beds.get(beds_cur, (1.0, 8.0))

    beds_lo,  beds_hi  = int(beds_lo),  int(beds_hi)
    baths_lo, baths_hi = float(round(baths_lo * 2) / 2), float(round(baths_hi * 2) / 2)

    # ensure ranges are never degenerate
    if beds_lo  == beds_hi:  beds_lo  = max(1,   beds_lo  - 1); beds_hi  = min(8,   beds_hi  + 1)
    if baths_lo == baths_hi: baths_lo = max(1.0, baths_lo - 0.5); baths_hi = min(8.0, baths_hi + 0.5)

    # clamp stored values to new bounds before rendering to avoid Streamlit range errors
    st.session_state["va_baths"] = float(max(baths_lo, min(baths_hi, baths_cur)))
    st.session_state["va_beds"]  = int(max(beds_lo,  min(beds_hi,  beds_cur)))

    sqft_lo, sqft_hi = compute_sqft_bounds(
        st.session_state["va_baths"], st.session_state["va_beds"], sqft_by_baths, sqft_by_beds
    )
    st.session_state["va_sqft"] = int(max(sqft_lo, min(sqft_hi, st.session_state["va_sqft"])))

    # render sliders — session state drives the current value via key=
    col_beds, col_baths = st.columns(2)
    with col_beds:
        beds  = st.slider("Bedrooms",  beds_lo,  beds_hi,  step=1,   key="va_beds")
    with col_baths:
        baths = st.slider("Bathrooms", baths_lo, baths_hi, step=0.5, key="va_baths")

    # recompute sqft bounds now that baths/beds are confirmed, then clamp + render
    sqft_lo, sqft_hi = compute_sqft_bounds(baths, beds, sqft_by_baths, sqft_by_beds)
    st.session_state["va_sqft"] = int(max(sqft_lo, min(sqft_hi, st.session_state["va_sqft"])))
    sqft = st.slider("Square Feet", sqft_lo, sqft_hi, step=100, key="va_sqft")

    st.caption(
        f"Slider ranges are data-driven from Virginia listings · "
        f"Realistic sqft for this config: {sqft_lo:,} – {sqft_hi:,}"
    )

    col_acres, col_year = st.columns(2)
    with col_acres:
        acres = st.number_input("Acres", min_value=0.0, value=0.25)
    with col_year:
        year_built = st.number_input("Year Built", min_value=1800, value=2005)

    col_dom, col_hoa = st.columns(2)
    with col_dom:
        days_on_market = st.number_input("Days on Market", min_value=0, value=14)
    with col_hoa:
        hoa = st.number_input("HOA per Month", min_value=0, value=50)

    prop_type = st.selectbox("Property Type", ["Single Family", "Townhouse", "Condo", "Multi-Family", "Ranch"])

    input_data = {
        "city_encoded": city_encoded,
        "beds": beds,
        "baths": baths,
        "square_feet": sqft,
        "acres": acres,
        "year_built": year_built,
        "days_on_market": days_on_market,
        "hoa_per_month": hoa,
        "property_type_Townhouse":    1 if prop_type == "Townhouse"    else 0,
        "property_type_Condo":        1 if prop_type == "Condo"        else 0,
        "property_type_Single Family":1 if prop_type == "Single Family" else 0,
        "property_type_Multi-Family": 1 if prop_type == "Multi-Family" else 0,
        "property_type_Ranch":        1 if prop_type == "Ranch"        else 0,
    }

    X_input = pd.DataFrame([input_data], columns=features_property)
    log_price = model.predict(X_input)[0]
    price = np.expm1(log_price)
    st.success(f"Predicted Home Price: ${price:,.2f}")

elif city:
    st.error("Invalid city name. Please try again.")
