from PIL import Image, ImageDraw

# Настройте эти координаты под вашу схему (пример)
SEAT_COORDS = {
    1: (100, 200),
    2: (100, 300),
    3: (100, 400),
    4: (400, 300),
}

def draw_map(reservations: dict, base_path="hall_base.png", out_path="hall_map.png"):
    """
    reservations: {номер_стола: True/False}, True = занято, False = свободно
    """
    im = Image.open(base_path).convert("RGBA")
    draw = ImageDraw.Draw(im)
    r = 15  # радиус точки

    for seat, (x, y) in SEAT_COORDS.items():
        color = (255, 0, 0, 255) if reservations.get(seat) else (0, 200, 0, 255)
        draw.ellipse((x-r, y-r, x+r, y+r), fill=color)

    im.save(out_path)
    return out_path

if __name__ == "__main__":
    # тестовый вызов
    demo = {1: True, 2: False, 3: True, 4: False}
    draw_map(demo)
    print("Saved hall_map.png")
