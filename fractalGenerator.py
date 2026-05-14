import colorsys
import math
import random

import numpy as np
import opensimplex
from PIL import Image, ImageDraw


# === Konfiguration ===
SUPERSAMPLE = 4
WIDTH, HEIGHT = 2560, 1440
HEX_RADIUS_BASE = 80 * SUPERSAMPLE # Basis-Radius für die Hexagone
GAP_SIZE = 0



RENDER_WIDTH = WIDTH * SUPERSAMPLE
RENDER_HEIGHT = HEIGHT * SUPERSAMPLE
# === Noise Konfiguration (Das Fraktal) ===
SCALE = RENDER_WIDTH * 0.9  # Der "Zoom-Faktor". Größer = breitere, weichere Pfade


X_SCALE = SCALE * 1.2
Y_SCALE = SCALE * 0.8
OCTAVES = 2 # Die Anzahl der fraktalen Detail-Schichten
PERSISTENCE = 0.4  # Wie stark die Details ins Gewicht fallen
LACUNARITY = 2.0  # Wie "krisselig" die Details werden

SEED = np.random.randint(2, 999999) # Startwert für den Zufall


HILL_PERCENTAGE = 0.3
PLAINS_PERCENTAGE = 0.5
TALE_PERCENTAGE = 1 - HILL_PERCENTAGE - PLAINS_PERCENTAGE

# === Random Offsets für Anti-Burn-In ===
# Verschiebt das gesamte Grid zufällig
GRID_OFFSET_X = random.randint(0, int(HEX_RADIUS_BASE * 2))
GRID_OFFSET_Y = random.randint(0, int(HEX_RADIUS_BASE * 2))
HUE_OFFSET = random.random()

endrandomizen =False
if endrandomizen:
    SEED=1
    GRID_OFFSET_X=0
    GRID_OFFSET_Y=0
    HUE_OFFSET = 0
# Verschiebt den Startwert der Farben


# === Tile-Arten ===
BG_COLOR = (0, 0, 0)
COLOR_DARK = (20, 20, 20)
COLOR_ELEVATED = (30, 30, 30)

# === Farbverlauf für helle Tiles (Täler) ===
COLOR_BRIGHTNESS = 1  # Helligkeit der farbigen Tiles (0.0 bis 1.0)

# Setze den Seed für das Rauschen
opensimplex.seed(SEED)


def fbm(x, y, octaves, persistence, lacunarity):
    """
    Fractal Brownian Motion (FBM)
    Überlagert mehrere Schichten (Octaves) von Rauschen für organische Details.
    """
    total = 0.0
    frequency = 1.0
    amplitude = 1.0
    max_value = 0.0  # Zum Normalisieren des Ergebnisses

    for _ in range(octaves):
        # opensimplex.noise2 gibt Werte zwischen ca. -1.0 und 1.0 zurück
        total += opensimplex.noise2(x * frequency, y * frequency) * amplitude
        max_value += amplitude

        amplitude *= persistence
        frequency *= lacunarity

    return total / max_value


def darken_color(color, factor=0.7):
    """Macht eine RGB-Farbe dunkler."""
    return tuple(int(max(0, c * factor)) for c in color)


def get_hex_vertices(x, y, draw_radius):
    """Berechnet die 6 Eckpunkte eines Hexagons (flach)."""
    vertices = []
    # Index 0: -30 deg -> 330 deg (Top Right)
    # Index 1: 30 deg (Bottom Right)
    # Index 2: 90 deg (Bottom)
    # Index 3: 150 deg (Bottom Left)
    # Index 4: 210 deg (Top Left)
    # Index 5: 270 deg (Top)
    for i in range(6):
        angle_deg = 60 * i #- 30
        angle_rad = math.pi / 180 * angle_deg
        px = x + draw_radius * math.cos(angle_rad)
        py = y + draw_radius * math.sin(angle_rad)
        vertices.append((px, py))
    return vertices

def apply_isometric(x, y, z, width, height, y_offset=0):


    cy = height / 3
    pitch = math.pi / 3  # 45 Grad Neigung
    y_tilted = y * math.cos(pitch) - z * math.sin(pitch)
    x_proj = x
    y_proj = y_tilted + cy + y_offset

    return x_proj, y_proj


