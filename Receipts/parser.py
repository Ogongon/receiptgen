import re
from datetime import datetime
import pytz 

class MpesaParser:
    def parse(self, text):
        text = text.strip()
        
        # 1. Code
        code_match = re.search(r"^([A-Z0-9]{10})\s+Confirmed", text)
        if not code_match: return None
        code = code_match.group(1)
        
        # 2. Amount
        amount_match = re.search(r"Ksh([\d,]+\.\d{2})", text)
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0
            
        # 3. Date & Time (Nairobi Time)
        date_match = re.search(r"on\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)", text)
        nairobi = pytz.timezone('Africa/Nairobi')
        transaction_date = datetime.now(nairobi) # Fallback
        
        if date_match:
            try:
                date_str, time_str = date_match.groups()
                # Handle varying year formats (25 vs 2025)
                fmt = "%d/%m/%y %I:%M %p" if len(date_str.split('/')[-1]) == 2 else "%d/%m/%Y %I:%M %p"
                naive_dt = datetime.strptime(f"{date_str} {time_str}", fmt)
                transaction_date = nairobi.localize(naive_dt)
            except ValueError: pass

        # 4. Name extraction
        customer_name = "Unknown Customer"
        to_match = re.search(r"sent to\s+(.+?)\s+on", text)
        from_match = re.search(r"received from\s+(.+?)\s+on", text)
        
        if to_match: customer_name = to_match.group(1)
        elif from_match: customer_name = from_match.group(1)

        # 5. Phone
        phone = ""
        phone_match = re.search(r"(\d{10,12})", customer_name)
        if phone_match: phone = phone_match.group(1)

        return {
            'code': code, 'amount': amount, 'date': transaction_date,
            'customer_name': customer_name, 'customer_phone': phone, 'raw_text': text
        }