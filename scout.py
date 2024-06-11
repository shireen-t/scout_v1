import os
import re
from datetime import datetime
import fitz  # PyMuPDF
import requests
from googlesearch import search
import aiohttp
import json

# Directories setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDFS_FOLDER = os.path.join(BASE_DIR, "verified")
TEMP_FOLDER = os.path.join(BASE_DIR, "uploads")
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
    if report_list:
        try:
            json_string = json.dumps(report_list, indent=4)
            report_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
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
    escaped_sequence = re.escape(sequence)
    return re.compile(rf'\b{escaped_sequence}\b', re.IGNORECASE)

# Verify PDF content
def verify_pdf(file_path, cas=None, name=None):
    try:
        text = extract_text_from_pdf(file_path)
        if text is None:
            print(f"Failed to extract text from PDF: {file_path}")
            return False
        patterns = [set_pattern("safety data sheet")]
        if cas:
            patterns.append(set_pattern(cas))
        if name:
            patterns.append(set_pattern(name))

        verified = all(pattern.search(text) for pattern in patterns)
        if verified:
            print(f"PDF verified successfully: {file_path}")
            return True
    except Exception as e:
        print(f"An error occurred while verifying {file_path}: {e}")
    print(f"PDF verification failed: {file_path}")
    return False

# Download and verify PDFs for CAS number or name
async def download_and_verify_pdfs(cas=None, name=None, url=None):
    if cas:
        query = f'"{cas}" "safety data sheet" filetype:pdf'
        print(f"Querying for CAS: {query}")
    elif name:
        query = f'"{name}" "safety data sheet" filetype:pdf'
        print(f"Querying for Name: {query}")
    elif url:
        query = f'"{url}" filetype:pdf'
        print(f"Querying for URL: {query}")
    else:
        print("ERROR: CAS number or name or URL not provided.")
        return []

    global DOWNLOADED_FILES_COUNT
    DOWNLOADED_FILES_COUNT = 0
    report_list = []

    async with aiohttp.ClientSession() as session:
        for url in search(query, num_results=20):
            if DOWNLOADED_FILES_COUNT >= DOWNLOAD_LIMIT:
                print("Download limit reached.")
                break
            if is_pdf(url):
                print(f"Found PDF URL: {url}")
                file_path = await download_pdf(session, url)
                if file_path:
                    print(f"Verifying downloaded PDF: {file_path}")
                    if verify_pdf(file_path, cas, name):
                        print(f"Verified PDF: {file_path}")
                        add_report(report_list, cas, name, file_path, True, url, url)
                        return report_list  # Return the report list here
                    else:
                        print(f"Verification failed for: {file_path}")
                else:
                    print(f"Failed to download PDF from: {url}")
            else:
                print(f"URL is not a PDF: {url}")
    print(f"No valid PDFs found for query: {query}")
    return report_list

# Main function
async def main(input_data):
    global DOWNLOADED_FILES_COUNT
    DOWNLOADED_FILES_COUNT = 0
    report_list = []
    for data in input_data:
        cas = data.get("cas")
        name = data.get("name")
        urls = data.get("urls")
        if urls:
            for url in urls:
                verified_pdf_path = await download_and_verify_pdfs(cas, name, url)
                if verified_pdf_path:
                    report_list.extend(verified_pdf_path)
        else:
            verified_pdf_path = await download_and_verify_pdfs(cas, name)
            if verified_pdf_path:
                report_list.extend(verified_pdf_path)
    return save_report(report_list)  # Save and return the report list
