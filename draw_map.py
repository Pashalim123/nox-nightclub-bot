from PIL import Image, ImageDraw
from io import BytesIO

def draw_map(booked_seats: list) -> BytesIO:
    """
    Рисует простую схему зала 4x4,
    отмечая индексы из booked_seats красным, остальные — зелёным.
    Возвращает BytesIO с PNG.
    """
    size = 400
    img = Image.new('RGB',(size,size),'white')
    draw = ImageDraw.Draw(img)
    n = 4
    cell = size // n
    for i in range(n):
        for j in range(n):
            idx = i*n + j
            x0, y0 = j*cell, i*cell
            x1, y1 = x0+cell, y0+cell
            color = 'red' if idx in booked_seats else 'green'
            draw.rectangle([x0+5,y0+5,x1-5,y1-5], fill=color)
            draw.text((x0+10,y0+10), str(idx+1), fill='white')
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio
