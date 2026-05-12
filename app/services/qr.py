import os
import qrcode


def generate_qr(link: str, business_id: int) -> str:
    os.makedirs("static", exist_ok=True)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    path = f"static/qr_{business_id}.png"
    img.save(path)
    return path
