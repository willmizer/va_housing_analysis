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

    for k, v in [("va_baths", 2.0), ("va_beds", 3), ("va_sqft", 1_500)]:
        if k not in st.session_state:
            st.session_state[k] = v

    @st.fragment
    def property_inputs():
        col_beds, col_baths = st.columns(2)
        with col_beds:
            beds = st.slider("Bedrooms", 1, 8, step=1, key="va_beds")
        with col_baths:
            baths = st.slider("Bathrooms", 1.0, 8.0, step=0.5, key="va_baths")

        sqft = st.slider("Square Feet", 200, 10_000, step=100, key="va_sqft")

        # --- enforce boundaries after release, snap back with warnings ---
        warnings = []

        baths_max = baths_max_by_beds.get(beds, 8.0)
        if baths > baths_max:
            st.session_state["va_baths"] = baths_max
            baths = baths_max
            warnings.append(
                f"Bathrooms snapped back to **{baths_max:.1f}** — the typical max for "
                f"a {beds}-bedroom Virginia home. Increase bedrooms to unlock more bathrooms."
            )

        sqft_lo, sqft_hi = get_sqft_range(beds, baths, sqft_typical, sqft_by_beds, sqft_by_baths)
        if sqft > sqft_hi:
            st.session_state["va_sqft"] = sqft_hi
            sqft = sqft_hi
            warnings.append(
                f"Square footage snapped back to **{sqft_hi:,}** — the typical max for "
                f"{beds}bd / {baths:.1f}ba in Virginia. Increase bedrooms or bathrooms to go higher."
            )
        elif sqft < sqft_lo:
            st.session_state["va_sqft"] = sqft_lo
            sqft = sqft_lo
            warnings.append(
                f"Square footage snapped back to **{sqft_lo:,}** — the typical min for "
                f"{beds}bd / {baths:.1f}ba in Virginia. Decrease bedrooms or bathrooms to go lower."
            )

        for w in warnings:
            st.warning(w, icon="⚠️")

        if not warnings:
            st.caption(
                f"✅ Typical for {beds}bd / {baths:.1f}ba Virginia homes: "
                f"{sqft_lo:,} – {sqft_hi:,} sqft"
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
