from huey import crontab
from huey.contrib.djhuey import db_task, db_periodic_task
from .models import Receipt
from .pdf_engine import generate_receipt_pdf
import os
from django.utils import timezone
from datetime import timedelta

@db_task()
def generate_and_send_receipt(receipt_id):
    try:
        receipt = Receipt.objects.get(id=receipt_id)
        
        # Ensure directory exists
        output_dir = "generated_pdfs"
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f"{receipt.mpesa_code}.pdf")
        
        if generate_receipt_pdf(receipt, file_path):
            receipt.status = 'GENERATED'
            receipt.save()
            print(f"SUCCESS: Generated PDF for {receipt.mpesa_code}")
        else:
            receipt.status = 'FAILED'
            receipt.save()

    except Receipt.DoesNotExist:
        print("ERROR: Receipt ID not found")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

# --- COMPLIANCE JANITOR: DELETES DATA AFTER 24 HOURS ---
@db_periodic_task(crontab(minute='0', hour='3')) 
def clear_old_data():
    cutoff = timezone.now() - timedelta(hours=24)
    old_receipts = Receipt.objects.filter(created_at__lte=cutoff)
    
    count = old_receipts.count()
    if count > 0:
        print(f"Janitor: Cleaning {count} records...")
        for receipt in old_receipts:
            file_path = f"generated_pdfs/{receipt.mpesa_code}.pdf"
            if os.path.exists(file_path): os.remove(file_path)
        old_receipts.delete()