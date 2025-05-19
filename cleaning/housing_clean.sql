-- cleaning / standardization of housing data (using scraped data)
SELECT * FROM housing_data;

-- Create table for importing data
CREATE TABLE housing_data (
    address VARCHAR(255),
    price VARCHAR(50),
    bed VARCHAR(500),
    bath VARCHAR(25),
    sq_ft VARCHAR(20),
    acres VARCHAR(50),
    hoa VARCHAR(50),
    garages VARCHAR(10),
    pool VARCHAR(5),       
    land VARCHAR(5),       
    city_id VARCHAR(10),
    city_name VARCHAR(100),
    url TEXT
);

-- import data from uploads for an efficient import
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/all_scraped_listings.csv'
INTO TABLE housing_data
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- URLs have repeating items that need to be removed - used REPLACE statement and verified with LIKE
UPDATE housing_data
SET url = REPLACE(url, 'https://www.redfin.comhttps://www.redfin.com', 'https://www.redfin.com')
WHERE url LIKE 'https://www.redfin.comhttps://www.redfin.com%';

-- beds have weird values that need to be addressed
SELECT DISTINCT bed FROM housing_data;

-- addressing weird bed values 
SELECT * FROM housing_data
WHERE bed IN (
    'property at 6631 doo st',
    '44',
    'ford',
    'property at tbd aul rd unit n/a',
    'property at 1700 ford ave'
);

DELETE FROM housing_data
WHERE bed IN (
    'property at 6631 doo st',
    '44',
    'ford',
    'property at tbd aul rd unit n/a',
    'property at 1700 ford ave'
);

-- when scraping the website used — as a placeholder when acres were not mentioned in the listing so i replaced all values of — with N/A 
UPDATE housing_data
set sq_ft = REPLACE(sq_ft,"—", "N/A")
WHERE sq_ft LIKE "—";

-- Unknown is in place of price for some properties, I set it to null for eventual column change to int
UPDATE housing_data
set price = REPLACE(price,"Unknown", NULL)
WHERE price LIKE "Unknown";

-- after adjusting the "—" values I changed all N/A values to null for standardization
UPDATE housing_data SET bed = NULL WHERE bed = 'N/A';
UPDATE housing_data SET bath = NULL WHERE bath = 'N/A';
UPDATE housing_data SET sq_ft = NULL WHERE sq_ft = 'N/A';
UPDATE housing_data SET acres = NULL WHERE acres = 'N/A';
UPDATE housing_data SET hoa = NULL WHERE hoa = 'N/A';
UPDATE housing_data SET garages = NULL WHERE garages = 'N/A';
UPDATE housing_data SET url = NULL WHERE url = 'N/A';

-- standardizing price column so it is easier to work with as a int value
UPDATE housing_data
SET price = REPLACE(REPLACE(price, '$', ''), ',', '');

-- change price to int value
ALTER TABLE housing_data MODIFY price INT;

