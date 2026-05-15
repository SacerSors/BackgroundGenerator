import colorsys
import math
import random

import numpy as np
import opensimplex
from PIL import Image, ImageDraw


# === Konfiguration ===
SUPERSAMPLE = 4
WIDTH, HEIGHT = 2560, 1440

GAP_SIZE = 0
HEIGHT_ELEVATET = 80
HEIGHT_BASE = 40
SPECTRUM_STRETCH = 1.5


RENDER_WIDTH = WIDTH * SUPERSAMPLE
RENDER_HEIGHT = HEIGHT * SUPERSAMPLE
# === Noise Konfiguration (Das Fraktal) ===
SCALE = RENDER_WIDTH * 0.7  # Der "Zoom-Faktor". Größer = breitere, weichere Pfade


X_SCALE = SCALE * 1.5
Y_SCALE = SCALE * 1.5
OCTAVES = 3 # Die Anzahl der fraktalen Detail-Schichten
PERSISTENCE = 0.8  # Wie stark die Details ins Gewicht fallen
LACUNARITY = 2.0  # Wie "krisselig" die Details werden




HILL_PERCENTAGE = 0.35
PLAINS_PERCENTAGE = 0.45
TALE_PERCENTAGE = 1 - HILL_PERCENTAGE - PLAINS_PERCENTAGE

# === Random Offsets für Anti-Burn-In ===
# Verschiebt das gesamte Grid zufällig (Verschiebung um bis zu 1 Hexagon)



endrandomizen =False
if endrandomizen:
    SEED=1
    GRID_OFFSET_X=0
    GRID_OFFSET_Y=0
    HUE_OFFSET = 0
# Verschiebt den Startwert der Farben


# === Tile-Arten ===
BG_COLOR = (0, 0, 0)
COLOR_DARK = (15, 15, 15)
COLOR_ELEVATED = (25, 25, 25)

