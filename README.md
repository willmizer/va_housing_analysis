# Virginia Housing Market Analysis & Prediction

This project provides a complete end-to-end pipeline for collecting, cleaning, analyzing, and modeling housing data from Virginia, sourced from Redfin. The primary goal is to build a system that helps identify desirable and cost-efficient housing options based on user preferences, and to predict home prices based on property dimensions. Users can input details such as square footage, number of beds and baths, and receive an estimated price that reflects current market conditions.


## Code Files Included

| File                        | Description                                                                                     |
| --------------------------- | ----------------------------------------------------------------------------------------------- |
| `housing_scrape.py`         | Scrapes housing listings from Redfin using city IDs. Saves full listing data to CSV.            |
| `xml_city_ids.py`           | Extracts and parses city IDs from Redfin’s XML sitemap for use in scraping.                     |
| `updated_housing_clean.sql` | SQL script for cleaning the scraped data before analysis.                                       |
| `housing_data_eda.ipynb`    | Jupyter notebook that performs exploratory data analysis on cleaned housing data.               |
| `ml_modeling.ipynb`         | Preps , builds and evaluates a Random Forest regression model to predict price per square foot. |


## Table of Contents

1. [Project Overview](#project-overview)  
2. [Files Included](#files-included)  
3. [Workflow Summary](#workflow-summary)  
4. [Prediction Approach](#prediction-approach)  
5. [Key Results](#key-results)  
6. [Future Improvements](#future-improvements)

## Project Overview

In this project I combined the power of web scraping, SQL cleaning, exploratory data analysis, and machine learning to try and predict patterns in Virginia housing listings and generate recommendations with value-based predictions. As the housing market grows more and more unpredictable, a tool to predict available houses with good value, and pricing info will allow users identify high-value properties and make more informed decisions when navigating Virginia's real estate landscape.

It includes:

- Automated scraping of Redfin listings 
- Cleaning and structuring raw data using SQL
- In-depth EDA to help guide modeling decisions
- A regression model to identify high-value housing options based on price per square foot
- A model to predict VA housing pricing given standard user housing information (beds, baths, sqft, acres etc.)
- A Streamlit GUI that allows users to easily and effortlessly predict housing prices


## Workflow Summary

### Part 1: Web Scraping Virginia Housing Listings 
The first stage of the project was focused on collecting housing data from Redfin by automating a two-step scraping workflow:

**Step 1: Extracting Unique Virginia City IDs (xml_city_ids.py)**
- To dynamically target every city with housing data in Virginia, I scraped the Redfin sitemap XML:

**Why**: This avoids hardcoding city names and ensures scalability across all current listings(this can be scaled to all cities in USA for example).

I parsed the XML sitemap to extract:

- The Redfin city ID (needed for API queries)

- City names for logging

- Corresponding URLs

**Output Ex**: 

| city_name     | city_id | url                                                       |
| ------------- | ------- | ---------------------------------------------------------- |
| Abbs Valley   | 37317   | https://www.redfin.com/city/37317/VA/Abbs-Valley          |
| Abingdon      | 22      | https://www.redfin.com/city/22/VA/Abingdon                |
| Accomac       | 28      | https://www.redfin.com/city/28/VA/Accomac                 |
| Aden          | 29022   | https://www.redfin.com/city/29022/VA/Aden                 |
| Adwolf        | 21132   | https://www.redfin.com/city/21132/VA/Adwolf               |


**Step 2: Scraping Listing Data by City (housing_scrape.py)**
Using the city ID list, I queired RedFins main site to collect detailed housing listings:

Queried each city using city_id and region_type=6 (Redfin's code for city search).

Paginated results using start and max_per_page=100 to retrieve all data available per city.

Key fields extracted included:

Address, city, price, beds, baths, square footage, lot size (converted to acres), year built, and property type.

The API only provides lot size in square feet, but acreage is more intuitive when dealing with land analysis.

Data handling considerations:

Fallbacks for missing fields ("N/A" defaults) to keep consistency

CSV output streamed in chunks for memory efficiency (all_corrected_listings.csv)

**Output Ex**:

| address               | city        | price   | acres | days_on_market | property_type           | url                                                                                   |
|-----------------------|-------------|---------|--------|----------------|--------------------------|----------------------------------------------------------------------------------------|
| 000 James St          | Bluefield   | 31500   | 1.36   | 41             | Vacant Land              | https://www.redfin.com/VA/Bluefield/James-St-24605/home/188951533                    |
| 0 Tyler St            | Abbs Valley | 25000   | N/A    | 41             | Vacant Land              | https://www.redfin.com/VA/Abbs-Valley/Tyler-St-24605/home/195316922                  |
| 19510 Wynscape Dr     | Abingdon    | 470000  | 0.45   | 7              | Single Family Residential| https://www.redfin.com/VA/Abingdon/19510-Wynscape-Dr-24210/home/133101574            |
| 16319 Mary St         | Abingdon    | 285000  | 0.53   | 4              | Single Family Residential| https://www.redfin.com/VA/Abingdon/16319-Mary-St-24210/home/133134572                |
| 15497 Porterfield Hwy | Abingdon    | 459900  | 1.07   | 4              | Single Family Residential| https://www.redfin.com/VA/Abingdon/15497-Porterfield-Hwy-24210/home/133033950        |

### **Scraping Overview**
The initial version of the scraper used Selenium and BeautifulSoup to navigate and extract listing data, but due to high latency and page load times, I transitioned to using requests with Redfin’s sitemap-based XML city IDs and their internal API. This optimization reduced total runtime from nearly 2 hours to under 10 minutes(saving approximately 92% of scraping time) for collecting data across all Virginia cities. This speed up of scraping time allows the program to become more scalable so in the future I can scale to the entire USA or multiple states etc.


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


