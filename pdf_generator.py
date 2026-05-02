from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_invoice_pdf(order):
    filename = f"/tmp/{order['order_number']}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)
    y = 800

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "Vendora Shop")
    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Order Number: {order['order_number']}")
    y -= 25
    c.drawString(50, y, f"Customer: {order['customer_name']}")
    y -= 25
    c.drawString(50, y, f"Phone: {order['phone']}")
    y -= 25
    c.drawString(50, y, f"Address: {order['address']}")
    y -= 40

    c.drawString(50, y, "Products:")
    y -= 25

    for item in order["cart"]:
        line = f"{item['name']} x {item['qty']} = {item['price']*item['qty']} NIS"
        c.drawString(50, y, line)
        y -= 20

    y -= 20
    c.drawString(50, y, f"Products Total: {order['products_total']} NIS")
    y -= 20
    c.drawString(50, y, f"Delivery: {order['delivery_price']} NIS")
    y -= 20
    c.drawString(50, y, f"Final Total: {order['final_total']} NIS")

    c.save()
    return filename
