import configparser
import subprocess
import sys
from pathlib import Path
import os
import pandas as pd
from sqlalchemy import create_engine, text

def get_db_connection_string(config, dbname=None):
    """Constructs a SQLAlchemy connection string from the config."""
    db_config = config['postgresql']
    user = db_config['user']
    # Provide a default empty string for password if it does not exist
    password = db_config.get('password', '')
    host = db_config['host']
    port = db_config['port']
    database = dbname if dbname else db_config['database']
    # URL-encode the password to handle special characters
    from urllib.parse import quote_plus
    password = quote_plus(password)
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

def run_sql_script(sql_file, config, set_vars=None):
    """Executes a SQL script using psql."""
    print(f"\n-- Running SQL script: {sql_file} --")
    db_config = config['postgresql']
    user = db_config['user']
    password = db_config.get('password', '')
    host = db_config['host']
    port = db_config['port']
    dbname = db_config['database']

    env = {**os.environ, "PGPASSWORD": password}

    command = ["psql", "-h", host, "-p", port, "-U", user, "-d", dbname]
    if set_vars:
        for var, value in set_vars.items():
            command.extend(["--set", f"{var}={value}"])
    command.extend(["-f", str(sql_file)])

    try:
        # Use shell=True for Windows compatibility
        is_windows = sys.platform == "win32"
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=env,
            shell=is_windows
        )
        print(f"✅ Successfully ran {sql_file}")
        if result.stdout:
            print("   Output:", result.stdout[:200] + "...") # Print snippet of output
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run {sql_file}.")
        print(f"   Command: {' '.join(e.cmd)}")
        print(f"   Error: {e.stderr}")
        sys.exit("Exiting due to SQL script execution failure.")

def load_concept_csvs(config):
    """Loads the concept CSV files into the database, replicating the R script."""
    print("\n-- Loading concept CSV files into database --")
    db_config = config['postgresql']
    mimic_schema = db_config['mimic_schema']

    conn_str = get_db_connection_string(config)
    engine = create_engine(conn_str)

    csv_path = Path("extras/concept/")
    csv_files = list(csv_path.glob("*.csv"))

    with engine.connect() as connection:
        for csv_file in csv_files:
            table_name = f"gcpt_{csv_file.stem.lower()}"
            print(f"Processing {csv_file.name} -> {mimic_schema}.{table_name}")

            # Using 'text' to ensure the schema is part of the SQL command
            connection.execute(text(f'DROP TABLE IF EXISTS "{mimic_schema}"."{table_name}" CASCADE;'))

            df = pd.read_csv(csv_file, comment="#", quotechar='"', skipinitialspace=True)
            df.columns = [x.lower() for x in df.columns]

            # Write to a temporary table in public schema first, then move.
            # This avoids potential issues with pandas to_sql and schemas.
            df.to_sql(table_name, engine, schema='public', if_exists='replace', index=False)

            # Move table to the target schema
            connection.execute(text(f'ALTER TABLE public."{table_name}" SET SCHEMA "{mimic_schema}";'))

            alter_sql = f"""
            ALTER TABLE "{mimic_schema}"."{table_name}"
            ADD COLUMN IF NOT EXISTS mimic_id INTEGER DEFAULT nextval('"{mimic_schema}".mimic_id_concept_seq'::regclass);
            """
            connection.execute(text(alter_sql))
            print(f"✅ Loaded and altered table {table_name}")

        connection.commit()

def main():
    """Main function to run the ETL process."""
    print("--- Starting MIMIC-OMOP ETL Process ---")

    config_path = Path('config.ini')
    if not config_path.exists():
        print(f"❌ {config_path} not found. Please run setup.py first.")
        sys.exit()

    config = configparser.ConfigParser()
    config.read(config_path)

    omop_schema = config['postgresql']['omop_schema']

    # 1. Create MIMIC-III concept IDs and sequences
    run_sql_script(Path("mimic/build-mimic/postgres_create_mimic_id.sql"), config)

    # 2. Load concept CSVs (Python version of the R script)
    load_concept_csvs(config)

    # 3. Run the main ETL script, passing the OMOP_SCHEMA variable
    run_sql_script(Path("etl/etl.sql"), config, set_vars={"OMOP_SCHEMA": omop_schema})

    print("\n🎉 ETL process finished successfully!")

if __name__ == "__main__":
    main()
