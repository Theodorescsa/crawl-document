from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import DownloadRequest
import json
import uuid

def index(request):
    return render(request, 'downloader/index.html')

def create_request(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        if url:
            order_code = f"DOC{str(uuid.uuid4().int)[:6]}"
            download_req = DownloadRequest.objects.create(
                url=url,
                order_code=order_code
            )
            return redirect('payment_page', pk=download_req.id)
    return redirect('index')

def payment_page(request, pk):
    download_req = get_object_or_404(DownloadRequest, pk=pk)
    context = {
        'request': download_req,
        'amount': 5000,
        'bank': 'MBBank',
        'account': '0354235270',
        # Sepay compact template
        'qr_url': f"https://qr.sepay.vn/img?acc=0354235270&bank=MBBank&amount=5000&des={download_req.order_code}&template=compact"
    }
    return render(request, 'downloader/payment.html', context)

def check_status(request, pk):
    download_req = get_object_or_404(DownloadRequest, pk=pk)
    return JsonResponse({'status': download_req.status})

@csrf_exempt
def sepay_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # data structure as provided by sepay
            # e.g., "transferAmount": 5000, "content": "DOC123456 chuyen tien"
            amount = data.get('transferAmount')
            content = data.get('content') or data.get('description', '')

            if amount >= 5000:
                # Find matching order code in the content
                requests_pending = DownloadRequest.objects.filter(status='PENDING_PAYMENT')
                for req in requests_pending:
                    if req.order_code.lower() in content.lower():
                        req.status = 'PROCESSING'
                        req.save()
                        
                        # Trigger background task here
                        from .tasks import start_crawling_task
                        start_crawling_task(req.id)
                        
                        return JsonResponse({'success': True, 'message': 'Payment confirmed'})

            return JsonResponse({'success': True, 'message': 'Ignored'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

def download_page(request, pk):
    download_req = get_object_or_404(DownloadRequest, pk=pk)
    return render(request, 'downloader/download.html', {'request': download_req})
