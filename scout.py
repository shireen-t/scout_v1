"""
Scout for accepting input as CAS number or element name and perform a strict validation process.
"""

import os
import re
from datetime import datetime
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from googlesearch import search
import aiohttp
import json

# Directories setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDFS_FOLDER = os.path.join(BASE_DIR, "verified")
TEMP_FOLDER = os.path.join(BASE_DIR, "unverified")
LOGS_FOLDER = os.path.join(BASE_DIR, "logs")
os.makedirs(PDFS_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(LOGS_FOLDER, exist_ok=True)

# List of URLs to skip
SKIP_URLS = set([
    "guidechem", "chemicalbook", "commonchemistry", "alpha-chemistry", "lookchem",
    "home", "pharmaffiliates", "login", "privacy", "linkedin", "twitter", "x.com",
    "facebook", "youtube", "support", "contact", "food", "chemicalbook.com",
    "guidechem.com", "pharmaffiliates.com", "benjaminmoore.com", "wikipedia",
    "imdb", "amazon", "ebay", "craigslist", "pinterest", "instagram", "tumblr",
    "reddit", "snapchat", "tiktok", "nytimes", "huffingtonpost", "forbes",
    "bloomberg", "bbc", "cnn", "foxnews", "nbcnews", "abcnews", "theguardian",
    "dailymail", "usatoday", "quora", "stackexchange", "stackoverflow", "tripadvisor",
    "yelp", "zomato", "opentable", "healthline", "webmd", "mayoclinic", "nih.gov",
    "cdc.gov", "fda.gov", "epa.gov", "google", "bing", "yahoo", "ask", "aol", "baidu",
    "msn", "duckduckgo", "yandex", "coursera", "udemy", "edx", "khanacademy",
    "linkedin.com", "twitter.com", "facebook.com", "youtube.com", "instagram.com",
    "tumblr.com", "reddit.com", "snapchat.com", "tiktok.com", "nytimes.com",
    "huffingtonpost.com", "forbes.com", "bloomberg.com", "bbc.com", "cnn.com",
    "foxnews.com", "nbcnews.com", "abcnews.com", "theguardian.com", "dailymail.co.uk",
    "usatoday.com", "quora.com", "stackexchange.com", "stackoverflow.com",
    "tripadvisor.com", "yelp.com", "zomato.com", "opentable.com", "healthline.com",
    "webmd.com", "mayoclinic.org", "nih.gov", "cdc.gov", "fda.gov", "epa.gov",
    "google.com", "bing.com", "yahoo.com", "ask.com", "aol.com", "baidu.com",
    "msn.com", "duckduckgo.com", "yandex.com", "coursera.org", "udemy.com",
    "edx.org", "login", "register", "signup", "signin", "faq", "terms", "conditions",
    "terms-of-service", "support", "help", "contact", "about", "my-account", "favourites",
    "bulkOrder", "cart", "pinterest", "scribd",
])

# URL visit count dictionary
URL_VISIT_COUNT = {}
DOMAIN_VISIT_COUNT = {}
MAX_URL_VISITS = 5
MAX_DOMAIN_VISITS = 5

# Limit for downloading files
DOWNLOAD_LIMIT = 5
DOWNLOADED_FILES_COUNT = 0


# Save report to JSON file
def save_report(report_list):
    """
    Save the global report list to a JSON file in the logs directory.

    The report includes details of each processed file such as the CAS number or name,
    filename, download status, and provider.
    """
    if report_list:
        try:
            json_string = json.dumps(report_list, indent=4)
            report_filename = datetime.now().strftime(
                "%Y-%m-%d_%H-%M-%S") + ".json"
            report_filename = os.path.join(LOGS_FOLDER, report_filename)
            with open(report_filename, "w") as report_file:
                report_file.write(json_string)
            print(f"Scout report generated, check {report_filename}")
            return json.loads(json_string)
        except Exception as e:
            print(f"An error occurred while generating the report: {e}")
    else:
        print("NO REPORT GENERATED")

    return {}


# Add report entry
def add_report(report_list, cas, name, filepath, verified, provider, url):
    """
    Add an entry to the global report list.

    Params:
        cas (str): The CAS number.
        name (str): The element name.
        filepath (str): The file path of the PDF.
        verified (bool): Whether the file was successfully verified.
        provider (str): The provider or source of the file.
        url (str) : The URL from which the PDF is downloaded.
    """
    report = {
        "cas": cas,
        "name": name,
        "provider": provider,
        "verified": verified,
        "filepath": filepath,
        "url": url
    }
    report_list.append(report)


# Check if URL is a PDF
def is_pdf(url):
    """
    Check if a URL points to a PDF file.

    Params:
        url (str): The URL to check.

    Returns:
        bool: True if the URL points to a PDF file, False otherwise.
    """
    try:
        if url.endswith(".pdf"):
            return True

        response = requests.head(url, timeout=10)
        content_type = response.headers.get("content-type")
        return content_type == "application/pdf"
    except requests.Timeout:
        print(f"Timeout occurred while checking {url}")
        return False
    except Exception as e:
        print(f"Error occurred while checking {url}: {e}")
        return False


# Download PDF from URL
async def download_pdf(session, url):
    """
    Download a PDF file from a URL and save it to the specified folder.

    Params:
        url (str): The URL of the PDF file.

    Returns:
        str: The file path of the downloaded PDF, or None if the download failed.
    """
    global DOWNLOADED_FILES_COUNT
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            if response.headers.get('content-type') == 'application/pdf':
                file_name = url.split("/")[-1]
                if not file_name.endswith(".pdf"):
                    file_name += ".pdf"
                file_path = os.path.join(TEMP_FOLDER, file_name)
                with open(file_path, 'wb') as pdf_file:
                    pdf_file.write(await response.read())
                print(f"Downloaded: {file_name}")
                DOWNLOADED_FILES_COUNT += 1
                return file_path
            else:
                print(f"Skipping {url}, not a PDF file.")
                return None
    except Exception as e:
        print(f"An error occurred while downloading {url}: {e}")
    return None


# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file.

    Params:
        pdf_path (str): The file path of the PDF.

    Returns:
        str: The extracted text content, or None if extraction failed.
    """
    try:
        pageno = 1
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            if pageno > 5:  # read only first 5 pages
                break
            text += page.get_text()
            pageno += 1
        doc.close()
        return text
    except Exception as e:
        print(f"An error occurred while extracting text from {pdf_path}: {e}")
        return None


# Set regular expression pattern
def set_pattern(sequence):
    """
    Create a regular expression pattern for a given sequence.

    Params:
        sequence (str): The sequence to escape and compile into a pattern.

    Returns:
        re.Pattern: The compiled regular expression pattern.
    """
    escaped_sequence = re.escape(sequence)
    return re.compile(rf'\b{escaped_sequence}\b', re.IGNORECASE)


# Verify PDF content
def verify_pdf(file_path, cas=None, name=None):
    """
    Verify if a PDF file contains the specified CAS number or element name and the phrase "safety data sheet".

    Params:
        file_path (str): The file path of the PDF.
        cas (str): The CAS number to verify against.
        name (str): The element name to verify against.

    Returns:
        bool: True if the PDF content is verified, False otherwise.
    """
    try:
        text = extract_text_from_pdf(file_path)
        if text is None:
            return False
        patterns = [set_pattern("safety data sheet")]
        if cas:
            patterns.append(set_pattern(cas))
        if name:
            patterns.append(set_pattern(name))

        verified = all(pattern.search(text) for pattern in patterns)
        if verified:
            return True
    except Exception as e:
        print(f"An error occurred while verifying {file_path}: {e}")
    return False


# Download and verify PDFs for CAS number or name
async def download_and_verify_pdfs(cas=None, name=None, url=None):
    """
    Download and verify PDFs for the specified CAS number or element name.

    Params:
        cas (str): The CAS number to search for.
        name (str): The element name to search for.
        url (str): The URL to fetch the search results.

    Returns:
        list: A list of tuples containing the URL and file path of verified PDFs.
    """
    if cas:
        query = f'"{cas}" filetype:pdf'
    elif name:
        query = f'"{name}" "safety data sheet" filetype:pdf'
    elif url:
        query = f'{url}'
    else:
        return []

    verified_pdfs = []
    async with aiohttp.ClientSession() as session:
        for url in search(query, num_results=50):
            if DOWNLOADED_FILES_COUNT >= DOWNLOAD_LIMIT:
                break

            domain = urlparse(url).netloc

            if any(skip_word in domain for skip_word in SKIP_URLS) or any(skip_word in url for skip_word in SKIP_URLS):
                print(f"Skipping URL: {url} (matches skip words)")
                continue

            if url in URL_VISIT_COUNT and URL_VISIT_COUNT[url] >= MAX_URL_VISITS:
                print(f"Skipping URL: {url} (visit limit reached)")
                continue

            if domain in DOMAIN_VISIT_COUNT and DOMAIN_VISIT_COUNT[domain] >= MAX_DOMAIN_VISITS:
                print(f"Skipping URL: {url} (domain visit limit reached)")
                continue

            URL_VISIT_COUNT[url] = URL_VISIT_COUNT.get(url, 0) + 1
            DOMAIN_VISIT_COUNT[domain] = DOMAIN_VISIT_COUNT.get(domain, 0) + 1

            if is_pdf(url):
                pdf_path = await download_pdf(session, url)
                if pdf_path:
                    verified = verify_pdf(pdf_path, cas, name)
                    if verified:
                        new_file_path = os.path.join(PDFS_FOLDER, os.path.basename(pdf_path))
                        os.rename(pdf_path, new_file_path)
                        verified_pdfs.append((url, new_file_path))
                        print(f"Verified PDF: {new_file_path}")
                    else:
                        os.remove(pdf_path)
                        print(f"Deleted unverified PDF: {pdf_path}")
    return verified_pdfs


# Main function
async def main(input_data):
    """
    Main function to handle the search, download, and verification process.

    Params:
        input_data (list): List of dictionaries containing 'cas' or 'name' keys.

    Returns:
        dict: The generated report of the process.
    """
    global DOWNLOADED_FILES_COUNT
    DOWNLOADED_FILES_COUNT = 0
    report_list = []
    for data in input_data:
        cas = data.get("cas")
        name = data.get("name")
        urls = data.get("urls")
        if urls:
            for url in urls:
                verified_pdfs = await download_and_verify_pdfs(cas=cas, name=name, url=url)
                for url, path in verified_pdfs:
                    add_report(report_list, cas, name, path, True, url, url)
        elif cas or name:
            verified_pdfs = await download_and_verify_pdfs(cas=cas, name=name)
            for url, path in verified_pdfs:
                add_report(report_list, cas, name, path, True, url, url)
        else:
            print(f"Skipping data: {data} (missing 'cas' or 'name')")
    return save_report(report_list)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scout for downloading and verifying SDS PDFs.")
    parser.add_argument("input_file", help="Path to the JSON input file containing CAS numbers or names.")
    args = parser.parse_args()

    with open(args.input_file, "r") as f:
        input_data = json.load(f)

    import asyncio
    asyncio.run(main(input_data))
