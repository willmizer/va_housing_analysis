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
def load_bucket_averages():
    df = pd.read_csv("cleaning/cleaned_housing_data.csv")
    df = df[(df["price"] > 0) & (df["price"] <= 3_000_000)]

    dom_buckets = {
        "Under 2 weeks":   (0,   13),
        "2 weeks – 1 month": (14,  30),
        "1 – 3 months":    (31,  90),
        "3 – 6 months":    (91, 180),
        "6+ months":       (181, 9999),
    }
    hoa_buckets = {
        "No HOA":              (0,   0),
        "Low ($1–$100/mo)":    (1,   100),
        "Moderate ($101–$300/mo)": (101, 300),
        "High ($301–$600/mo)": (301, 600),
        "Premium ($600+/mo)":  (601, 99999),
    }

    dom_avgs, hoa_avgs = {}, {}
    for label, (lo, hi) in dom_buckets.items():
        vals = df["days_on_market"][(df["days_on_market"] >= lo) & (df["days_on_market"] <= hi)]
        dom_avgs[label] = float(vals.mean()) if len(vals) > 0 else (lo + hi) / 2

    for label, (lo, hi) in hoa_buckets.items():
        if lo == 0 and hi == 0:
            hoa_avgs[label] = 0.0
        else:
            vals = df["hoa_per_month"][(df["hoa_per_month"] >= lo) & (df["hoa_per_month"] <= hi)]
            hoa_avgs[label] = float(vals.mean()) if len(vals) > 0 else (lo + min(hi, 9999)) / 2

    return dom_avgs, hoa_avgs


@st.cache_data
def load_constraints():
    """
    One-way chain: beds → baths ceiling; (beds, baths) → sqft range.
    All sliders render at full range — values snap back on release if
    the user exceeds the data-driven boundary, with a warning shown.
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

    baths_max_by_beds = {}
    for b, grp in df.groupby("beds_i"):
        if len(grp) >= 15:
            hi = round(float(grp["baths_r"].quantile(0.95)) * 2) / 2
            baths_max_by_beds[int(b)] = min(8.0, float(hi))

    sqft_typical = {}
    for (beds, baths), grp in df.groupby(["beds_i", "baths_r"]):
        if len(grp) >= 10:
            sqft_typical[(int(beds), round(float(baths) * 2) / 2)] = (
                int(grp["square_feet"].quantile(0.10)),
                int(grp["square_feet"].quantile(0.90)),
            )

    sqft_by_beds, sqft_by_baths = {}, {}
    for b, grp in df.groupby("beds_i"):
        if len(grp) >= 15:
            sqft_by_beds[int(b)] = (
                int(grp["square_feet"].quantile(0.10)),
                int(grp["square_feet"].quantile(0.90)),
            )
    for b, grp in df.groupby("baths_r"):
        if len(grp) >= 15:
            sqft_by_baths[round(float(b) * 2) / 2] = (
                int(grp["square_feet"].quantile(0.10)),
                int(grp["square_feet"].quantile(0.90)),
            )

    return baths_max_by_beds, sqft_typical, sqft_by_beds, sqft_by_baths


def get_sqft_range(beds, baths, sqft_typical, sqft_by_beds, sqft_by_baths):
    bk = round(float(baths) * 2) / 2
    if (int(beds), bk) in sqft_typical:
        return sqft_typical[(int(beds), bk)]
    lo1, hi1 = sqft_by_beds.get(int(beds), (200, 10_000))
    lo2, hi2 = sqft_by_baths.get(bk, (200, 10_000))
    return max(lo1, lo2), min(hi1, hi2)


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
    baths_max_by_beds, sqft_typical, sqft_by_beds, sqft_by_baths = load_constraints()
    dom_avgs, hoa_avgs = load_bucket_averages()

    for k, v in [("va_baths", 2.0), ("va_beds", 3), ("va_sqft", 1_500)]:
        if k not in st.session_state:
            st.session_state[k] = v

    @st.fragment
    def property_inputs():
        # Read current session state values FIRST — Streamlit updates them
        # before the rerun, so these already reflect the latest drag position.
        beds_cur  = int(st.session_state["va_beds"])
        baths_cur = float(st.session_state["va_baths"])
        sqft_cur  = int(st.session_state["va_sqft"])

        st.caption(
            "Sliders are constrained to realistic Virginia listing ranges. "
            "If a value snaps when adjusting another field, it means the combination "
            "falls outside what's typical in the data — try adjusting the other sliders first."
        )

        # Clamp session state BEFORE rendering — widgets pick up clamped values via key=
        baths_max = baths_max_by_beds.get(beds_cur, 8.0)
        if baths_cur > baths_max:
            st.session_state["va_baths"] = baths_max
            baths_cur = baths_max

        sqft_lo, sqft_hi = get_sqft_range(beds_cur, baths_cur, sqft_typical, sqft_by_beds, sqft_by_baths)
        if sqft_cur > sqft_hi:
            st.session_state["va_sqft"] = sqft_hi
        elif sqft_cur < sqft_lo:
            st.session_state["va_sqft"] = sqft_lo

        col_beds, col_baths = st.columns(2)
        with col_beds:
            beds = st.slider("Bedrooms", 1, 8, step=1, key="va_beds")
        with col_baths:
            baths = st.slider("Bathrooms", 1.0, 8.0, step=0.5, key="va_baths")

        sqft = st.slider("Square Feet", 200, 10_000, step=100, key="va_sqft")

        col_acres, col_year = st.columns(2)
        with col_acres:
            acres = st.number_input("Acres", min_value=0.0, value=0.25, step=0.1)
        with col_year:
            year_built = st.number_input("Year Built", min_value=1800, value=2005)

        col_dom, col_hoa = st.columns(2)
        with col_dom:
            dom_label = st.selectbox("Days on Market", list(dom_avgs.keys()), index=1)
            days_on_market = dom_avgs[dom_label]
        with col_hoa:
            hoa_label = st.selectbox("HOA per Month", list(hoa_avgs.keys()), index=0)
            hoa = hoa_avgs[hoa_label]

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
