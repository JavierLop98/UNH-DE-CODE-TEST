-- Snowflake DDL for UHC Transparency in Coverage tables.
-- The Python loader (06_load_to_snowflake.py) can auto-create these,
-- but having explicit DDL is better for version control and review.

CREATE OR REPLACE TABLE INDEX_FILES (
    INDEX_FILE_ID    NUMBER       COMMENT 'Auto-assigned ID for each parsed file',
    FILE_NAME        STRING       COMMENT 'Original filename from UHC API',
    LOCAL_PATH       STRING       COMMENT 'Path where JSON was saved locally',
    REPORTING_ENTITY_NAME STRING  COMMENT 'e.g. United-HealthCare-Services-Inc',
    REPORTING_ENTITY_TYPE STRING  COMMENT 'e.g. Third-Party Administrator',
    LAST_UPDATED_ON  STRING       COMMENT 'Date string from the JSON file',
    VERSION          STRING       COMMENT 'CMS schema version',
    PARSED_AT        STRING       COMMENT 'UTC timestamp when we parsed it'
);

CREATE OR REPLACE TABLE REPORTING_ENTITIES (
    INDEX_FILE_ID         NUMBER,
    REPORTING_ENTITY_NAME STRING,
    REPORTING_ENTITY_TYPE STRING,
    LAST_UPDATED_ON       STRING,
    VERSION               STRING
);

CREATE OR REPLACE TABLE PLANS (
    PLAN_KEY         STRING  COMMENT 'Composite key: indexId_structIdx_planIdx',
    INDEX_FILE_ID    NUMBER,
    PLAN_NAME        STRING  COMMENT 'e.g. Choice Plus, Core',
    PLAN_ID          STRING  COMMENT 'Usually an EIN',
    PLAN_ID_TYPE     STRING  COMMENT 'e.g. EIN',
    PLAN_MARKET_TYPE STRING  COMMENT 'e.g. group'
);

CREATE OR REPLACE TABLE REFERENCED_FILES (
    REFERENCED_FILE_KEY STRING  COMMENT 'Composite key: planKey_fileType_fileIdx',
    PLAN_KEY            STRING,
    INDEX_FILE_ID       NUMBER,
    FILE_TYPE           STRING  COMMENT 'in_network or allowed_amount',
    DESCRIPTION         STRING  COMMENT 'Human-readable description from JSON',
    LOCATION_URL        STRING  COMMENT 'URL to the actual rate file (.json.gz)'
);
