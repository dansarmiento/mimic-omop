import configparser
import subprocess
import sys
from pathlib import Path
import os

def check_prerequisites():
    """Checks if all required prerequisites are installed."""
    print("Checking prerequisites...")
    prereqs = {
        "python": [sys.executable, "--version"],
        "git": ["git", "--version"],
        "psql": ["psql", "--version"]
    }
    all_ok = True
    for name, command in prereqs.items():
        try:
            # Using shell=True for Windows compatibility, though less secure.
            # For this use case, it's acceptable as commands are hardcoded.
            is_windows = sys.platform == "win32"
            subprocess.run(command, check=True, capture_output=True, shell=is_windows)
            print(f"✅ {name} is installed.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {name} is not installed or not in PATH. Please install it and try again.")
            all_ok = False
    if not all_ok:
        sys.exit("Exiting due to missing prerequisites.")

def clone_dependencies():
    """Clones the required GitHub repositories."""
    print("\nCloning dependencies...")
    vendor_dir = Path("vendor")
    vendor_dir.mkdir(exist_ok=True)

    repos = {
        "CommonDataModel": "https://github.com/OHDSI/CommonDataModel.git"
    }

    for name, url in repos.items():
        repo_path = vendor_dir / name
        if repo_path.exists():
            print(f"✅ {name} repository already exists. Skipping.")
        else:
            print(f"Cloning {name} repository...")
            try:
                subprocess.run(["git", "clone", url, str(repo_path)], check=True)
                print(f"✅ Successfully cloned {name}.")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to clone {name}: {e}")
                sys.exit("Exiting due to failed dependency cloning.")

def download_vocabularies():
    """Provides instructions for downloading the OMOP vocabularies."""
    print("\n-- OMOP Vocabulary Download --")
    print("This step cannot be fully automated due to Athena's license agreement.")
    print("Please follow these steps manually:")
    print("1. Go to https://athena.ohdsi.org/ and log in (or register).")
    print("2. Add the required vocabularies to your cart (e.g., SNOMED, LOINC, RxNorm).")
    print("3. Click 'Download' and agree to the terms.")
    print("4. After downloading, unzip the file.")
    print("5. Update the 'athena_vocab' path in your `config.ini` to point to the directory with the vocabulary CSV files.")

    config = configparser.ConfigParser()
    config.read('config.ini')
    vocab_path = config['paths']['athena_vocab']

    print(f"\nCurrent path in config.ini is: '{vocab_path}'")

    while True:
        proceed = input("Have you downloaded the vocabularies and updated the config file? (y/n): ")
        if proceed.lower() == 'y':
            break
        else:
            print("Please complete the manual steps before continuing.")


def create_database(config):
    """Creates the PostgreSQL database and schemas."""
    print("\n-- Database and Schema Setup --")
    db_config = config['postgresql']
    user = db_config['user']
    password = db_config.get('password', '') # Use empty string if password is not set
    host = db_config['host']
    port = db_config['port']
    dbname = db_config['database']
    mimic_schema = db_config['mimic_schema']
    omop_schema = db_config['omop_schema']

    env = {**os.environ, "PGPASSWORD": password} if password else os.environ

    # We assume the main database is already created.
    # The script will create the necessary schemas.
    print(f"Assuming database '{dbname}' exists.")
    print(f"Attempting to create schemas '{mimic_schema}' and '{omop_schema}'...")

    commands = [
        f"CREATE SCHEMA IF NOT EXISTS {mimic_schema};",
        f"CREATE SCHEMA IF NOT EXISTS {omop_schema};"
    ]

    for sql_command in commands:
        try:
            subprocess.run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", dbname, "-c", sql_command],
                check=True,
                capture_output=True,
                text=True,
                env=env
            )
            print(f"✅ Successfully executed: \"{sql_command}\"")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to execute command. Is the database running and accessible?")
            print(f"Command: {e.cmd}")
            print(f"Error: {e.stderr}")
            sys.exit("Exiting due to database setup failure.")

def main():
    """Main function to run the setup process."""
    print("--- Starting MIMIC-OMOP ETL Setup ---")

    config_path = Path('config.ini')
    if not config_path.exists():
        print(f"❌ {config_path} not found.")
        print("Please copy `config.example.ini` to `config.ini` and fill in your details.")
        sys.exit()

    # 1. Check prerequisites
    check_prerequisites()

    # 2. Clone dependencies
    clone_dependencies()

    # 3. Handle vocabulary download
    download_vocabularies()

    # 4. Create database and schemas
    config = configparser.ConfigParser()
    config.read(config_path)
    create_database(config)

    print("\n🎉 Setup script finished successfully!")
    print("You are now ready to run the ETL process using `run_etl.py`.")


if __name__ == "__main__":
    main()
