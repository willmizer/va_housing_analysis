-- create table for importing data
CREATE TABLE housing_data (
    address VARCHAR(255),
    city VARCHAR(100),
    beds VARCHAR(20),
    baths VARCHAR(20),
    price VARCHAR(20),
    status VARCHAR(50),
    square_feet VARCHAR(20),
    acres VARCHAR(20),
    year_built VARCHAR(10),
    days_on_market VARCHAR(20),
    property_type VARCHAR(100),
    hoa_per_month VARCHAR(50),
    url VARCHAR(1000)
);

-- import data from uploads for an efficient import
LOAD DATA INFILE "C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/all_corrected_listings.csv"
INTO TABLE housing_data
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- removing duplicates throughout dataset 
CREATE TABLE housing_data_copy AS
SELECT DISTINCT *
FROM housing_data;

-- drop original
DROP TABLE housing_data;

-- switch name of copy to original
RENAME TABLE housing_data_copy TO housing_data;

-- delete all rows with non-existent addresses
DELETE FROM housing_data
WHERE address = "N/A";

-- standardize property types for easier analysis
SELECT DISTINCT property_type FROM housing_data;

-- parking isnt a housing option so remove unessisary rows 
DELETE FROM housing_data
WHERE property_type = "Parking";

-- standardize property types
UPDATE housing_data
SET property_type = REPLACE(property_type, "Single Family Residential", "Single Family");

UPDATE housing_data
SET property_type = REPLACE(property_type, "Vacant Land", "Land");

UPDATE housing_data
SET property_type = REPLACE(property_type, "Multi-Family (2-4 Unit)", "Multi-Family");

UPDATE housing_data
SET property_type = REPLACE(property_type, "Condo/Co-op", "Condo");

UPDATE housing_data
SET property_type = REPLACE(property_type, "Multi-Family (5+ Unit)", "Large Multi-Family");

-- remove unwanted values from status
SELECT DISTINCT status FROM housing_data;

DELETE FROM housing_data
WHERE status = "Off Market";

-- removes N/A in baths column
UPDATE housing_data
SET baths = NULL
WHERE baths = "N/A";

-- change baths to double
ALTER TABLE housing_data
MODIFY COLUMN baths DOUBLE;

-- removes N/A in beds column
UPDATE housing_data
SET beds = NULL
WHERE beds = "N/A";

-- change beds to double
ALTER TABLE housing_data
MODIFY COLUMN beds DOUBLE;

-- when price is N/A thier is no real address so i am removing all values 
DELETE FROM housing_data
WHERE price = "N/A";

-- change price to int
ALTER TABLE housing_data
MODIFY COLUMN price INT;

-- change square feet to null if value currently N/A
UPDATE housing_data
SET square_feet = NULL
WHERE square_feet = "N/A";

-- change square feet to int
ALTER TABLE housing_data
MODIFY COLUMN square_feet INT;

-- change acres to null if value currently N/A
UPDATE housing_data
SET acres = NULL
WHERE acres = "N/A";

-- change square feet to double
ALTER TABLE housing_data
MODIFY COLUMN acres DOUBLE;

-- change year built to null if value currently N/A
UPDATE housing_data
SET year_built = NULL
WHERE year_built = "N/A";

-- change year built to int
ALTER TABLE housing_data
MODIFY COLUMN year_built INT;

-- change days on market to null if value currently N/A
UPDATE housing_data
SET days_on_market = NULL
WHERE days_on_market = "N/A";

-- change days on market to int
ALTER TABLE housing_data
MODIFY COLUMN days_on_market INT;

-- change hoa to null if value currently N/A
UPDATE housing_data
SET hoa_per_month = NULL
WHERE hoa_per_month = "N/A";

-- change hoa to int
ALTER TABLE housing_data
MODIFY COLUMN hoa_per_month INT;

-- trim longer entries 
UPDATE housing_data SET address = TRIM(address);
UPDATE housing_data SET url = TRIM(url);

-- avoid creation of newlines in csv output
UPDATE housing_data
SET url = REPLACE(REPLACE(url, '\r', ''), '\n', '');


-- check for any more N/A values that i might have missed
SELECT * FROM housing_data
WHERE address = "N/A"
   OR city = "N/A"
   OR status = "N/A"
   OR property_type = "N/A"
   OR url = "N/A";

-- add a primary key to track rows uniquely
ALTER TABLE housing_data
ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST;

-- final preview
SELECT * FROM housing_data;
