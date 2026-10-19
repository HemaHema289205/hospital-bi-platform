-- =====================================================================
--  HospitalFlow AI  -  Database schema  (Database Layer)
--  Works on MySQL 8+. For SQLite the loader creates the same tables
--  automatically, so you only need this file if you use MySQL.
--
--  Run:  mysql -u root -p < sql/schema.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS hospital_bi
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hospital_bi;

-- ---------------------------------------------------------- dimension
DROP TABLE IF EXISTS fact_procedures;
DROP TABLE IF EXISTS fact_conditions;
DROP TABLE IF EXISTS fact_encounters;
DROP TABLE IF EXISTS agg_daily_flow;
DROP TABLE IF EXISTS agg_department;
DROP TABLE IF EXISTS dim_patients;

CREATE TABLE dim_patients (
    PATIENT_ID           VARCHAR(64)  PRIMARY KEY,
    FULL_NAME            VARCHAR(120),
    FIRST                VARCHAR(60),
    LAST                 VARCHAR(60),
    BIRTHDATE            DATE,
    DEATHDATE            DATE NULL,
    AGE                  INT,
    AGE_BAND             VARCHAR(10),
    GENDER               CHAR(1),
    GENDER_LABEL         VARCHAR(10),
    MARITAL              VARCHAR(10),
    RACE                 VARCHAR(40),
    ETHNICITY            VARCHAR(40),
    CITY                 VARCHAR(80),
    STATE                VARCHAR(40),
    ZIP                  VARCHAR(12),
    HEALTHCARE_EXPENSES  DECIMAL(14,2),
    HEALTHCARE_COVERAGE  DECIMAL(14,2),
    IS_DECEASED          TINYINT,
    INDEX idx_patient_age   (AGE_BAND),
    INDEX idx_patient_gender(GENDER_LABEL)
);

-- -------------------------------------------------------------- facts
CREATE TABLE fact_encounters (
    ENCOUNTER_ID         VARCHAR(64) PRIMARY KEY,
    PATIENT_ID           VARCHAR(64),
    FULL_NAME            VARCHAR(120),
    AGE                  INT,
    AGE_BAND             VARCHAR(10),
    GENDER_LABEL         VARCHAR(10),
    ORGANIZATION         VARCHAR(64),
    DEPARTMENT           VARCHAR(60),
    ENCOUNTERCLASS       VARCHAR(30),
    DESCRIPTION          VARCHAR(200),
    REASONDESCRIPTION    VARCHAR(200),
    PAYER_NAME           VARCHAR(80),
    START                DATETIME,
    STOP                 DATETIME NULL,
    VISIT_DATE           DATE,
    DISCHARGE_DATE       DATE NULL,
    YEAR                 INT,
    MONTH                INT,
    DAY_OF_WEEK          INT,
    DAY_NAME             VARCHAR(12),
    HOUR                 INT,
    IS_WEEKEND           TINYINT,
    IS_ADMISSION         TINYINT,
    IS_EMERGENCY         TINYINT,
    LENGTH_OF_STAY       DECIMAL(8,2),
    STAY_HOURS           DECIMAL(10,2),
    WAIT_MINUTES         INT,
    STATUS               VARCHAR(20),
    BASE_ENCOUNTER_COST  DECIMAL(12,2),
    TOTAL_CLAIM_COST     DECIMAL(12,2),
    PAYER_COVERAGE       DECIMAL(12,2),
    OUT_OF_POCKET        DECIMAL(12,2),
    INDEX idx_enc_date  (VISIT_DATE),
    INDEX idx_enc_dept  (DEPARTMENT),
    INDEX idx_enc_class (ENCOUNTERCLASS),
    INDEX idx_enc_adm   (IS_ADMISSION),
    CONSTRAINT fk_enc_patient FOREIGN KEY (PATIENT_ID) REFERENCES dim_patients(PATIENT_ID)
);

CREATE TABLE fact_conditions (
    START         DATE,
    STOP          DATE NULL,
    PATIENT_ID    VARCHAR(64),
    ENCOUNTER_ID  VARCHAR(64),
    CODE          VARCHAR(40),
    DESCRIPTION   VARCHAR(200),
    IS_ACTIVE     TINYINT,
    INDEX idx_cond_desc    (DESCRIPTION),
    INDEX idx_cond_patient (PATIENT_ID)
);

CREATE TABLE fact_procedures (
    START         DATETIME,
    PATIENT_ID    VARCHAR(64),
    ENCOUNTER_ID  VARCHAR(64),
    CODE          VARCHAR(40),
    DESCRIPTION   VARCHAR(200),
    BASE_COST     DECIMAL(12,2),
    INDEX idx_proc_patient (PATIENT_ID)
);

-- --------------------------------------------------------- aggregates
CREATE TABLE agg_daily_flow (
    FLOW_DATE           DATE PRIMARY KEY,
    VISITS              INT,
    ADMISSIONS          INT,
    DISCHARGES          INT,
    EMERGENCY_CASES     INT,
    REVENUE             DECIMAL(14,2),
    AVG_WAIT_MINUTES    DECIMAL(8,1),
    AVG_LENGTH_OF_STAY  DECIMAL(8,2),
    DAY_OF_WEEK         INT,
    DAY_NAME            VARCHAR(12),
    MONTH               INT,
    WEEK_OF_YEAR        INT,
    IS_WEEKEND          TINYINT,
    BEDS_OCCUPIED       INT,
    BED_OCCUPANCY_PCT   DECIMAL(5,1)
);

CREATE TABLE agg_department (
    DEPARTMENT          VARCHAR(60) PRIMARY KEY,
    TOTAL_VISITS        INT,
    ADMISSIONS          INT,
    EMERGENCY_CASES     INT,
    AVG_LENGTH_OF_STAY  DECIMAL(8,2),
    AVG_WAIT_MINUTES    DECIMAL(8,1),
    REVENUE             DECIMAL(14,2),
    SHARE_PCT           DECIMAL(5,1)
);
