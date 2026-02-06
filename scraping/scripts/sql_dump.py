import pandas as pd
import sys
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
user = os.getenv("db_user")
password = os.getenv("db_password")
database = os.getenv("database")
db_host = os.getenv("db_host")
port = os.getenv("db_port")

conn = psycopg2.connect(
    dbname=database,
    user=user,
    password=password,
    host=db_host,
    port=port
)

ticker = sys.argv[1]
table_name = "companies"

if conn:
    cur = conn.cursor()

    # expects to be run from /analytics/scraping
    fp = f"./data/{ticker}/processed_eps.csv"
    df = pd.read_csv(fp)
    
    schema = f"""
    CREATE TABLE IF NOT EXISTS "{table_name}" (
    "prev_year_eps" MONEY,
    "curr_year_eps" MONEY,
    "filing_date" DATE,
    "report_date" DATE,
    "form" CHAR(4),
    "fiscal_year" INTEGER,
    "quarter" INTEGER CHECK(quarter BETWEEN 1 AND 4),
    "ticker" VARCHAR(14) CHECK(LENGTH(ticker) >= 1)
    );
    """

    with open(fp) as f:
        columns = f.readline().strip().split(",")
        cur.execute(schema)
        cur.copy_from(f, table_name, sep=",", null="", columns=columns)

    conn.commit()
    print(f"added table {table_name}")

    conn.close()
