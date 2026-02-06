import sys
import subprocess
import json

# runner.py expects the following setup:
# - environment: conda activate edgar_scraping
# - directory: analytics/scraping

cik_fp = "cik_mappings.json"
with open(cik_fp, "r") as f:
    mappings = json.load(f)

cik_scripts = [
    "scripts/generate_urls.py",
]
ticker_scripts = [
    "scripts/retrieve_eps.py",
    "scripts/process_eps.py",
    "scripts/sql_dump.py",
]

i = 0
j = 50
for cik, name_info in list(mappings.items())[j:]:
    # if i == 0:
    #     i += 1
    #     continue
    if i > 10:
        break

    for ticker in name_info["tickers"]:
        broken = False
        for script_path in cik_scripts:
            # continue  
            try:
                subprocess.run([sys.executable, script_path, cik, ticker])
            except Exception as e:
                print(f"Process {script_path} failed for CIK '{cik}' ({name_info["full_name"]})")
                continue
        
        j = 0
        for script_path in ticker_scripts:
            j += 1
            # if j < 2:
            #     continue

            try:
                subprocess.run([sys.executable, script_path, ticker])
            except Exception as e:
                print(f"Process {script_path} failed for ticker '{ticker}' ({name_info["full_name"]})")
                broken = True
                break

        
        if broken:
            continue


    i += 1