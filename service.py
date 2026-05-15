import colorsys
import math
import random
import subprocess
import os
import time
import glob

import numpy as np
import opensimplex
from PIL import Image, ImageDraw

# === Konfiguration ===
SUPERSAMPLE = 4
# Breite verdoppelt für zwei WQHD Monitore!
WIDTH, HEIGHT = 2560 * 2, 1440

GAP_SIZE = 0
HEIGHT_ELEVATET = 80
HEIGHT_BASE = 40
SPECTRUM_STRETCH = 1.5

RENDER_WIDTH = WIDTH * SUPERSAMPLE
RENDER_HEIGHT = HEIGHT * SUPERSAMPLE

# === Noise Konfiguration (Das Fraktal) ===
SCALE = RENDER_WIDTH * 0.7
X_SCALE = SCALE * 1.5
Y_SCALE = SCALE * 1.5
OCTAVES = 3
PERSISTENCE = 0.8
LACUNARITY = 2.0

HILL_PERCENTAGE = 0.35
PLAINS_PERCENTAGE = 0.45
TALE_PERCENTAGE = 1 - HILL_PERCENTAGE - PLAINS_PERCENTAGE

# === Tile-Arten ===
BG_COLOR = (0, 0, 0)
COLOR_DARK = (15, 15, 15)
COLOR_ELEVATED = (25, 25, 25)
COLOR_BRIGHTNESS = 1


def fbm(x, y, octaves, persistence, lacunarity):
    total = 0.0
    frequency = 1.0
    amplitude = 1.0
    max_value = 0.0
    for _ in range(octaves):
        total += opensimplex.noise2(x * frequency, y * frequency) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity
    return total / max_value


def darken_color(color, factor=0.7):
    return int(color[0] * factor), int(color[1] * factor), int(color[2] * factor)


def get_hex_vertices(x, y, draw_radius):
    vertices = []
    for i in range(6):
        angle_deg = 60 * i
        angle_rad = math.pi / 180 * angle_deg
        px = x + draw_radius * math.cos(angle_rad)
        py = y + draw_radius * math.sin(angle_rad)
        vertices.append((px, py))
    return vertices


