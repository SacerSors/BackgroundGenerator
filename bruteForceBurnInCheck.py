import numpy as np
from PIL import Image
import time

from fractalGenerator import generate_wallpaper
from fractalGenerator import HEIGHT, WIDTH


# Hinweis: Dieses Skript setzt voraus, dass generate_wallpaper()
# in deinem Hauptskript definiert ist und SEED/OFFSETS bei jedem Aufruf würfelt.

def run_stress_test(iterations=100):
    print(f"=== OLED Belastungstest gestartet ({iterations} Iterationen) ===")

    # Accumulator für die Bilder (Float32 verhindert Überlauf)
    # Nutzt RENDER_WIDTH/HEIGHT falls du das Supersampling im Test behalten willst,
    # ansonsten WIDTH/HEIGHT für einen schnelleren Check.

    acc = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)

    start_time = time.time()

    for i in range(iterations):
        img = generate_wallpaper()
        acc += np.array(img, dtype=np.float32)

        if (i + 1) % 10 == 0:
            avg_temp = (acc / (i + 1)).mean()
            print(f"Fortschritt: {i + 1}/{iterations} | Aktueller Helligkeitsschnitt: {avg_temp:.2f}/255")

    # Durchschnittsbild berechnen
    heatmap_array = acc / iterations

    # --- STATISTIK AUSWERTUNG ---
    # 1. Gesamtdurchschnitt pro Kanal
    avg_r = np.mean(heatmap_array[:, :, 0])
    avg_g = np.mean(heatmap_array[:, :, 1])
    avg_b = np.mean(heatmap_array[:, :, 2])
    total_avg = (avg_r + avg_g + avg_b) / 3.0

    # 2. Hotspots (Maximalwerte eines einzelnen Pixels über die Zeit)
    # Wir suchen das Pixel, das über alle Bilder hinweg am hellsten war
    max_pixel_channels = np.max(heatmap_array, axis=(0, 1))  # Max pro Kanal
    max_brightness_map = np.mean(heatmap_array, axis=2)  # Helligkeitsmap (Schnitt der Kanäle)
    absolute_max_pixel = np.max(max_brightness_map)  # Der hellste Punkt im Durchschnittsbild

    print("\n" + "=" * 40)
    print("ERGEBNIS DER BELASTUNGSANALYSE")
    print("=" * 40)

    print(f"1. Gesamtdurchschnittliche Belastung (Skala 0-255)")
    print(f"   Rot:   ~{avg_r:.2f}")
    print(f"   Grün:  ~{avg_g:.2f}")
    print(f"   Blau:  ~{avg_b:.2f}")
    print(f"   INFO:  Helligkeit liegt bei {total_avg:.2f} (~{(total_avg / 255) * 100:.1f}%).")
    print("   Bedeutung: Sehr schonend für OLEDs (Ideal unter 15%).")

    print(f"\n2. Maximal mögliche 'Hotspots' (Skala 0-255)")
    print(f"   (Durchschnittliche Belastung des hellsten Pixels)")
    print(f"   Max Rot:   {max_pixel_channels[0]:.2f}")
    print(f"   Max Grün:  {max_pixel_channels[1]:.2f}")
    print(f"   Max Blau:  {max_pixel_channels[2]:.2f}")
    print(f"   Max Helligkeit (Pixel-Mittelwert): {absolute_max_pixel:.2f} / 255")

    # Abweichungs-Check
    diff = absolute_max_pixel - total_avg
    print(f"\n3. Gleichmäßigkeits-Check")
    if diff < 15:
        print(f"   Abweichung: {diff:.2f} -> EXZELLENT. Das Gitter wandert perfekt.")
    else:
        print(f"   Abweichung: {diff:.2f} -> WARNUNG. Muster könnte sich leicht einprägen.")

    # Heatmap speichern
    heatmap_img = Image.fromarray(np.clip(heatmap_array, 0, 255).astype(np.uint8))
    heatmap_img.save("oled_stress_test_result.png")
    print("\nHeatmap wurde als 'oled_stress_test_result.png' gespeichert.")


if __name__ == "__main__":
    run_stress_test(10)