import pandas as pd
import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# file paths
city_ids_file = r"C:\Users\willm\Desktop\housing_project\unique_city_ids.csv"
output_file = r"C:\Users\willm\Desktop\housing_project\all_scraped_listings.csv"

# setup selenium headless
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

# load existing output if it exists
try:
    df_existing = pd.read_csv(output_file)
    scraped_ids = set(df_existing["city_id"].astype(str))
except FileNotFoundError:
    df_existing = pd.DataFrame()
    scraped_ids = set()

all_data = []

def parse_listings(html):
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    cards = soup.select("a[data-rf-test-name='basicNode-homeCard']")

    for card in cards:
        try:
            address = card.get("title", "").strip()
            summary = card.get("aria-label", "").lower()
            beds = baths = "N/A"
            for part in summary.split(","):
                if "bed" in part:
                    beds = part.strip().replace("beds", "").replace("bed", "").strip()
                if "bath" in part:
                    baths = part.strip().replace("baths", "").replace("bath", "").strip()

            price_tag = card.select_one("span.bp-Homecard__Price--value")
            price = price_tag.text.strip() if price_tag else "N/A"

            sqft_tag = card.select_one("span.bp-Homecard__LockedStat--value")
            sqft = sqft_tag.text.strip() if sqft_tag else "-"

            keyfacts = card.select("span.KeyFacts-item")
            acres = hoa = garages = "N/A"
            pool = False
            for fact in keyfacts:
                text = fact.get_text(strip=True).lower()
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
                "land": land
            })
        except Exception as e:
            print(f"  error parsing listing: {e}")
    return listings

# loop through each city
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
            time.sleep(2)
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("a[data-rf-test-name='basicNode-homeCard']")
            if not cards:
                print("  no listings found, stopping pagination")
                break

            sig = cards[0].get("title")
            if first_sig is None:
                first_sig = sig
            elif sig == first_sig:
                print("  repeated first listing — stopping")
                break

            listings = parse_listings(html)
            for listing in listings:
                listing["city_id"] = city_id
                listing["city_name"] = row["city_name"]
            all_data.extend(listings)

        except Exception as e:
            print(f"  failed to load page: {e}")
            break

# finalize
driver.quit()

# merge and save
df_new = pd.DataFrame(all_data)
df_final = pd.concat([df_existing, df_new], ignore_index=True)
df_final.to_csv(output_file, index=False)

print(f"\nfinished scraping. total listings saved: {len(df_final)}")
print(f"output saved to: {output_file}")
