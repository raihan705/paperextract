import requests
import os
import json
import time
from datetime import datetime
import re

# Folder to save DOIs
SAVE_DIR = 'doi_results'
os.makedirs(SAVE_DIR, exist_ok=True)

# Scopus API endpoint and key (replace with your actual key)
SCOPUS_API_KEY = 'aa5baf85e204f12cd0413199e9aa6402'
SCOPUS_ENDPOINT = 'https://api.elsevier.com/content/search/scopus'

JOURNALS = [
    "ieee transactions on software engineering",
    "acm transactions on software engineering and methodology",
    "automated software engineering journal",
    "empirical software engineering journal",
    "information and software technology",
    "journal of systems and software",
    "computer supported cooperative work",
    "requirements engineering journal",
    "journal of software evolution and process",
    "software testing verification and reliability",
    "journal of software maintenance and evolution research and practice"
]

RESEARCH_METHODS = [
    "data science", "engineering research", "design science", "experiments", "grounded theory", 
    "longitudinal", "meta science", "optimization", "qualitative survey", "quantitative survey", 
    "quantitative simulation", "qualitative simulation", "questionnaire survey", "replication", 
    "repository mining", "systematic review", "mixed method", "empirical study", "literature survey"
]

# Extract unique single-word keywords from RESEARCH_METHODS
METHOD_KEYWORDS = set(word for phrase in RESEARCH_METHODS for word in phrase.lower().split())

CURRENT_YEAR = datetime.now().year

# Fetch data using offset-based pagination
def fetch_scopus_data(query, count=25, start=0):
    headers = {'X-ELS-APIKey': SCOPUS_API_KEY}
    params = {
        'query': query,
        'count': count,
        'start': start,
        'httpAccept': 'application/json',
        'view': 'STANDARD'
    }
    response = requests.get(SCOPUS_ENDPOINT, headers=headers, params=params)
    if response.status_code == 403:
        print("Permission error: Check API key, subscription level, or quota.")
        print(f"Error details: {response.text}")
        exit(1)
    response.raise_for_status()
    return response.json()

def normalize_text(text):
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()

def is_valid_doi(doi):
    doi = doi.strip()
    return bool(re.match(r'^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$', doi))

def filter_articles(entries):
    filtered_dois = []
    for entry in entries:
        publication_name = normalize_text(entry.get('prism:publicationName', ''))
        year_str = entry.get('prism:coverDate', '0')[:4]

        try:
            year = int(year_str)
        except ValueError:
            continue

        journal_found = any(journal in publication_name for journal in JOURNALS)

        title = normalize_text(entry.get('dc:title', ''))
        abstract = normalize_text(entry.get('dc:description', ''))
        keywords = normalize_text(' '.join(entry.get('authkeywords', '').split('|')))

        metadata_text = f"{title} {abstract} {keywords}"
        method_found = any(keyword in metadata_text for keyword in METHOD_KEYWORDS)

        if 2000 <= year <= CURRENT_YEAR and journal_found and method_found:
            doi = entry.get('prism:doi', '').strip()
            if doi and is_valid_doi(doi):
                filtered_dois.append(doi)

    return filtered_dois

def save_dois(dois, filename):
    filepath = os.path.join(SAVE_DIR, filename)
    with open(filepath, 'w') as file:
        for doi in dois:
            file.write(doi + '\n')
    print(f"Saved {len(dois)} validated DOIs to {filepath}")

def collect_all_dois(query, max_results=5000):
    start = 0
    page_size = 25
    all_dois = []

    while start < max_results:
        print(f"Fetching records: {start} to {start + page_size}")
        data = fetch_scopus_data(query, count=page_size, start=start)
        entries = data.get('search-results', {}).get('entry', [])
        if not entries:
            print("No more entries found. Ending pagination.")
            break

        filtered_dois = filter_articles(entries)
        all_dois.extend(filtered_dois)

        start += page_size
        time.sleep(1)

    return list(set(all_dois))  # Remove duplicates

def main():
    scopus_query = '"software ecosystem"'
    all_filtered_dois = collect_all_dois(scopus_query)
    save_dois(all_filtered_dois, 'scopus_dois.txt')

if __name__ == '__main__':
    main()