def generate_wallpaper():
    MAX_RETRIES = 15  # Maximale Versuche für ein ausbalanciertes Bild

    for attempt in range(MAX_RETRIES):
        SEED = np.random.randint(2, 9999999)
        base_r = 30
        current_hex_radius = base_r * SUPERSAMPLE
        opensimplex.seed(SEED)
        HUE_OFFSET = random.random()

        MAX_OFFSET_X = int(current_hex_radius * 2)
        MAX_OFFSET_Y = int(current_hex_radius * 2)
        GRID_OFFSET_X = random.randint(0, MAX_OFFSET_X)
        GRID_OFFSET_Y = random.randint(0, MAX_OFFSET_Y)

        # Basis-Grid Größe berechnen
        grid_width = RENDER_WIDTH + current_hex_radius * 4 + (MAX_OFFSET_X * SUPERSAMPLE)
        grid_height = int(RENDER_HEIGHT * 2.0) + current_hex_radius * 4 + (MAX_OFFSET_Y * SUPERSAMPLE)

        start_x = -current_hex_radius * 2 - (MAX_OFFSET_X * SUPERSAMPLE) + (GRID_OFFSET_X * SUPERSAMPLE)
        start_y = -RENDER_HEIGHT - (MAX_OFFSET_Y * SUPERSAMPLE) + (GRID_OFFSET_Y * SUPERSAMPLE)

        hex_width = 2 * current_hex_radius
        hex_height = math.sqrt(3) * current_hex_radius
        cols = int(grid_width / (hex_width * 0.75)) + 2
        rows = int(grid_height / hex_height) + 2

        hexagons_temp = []
        all_noise_values = []

        huge_shifter_x = random.randint(0, int(X_SCALE * 10))
        huge_shifter_y = random.randint(0, int(Y_SCALE * 10))

        # 1. Rauschen für alle Hexagone berechnen
        for col in range(cols):
            for row in range(rows):
                x = start_x + col * hex_width * 0.75
                y = start_y + row * hex_height
                if col % 2 == 1:
                    y += hex_height / 2

                noise_x = (x + huge_shifter_x) / X_SCALE
                noise_y = (y + huge_shifter_y) / Y_SCALE

                noise_val = fbm(noise_x, noise_y, OCTAVES, PERSISTENCE, LACUNARITY)
                noise_val = abs(noise_val)

                all_noise_values.append(noise_val)
                hexagons_temp.append({'x': x, 'y': y, 'noise': noise_val})

        # 2. Schwellenwerte berechnen
        all_noise_values.sort()
        total_hexes = len(all_noise_values)

        idx_valley_end = int(total_hexes * TALE_PERCENTAGE)
        idx_plains_end = int(total_hexes * (TALE_PERCENTAGE + PLAINS_PERCENTAGE))

        thresh_valley = all_noise_values[min(idx_valley_end, total_hexes - 1)]
        thresh_plains = all_noise_values[min(idx_plains_end, total_hexes - 1)]

        # === 3. BALANCE-CHECK (Rejection Sampling) ===
        left_valleys = 0
        right_valleys = 0
        mitte_x = RENDER_WIDTH / 2.0

        for h in hexagons_temp:
            if h['noise'] < thresh_valley:
                # Wir zählen nur Hexagone, die wirklich auf dem Bildschirm liegen
                if -current_hex_radius <= h['x'] <= RENDER_WIDTH + current_hex_radius:
                    if h['x'] < mitte_x:
                        left_valleys += 1
                    else:
                        right_valleys += 1

        total_valleys = left_valleys + right_valleys

        if total_valleys == 0:
            continue  # Vermeidet Division durch Null bei extremen Ausreißern

        left_ratio = left_valleys / total_valleys

        # Check: Liegt der Anteil des linken Monitors zwischen 40% und 60%?
        if 0.40 <= left_ratio <= 0.60:
            print(f"Versuch {attempt + 1}: Balance OK! Monitor L: {left_ratio:.1%} | Monitor R: {1 - left_ratio:.1%}")
            break  # Erfolgreich! Wir verlassen die for-Schleife und behalten diese Werte.
        else:
            print(f"Versuch {attempt + 1} verworfen (Unwucht L: {left_ratio:.1%}). Generiere neu...")

    # ====================================================================
    # AB HIER WIRD GEZEICHNET (Läuft nur für den erfolgreichen Versuch)
    # ====================================================================

    image = Image.new("RGB", (RENDER_WIDTH, RENDER_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    projected_hexagons = []
    y_offset = RENDER_HEIGHT * 0.1

    pitch = math.pi / 3
    pitch_cos = math.cos(pitch)
    pitch_sin = math.sin(pitch)
    cy_render = RENDER_HEIGHT / 3
    hex_base_offsets = get_hex_vertices(0, 0, current_hex_radius - GAP_SIZE)

    SIDE_COLOR_ELEVATED = darken_color(COLOR_ELEVATED, 0.1)
    SIDE_COLOR_DARK = darken_color(COLOR_DARK, 0.1)

    for h in hexagons_temp:
        x = h['x']
        y = h['y']
        noise_val = h['noise']

        if noise_val >= thresh_plains:
            color = COLOR_ELEVATED
            z = HEIGHT_ELEVATET
            side_color = SIDE_COLOR_ELEVATED
            outline_color = BG_COLOR
        elif noise_val >= thresh_valley:
            color = COLOR_DARK
            z = HEIGHT_BASE
            side_color = SIDE_COLOR_DARK
            outline_color = BG_COLOR
        else:
            hue = (((x - start_x) / grid_width) + ((y - start_y) / grid_height)) / 2.0
            hue = (hue / SPECTRUM_STRETCH + HUE_OFFSET) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, COLOR_BRIGHTNESS)
            color = (int(r * 220), int(g * 220), int(b * 220))
            z = 0
            side_color = darken_color(color, 0.1)
            core_r, core_g, core_b = colorsys.hsv_to_rgb(hue, 0.75, COLOR_BRIGHTNESS)
            outline_color = (int(core_r * 255), int(core_g * 255), int(core_b * 255))

        # Culling - Überspringt das Zeichnen von nicht sichtbaren Hexagonen
        if x < -current_hex_radius * 4 or x > RENDER_WIDTH + current_hex_radius * 4:
            continue

        proj_base_vertices = []
        proj_top_vertices = []

        for dx, dy in hex_base_offsets:
            vx = x + dx
            vy = y + dy
            vy_tilted_base = vy * pitch_cos
            proj_base_vertices.append((vx, vy_tilted_base + cy_render + y_offset))
            vy_tilted_top = vy * pitch_cos - z * pitch_sin
            proj_top_vertices.append((vx, vy_tilted_top + cy_render + y_offset))

        projected_hexagons.append({
            'sort_y': y,
            'base_pts': proj_base_vertices,
            'top_pts': proj_top_vertices,
            'color': color,
            'side_color': side_color,
            'outline_color': outline_color,
            'z_height': z
        })

    # Painter's Algorithm: Von hinten nach vorne sortieren
    projected_hexagons.sort(key=lambda item: item['sort_y'])

    # Finales Zeichnen
    for h in projected_hexagons:
        base_pts = h['base_pts']
        top_pts = h['top_pts']
        color = h['color']
        side_color = h['side_color']
        outline_color = h['outline_color']

        if h['z_height'] > 1:
            draw.polygon([top_pts[0], top_pts[1], base_pts[1], base_pts[0]], fill=side_color)
            draw.polygon([top_pts[1], top_pts[2], base_pts[2], base_pts[1]], fill=side_color)
            draw.polygon([top_pts[2], top_pts[3], base_pts[3], base_pts[2]], fill=side_color)

        draw.polygon(top_pts, fill=color)
        draw.line(top_pts + [top_pts[0]], fill=outline_color, width=3)

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return image


def set_kde_wallpaper(path_left, path_right):
    """Weist KDE Plasma die beiden Bildhälften den Monitoren zu"""
    kde_script = f"""
    var allDesktops = desktops();
    for (i=0; i<allDesktops.length; i++) {{
        d = allDesktops[i];
        d.wallpaperPlugin = "org.kde.image";
        d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
        if (i == 0) {{
            d.writeConfig("Image", "file://{path_right}");
        }} else if (i == 1) {{
            d.writeConfig("Image", "file://{path_left}");
        }}
    }}
    """
    try:
        # dbus-send ist unter Linux absolut standard und immer installiert
        subprocess.run([
            "dbus-send", "--session", "--dest=org.kde.plasmashell",
            "--type=method_call", "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript", f"string:{kde_script}"
        ], check=True)
    except Exception as e:
        print(f"Fehler beim Setzen des Wallpapers: {e}")


if __name__ == "__main__":
    BASE_PATH = "/dev/shm/"

    print("Generiere 5120x1440 OLED Wallpaper...")
    img = generate_wallpaper()

    # Schneide das Bild exakt in zwei Hälften
    img_left = img.crop((0, 0, 2560, 1440))
    img_right = img.crop((2560, 0, 5120, 1440))

    # 1. MÜLLABFUHR: Alte Bilder im RAM löschen
    old_files = glob.glob(os.path.join(BASE_PATH, "oled_grid_*.png"))
    for f in old_files:
        try:
            os.remove(f)
        except OSError:
            pass

    # 2. Einzigartigen Dateinamen generieren (Unix-Timestamp)
    timestamp = int(time.time())
    path_left = os.path.join(BASE_PATH, f"oled_grid_left_{timestamp}.png")
    path_right = os.path.join(BASE_PATH, f"oled_grid_right_{timestamp}.png")

    # 3. Neue Bilder speichern
    img_left.save(path_left)
    img_right.save(path_right)

    print("Bilder gespeichert. Sende DBus Kommando an KDE Plasma...")
    set_kde_wallpaper(path_left, path_right)
    print("Erledigt!")