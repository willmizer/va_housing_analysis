# Virginia Housing Market Analysis & Prediction

This project provides a complete end-to-end pipeline for collecting, cleaning, analyzing, and modeling housing data from Virginia, sourced from Redfin. The primary goal is to build a system that helps identify desirable and cost-efficient housing options based on user preferences, and to predict home prices based on property dimensions. Users can input details such as square footage, number of beds and baths, and receive an estimated price that reflects current market conditions.

## Table of Contents

1. [Project Overview](#project-overview)  
2. [Files Included](#files-included)  
3. [Workflow Summary](#workflow-summary)  
4. [Prediction Approach](#prediction-approach)  
5. [Key Results](#key-results)  
6. [Future Improvements](#future-improvements)

## Project Overview

This project combines web scraping, SQL cleaning, exploratory data analysis, and machine learning to uncover patterns in Virginia housing listings and generate recommendations based on predicted value. 

It includes:

- Automated scraping of Redfin listings 
- Cleaning and structuring raw data using SQL
- In-depth EDA to guide modeling decisions
- A regression model to predict housing value by price per square foot

## Files Included

| File                        | Description                                                                                     |
| --------------------------- | ----------------------------------------------------------------------------------------------- |
| `housing_scrape.py`         | Scrapes housing listings from Redfin using city IDs. Saves full listing data to CSV.            |
| `xml_city_ids.py`           | Extracts and parses city IDs from Redfin’s XML sitemap for use in scraping.                     |
| `updated_housing_clean.sql` | SQL script for cleaning the scraped data before analysis.                                       |
| `housing_data_eda.ipynb`    | Jupyter notebook that performs exploratory data analysis on cleaned housing data.               |
| `ml_modeling.ipynb`         | Preps , builds and evaluates a Random Forest regression model to predict price per square foot. |

## Workflow Summary

### 1. Scraping

- City-specific listing data is collected via Redfin’s public GIS API using city IDs pulled from a compressed XML sitemap.
- Data includes attributes like address, price, beds, baths, square footage, lot size, year built, property type, and listing URL.

### 2. Cleaning (SQL)

- Loaded into a MySQL table and cleaned using SQL:
  - Removed duplicates and entries with missing or invalid data
  - Standardized property types
  - Converted all fields to appropriate types (e.g., price to `INT`, acres to `DOUBLE`)
  - Added an auto-increment primary key

### 3. Exploratory Data Analysis (Python [pandas,numpy,seaborn and matplotlib])

- Visualized price trends by city, property type, and size
- Identified feature correlations and outliers
- Segregated land-only listings from residential listings due to distinct characteristics

### 4. Machine Learning Modeling(Python [Random Forest Regressor and scikit-learn])

- Focused on predicting `price_per_sqft` for residential properties
- Applied log transformation to normalize the target
- Encoded cities based on average price/sqft to improve location representation
- Trained a Random Forest Regressor using engineered features

## Prediction Approach

A prediction function was developed that:

- Accepts user-defined preferences (beds, baths, square footage, acreage)
- Ranks and filters listings to show top value-matching options

This enables the system to recommend homes that deliver strong value relative to their size, type, and location.

## Key Results

- Initial model had a ±$180 error in predicting price per square foot.
- After city encoding and log transformation, error was reduced to ±$37.52.
- Most influential features: square footage, number of baths, city-encoded price, and property type.
- Modeling `price_per_sqft` helped normalize across property sizes and improve model interpretability.

## Future Improvements

- Add a secondary model to predict total home price directly (using `log(price)`).
- Integrate external datasets (e.g., school ratings, crime stats, walk scores).
- Build a user interface to allow real-time filtering and comparison.
- Build a price predicting function for users trying to sell or see house value


