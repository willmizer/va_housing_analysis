SELECT * FROM housing_data;

-- Create table for importing data
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
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/all_corrected_listings.csv'
INTO TABLE housing_data
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

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
SET property_type = REPLACE(property_type, "Multi-Family (2-4 Unit)", "Multi-Familty");

UPDATE housing_data
SET property_type = REPLACE(property_type, "Condo/Co-op", "Condo");

UPDATE housing_data
SET property_type = REPLACE(property_type, "Multi-Family (5+ Unit)", "Large Multi-Familty");
--

-- remove unwanted values from status
SELECT DISTINCT status
FROM housing_data;

DELETE FROM housing_data
WHERE status = "Off Market";

