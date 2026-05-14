import colorsys
import math
import random

import numpy as np
import opensimplex
from PIL import Image, ImageDraw


# === Konfiguration ===
WIDTH, HEIGHT = 2560, 1440
HEX_RADIUS_BASE = 50  # Basis-Radius für die Hexagone
GAP_SIZE = 2

# === Noise Konfiguration (Das Fraktal) ===
SCALE = 400.0  # Der "Zoom-Faktor". Größer = breitere, weichere Pfade
OCTAVES = 4  # Die Anzahl der fraktalen Detail-Schichten
PERSISTENCE = 0.5  # Wie stark die Details ins Gewicht fallen
LACUNARITY = 2.0  # Wie "krisselig" die Details werden

SEED = np.random.randint(2, 999999) # Startwert für den Zufall

# === Random Offsets für Anti-Burn-In ===
# Verschiebt das gesamte Grid zufällig
GRID_OFFSET_X = random.randint(0, int(HEX_RADIUS_BASE * 2))
GRID_OFFSET_Y = random.randint(0, int(HEX_RADIUS_BASE * 2))
# Verschiebt den Startwert der Farben
HUE_OFFSET = random.random()

# === Tile-Arten ===
BG_COLOR = (0, 0, 0)
COLOR_DARK = (15, 15, 15)  # Berge (Hoch)
COLOR_ELEVATED = (35, 35, 35)  # Normal (Mittel)

# === Farbverlauf für helle Tiles (Täler) ===
COLOR_BRIGHTNESS = 0.8  # Helligkeit der farbigen Tiles (0.0 bis 1.0)

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
        angle_deg = 60 * i - 30
        angle_rad = math.pi / 180 * angle_deg
        px = x + draw_radius * math.cos(angle_rad)
        py = y + draw_radius * math.sin(angle_rad)
        vertices.append((px, py))
    return vertices

def apply_isometric(x, y, z, width, height, y_offset=0):
    """
    Wendet eine isometrische (orthografische) Projektion an.
    Kein Perspektiven-Scaling (Hexagone bleiben gleich groß).
    """
    # 1. Zentrieren für die Projektion
    cx = width / 2
    cy = height / 2

    # 2. Kippen um die X-Achse (Pitch) - Isometrisch/Schräg von oben
    pitch = math.pi / 4  # 45 Grad Neigung
    y_tilted = y * math.cos(pitch) - z * math.sin(pitch)
    # z wird für orthografisch nicht zur Skalierung genutzt

    # 3. Orthografische Projektion (kein Scaling durch Tiefe)
    # x bleibt, y_tilted wird auf den Bildschirm gelegt

    x_proj = x
    y_proj = y_tilted + cy + y_offset

    return x_proj, y_proj


