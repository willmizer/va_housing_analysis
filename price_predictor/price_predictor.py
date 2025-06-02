import streamlit as st
import numpy as np
import pandas as pd
import bz2
import pickle

# Helper function to decompress and load a pickle file
@st.cache_resource
def decompress_pickle(file):
    with bz2.BZ2File(file, "rb") as f:
        return pickle.load(f)

# Load the trained model and city mapping dictionary
model = decompress_pickle("price_predictor/model_price.pbz2")
city_mapping = decompress_pickle("price_predictor/city_mapping.pbz2")

# Feature columns expected by the model
features_property = [
    "city_encoded", "beds", "baths", "square_feet", "acres", "year_built",
    "days_on_market", "hoa_per_month",
    "property_type_Townhouse", "property_type_Condo", "property_type_Single Family",
    "property_type_Multi-Family", "property_type_Ranch"
]

# Streamlit app title
st.title("Virginia Home Price Predictor")

# Get user input for city
city = st.text_input("Enter a Virginia City",value = "Richmond").strip().lower().capitalize()
if city not in city_mapping:
    st.error("Invalid city name. Please try again.")
    st.stop()

city_encoded = city_mapping[city]

# Get user inputs for model features
beds = st.slider("Bedrooms", 1, 10, 2)
baths = st.slider("Bathrooms", 1, 10, 2)
sqft = st.number_input("Square Feet", min_value=200, max_value=10000, value=1500)
acres = st.number_input("Acres", min_value=0.0, value=0.25)
year_built = st.number_input("Year Built", min_value=1800, value=2005)
days_on_market = st.number_input("Days on Market", min_value=0, value=14)
hoa = st.number_input("HOA per Month", min_value=0, value=50)
prop_type = st.selectbox("Property Type", ["Single Family", "Townhouse", "Condo", "Multi-Family", "Ranch"])

# Construct input features for prediction
input_data = {
    "city_encoded": city_encoded,
    "beds": beds,
    "baths": baths,
    "square_feet": sqft,
    "acres": acres,
    "year_built": year_built,
    "days_on_market": days_on_market,
    "hoa_per_month": hoa,
    "property_type_Townhouse": 1 if prop_type == "Townhouse" else 0,
    "property_type_Condo": 1 if prop_type == "Condo" else 0,
    "property_type_Single Family": 1 if prop_type == "Single Family" else 0,
    "property_type_Multi-Family": 1 if prop_type == "Multi-Family" else 0,
    "property_type_Ranch": 1 if prop_type == "Ranch" else 0,
}

X_input = pd.DataFrame([input_data], columns=features_property)

# Predict log price and convert back to actual price
log_price = model.predict(X_input)[0]
price = np.expm1(log_price)

# Display the predicted price
st.success(f"Predicted Home Price: ${price:,.2f}")
