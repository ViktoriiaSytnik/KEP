# fetch_tenders.py
import requests
import csv
from concurrent.futures import ThreadPoolExecutor

tender_ids_file = 'C:\\Temp\\Python 2\\.idea\\Пайтон Код\\2023-2024.csv'
tender_details_file = 'C:\\Temp\\Python 2\\.idea\\Пайтон Код\\tender_details.csv'
base_tender_url = 'https://public-api.prozorro.gov.ua/api/2.5/tenders/'

def fetch_tender_details(tender_id):
    tender_url = f"{base_tender_url}{tender_id}"
    response = requests.get(tender_url)
    if response.status_code == 200:
        tender_data = response.json()
        procuring_entity = tender_data.get('data', {}).get('procuringEntity', {})
        result = {
            'tender_id': tender_id,
            'procuringEntity_id': procuring_entity.get('identifier', {}).get('id'),
            'procuringEntity_name': procuring_entity.get('identifier', {}).get('legalName')
        }
        signature_docs = [
            doc['url'] for doc in tender_data.get('data', {}).get('documents', [])
            if doc.get('title_en') == 'sign.p7s'
        ]
        return result, signature_docs
    return None, []

def main():
    with open(tender_ids_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        tender_ids = [row[0].split(';')[0] for row in reader]

    with open(tender_details_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['tender_id', 'procuringEntity_id', 'procuringEntity_name', 'signature_url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_tender_details, tender_id): tender_id for tender_id in tender_ids}
            for future in futures:
                result, signature_docs = future.result()
                if result and signature_docs:
                    for url in signature_docs:
                        result['signature_url'] = url
                        writer.writerow(result)

if __name__ == "__main__":
    main()
