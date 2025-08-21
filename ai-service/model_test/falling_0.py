import os

# Klasör yolunu buraya yaz
image_folder = r"C:\Users\duggy\OneDrive\Masaüstü\not-falling"

# Klasördeki tüm dosyaları al ve sadece dosya olanları filtrele
files = [f for f in os.listdir(image_folder) if os.path.isfile(os.path.join(image_folder, f))]

# Zaten yeniden adlandırılmış dosyaları bulmak için desen
existing_numbers = []

for f in files:
    if f.startswith("fallingtest_0_") and f.endswith((".jpg", ".jpeg", ".png")):
        try:
            number = int(f.split("_")[2].split(".")[0])
            existing_numbers.append(number)
        except ValueError:
            continue

# En son kullanılan sayıyı bul (yoksa -1)
last_number = max(existing_numbers) if existing_numbers else -1

# Yeni dosyaları bu sayıdan sonra adlandır
counter = last_number + 1

# Sadece henüz adlandırılmamış dosyaları yeniden adlandır
for filename in files:
    # Eğer zaten "fallingtest_" ile başlamıyorsa işlem yap
    if not filename.startswith("fallingtest_0_"):
        name, ext = os.path.splitext(filename)
        new_name = f"fallingtest_0_{counter:04d}{ext}"
        old_path = os.path.join(image_folder, filename)
        new_path = os.path.join(image_folder, new_name)

        try:
            os.rename(old_path, new_path)
            print(f"{filename} -> {new_name}")
            counter += 1
        except FileExistsError:
            print(f"Hata: {new_name} zaten mevcut!")
            counter += 1  # Bir sonraki sayıya geç