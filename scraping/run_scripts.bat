@echo off
echo Running Scraping Scripts...

call conda activate edgar_scraping
echo ./scripts/generate_urls.py
python ./scripts/generate_urls.py
echo ./scripts/retrieve_eps.py
python ./scripts/retrieve_eps.py
echo ./scripts/process_eps.py
python ./scripts/process_eps.py
echo ./scripts/sql_dump.py
python ./scripts/sql_dump.py
call conda deactivate

echo Script Finished.