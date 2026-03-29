import os
import time
import requests
import shutil
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
import concurrent.futures
from django.conf import settings

MAX_WORKERS = 2  # Giảm xuống 3 để tránh làm nghẽn server nhà trường

def download_single_page(session, doc_id, subfolder, page_num, temp_dir):
    """Worker function for downloading a single image page with retries"""
    img_url = f"https://dlib.hvtc.edu.vn/server/viewer/services/view.php?doc={doc_id}&format=jpg&page={page_num}&subfolder={subfolder}"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Tăng timeout lên 30s
            response = session.get(img_url, timeout=30)
            if response.status_code == 200:
                img_path = os.path.join(temp_dir, f"page_{page_num}.jpg")
                with open(img_path, 'wb') as f:
                    f.write(response.content)
                return page_num, img_path
            else:
                print(f"Error downloading page {page_num}: HTTP {response.status_code}")
                time.sleep(2) # Nghỉ 2s trước khi thử lại
        except Exception as e:
            print(f"Connection error on page {page_num} (Attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(2) # Nghỉ trước khi thử lại
            
    return page_num, None


def process_document(url, request_id):
    """
    Headless processing of a single document
    Returns the relative path like 'documents/TaiLieu_DOCID.pdf' on success, None on failure.
    """
    print(f"Processing link: {url[:60]}...")
    
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    doc_id = query_params.get('doc', [''])[0]
    subfolder = query_params.get('subfolder', [''])[0]

    if not doc_id or not subfolder:
        print("Missing 'doc' or 'subfolder' in URL.")
        return None

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        time.sleep(5)  # Let it load inside headless browser
        
        pages = driver.find_elements(By.CLASS_NAME, "flowpaper_page")
        total_pages = len(pages)
        
        if total_pages == 0:
            print("Could not find any pages. Site may require login or block headless browsers.")
            return None

        print(f"Found {total_pages} pages. Running workers...")

        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

        temp_dir = f"temp_doc_{request_id}"
        os.makedirs(temp_dir, exist_ok=True)

        downloaded_files = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_page = {
                executor.submit(download_single_page, session, doc_id, subfolder, i, temp_dir): i 
                for i in range(1, total_pages + 1)
            }
            
            for future in concurrent.futures.as_completed(future_to_page):
                page_num, img_path = future.result()
                if img_path:
                    downloaded_files.append((page_num, img_path))

        downloaded_files.sort(key=lambda x: x[0])

        image_list = []
        for _, path in downloaded_files:
            try:
                img = Image.open(path).convert('RGB')
                image_list.append(img)
            except Exception as e:
                pass

        if image_list:
            doc_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
            os.makedirs(doc_dir, exist_ok=True)
            
            filename = f"TaiLieu_{doc_id}_{str(request_id)[:8]}.pdf"
            abs_pdf_path = os.path.join(doc_dir, filename)
            
            # Save the PDF
            image_list[0].save(
                abs_pdf_path, 
                save_all=True, 
                append_images=image_list[1:]
            )
            
            # Remove temp dir
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Return relative path to match MEDIA_URL schema
            return f"documents/{filename}"
            
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
            
    finally:
        driver.quit()