def generate_wallpaper():
    image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    # Basis-Grid Größe (unprojiziert)
    # Da wir kippen, brauchen wir mehr Y-Reihen. Damit auch oben kein schwarzer Rand ist,
    # setzen wir den start_y noch weiter nach oben.
    grid_width = WIDTH + HEX_RADIUS_BASE * 4
    grid_height = int(HEIGHT * 2.0) + HEX_RADIUS_BASE * 4

    start_x = -HEX_RADIUS_BASE * 2 + GRID_OFFSET_X
    start_y = -HEIGHT + GRID_OFFSET_Y  # Noch weiter oben anfangen, um die obere Kante zu füllen

    hex_width = math.sqrt(3) * HEX_RADIUS_BASE
    hex_height = 2 * HEX_RADIUS_BASE
    cols = int(grid_width / hex_width) + 2
    rows = int(grid_height / (hex_height * 0.75)) + 2

    hexagons = []

    for row in range(rows):
        for col in range(cols):
            x = start_x + col * hex_width
            if row % 2 == 1:
                x += hex_width / 2
            y = start_y + row * hex_height * 0.75

            # Noise Sampling
            noise_val = fbm(x / SCALE, y / SCALE, OCTAVES, PERSISTENCE, LACUNARITY)

            # Umkehren der Höhen/Farben-Logik wie vom User gewünscht
            # Täler (bunt) < Normale Ebene (grau) < Berge (dunkel)

            # Höhe berechnen (z-Achse im lokalen Raum, positiv geht "nach oben")
            if noise_val > 0.2:
                # Berge (Hohe Werte)
                tile_color = COLOR_DARK
                height_z = 120 * noise_val
            elif noise_val > -0.2:
                # Normale Ebene
                tile_color = COLOR_ELEVATED
                height_z = 20 + 20 * noise_val
            else:
                # Täler (Niedrige Werte)
                # Bunter Farbverlauf + HUE_OFFSET
                hue = (((x - start_x) / grid_width) + ((y - start_y) / grid_height)) / 2.0
                hue = (hue + HUE_OFFSET) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, COLOR_BRIGHTNESS)
                tile_color = (int(r * 255), int(g * 255), int(b * 255))
                height_z = 0 # Täler sind ganz unten (flach)

            hexagons.append({
                'x': x,
                'y': y,
                'z': height_z,
                'color': tile_color,
                'noise': noise_val
            })

    # Sortieren für den Painter's Algorithm
    projected_hexagons = []
    y_offset = HEIGHT * 0.1 # Verschiebung auf dem Bildschirm

    for h in hexagons:
        x, y, z, color = h['x'], h['y'], h['z'], h['color']

        # Mittelpunkt projizieren (Dach)
        cx_top, cy_top = apply_isometric(x, y, z, WIDTH, HEIGHT, y_offset)

        # Eckpunkte Boden
        base_vertices = get_hex_vertices(x, y, HEX_RADIUS_BASE - GAP_SIZE)
        proj_base_vertices = [apply_isometric(vx, vy, 0, WIDTH, HEIGHT, y_offset) for vx, vy in base_vertices]

        # Eckpunkte Dach
        top_vertices = get_hex_vertices(x, y, HEX_RADIUS_BASE - GAP_SIZE)
        proj_top_vertices = [apply_isometric(vx, vy, z, WIDTH, HEIGHT, y_offset) for vx, vy in top_vertices]

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
            side_color_1 = darken_color(color, 0.6) # Links
            side_color_2 = darken_color(color, 0.4) # Rechts
            side_color_3 = darken_color(color, 0.5) # Unten

            # Eckpunkte des Hexagons aus get_hex_vertices:
            # 0: -30° (Top Right)
            # 1: 30° (Bottom Right)
            # 2: 90° (Bottom Center)
            # 3: 150° (Bottom Left)
            # 4: 210° (Top Left)
            # 5: 270° (Top Center)

            # Bei Isometrie/Kippen um X-Achse sind die sichtbaren Kanten:
            # 1-2 (Bottom Right zu Bottom Center)
            # 2-3 (Bottom Center zu Bottom Left)
            # Manchmal 0-1 (Top Right zu Bottom Right)
            # Manchmal 3-4 (Bottom Left zu Top Left)

            # Wir zeichnen die Wände von hinten nach vorne / Seiten nach Mitte

            # Wand Rechts Oben (0-1)
            draw.polygon([top_pts[0], top_pts[1], base_pts[1], base_pts[0]], fill=side_color_2)
            # Wand Links Oben (3-4)
            draw.polygon([top_pts[3], top_pts[4], base_pts[4], base_pts[3]], fill=side_color_1)

            # Wand Rechts Unten (1-2)
            draw.polygon([top_pts[1], top_pts[2], base_pts[2], base_pts[1]], fill=darken_color(side_color_2, 0.8))
            # Wand Links Unten (2-3)
            draw.polygon([top_pts[2], top_pts[3], base_pts[3], base_pts[2]], fill=darken_color(side_color_1, 0.8))

        # Dach zeichnen
        draw.polygon(top_pts, fill=color)

    return image


if __name__ == "__main__":
    print("Generiere organische OLED Wallpaper Basis mit OpenSimplex...")
    img = generate_wallpaper()
    img.save("oled_simplex_grid.png")
    print("Erledigt! Bild wurde als 'oled_simplex_grid.png' gespeichert.")
