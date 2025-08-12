# MIMIC-OMOP Local Setup Automation

This repository contains a streamlined, Python-based toolkit to build a local instance of the MIMIC-III database mapped to the OMOP Common Data Model. It automates the setup, data loading, and transformation process, making it significantly easier for researchers and developers to get started.

This project is a fork of the original [MIT-LCP/mimic-omop](https://github.com/MIT-LCP/mimic-omop) repository, refactored to be a standalone tool for local database creation.

## Project Goals

- **Simplicity**: To provide a simple, command-line-based approach to setting up a MIMIC-OMOP database.
- **Automation**: To automate as much of the setup and ETL process as possible, reducing manual steps.
- **Reproducibility**: To ensure that anyone can create a consistent version of the database using this toolkit.

---

## Running with Docker (Recommended)

Using Docker is the recommended way to run this project. It simplifies setup by providing a self-contained environment with all the necessary dependencies.

### 1. Prerequisites

- **Docker**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop) for your operating system.
- **MIMIC-III & OMOP Data**: You still need to acquire the MIMIC-III and OMOP Vocabulary data files as described in the manual setup.

### 2. Configure Docker Compose

Open the `docker-compose.yml` file and update the volume paths to point to your local data directories:

```yaml
services:
  etl:
    volumes:
      # ...
      # --- IMPORTANT ---
      # You MUST update the paths below to the absolute paths on your host machine.
      - /path/to/your/mimic-iii-clinical-database-1.4:/data/mimic-iii
      - /path/to/your/athena-vocabulary:/data/athena
```

### 3. Build and Run the Containers

Build and start the `postgres` and `etl` services in the background:

```bash
docker-compose up --build -d
```

### 4. Run the ETL Process

Once the containers are running, you can execute the ETL scripts inside the `etl` container.

First, open an interactive shell in the running container:

```bash
docker-compose exec etl bash
```

Now, from within the container's shell, run the scripts in order:

```bash
# Run the setup script (it will be fast as most setup is done by Docker)
python setup.py

# Run the main ETL script
python run_etl.py

# Run the validation script
python validate.py
```

### 5. Accessing the Database

The PostgreSQL database is exposed on port `5433` on your host machine. You can connect to it using any database client with the credentials from the `config.ini` file.

---

## Getting Started (Manual Setup)

Follow these steps if you prefer to set up your local MIMIC-OMOP database without Docker.

### 1. Prerequisites

Before you begin, ensure you have the following software installed and accessible from your command line:

- **Python 3.7+**: Required to run the automation scripts.
- **Git**: Required to clone this repository and its dependencies.
- **PostgreSQL 9.6+**: The database system where MIMIC and OMOP data will be stored. You must have a running PostgreSQL server.
- **MIMIC-III Clinical Data**: You must have access to the MIMIC-III Clinical Database files (version 1.4). You can request access via [PhysioNet](https://mimic.physionet.org/gettingstarted/access/).
- **OMOP Vocabulary**: You need to download the standardized vocabularies (e.g., SNOMED, LOINC, RxNorm) from [OHDSI Athena](https://athena.ohdsi.org/).

### 2. Clone the Repository

Start by cloning this repository to your local machine:

```bash
git clone https://github.com/dansarmiento/mimic-omop.git
cd mimic-omop
```

### 3. Install Python Dependencies

Install the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 4. Configure Your Setup

Create a configuration file by copying the example template:

```bash
cp config.example.ini config.ini
```

Now, open `config.ini` in a text editor and fill in your local details. This is a critical step.

**`[postgresql]` section:**
- `host`: The hostname or IP address of your PostgreSQL server (e.g., `localhost`).
- `port`: The port your PostgreSQL server is running on (e.g., `5432`).
- `user`: Your PostgreSQL username.
- `password`: Your PostgreSQL password.
- `database`: The name of the database to use. The `setup.py` script assumes this database already exists.
- `mimic_schema`: The name for the schema where the raw MIMIC-III data will be stored (e.g., `mimiciii`).
- `omop_schema`: The name for the schema where the final OMOP CDM data will be stored (e.g., `omop`).

**`[paths]` section:**
- `mimic_data`: The absolute path to the directory containing the unzipped MIMIC-III `.csv` files.
- `athena_vocab`: The absolute path to the directory containing the unzipped OMOP vocabulary `.csv` files you downloaded from Athena.

### 5. Run the Setup Script

The `setup.py` script prepares your environment. It checks prerequisites, clones the OMOP CommonDataModel repository, guides you through the vocabulary download, and creates the necessary database schemas.

```bash
python setup.py
```

The script will pause and ask you to confirm once you have downloaded the vocabularies from Athena and updated your `config.ini`.

### 6. Run the ETL Script

This is the main event. The `run_etl.py` script orchestrates the entire Extract, Transform, Load (ETL) process. It will:
1.  Create unique identifiers (`mimic_id`) for local concepts.
2.  Load the custom concept mappings from the CSV files.
3.  Transform the MIMIC data and load it into the OMOP CDM tables.

This process can take a significant amount of time depending on your hardware.

```bash
python run_etl.py
```

### 7. Validate the Installation

After the ETL process is complete, you can run the `validate.py` script to perform a series of checks on the resulting database. This will verify that tables were created, data was loaded, and primary keys are not null.

```bash
python validate.py
```

If all checks pass, you are ready to start using your local MIMIC-OMOP database!

---

## How It Works

This toolkit consists of three main Python scripts:

- **`setup.py`**: Prepares the environment. It's designed to be run once at the beginning.
- **`run_etl.py`**: Executes the full ETL process. It's the core of this toolkit and is responsible for all data transformation and loading.
- **`validate.py`**: A testing script to verify that the ETL was successful.

The original SQL scripts from the `MIT-LCP/mimic-omop` project are preserved in the `etl/` directory and are executed by the `run_etl.py` script. The original R script for loading concepts has been replaced with a Python equivalent within `run_etl.py`.
