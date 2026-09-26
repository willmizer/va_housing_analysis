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
    One-way constraint chain: beds → baths ceiling → sqft range.
    baths never constrains beds, so moving beds is always snap-free.
    Sqft only snaps if the current value falls outside the new range.
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

    # baths ceiling per bed count (p95)
    baths_max_by_beds = {}
    for b, grp in df.groupby("beds_i"):
        if len(grp) < 15:
            continue
        hi = round(float(grp["baths_r"].quantile(0.95)) * 2) / 2
        baths_max_by_beds[int(b)] = min(8.0, float(hi))

    # sqft range keyed by (beds, baths) — joint lookup, marginal fallbacks
    sqft_joint = {}
    for (beds, baths), grp in df.groupby(["beds_i", "baths_r"]):
        if len(grp) < 10:
            continue
        sqft_joint[(int(beds), round(float(baths) * 2) / 2)] = (
            max(200, int(grp["square_feet"].quantile(0.05))),
            min(10_000, int(grp["square_feet"].quantile(0.95))),
        )

    sqft_by_beds, sqft_by_baths = {}, {}
    for b, grp in df.groupby("beds_i"):
        if len(grp) < 15:
            continue
        sqft_by_beds[int(b)] = (
            max(200, int(grp["square_feet"].quantile(0.05))),
            min(10_000, int(grp["square_feet"].quantile(0.95))),
        )
    for b, grp in df.groupby("baths_r"):
        if len(grp) < 15:
            continue
        sqft_by_baths[round(float(b) * 2) / 2] = (
            max(200, int(grp["square_feet"].quantile(0.05))),
            min(10_000, int(grp["square_feet"].quantile(0.95))),
        )

    return baths_max_by_beds, sqft_joint, sqft_by_beds, sqft_by_baths


def compute_sqft_bounds(beds, baths, sqft_joint, sqft_by_beds, sqft_by_baths):
    bk = round(float(baths) * 2) / 2
    key = (int(beds), bk)
    if key in sqft_joint:
        lo, hi = sqft_joint[key]
    else:
        lo1, hi1 = sqft_by_beds.get(int(beds), (200, 10_000))
        lo2, hi2 = sqft_by_baths.get(bk, (200, 10_000))
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
    baths_max_by_beds, sqft_joint, sqft_by_beds, sqft_by_baths = load_constraints()

    for k, v in [("va_baths", 2.0), ("va_beds", 3), ("va_sqft", 1_500)]:
        if k not in st.session_state:
            st.session_state[k] = v

    @st.fragment
    def property_inputs():
        # beds: always full range — never constrained by other fields
        beds = st.slider("Bedrooms", 1, 8, step=1, key="va_beds")

        # baths: ceiling moves with beds; only snaps if current value exceeds new ceiling
        baths_hi = baths_max_by_beds.get(beds, 8.0)
        if st.session_state["va_baths"] > baths_hi:
            st.session_state["va_baths"] = baths_hi
        baths = st.slider("Bathrooms", 1.0, baths_hi, step=0.5, key="va_baths")

        # sqft: range narrows with beds+baths; only snaps if current value is out of range
        sqft_lo, sqft_hi = compute_sqft_bounds(
            beds, baths, sqft_joint, sqft_by_beds, sqft_by_baths
        )
        cur_sqft = st.session_state["va_sqft"]
        if cur_sqft < sqft_lo:
            st.session_state["va_sqft"] = sqft_lo
        elif cur_sqft > sqft_hi:
            st.session_state["va_sqft"] = sqft_hi
        sqft = st.slider("Square Feet", sqft_lo, sqft_hi, step=100, key="va_sqft")

        st.caption(
            f"Baths and sqft limits are data-driven from Virginia listings · "
            f"Typical for {beds}bd / {baths}ba: {sqft_lo:,} – {sqft_hi:,} sqft"
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

        prop_type = st.selectbox(
            "Property Type",
            ["Single Family", "Townhouse", "Condo", "Multi-Family", "Ranch"]
        )

        input_data = {
            "city_encoded": city_encoded,
            "beds": beds,
            "baths": baths,
            "square_feet": sqft,
            "acres": acres,
            "year_built": year_built,
            "days_on_market": days_on_market,
            "hoa_per_month": hoa,
            "property_type_Townhouse":     1 if prop_type == "Townhouse"     else 0,
            "property_type_Condo":         1 if prop_type == "Condo"         else 0,
            "property_type_Single Family": 1 if prop_type == "Single Family" else 0,
            "property_type_Multi-Family":  1 if prop_type == "Multi-Family"  else 0,
            "property_type_Ranch":         1 if prop_type == "Ranch"         else 0,
        }

        X_input = pd.DataFrame([input_data], columns=features_property)
        log_price = model.predict(X_input)[0]
        price = np.expm1(log_price)
        st.success(f"Predicted Home Price: ${price:,.2f}")

    property_inputs()

elif city:
    st.error("Invalid city name. Please try again.")
