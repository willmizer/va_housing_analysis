import requests
import csv
import pandas as pd
from io import StringIO

# load the list of cities 
cities_df = pd.read_csv(r"C:\Users\willm\Desktop\housing_project\scraping\unique_city_ids.csv")
cities_df = cities_df[["city_name", "city_id"]].dropna().drop_duplicates()

# output file path 
output_file = r"C:\Users\willm\Desktop\housing_project\all_corrected_listings.csv"

# column headers to write into the CSV
fieldnames = [
    "address", "city", "beds", "baths", "price", "status",
    "square_feet", "acres", "year_built", "days_on_market",
    "property_type", "hoa_per_month", "url"
]

# create the CSV file and write the header row
with open(output_file, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

# loop through each city in the CSV
for _, row in cities_df.iterrows():
    city_name = row["city_name"]
    region_id = int(row["city_id"])
    region_type = 6  # redfin code for city
    market = "va"
    max_per_page = 100  # max results per page
    start = 0  

    print(f"Scraping {city_name}...")

    # paginate through all pages 
    while True:
        # api request
        url = (
            f"https://www.redfin.com/stingray/api/gis-csv?"
            f"al=1&market={market}&num_homes={max_per_page}&region_id={region_id}"
            f"&region_type={region_type}&status=9&uipt=1,2,3,4,5,6&v=8&start={start}"
        )

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed request for {city_name} (status code {response.status_code})")
                break

            # parse csv into rows
            rows = list(csv.DictReader(StringIO(response.text)))
            if not rows:
                break  # no more listings to process

            # add listing to csv
            with open(output_file, "a", newline='', encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)

                for listing in rows:
                    # convert lot size which is in sq_ft to acres
                    lot_size = listing.get("LOT SIZE")
                    try:
                        sqft = float(lot_size)
                        acres = round(sqft / 43560, 2)
                    except:
                        acres = "N/A"

                    # writing one listing to csv
                    writer.writerow({
                        "address": listing.get("ADDRESS", "N/A") or "N/A",
                        "city": listing.get("CITY", city_name),
                        "beds": listing.get("BEDS", "N/A") or "N/A",
                        "baths": listing.get("BATHS", "N/A") or "N/A",
                        "price": listing.get("PRICE", "N/A") or "N/A",
                        "status": listing.get("STATUS", "N/A") or "N/A",
                        "square_feet": listing.get("SQUARE FEET", "N/A") or "N/A",
                        "acres": acres,
                        "year_built": listing.get("YEAR BUILT", "N/A") or "N/A",
                        "days_on_market": listing.get("DAYS ON MARKET", "N/A") or "N/A",
                        "property_type": listing.get("PROPERTY TYPE", "N/A") or "N/A",
                        "hoa_per_month": listing.get("HOA/MONTH", "N/A") or "N/A",
                        "url": listing.get(
                            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
                            ""
                        ) or "N/A"
                    })

            print(f"{len(rows)} listings added (start={start})")

            # < than full page then reached end
            if len(rows) < max_per_page:
                break

            # go to next page
            start += max_per_page

        except Exception as e:
            print(f"skipping {city_name} ID: {region_id} due to error: {e}")
            break

print("saved all listings")
