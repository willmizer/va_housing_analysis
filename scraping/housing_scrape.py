import pandas as pd
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# input/output paths
city_ids_file = r"C:\Users\willm\Desktop\housing_project\unique_city_ids.csv"
output_file = r"C:\Users\willm\Desktop\housing_project\all_scraped_listings.csv"

# setup selenium
options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
options.add_argument("--disable-webgl")
options.add_argument("--no-sandbox")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
options.page_load_strategy = 'eager'
driver = webdriver.Chrome(options=options)

# load city ids
df_ids = pd.read_csv(city_ids_file).drop_duplicates(subset=["city_id", "city_name"])

# load previous output
try:
    df_existing = pd.read_csv(output_file)
    scraped_ids = set(df_existing["city_id"].astype(str))
except FileNotFoundError:
    df_existing = pd.DataFrame()
    scraped_ids = set()

all_data = []

def parse_listings(cards, city_id, city_name):
    listings = []

    for card in cards:
        try:
            address = card.get_attribute("title").strip()
            summary = card.get_attribute("aria-label").lower()
            beds = baths = "N/A"
            for part in summary.split(","):
                if "bed" in part:
                    beds = part.strip().replace("beds", "").replace("bed", "").strip()
                if "bath" in part:
                    baths = part.strip().replace("baths", "").replace("bath", "").strip()

            try:
                price = card.find_element(By.CSS_SELECTOR, "span.bp-Homecard__Price--value").text.strip()
            except:
                price = "N/A"

            try:
                sqft = card.find_element(By.CSS_SELECTOR, "span.bp-Homecard__LockedStat--value").text.strip()
            except:
                sqft = "-"

            acres = hoa = garages = "N/A"
            pool = False
            keyfacts = card.find_elements(By.CSS_SELECTOR, "span.KeyFacts-item")
            for fact in keyfacts:
                text = fact.text.lower().strip()
                if "acre" in text:
                    acres = text
                elif "hoa" in text:
                    hoa = text
                elif "garage" in text:
                    match = re.search(r"\d+", text)
                    if match:
                        garages = match.group()
                elif "pool" in text:
                    pool = True

            land = beds == "N/A" and baths == "N/A"

            href = card.get_attribute("href")
            listing_url = f"https://www.redfin.com{href}" if href else "N/A"

            listings.append({
                "address": address,
                "price": price,
                "bed": beds,
                "bath": baths,
                "sq_ft": sqft,
                "acres": acres,
                "hoa": hoa,
                "garages": garages,
                "pool": pool,
                "land": land,
                "city_id": city_id,
                "city_name": city_name,
                "url": listing_url
            })
        except Exception as e:
            print(f"  error parsing listing: {e}")
    return listings

# loop through all cities
for _, row in df_ids.iterrows():
    city_id = str(row["city_id"]).strip()
    city_name = str(row["city_name"]).strip().replace(" ", "-")

    if city_id in scraped_ids:
        print(f"skipping already scraped city_id: {city_id}")
        continue

    base_url = f"https://www.redfin.com/city/{city_id}/VA/{city_name}"
    print(f"\nscraping: {base_url}")
    first_sig = None

    for page in range(1, 100):
        url = base_url if page == 1 else f"{base_url}/page-{page}"
        print(f"  visiting: {url}")
        try:
            driver.get(url)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-rf-test-name='basicNode-homeCard']"))
            )
            cards = driver.find_elements(By.CSS_SELECTOR, "a[data-rf-test-name='basicNode-homeCard']")
            if not cards:
                print("  no listings found, stopping pagination")
                break

            sig = cards[0].get_attribute("title")
            if first_sig is None:
                first_sig = sig
            elif sig == first_sig:
                print("  repeated first listing — stopping")
                break

            listings = parse_listings(cards, city_id, row["city_name"])
            all_data.extend(listings)

        except Exception as e:
            print(f"  failed to load page: {e}")
            break

driver.quit()

# save results
df_new = pd.DataFrame(all_data)
df_final = pd.concat([df_existing, df_new], ignore_index=True)
df_final.to_csv(output_file, index=False)

print(f"\nfinished scraping {len(df_ids)} cities")
print(f"total listings scraped this run: {len(df_new)}")
print(f"total listings saved: {len(df_final)}")
print(f"output saved to: {output_file}")
