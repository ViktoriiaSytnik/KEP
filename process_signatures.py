# process_signatures.py
import requests
import base64
import csv
import time
from concurrent.futures import ThreadPoolExecutor
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7, pkcs12
from cryptography.hazmat.backends import default_backend
from pyasn1.codec.der.decoder import decode
from pyasn1.type import univ

tender_details_file = 'C:\\Temp\\Python 2\\.idea\\Пайтон Код\\tender_details.csv'
processed_details_file = 'C:\\Temp\\Python 2\\.idea\\Пайтон Код\\processed_tenders.csv'

def decode_base64_if_needed(data):
    try:
        decoded_data = base64.b64decode(data)
        return decoded_data
    except base64.binascii.Error:
        return data

def extract_pkcs7_content(pkcs7_data):
    try:
        pkcs7_obj = pkcs7.load_der_pkcs7_certificates(pkcs7_data)
        if pkcs7_obj:
            for cert in pkcs7_obj:
                subject = cert.subject
                issuer = cert.issuer
                serial_number = cert.serial_number
                edrp_rnokpp_object_id = ObjectIdentifier('2.5.29.9')
                edrp_rnokpp_extension = cert.extensions.get_extension_for_oid(edrp_rnokpp_object_id)
                edrp_rnokpp_raw_value = edrp_rnokpp_extension.value.value
                decoded_edrp_rnokpp, _ = decode(edrp_rnokpp_raw_value, asn1Spec=univ.Sequence())
                parsed_edrp_rnokpp = parse_edrpou_string(str(decoded_edrp_rnokpp.prettyPrint()))
                edrp_result = parsed_edrp_rnokpp[0]['field-0'].split()[-1]
                rnokpp_result = parsed_edrp_rnokpp[1]['field-0'].split()[-1]

                def get_attribute(name, oid):
                    try:
                        return name.get_attributes_for_oid(oid)[0].value
                    except IndexError:
                        return None

                signer_info = {
                    "РНОКПП": rnokpp_result,
                    "Код ЄДРПОУ": edrp_result,
                    "Посада": get_attribute(subject, x509.ObjectIdentifier("2.5.4.12")),
                    "Організація": get_attribute(subject, x509.NameOID.ORGANIZATION_NAME),
                    "Підписувач": get_attribute(subject, x509.NameOID.COMMON_NAME),
                }

                return signer_info
        else:
            print("Файл не містить дійсних даних PKCS#7.")
            return None
    except Exception as e:
        print(f"Помилка при витяганні даних з PKCS#7: {e}")
        return None

def extract_pkcs12_content(pkcs12_data, password=None):
    try:
        private_key, cert, additional_certs = pkcs12.load_key_and_certificates(pkcs12_data, password, default_backend())
        if cert:
            subject = cert.subject
            issuer = cert.issuer
            serial_number = cert.serial_number

            def get_attribute(name, oid):
                try:
                    return name.get_attributes_for_oid(oid)[0].value
                except IndexError:
                    return None

            rnokpp_result = get_attribute(subject, x509.ObjectIdentifier("2.5.4.5"))
            edrp_result = get_attribute(subject, x509.ObjectIdentifier("1.2.840.113549.1.9.1"))

            signer_info = {
                "РНОКПП": rnokpp_result,
                "Код ЄДРПОУ": edrp_result,
                "Посада": get_attribute(subject, x509.ObjectIdentifier("2.5.4.12")),
                "Організація": get_attribute(subject, x509.NameOID.ORGANIZATION_NAME),
                "Підписувач": get_attribute(subject, x509.NameOID.COMMON_NAME),
            }

            return signer_info
        else:
            print("Файл не містить дійсних даних PKCS#12.")
            return None
    except Exception as e:
        print(f"Помилка при витяганні даних з PKCS#12: {e}")
        return None

def download_file(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content, response.headers.get('Content-Type')
    else:
        print(f"Не вдалося завантажити файл з {url}. Статус-код: {response.status_code}")
        return None, None

def process_signature(tender_id, signature_url):
    start_time = time.time()
    file_data, mime_type = download_file(signature_url)
    if file_data:
        decoded_data = decode_base64_if_needed(file_data)
        signer_info = None
        if mime_type == 'application/pkcs7-signature':
            signer_info = extract_pkcs7_content(decoded_data)
        elif mime_type == 'application/x-pkcs12':
            signer_info = extract_pkcs12_content(decoded_data)
        else:
            print(f"Непідтримуваний MIME-тип: {mime_type}")

        end_time = time.time()
        print(f"Обробка підпису для тендера {tender_id} зайняла {end_time - start_time:.3f} секунд.")
        return signer_info
    return None

def main():
    with open(tender_details_file, 'r', encoding='utf-8') as infile, open(processed_details_file, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['ПІБ', 'Організація', 'РНОКПП', 'ЄДРПОУ', 'Посада']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            for row in reader:
                tender_id = row['tender_id']
                signature_url = row['signature_url']
                futures[executor.submit(process_signature, tender_id, signature_url)] = row

            for future in as_completed(futures):
                row = futures[future]
                signer_info = future.result()
                if signer_info:
                    row.update(signer_info)
                writer.writerow(row)

if __name__ == "__main__":
    main()