def generate_wallpaper():
    image = Image.new("RGB", (RENDER_WIDTH, RENDER_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    # Basis-Grid Größe (unprojiziert)
    grid_width = RENDER_WIDTH + HEX_RADIUS_BASE * 4
    grid_height = int(RENDER_HEIGHT * 2.0) + HEX_RADIUS_BASE * 4

    start_x = -HEX_RADIUS_BASE * 2 + (GRID_OFFSET_X * SUPERSAMPLE)
    start_y = -RENDER_HEIGHT + (GRID_OFFSET_Y * SUPERSAMPLE)

    hex_width = 2 * HEX_RADIUS_BASE
    hex_height = math.sqrt(3) * HEX_RADIUS_BASE
    cols = int(grid_width / (hex_width * 0.75)) + 2
    rows = int(grid_height / hex_height) + 2

    hexagons_temp = []
    all_noise_values = []

    for col in range(cols):
        for row in range(rows):
            x = start_x + col * hex_width * 0.75
            y = start_y + row * hex_height
            if col % 2 == 1:
                y += hex_height / 2

            # Noise mit Streckung berechnen
            noise_val = fbm(x / X_SCALE, y / Y_SCALE, OCTAVES, PERSISTENCE, LACUNARITY)
            noise_val = abs(noise_val)  # Ridge-Noise (Flüsse erzwingen)

            all_noise_values.append(noise_val)
            hexagons_temp.append({'x': x, 'y': y, 'noise': noise_val})

    # === 2. Werte sortieren und exakte Schwellenwerte berechnen ===
    all_noise_values.sort()
    total_hexes = len(all_noise_values)

    idx_valley_end = int(total_hexes * TALE_PERCENTAGE)
    idx_plains_end = int(total_hexes * (TALE_PERCENTAGE + PLAINS_PERCENTAGE))

    thresh_valley = all_noise_values[min(idx_valley_end, total_hexes - 1)]
    thresh_plains = all_noise_values[min(idx_plains_end, total_hexes - 1)]

    # === 3. Farben und Höhen final zuweisen ===
    hexagons = []

    for h in hexagons_temp:
        x = h['x']
        y = h['y']
        noise_val = h['noise']  # Den identischen Noise-Wert auslesen!

        if noise_val >= thresh_plains:
            # Berge (Die obersten X Prozent)
            tile_color = COLOR_ELEVATED
            height_z = 20
        elif noise_val >= thresh_valley:
            # Normale Ebene (Die mittleren X Prozent)
            tile_color = COLOR_DARK
            height_z = 10
        else:
            # Täler (Die untersten X Prozent, ganz nah an der Null-Linie)
            hue = (((x - start_x) / grid_width) + ((y - start_y) / grid_height)) / 2.0
            hue = (hue + HUE_OFFSET) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, COLOR_BRIGHTNESS)
            tile_color = (int(r * 255), int(g * 255), int(b * 255))
            height_z = 0

        hexagons.append({
            'x': x,
            'y': y,
            'z': height_z,
            'color': tile_color,
            'noise': noise_val
        })

    # Sortieren für den Painter's Algorithm
    projected_hexagons = []
    y_offset = RENDER_HEIGHT * 0.1 # Verschiebung auf dem Bildschirm

    for h in hexagons:
        x, y, z, color = h['x'], h['y'], h['z'], h['color']

        # Mittelpunkt projizieren (Dach)
        cx_top, cy_top = apply_isometric(x, y, z, WIDTH, HEIGHT, y_offset)

        # Eckpunkte Boden
        base_vertices = get_hex_vertices(x, y, HEX_RADIUS_BASE - GAP_SIZE)
        proj_base_vertices = [apply_isometric(vx, vy, 0, RENDER_WIDTH, RENDER_HEIGHT, y_offset) for vx, vy in base_vertices]

        # Eckpunkte Dach
        top_vertices = get_hex_vertices(x, y, HEX_RADIUS_BASE - GAP_SIZE)
        proj_top_vertices = [apply_isometric(vx, vy, z, RENDER_WIDTH, RENDER_HEIGHT, y_offset) for vx, vy in top_vertices]

        # Sortierkriterium: y im unprojizierten Raum
        projected_hexagons.append({
            'sort_y': y,
            'base_pts': [(p[0], p[1]) for p in proj_base_vertices],
            'top_pts': [(p[0], p[1]) for p in proj_top_vertices],
            'color': color,
            'z_height': z
        })

    # Painter's Algorithm: Sortieren nach y aufsteigend (kleines y = weiter hinten)
    projected_hexagons.sort(key=lambda item: item['sort_y'])

    # Zeichnen
    for h in projected_hexagons:
        base_pts = h['base_pts']
        top_pts = h['top_pts']
        color = h['color']
        z_height = h['z_height']

        # Kanten (Säulenwände) zeichnen
        if z_height > 1:
            side_color_r = darken_color(color, 0.2)  # Rechte Wand (am dunkelsten)
            side_color_f = darken_color(color, 0.2)  # Frontale Wand (heller, blickt zu uns)
            side_color_l = darken_color(color, 0.2)  # Linke Wand

            # Wand Rechts (Eckpunkte 0 und 1)
            draw.polygon([top_pts[0], top_pts[1], base_pts[1], base_pts[0]], fill=side_color_r)
            # Wand Vorne / Front (Eckpunkte 1 und 2) -> Parallel zum Bildschirmrand!
            draw.polygon([top_pts[1], top_pts[2], base_pts[2], base_pts[1]], fill=side_color_f)
            # Wand Links (Eckpunkte 2 und 3)
            draw.polygon([top_pts[2], top_pts[3], base_pts[3], base_pts[2]], fill=side_color_l)

        # Dach zeichnen
        draw.polygon(top_pts, fill=color, outline=BG_COLOR, width=2)
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return image


if __name__ == "__main__":
    print("Generiere organische OLED Wallpaper Basis mit OpenSimplex...")
    img = generate_wallpaper()
    img.save("oled_simplex_grid.png")
    print("Erledigt! Bild wurde als 'oled_simplex_grid.png' gespeichert.")
