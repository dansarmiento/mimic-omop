import configparser
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from urllib.parse import quote_plus

def get_db_connection_string(config):
    """Constructs a SQLAlchemy connection string from the config."""
    db_config = config['postgresql']
    user = db_config['user']
    password = db_config.get('password', '')
    host = db_config['host']
    port = db_config['port']
    database = db_config['database']
    password_encoded = quote_plus(password)
    return f"postgresql+psycopg2://{user}:{password_encoded}@{host}:{port}/{database}"

def main():
    """Main function to run the validation process."""
    print("--- Starting MIMIC-OMOP Validation Process ---")

    config_path = Path('config.ini')
    if not config_path.exists():
        print(f"❌ {config_path} not found. Please run setup.py first.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    omop_schema = config['postgresql']['omop_schema']

    try:
        engine = create_engine(get_db_connection_string(config), echo=False)
        inspector = inspect(engine)
    except Exception as e:
        print(f"❌ Failed to connect to the database. Please check your config.ini settings. Error: {e}")
        sys.exit(1)

    print(f"Successfully connected to database. Inspecting schema '{omop_schema}'...")

    populated_tables = [
        'care_site', 'person', 'death', 'visit_occurrence', 'observation_period',
        'visit_detail', 'procedure_occurrence', 'provider', 'condition_occurrence',
        'observation', 'drug_exposure', 'measurement', 'specimen', 'note',
        'note_nlp', 'fact_relationship', 'dose_era'
    ]

    all_checks_passed = True

    # 1. Check for table existence
    print("\n-- 1. Checking for table existence --")
    try:
        schema_tables = inspector.get_table_names(schema=omop_schema)
    except Exception as e:
        print(f"❌ Could not inspect schema '{omop_schema}'. Does it exist? Error: {e}")
        sys.exit(1)

    missing_tables = []
    for table in populated_tables:
        if table not in schema_tables:
            print(f"❌ MISSING: Table '{table}' not found in schema '{omop_schema}'.")
            missing_tables.append(table)
            all_checks_passed = False
        else:
            print(f"✅ FOUND: Table '{table}'.")

    if missing_tables:
        print("Error: Some expected tables are missing. The ETL did not complete successfully.")
    else:
        print("✅ All expected populated tables exist.")

    # 2. Check for row counts in key tables
    print("\n-- 2. Checking for row counts (must be > 0) --")
    with engine.connect() as connection:
        for table in populated_tables:
            if table in missing_tables:
                continue
            try:
                result = connection.execute(text(f'SELECT COUNT(*) FROM "{omop_schema}"."{table}";'))
                count = result.scalar_one()
                if count > 0:
                    print(f"✅ OK: Table '{table}' has {count} rows.")
                else:
                    print(f"⚠️ WARNING: Table '{table}' has 0 rows. This might be expected.")
            except Exception as e:
                print(f"❌ ERROR: Could not count rows in table '{table}'. Reason: {e}")
                all_checks_passed = False

    # 3. Basic data quality checks (no nulls in primary keys)
    print("\n-- 3. Checking for NULLs in primary key columns --")
    quality_checks = {
        'person': 'person_id',
        'visit_occurrence': 'visit_occurrence_id',
        'condition_occurrence': 'condition_occurrence_id',
        'drug_exposure': 'drug_exposure_id',
        'measurement': 'measurement_id',
        'observation': 'observation_id'
    }

    with engine.connect() as connection:
        for table, pk_column in quality_checks.items():
            if table in missing_tables:
                continue
            try:
                result = connection.execute(text(f'SELECT COUNT(*) FROM "{omop_schema}"."{table}" WHERE "{pk_column}" IS NULL;'))
                null_count = result.scalar_one()
                if null_count == 0:
                    print(f"✅ OK: PK '{pk_column}' in table '{table}' has no NULL values.")
                else:
                    print(f"❌ FAILED: PK '{pk_column}' in table '{table}' has {null_count} NULL values.")
                    all_checks_passed = False
            except Exception as e:
                print(f"❌ ERROR: Could not perform quality check on table '{table}'. Reason: {e}")
                all_checks_passed = False

    print("\n--- Validation Summary ---")
    if all_checks_passed:
        print("🎉 All validation checks passed successfully!")
    else:
        print("🔥 Some validation checks failed. Please review the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
