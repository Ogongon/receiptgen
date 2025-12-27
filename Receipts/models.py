from django.db import models
from django.contrib.auth.models import User

class BusinessProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_profile')
    
    phone_number = models.CharField(max_length=20)
    business_name = models.CharField(max_length=100, default="My Business")
    logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    
    # Tax Compliance Fields
    kra_pin = models.CharField(max_length=20, blank=True, null=True)
    charges_vat = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business_name} ({self.user.username})"

class Receipt(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Processing'),
        ('GENERATED', 'PDF Generated'),
        ('FAILED', 'Parsing Failed'),
    ]

    # Data Isolation: Link receipt to a Business Profile
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="receipts")
    
    mpesa_code = models.CharField(max_length=20, db_index=True) 
    # Not unique globally, but unique per business ideally
    transaction_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    raw_sms_text = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class ReceiptItem(models.Model):
    receipt = models.ForeignKey(Receipt, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} - {self.cost}"