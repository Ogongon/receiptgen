from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
import os
from .forms import RegisterForm
from .models import Receipt, BusinessProfile, ReceiptItem
from .parser import MpesaParser
from .tasks import generate_and_send_receipt


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')
# --- AUTH ---
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            BusinessProfile.objects.create(user=user, business_name=f"{user.username}'s Shop")
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('dashboard')
    else: form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else: form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

# --- APP ---
@login_required(login_url='login')
def dashboard(request):
    # Ensure Profile Exists
    profile, _ = BusinessProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        sms_text = request.POST.get('sms_text')
        parser = MpesaParser()
        data = parser.parse(sms_text)
        
        if not data:
            messages.error(request, "Invalid SMS format.")
            return redirect('dashboard')
            
        # Data Isolation: Only check duplicates for THIS business
        if Receipt.objects.filter(business=profile, mpesa_code=data['code']).exists():
            messages.warning(request, "Receipt already exists.")
            return redirect('dashboard')

        receipt = Receipt.objects.create(
            business=profile,
            mpesa_code=data['code'],
            amount=data['amount'],
            transaction_date=data['date'],
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            raw_sms_text=data['raw_text'],
            status='PENDING'
        )

        descriptions = request.POST.getlist('item_desc[]')
        costs = request.POST.getlist('item_cost[]')
        
        has_items = False
        if descriptions and costs:
            for desc, cost in zip(descriptions, costs):
                if desc.strip() and cost.strip():
                    ReceiptItem.objects.create(receipt=receipt, description=desc.strip(), cost=cost.strip())
                    has_items = True

        if not has_items:
            ReceiptItem.objects.create(receipt=receipt, description="M-Pesa Payment", cost=data['amount'])

        generate_and_send_receipt(receipt.id)
        messages.success(request, "Processing receipt...")
        return redirect('dashboard')

    receipts = Receipt.objects.filter(business=profile).order_by('-created_at')[:20]
    return render(request, 'dashboard.html', {'receipts': receipts, 'profile': profile})


@login_required(login_url='login')
def update_settings(request):
    if request.method == "POST":
        p = request.user.business_profile
        p.business_name = request.POST.get('business_name')
        p.phone_number = request.POST.get('business_phone')
        p.kra_pin = request.POST.get('kra_pin')
        p.charges_vat = request.POST.get('charges_vat') == 'on'
        p.save()
        messages.success(request, "Settings saved.")
    return redirect('dashboard')

@login_required(login_url='login')
def download_pdf(request, receipt_id):
    try:
        receipt = Receipt.objects.get(id=receipt_id, business=request.user.business_profile)
        path = f"generated_pdfs/{receipt.mpesa_code}.pdf"
        if os.path.exists(path):
            return FileResponse(open(path, 'rb'), as_attachment=True, filename=f"{receipt.mpesa_code}.pdf")
        raise Http404
    except Receipt.DoesNotExist: raise Http404

@login_required(login_url='login')
def clear_dashboard(request):
    if request.method == "POST":
        Receipt.objects.filter(business=request.user.business_profile).delete()
        messages.success(request, "All data wiped.")
    return redirect('dashboard')

@login_required(login_url='login')
def update_settings(request):
    if request.method == "POST":
        p = request.user.business_profile
        p.business_name = request.POST.get('business_name')
        p.phone_number = request.POST.get('business_phone')
        p.kra_pin = request.POST.get('kra_pin')
        p.charges_vat = request.POST.get('charges_vat') == 'on'
        
        # NEW: Handle Logo Upload
        if 'business_logo' in request.FILES:
            p.logo = request.FILES['business_logo']
            
        p.save()
        messages.success(request, "Settings saved.")
    return redirect('dashboard')

