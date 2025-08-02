from PIL import Image, ImageDraw, ImageFont

# 1) Загружаем схему зала
base = Image.open("hall_map.png").convert("RGBA")
draw = ImageDraw.Draw(base)

# 2) Координаты столиков на изображении (пример)
#    ключ — имя столика, значение — (x, y) центра круга
coords = {
    "VIP-1": (100, 150),
    "VIP-2": (200, 150),
    "Балкон-1": (100, 300),
    "Б-2": (200, 300),
    "Т-1": (100, 450),
    "Т-2": (200, 450),
    "Бар-1": (150, 600),
}

# 3) Статус брони: True = занято (🔴), False = свободно (🟢)
#    В реальном коде получаем из БД или списка reservations
status = {
    "VIP-1": True,
    "VIP-2": False,
    "Балкон-1": True,
    "Б-2": False,
    "Т-1": False,
    "Т-2": True,
    "Бар-1": False,
}

# 4) Рисуем кружки
radius = 15
for table, (x, y) in coords.items():
    color = (255, 0, 0, 200) if status.get(table, False) else (0, 255, 0, 200)
    draw.ellipse(
        [(x - radius, y - radius), (x + radius, y + radius)],
        fill=color,
        outline=(0,0,0)
    )

# 5) Сохраняем итог
base.save("hall_map_status.png")
print("Saved hall_map_status.png")
