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

ALL_PROP_TYPES = ["Single Family", "Townhouse", "Condo", "Multi-Family", "Ranch"]



@st.cache_data
def load_bucket_averages():
    df = pd.read_csv("cleaning/cleaned_housing_data.csv")
    df = df[(df["price"] > 0) & (df["price"] <= 3_000_000)]

    dom_buckets = {
        "Under 2 weeks":             (0,   13),
        "2 weeks - 1 month":         (14,  30),
        "1 - 3 months":              (31,  90),
        "3 - 6 months":              (91,  180),
        "6+ months":                 (181, 9999),
    }
    hoa_buckets = {
        "No HOA":                    (0,   0),
        "Low ($1-$100/mo)":          (1,   100),
        "Moderate ($101-$300/mo)":   (101, 300),
        "High ($301-$600/mo)":       (301, 600),
        "Premium ($600+/mo)":        (601, 99999),
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
def load_city_bounds():
    df = pd.read_csv("cleaning/cleaned_housing_data.csv")
    df = df[(df["price"] > 0) & (df["price"] <= 3_000_000)].copy()
    df["city"] = df["city"].str.strip().str.lower().str.title()

    acres_bounds, year_min, prop_types_by_city = {}, {}, {}
    for city, grp in df.groupby("city"):
        if len(grp) < 10:
            continue

        acres_grp = grp[(grp["acres"] >= 0) & (grp["acres"] <= 100)]
        if len(acres_grp) >= 10:
            lo = round(float(acres_grp["acres"].quantile(0.02)) * 10) / 10
            hi = round(float(acres_grp["acres"].quantile(0.98)) * 10) / 10
            if hi <= lo:
                hi = lo + 1.0
            acres_bounds[city] = (max(0.0, lo), hi)

        year_grp = grp[(grp["year_built"] >= 1800) & (grp["year_built"] <= 2026)]
        if len(year_grp) >= 10:
            year_min[city] = int(year_grp["year_built"].quantile(0.15))

        available = [t for t in ALL_PROP_TYPES if (grp["property_type"] == t).sum() >= 5]
        prop_types_by_city[city] = available if available else ALL_PROP_TYPES

    return acres_bounds, year_min, prop_types_by_city


@st.cache_data
def load_constraints():
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


def predict(model, X_input, sqft):
    log_price = model.predict(X_input)[0]
    price = np.expm1(log_price)
    return price, price / sqft


features_property = [
    "city_encoded", "beds", "baths", "square_feet", "acres", "year_built",
    "days_on_market", "hoa_per_month",
    "property_type_Townhouse", "property_type_Condo", "property_type_Single Family",
    "property_type_Multi-Family", "property_type_Ranch",
]

st.title("Virginia Home Price Predictor")


city_options = sorted(city_mapping.keys())
city = st.selectbox("Select a Virginia City", options=[""] + city_options)

if city:
    st.warning("Slider ranges are data-driven from Virginia listings. Values may snap if the combination is atypical for the selected city.", icon="⚠️")

if city and city in city_mapping:
    city_encoded = city_mapping[city]
    baths_max_by_beds, sqft_typical, sqft_by_beds, sqft_by_baths = load_constraints()
    dom_avgs, hoa_avgs = load_bucket_averages()
    acres_bounds, year_min_by_city, prop_types_by_city = load_city_bounds()

    acres_lo, acres_hi = acres_bounds.get(city, (0.0, 10.0))
    acres_default = round(min(max(0.25, acres_lo), acres_hi) * 10) / 10
    year_lo = year_min_by_city.get(city, 1900)
    year_hi = 2026
    city_prop_types = prop_types_by_city.get(city, ALL_PROP_TYPES)

    for k, v in [("va_baths", 2.0), ("va_beds", 3), ("va_sqft", 1_500),
                 ("va_acres", acres_default), ("va_year", 2005)]:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.get("_last_city") != city:
        st.session_state["va_acres"] = acres_default
        st.session_state["va_year"] = max(2005, year_lo)
        st.session_state["_last_city"] = city

    @st.fragment
    def property_inputs():
        beds_cur  = int(st.session_state["va_beds"])
        baths_cur = float(st.session_state["va_baths"])
        sqft_cur  = int(st.session_state["va_sqft"])
        acres_cur = float(st.session_state["va_acres"])
        year_cur  = int(st.session_state["va_year"])

        baths_max = baths_max_by_beds.get(beds_cur, 8.0)
        if baths_cur > baths_max:
            st.session_state["va_baths"] = baths_max
            baths_cur = baths_max

        sqft_lo, sqft_hi = get_sqft_range(beds_cur, baths_cur, sqft_typical, sqft_by_beds, sqft_by_baths)
        if sqft_cur > sqft_hi:
            st.session_state["va_sqft"] = sqft_hi
        elif sqft_cur < sqft_lo:
            st.session_state["va_sqft"] = sqft_lo

        if acres_cur < acres_lo:
            st.session_state["va_acres"] = acres_lo
        elif acres_cur > acres_hi:
            st.session_state["va_acres"] = acres_hi

        if year_cur < year_lo:
            st.session_state["va_year"] = year_lo

        col_beds, col_baths = st.columns(2)
        with col_beds:
            beds = st.slider("Bedrooms", 1, 8, step=1, key="va_beds")
        with col_baths:
            baths = st.slider("Bathrooms", 1.0, 8.0, step=0.5, key="va_baths")

        sqft = st.slider("Square Feet", 200, 10_000, step=100, key="va_sqft")

        col_acres, col_year, col_prop = st.columns(3)
        with col_acres:
            acres = st.slider("Acres", acres_lo, acres_hi, step=0.1, key="va_acres")
        with col_year:
            year_built = st.slider("Year Built", year_lo, year_hi, step=1, key="va_year")
        with col_prop:
            prop_type = st.selectbox("Property Type", city_prop_types)

        col_dom, col_hoa = st.columns(2)
        with col_dom:
            dom_label = st.selectbox("Days on Market", list(dom_avgs.keys()), index=1)
            days_on_market = dom_avgs[dom_label]
        with col_hoa:
            hoa_label = st.selectbox("HOA per Month", list(hoa_avgs.keys()), index=0)
            hoa = hoa_avgs[hoa_label]

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
        price, ppsf = predict(model, X_input, sqft)

        st.divider()
        col_price, col_ppsf = st.columns(2)
        with col_price:
            st.metric("Predicted Price", f"${price:,.0f}")
        with col_ppsf:
            st.metric("Price per sqft", f"${ppsf:,.0f} / sqft")

    property_inputs()
