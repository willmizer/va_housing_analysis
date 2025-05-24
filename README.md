# Housing Market Data Project

This project collects, cleans, analyzes, and models real estate data to explore housing market trends and build predictive models for property attributes like pricing or land classification.

---

## Main question/Idea

- How can we help homebuyers in Virginia find their ideal home faster?
- Highlighting impact such as (model reduced search time by 40% for a simulated user profile)
- evaluate model and discuss improvements/different methods
- Predicting price or ranking homes based on value
- Recommending homes based on features like beds, baths, HOA, property_type
- Identifying “good deals” based on price_per_sqft vs. similar properties
## Purpose

The primary objectives of this project are to:


- Scrape housing data from public listing sources
- Clean and normalize the collected data
- Explore market trends through data analysis and visualization
- Train machine learning models to predict housing characteristics
- Build a scalable data pipeline for future housing data tasks

---

## Web Scraping

- **Source**: Redfin city listing pages
- **Tools**: requests, pandas 
- **Approach**:
  - Scrape listings by city ID from sitemap
  - Traverse paginated listing pages until no new results
- **Data Fields Collected**:
  - Address
  - Price
  - Number of bedrooms and bathrooms
  - Square footage
  - Lot size (acres)
  - HOA fee
  - Garage count
  - Pool presence
  - Land flag (if no structure data is present)

- **Output**: `all_scraped_listings.csv`
  
- (example output image)
  
--- 

## Data Cleaning

- Remove duplicate listings and cities
- Standardize fields (e.g., convert text-based square footage and prices to numeric)
- Extract structured info from messy fields (e.g., garage counts, HOA fees)
- Handle missing values and inconsistent formats
- Add derived columns (`is_land`, more)

---

## Exploratory Data Analysis (EDA)

Using pandas and visualization libraries, we explore:

- Price distribution by region and property type
- Relationships between price, square footage, and number of rooms
- City-level comparisons of median prices
- Land-only vs residential property trends

---

## Machine Learning

- Add later

---

## Project Structure

- Add later
