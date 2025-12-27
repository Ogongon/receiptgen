from fpdf import FPDF
import qrcode
import os
import pytz 

class ReceiptPDF(FPDF):
    def header(self): pass
    def footer(self): pass
def generate_receipt_pdf(receipt_obj, output_path):
    # Setup Page (80mm width)
    pdf = ReceiptPDF('P', 'mm', (80, 200))
    pdf.set_margins(4, 5, 4)
    pdf.set_auto_page_break(auto=True, margin=5)
    pdf.add_page()
    
    biz = receipt_obj.business
    
    # --- LOGO LOGIC (NEW) ---
    # If a logo exists, print it centered at the top
    if biz.logo and os.path.exists(biz.logo.path):
        # We want the logo to be about 20mm wide
        logo_w = 20
        # Center X calculation: (Page Width 80 - Logo Width 20) / 2 = 30
        x_pos = (80 - logo_w) / 2
        
        try:
            pdf.image(biz.logo.path, x=x_pos, y=5, w=logo_w)
            # Move cursor down so text doesn't overlap logo
            pdf.ln(15) 
        except Exception as e:
            print(f"Error printing logo: {e}")

    # --- HELPER ---
    def draw_dashed_line():
        pdf.set_font("Courier", '', 10)
        pdf.cell(0, 4, "-" * 38, 0, 1, 'C')

    # --- MATH & LOGIC ---
    mpesa_amount = float(receipt_obj.amount)
    items = receipt_obj.items.all()
    items_total = sum(float(item.cost) for item in items) if items else 0
    bill_total = items_total if items_total > 0 else mpesa_amount
    
    net_amount = bill_total / 1.16 if biz.charges_vat else bill_total
    vat_amount = bill_total - net_amount if biz.charges_vat else 0.0

    # --- HEADER ---
    pdf.set_font("Courier", 'B', 11)
    pdf.cell(0, 5, biz.business_name[:25].upper(), 0, 1, 'C')
    pdf.set_font("Courier", '', 9)
    pdf.cell(0, 4, "NAIROBI, KENYA", 0, 1, 'C')
    pdf.cell(0, 4, f"TEL: {biz.phone_number}", 0, 1, 'C')
    if biz.kra_pin:
        pdf.cell(0, 4, f"PIN: {biz.kra_pin.upper()}", 0, 1, 'C')
    
    pdf.ln(2)
    pdf.set_font("Courier", 'B', 10)
    title = "*** VAT RECEIPT ***" if biz.charges_vat else "*** PAYMENT RECEIPT ***"
    pdf.cell(0, 5, title, 0, 1, 'C')
    
    # --- META DATA ---
    draw_dashed_line()
    pdf.set_font("Courier", '', 9)
    
    nairobi_tz = pytz.timezone('Africa/Nairobi')
    if receipt_obj.transaction_date.tzinfo is None:
        local_date = nairobi_tz.localize(receipt_obj.transaction_date)
    else:
        local_date = receipt_obj.transaction_date.astimezone(nairobi_tz)
        
    date_str = local_date.strftime('%Y-%m-%d %H:%M:%S')
    
    pdf.cell(0, 4, f"Date: {date_str}", 0, 1, 'L')
    pdf.cell(0, 4, f"Ref No: {receipt_obj.mpesa_code}", 0, 1, 'L')
    pdf.cell(0, 4, f"Customer: {receipt_obj.customer_name.title()[:20]}", 0, 1, 'L')
    
    draw_dashed_line()

    # --- ITEMS ---
    pdf.set_font("Courier", 'B', 9)
    pdf.cell(45, 4, "ITEM", 0, 0, 'L')
    pdf.cell(0, 4, "TOTAL", 0, 1, 'R')
    pdf.set_font("Courier", '', 9)
    
    if not items:
        pdf.cell(45, 4, "M-Pesa Payment", 0, 0, 'L')
        pdf.cell(0, 4, f"{mpesa_amount:,.2f}", 0, 1, 'R')
    else:
        for item in items:
            pdf.cell(45, 4, item.description.title()[:22], 0, 0, 'L')
            pdf.cell(0, 4, f"{item.cost:,.2f}", 0, 1, 'R')

    draw_dashed_line()

    # --- TAX ANALYSIS ---
    def print_row(label, value, bold=False):
        pdf.set_font("Courier", 'B' if bold else '', 9)
        pdf.cell(40, 4, label, 0, 0, 'L')
        pdf.cell(0, 4, value, 0, 1, 'R')

    if biz.charges_vat:
        print_row("TOTAL NET:", f"{net_amount:,.2f}")
        print_row("VAT (16%):", f"{vat_amount:,.2f}")
        pdf.ln(1)

    # --- TOTALS ---
    pdf.set_font("Courier", 'B', 12)
    pdf.cell(40, 6, "TOTAL BILL:", 0, 0, 'L')
    pdf.cell(0, 6, f"{bill_total:,.2f}", 0, 1, 'R')
    
    # --- PAYMENT BREAKDOWN ---
    pdf.ln(1)
    draw_dashed_line()
    pdf.set_font("Courier", '', 9)
    
    print_row("M-PESA PAID:", f"{mpesa_amount:,.2f}")
    
    if mpesa_amount > bill_total:
        change = mpesa_amount - bill_total
        print_row("CHANGE:", f"{change:,.2f}")
    elif bill_total > mpesa_amount:
        balance = bill_total - mpesa_amount
        print_row("BALANCE DUE:", f"{balance:,.2f}", bold=True)

    draw_dashed_line()

    # --- FOOTER ---
    pdf.ln(2)
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(f"REF:{receipt_obj.mpesa_code}\nBILL:{bill_total}\nDATE:{date_str}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    qr_path = f"/tmp/qr_{receipt_obj.mpesa_code}.png"
    img.save(qr_path)
    pdf.image(qr_path, x=27.5, w=25)
    os.remove(qr_path)
    
    pdf.ln(4)
    pdf.set_font("Courier", '', 8)
    pdf.cell(0, 4, "Powered by ReceiptGen", 0, 1, 'C')
    pdf.ln(2)
    pdf.set_font("Courier", 'I', 6)
    pdf.multi_cell(0, 3, "System generated for internal records.\nNot a substitute for eTIMS invoice.", 0, 'C')

    pdf.output(output_path)
    return True