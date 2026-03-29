import threading
from .models import DownloadRequest
from .scraper import process_document

def start_crawling_task(request_id):
    """
    Start the crawling process in a separate background thread.
    This prevents the Sepay webhook response from hanging.
    """
    # Create the thread and start it
    thread = threading.Thread(target=_crawl_worker, args=(request_id,))
    thread.start()

def _crawl_worker(request_id):
    # Retrieve the model object
    try:
        req = DownloadRequest.objects.get(id=request_id)
        # Call the scraper processing function
        print(f"[Worker] Starting processing for {req.order_code}")
        pdf_path = process_document(req.url, req.id)
        
        if pdf_path:
            # File download successful
            req.pdf_file.name = pdf_path # Save relative path string
            req.status = 'COMPLETED'
            req.save()
            print(f"[Worker] Download SUCCESS for {req.order_code}")
        else:
            req.status = 'FAILED'
            req.save()
            print(f"[Worker] Download FAILED for {req.order_code}")
            
    except Exception as e:
        print(f"[Worker] Error processing {request_id}: {e}")
        try:
            req = DownloadRequest.objects.get(id=request_id)
            req.status = 'FAILED'
            req.save()
        except:
            pass
