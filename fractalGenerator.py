import colorsys
import math

import numpy as np
import opensimplex
from PIL import Image, ImageDraw


# === Konfiguration ===
WIDTH, HEIGHT = 2560, 1440
HEX_RADIUS = 40
GAP_SIZE = 2

# === Noise Konfiguration (Das Fraktal) ===
SCALE = 400.0  # Der "Zoom-Faktor". Größer = breitere, weichere Pfade
OCTAVES = 4  # Die Anzahl der fraktalen Detail-Schichten
PERSISTENCE = 0.5  # Wie stark die Details ins Gewicht fallen
LACUNARITY = 2.0  # Wie "krisselig" die Details werden

SEED = np.random.randint(2, 999999) # Startwert für den Zufall

# === Tile-Arten ===
BG_COLOR = (0, 0, 0)
COLOR_DARK = (15, 15, 15)
COLOR_ELEVATED = (35, 35, 35)

# === Farbverlauf für helle Tiles ===
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


def get_hex_vertices(x, y, draw_radius):
    """Berechnet die 6 Eckpunkte eines Hexagons."""
    vertices = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.pi / 180 * angle_deg
        px = x + draw_radius * math.cos(angle_rad)
        py = y + draw_radius * math.sin(angle_rad)
        vertices.append((px, py))
    return vertices


def generate_wallpaper():
    image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    hex_width = math.sqrt(3) * HEX_RADIUS
    hex_height = 2 * HEX_RADIUS
    cols = int(WIDTH / hex_width) + 2
    rows = int(HEIGHT / (hex_height * 0.75)) + 2

    for row in range(rows):
        for col in range(cols):
            x = col * hex_width
            if row % 2 == 1:
                x += hex_width / 2
            y = row * hex_height * 0.75

            # === Eigene Fraktal-Logik nutzen ===
            noise_val = fbm(x / SCALE, y / SCALE, OCTAVES, PERSISTENCE, LACUNARITY)

            # === Organische Verteilung ===
            # Der normalisierte noise_val liegt zwischen -1.0 und 1.0
            if noise_val > 0.25:
                # "Gipfel" - farbig
                # Diagonaler Fortschritt (von links oben nach rechts unten)
                hue = ((x / WIDTH) + (y / HEIGHT)) / 2.0
                # Sicherstellen, dass Hue zwischen 0 und 1 bleibt (optional, aber sicherer)
                hue = hue % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, COLOR_BRIGHTNESS)
                tile_color = (int(r * 255), int(g * 255), int(b * 255))
            elif noise_val > 0.0:
                tile_color = COLOR_ELEVATED  # "Hänge"
            else:
                tile_color = COLOR_DARK  # "Täler"

            # Hexagon zeichnen
            draw_radius = HEX_RADIUS - GAP_SIZE
            vertices = get_hex_vertices(x, y, draw_radius)
            draw.polygon(vertices, fill=tile_color)

    return image


if __name__ == "__main__":
    print("Generiere organische OLED Wallpaper Basis mit OpenSimplex...")
    img = generate_wallpaper()
    img.save("oled_simplex_grid.png")
    print("Erledigt! Bild wurde als 'oled_simplex_grid.png' gespeichert.")