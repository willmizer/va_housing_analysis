import requests
import xml.etree.ElementTree as ET
import pandas as pd

# sitemap URL and direct output path
sitemap_url = "https://www.redfin.com/sitemap_com_city_VA.xml.gz"
output_file = r"C:\Users\willm\Desktop\housing_project\unique_city_ids.csv"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# fetch XML content directly
response = requests.get(sitemap_url, headers=headers)
response.raise_for_status()
xml_content = response.content

# parse XML
root = ET.fromstring(xml_content)
ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# extract city entries
entries = []
for url in root.findall("ns:url", ns):
    loc = url.find("ns:loc", ns).text
    if "/city/" in loc:
        try:
            parts = loc.split("/")
            city_id = parts[4]
            city_name = parts[6].replace("-", " ")
            entries.append({
                "city_name": city_name.title(),
                "city_id": city_id,
                "url": loc
            })
        except Exception as e:
            print(f"error parsing: {loc} — {e}")

# convert to DataFrame and drop duplicates
df = pd.DataFrame(entries)
df = df.drop_duplicates().sort_values("city_name")

# save to CSV (assumes folder already exists)
df.to_csv(output_file, index=False)

print(df.head())
print(f"\nsaved {len(df)} unique virginia city entries to: {output_file}")