# === Farbverlauf für helle Tiles (Täler) ===
COLOR_BRIGHTNESS = 1  # Helligkeit der farbigen Tiles (0.0 bis 1.0)




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

    return int(color[0] * factor), int(color[1] * factor), int(color[2] * factor)


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
    # Setze den Seed für das Rauschen
    SEED = np.random.randint(2, 9999999)  # Startwert für den Zufall
    base_r = random.randint(40, 110)
    base_r = 30
    current_hex_radius = base_r * SUPERSAMPLE
    opensimplex.seed(SEED)
    HUE_OFFSET = random.random()


    MAX_OFFSET_X = int(current_hex_radius * 2 )
    MAX_OFFSET_Y = int(current_hex_radius * 2 )
    GRID_OFFSET_X = random.randint(0, MAX_OFFSET_X)
    GRID_OFFSET_Y = random.randint(0, MAX_OFFSET_Y)

    image = Image.new("RGB", (RENDER_WIDTH, RENDER_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    # Basis-Grid Größe (unprojiziert)
    # Wir machen das Grid groß genug, um den maximalen Offset in jede Richtung abzudecken.
    grid_width = RENDER_WIDTH + current_hex_radius * 4 + (MAX_OFFSET_X * SUPERSAMPLE)
    grid_height = int(RENDER_HEIGHT * 2.0) + current_hex_radius * 4 + (MAX_OFFSET_Y * SUPERSAMPLE)

    # Wir beginnen weiter im Negativen, damit auch bei einer positiven Verschiebung
    # durch den GRID_OFFSET keine schwarzen Ränder (links/oben) entstehen.
    start_x = -current_hex_radius * 2 - (MAX_OFFSET_X * SUPERSAMPLE) + (GRID_OFFSET_X * SUPERSAMPLE)
    start_y = -RENDER_HEIGHT - (MAX_OFFSET_Y * SUPERSAMPLE) + (GRID_OFFSET_Y * SUPERSAMPLE)

    hex_width = 2 * current_hex_radius
    hex_height = math.sqrt(3) * current_hex_radius
    cols = int(grid_width / (hex_width * 0.75)) + 2
    rows = int(grid_height / hex_height) + 2

    hexagons_temp = []
    all_noise_values = []

    # Offset für x und y damit nosie an (0,0) nicht ähnlich ist)
    huge_shifter_x = random.randint(0, int(X_SCALE * 10))
    huge_shifter_y = random.randint(0, int(Y_SCALE * 10))

    for col in range(cols):
        for row in range(rows):
            x = start_x + col * hex_width * 0.75
            y = start_y + row * hex_height
            if col % 2 == 1:
                y += hex_height / 2




            # Noise mit Streckung  und offset berechnen
            noise_x = (x + huge_shifter_x) / X_SCALE
            noise_y = (y + huge_shifter_y) / Y_SCALE

            noise_val = fbm(noise_x, noise_y, OCTAVES, PERSISTENCE, LACUNARITY)
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

    # === 3. Farben, Höhen und Projektion IN EINEM SCHRITT ===
    projected_hexagons = []
    y_offset = RENDER_HEIGHT * 0.1

    # Vorberechnete Konstanten für Isometrie
    pitch = math.pi / 3
    pitch_cos = math.cos(pitch)
    pitch_sin = math.sin(pitch)
    cy_render = RENDER_HEIGHT / 3
    hex_base_offsets = get_hex_vertices(0, 0, current_hex_radius - GAP_SIZE)

    # Vorberechnete Schatten-Farben (spart zehntausende Rechenoperationen!)
    SIDE_COLOR_ELEVATED = darken_color(COLOR_ELEVATED, 0.1)
    SIDE_COLOR_DARK = darken_color(COLOR_DARK, 0.1)

    for h in hexagons_temp:
        x = h['x']
        y = h['y']
        noise_val = h['noise']

        # 1. Farbe, Höhe und Schattenfarbe bestimmen
        if noise_val >= thresh_plains:  #-------------- Gray Hills------------------
            color = COLOR_ELEVATED
            z = HEIGHT_ELEVATET
            side_color = SIDE_COLOR_ELEVATED
            outline_color = BG_COLOR
        elif noise_val >= thresh_valley:    #-------------- Black Plains------------------
            color = COLOR_DARK
            z = HEIGHT_BASE
            side_color = SIDE_COLOR_DARK
            outline_color = BG_COLOR
        else:       #-------------- Colored Tales------------------
            hue = (((x - start_x) / grid_width) + ((y - start_y) / grid_height)) / 2.0
            hue = (hue / SPECTRUM_STRETCH + HUE_OFFSET) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, COLOR_BRIGHTNESS)
            color = (int(r * 220), int(g * 220), int(b * 220))
            z = 0
            # Nur für die bunten Täler müssen wir den Schatten dynamisch berechnen
            side_color = darken_color(color, 0.1)

            core_r, core_g, core_b = colorsys.hsv_to_rgb(hue, 0.75, COLOR_BRIGHTNESS)
            outline_color = (int(core_r * 255), int(core_g * 255), int(core_b * 255))

            # === OPTIONALES CULLING (Ignoriert Hexagone, die weit links/rechts außerhalb des Bildschirms liegen) ===
        if x < -current_hex_radius * 4 or x > RENDER_WIDTH + current_hex_radius * 4:
            continue

        # 2. Sofort projizieren
        proj_base_vertices = []
        proj_top_vertices = []

        for dx, dy in hex_base_offsets:
            vx = x + dx
            vy = y + dy

            # Boden (z=0)
            vy_tilted_base = vy * pitch_cos
            proj_base_vertices.append((vx, vy_tilted_base + cy_render + y_offset))

            # Dach (z=z)
            vy_tilted_top = vy * pitch_cos - z * pitch_sin
            proj_top_vertices.append((vx, vy_tilted_top + cy_render + y_offset))

        # 3. Direkt in die finale Liste speichern
        projected_hexagons.append({
            'sort_y': y,
            'base_pts': proj_base_vertices,
            'top_pts': proj_top_vertices,
            'color': color,
            'side_color': side_color,  # Wir übergeben die fertig berechnete Schattenfarbe
            'outline_color': outline_color,
            'z_height': z
        })

    # Painter's Algorithm: Sortieren nach y
    projected_hexagons.sort(key=lambda item: item['sort_y'])

    # === 4. Zeichnen (jetzt viel schlanker) ===
    for h in projected_hexagons:
        base_pts = h['base_pts']
        top_pts = h['top_pts']
        color = h['color']
        side_color = h['side_color']
        outline_color = h['outline_color']

        if h['z_height'] > 1:
            # Wir nutzen einfach 3-mal side_color, da sie im Originalcode alle 0.1 waren
            draw.polygon([top_pts[0], top_pts[1], base_pts[1], base_pts[0]], fill=side_color)
            draw.polygon([top_pts[1], top_pts[2], base_pts[2], base_pts[1]], fill=side_color)
            draw.polygon([top_pts[2], top_pts[3], base_pts[3], base_pts[2]], fill=side_color)

        draw.polygon(top_pts, fill=color)
        draw.line(top_pts + [top_pts[0]], fill=outline_color, width=3)
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return image


if __name__ == "__main__":
    print("Generiere organische OLED Wallpaper Basis mit OpenSimplex...")
    img = generate_wallpaper()
    img.save("oled_simplex_grid.png")
    print("Erledigt! Bild wurde als 'oled_simplex_grid.png' gespeichert.")
