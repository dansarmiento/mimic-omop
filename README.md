# MIMIC-OMOP

This repository contains an Extract-Transform-Load (ETL) process for mapping the [MIMIC-III database](mimic.physionet.org) to the [OMOP Common Data Model](https://github.com/OHDSI/CommonDataModel). This process involves both transforming the structure of the database (i.e. the relational schema), but also standardizing the many concepts in the MIMIC-III database to a standard vocabulary (primarily the [Athena Vocabulary](https://www.ohdsi.org/analytic-tools/athena-standardized-vocabularies/), which you can explore [here](athena.ohdsi.org)).

## Table of Contents

- [Project Description](#project-description)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Set Up Database and Environment Variables](#step-2-set-up-database-and-environment-variables)
  - [Step 3: Build the OMOP Common Data Model (CDM)](#step-3-build-the-omop-common-data-model-cdm)
  - [Step 4: Download and Load the Athena Vocabularies](#step-4-download-and-load-the-athena-vocabularies)
  - [Step 5: Prepare the MIMIC-III Data](#step-5-prepare-the-mimic-iii-data)
  - [Step 6: Run the ETL Process](#step-6-run-the-etl-process)
  - [Step 7: Build Indexes and Constraints (Optional)](#step-7-build-indexes-and-constraints-optional)
- [Testing](#testing)
- [Documentation](#documentation)

## Project Description

This project provides a set of scripts to transform the MIMIC-III database into the OMOP Common Data Model (CDM). The MIMIC (Medical Information Mart for Intensive Care) database is a rich, publicly available dataset of de-identified health-related data of patients who stayed in critical care units. The OMOP CDM is a standard data model for observational health data, which allows for the systematic analysis of disparate observational databases.

By transforming MIMIC-III to the OMOP CDM, this project makes it possible to use the analytical tools developed by the OHDSI (Observational Health Data Sciences and Informatics) community to analyze the MIMIC-III dataset.

## Prerequisites

Before you begin, ensure you have the following software installed on your system:

*   **Git**: For cloning the repository. You can download it from [git-scm.com](https://git-scm.com/).
*   **PostgreSQL**: The database for storing both the MIMIC-III and OMOP data. Version 9.6 or higher is required. You can download it from [postgresql.org](https://www.postgresql.org/).
*   **Python**: While most scripts are in SQL and R, Python is useful for data manipulation and future automation. You can download it from [python.org](https://www.python.org/).
*   **R**: Used for loading some of the concept tables. You can download it from [r-project.org](https://www.r-project.org/).
    *   You will also need to install the `remotes` and `RPostgres` R packages. You can do this by running the following commands in an R console:
        ```R
        install.packages("remotes")
        remotes::install_github("r-dbi/RPostgres")
        ```
*   **pgTap**: A testing framework for PostgreSQL, used to verify the ETL process. You can find installation instructions on [pgtap.org](http://pgtap.org/).

You will also need to have the MIMIC-III database installed in your PostgreSQL instance. For instructions on how to do this, please refer to the official MIMIC documentation: [https://mimic.physionet.org/gettingstarted/dbsetup/](https://mimic.physionet.org/gettingstarted/dbsetup/).

## Getting Started

This guide provides a step-by-step process for setting up the MIMIC-OMOP database.

### Step 1: Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/dansarmiento/mimic-omop.git
cd mimic-omop
```

### Step 2: Set Up Database and Environment Variables

This project uses environment variables to configure the database connections. These variables make it easier to run the scripts without hardcoding connection details.

Open a terminal and define the following environment variables. Replace the values with your actual database connection details. It is assumed that you have a PostgreSQL user with permissions to create schemas and tables.

```bash
# The name of the schema for the OMOP CDM
export OMOP_SCHEMA='omop'

# The name of the schema where MIMIC-III is stored
export MIMIC_SCHEMA='mimiciii'

# Connection string for the OMOP schema
export OMOP_DB_URL='postgresql://user:password@host:port/dbname'

# Connection string for the MIMIC schema
export MIMIC_DB_URL='postgresql://user:password@host:port/dbname'
```

**Note:** The original scripts used a `psql` specific connection string format. The format above is more standard, but you may need to adjust it for your specific setup. The rest of this guide will assume you have `psql` installed and configured to connect to your database. For example, by setting the `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` environment variables.

If you are using the `psql` command-line tool, you can define the connection strings as follows:

```bash
export OMOP_SCHEMA='omop'
export MIMIC_SCHEMA='mimiciii'
export OMOP="host=localhost dbname=postgres user=postgres options=--search_path=$OMOP_SCHEMA"
export MIMIC="host=localhost dbname=postgres user=postgres options=--search_path=$MIMIC_SCHEMA"
```

### Step 3: Build the OMOP Common Data Model (CDM)

The first step in the ETL process is to create the OMOP CDM schema and tables.

1.  **Clone the OHDSI CommonDataModel repository:**

    The DDL (Data Definition Language) scripts for the OMOP CDM are maintained in a separate repository. Clone it into the `mimic-omop` directory:

    ```bash
    git clone https://github.com/OHDSI/CommonDataModel.git
    cd CommonDataModel
    # We reset to a specific commit to ensure a consistent version of the DDL
    git reset --hard 0ac0f4bd56c7372dcd3417461a91f17a6b118901
    cd ..
    ```

2.  **Copy the DDL files:**

    Copy the PostgreSQL DDL files from the `CommonDataModel` repository to the `omop/build-omop/postgresql/` directory:

    ```bash
    cp CommonDataModel/PostgreSQL/*.txt omop/build-omop/postgresql/
    ```

3.  **Modify the DDL (Optional but Recommended):**

    For better performance during the ETL process, it's recommended to create the tables as `UNLOGGED`. This reduces the overhead of writing to the write-ahead log (WAL).

    ```bash
    sed -i 's/^CREATE TABLE \([a-z_]*\)/CREATE UNLOGGED TABLE \1/' "omop/build-omop/postgresql/OMOP CDM postgresql ddl.txt"
    ```

4.  **Create the OMOP schema and tables:**

    Now, run the DDL script to create the OMOP schema and tables in your database.

    ```bash
    psql "$OMOP" -c "DROP SCHEMA IF EXISTS $OMOP_SCHEMA CASCADE;"
    psql "$OMOP" -c "CREATE SCHEMA $OMOP_SCHEMA;"
    psql "$OMOP" -f "omop/build-omop/postgresql/OMOP CDM postgresql ddl.txt"
    ```

5.  **Alter table columns:**

    Some columns need to be altered to `text` type.

    ```bash
    psql "$OMOP" -f "omop/build-omop/postgresql/mimic-omop-alter.sql"
    ```

6.  **Add comments to the tables:**

    This script adds comments to the OMOP tables, which can be helpful for understanding the data model.

    ```bash
    psql "$OMOP" -f "omop/build-omop/postgresql/omop_cdm_comments.sql"
    ```

### Step 4: Download and Load the Athena Vocabularies

The OMOP CDM uses a set of standardized vocabularies, which can be downloaded from [Athena](https://athena.ohdsi.org/).

1.  **Download the vocabularies:**

    Go to [athena.ohdsi.org](https://athena.ohdsi.org/), select the vocabularies you need (e.g., SNOMED, LOINC, RxNorm), and download them as a zip file.

2.  **Extract and place the vocabulary files:**

    Extract the downloaded zip file. You should have a set of CSV files (e.g., `CONCEPT.csv`, `CONCEPT_RELATIONSHIP.csv`, etc.). Create a directory `extras/athena` and move these CSV files into it.

    ```bash
    mkdir -p extras/athena
    # Move the downloaded CSV files into extras/athena
    mv /path/to/your/vocabulary_files/*.csv extras/athena/
    ```

3.  **Load the vocabularies into the database:**

    Run the following script to load the vocabulary CSV files into the OMOP tables. This process may take a significant amount of time.

    ```bash
    psql "$OMOP" -f "omop/build-omop/postgresql/omop_vocab_load.sql"
    ```

### Step 5: Prepare the MIMIC-III Data

This step prepares the MIMIC-III data for the ETL process.

1.  **Create MIMIC-III concept IDs:**

    This script adds a `mimic_id` column to each table in the MIMIC-III schema. This ID is used to link the MIMIC data to the OMOP concepts.

    ```bash
    psql "$MIMIC" -f "mimic/build-mimic/postgres_create_mimic_id.sql"
    ```

2.  **Load manual mappings:**

    This project includes some manual mappings between MIMIC and OMOP concepts. These are loaded using an R script.

    First, create a configuration file named `mimic-omop.cfg` in the root of the repository with your database connection details:

    ```
    dbname=your_db_name
    user=your_db_user
    ```

    Then, run the R script:

    ```Rscript
    Rscript etl/ConceptTables/loadTables.R $MIMIC_SCHEMA
    ```

### Step 6: Run the ETL Process

Now you are ready to run the main ETL script. This script will populate the OMOP tables with data from the MIMIC-III database.

```bash
psql "$MIMIC" --set=OMOP_SCHEMA="$OMOP_SCHEMA" -f "etl/etl.sql"
```

This process can take a long time to complete, depending on the performance of your machine.

### Step 7: Build Indexes and Constraints (Optional)

After the ETL process is complete, you can build the indexes and constraints on the OMOP tables. This is done after the ETL to improve performance during the data loading phase.

```bash
psql "$OMOP" -f "omop/build-omop/postgresql/OMOP CDM postgresql indexes.txt"
psql "$OMOP" -f "omop/build-omop/postgresql/OMOP CDM postgresql constraints.txt"
```

## Testing

This project uses [pgTap](http://pgtap.org/), a testing framework for PostgreSQL, to verify that the ETL process has run correctly. The tests check for things like table existence, row counts, and data integrity.

### Step 1: Install pgTap

The method for installing pgTap depends on your operating system.

*   **Using a package manager (e.g., on Debian/Ubuntu):**

    ```bash
    sudo apt-get update
    sudo apt-get install pgtap
    ```

*   **From source:**

    If a package is not available for your system, you can build pgTap from source. You can find detailed instructions on the [pgTap website](http://pgtap.org/) and the [PGXN website](https://pgxn.org/dist/pgtap/).

### Step 2: Enable the pgTap Extension

Once pgTap is installed, you need to enable it as an extension in your PostgreSQL database. You only need to do this once per database.

```bash
psql "$MIMIC" -c "CREATE EXTENSION pgtap;"
```

**Note:** The command uses the `$MIMIC` environment variable, but you can run this on any database where you want to use pgTap. The tests in this project run against the MIMIC-III schema, so it's convenient to enable it there.

### Step 3: Run the Tests

After the ETL process is complete, you can run the test script:

```bash
psql "$MIMIC" -f "etl/check_etl.sql"
```

The script will output a series of test results in the [Test Anything Protocol (TAP)](https://testanything.org/) format. If all tests pass, you should see a summary line indicating that all tests were successful. If any tests fail, the output will provide details about the failures.

## Documentation

- [Resources](https://mit-lcp.github.io/mimic-omop/)
    - [Achilles](https://mit-lcp.github.io/mimic-omop/AchillesWeb)
    - [OMOP Data Model](https://mit-lcp.github.io/mimic-omop/schemaspy-omop)
    - [MIMIC Data Model](https://mit-lcp.github.io/mimic-omop/schemaspy-mimic)
