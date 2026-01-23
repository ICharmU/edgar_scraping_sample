@echo off
echo Running Alphabet Scripts...

call conda activate edgar_scraping
echo ./scripts/generate_alphabet_urls.py
python ./scripts/generate_alphabet_urls.py
echo ./scripts/retrieve_alphabet_eps.py
python ./scripts/retrieve_alphabet_eps.py
echo ./scripts/process_eps.py
python ./scripts/process_eps.py
call conda deactivate

echo Script Finished.