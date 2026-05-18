import numpy as np
from PIL import Image
import time
import multiprocessing
import os

from service import generate_wallpaper
from service import HEIGHT, WIDTH

# 1. Globale Variable deklarieren, aber NOCH NICHT füllen
shared_counter = None


# 2. Diese Funktion wird von jedem Worker beim Start EINMAL ausgeführt
def init_worker(counter):
    global shared_counter
    shared_counter = counter


def batch_worker(num_images):
    """Rechnet einen festen Block an Bildern ab und aktualisiert den Zähler."""
    local_acc = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)

    for _ in range(num_images):
        img = generate_wallpaper()
        local_acc += np.array(img, dtype=np.float32)
        del img  # Hab das del wieder rein, schont den RAM bei 1000 Bildern enorm!

        # Sicherer Zugriff auf den ECHTEN gemeinsamen Zähler
        with shared_counter.get_lock():
            shared_counter.value += 1

    return local_acc


def run_stress_test_ultra_stable(total_images=1000):
    num_workers = os.cpu_count()
    images_per_worker = total_images // num_workers
    remainder = total_images % num_workers

    tasks = [images_per_worker] * num_workers
    tasks[0] += remainder

    print(f"=== Ultra-Stabiler OLED Batch-Test ===")
    print(f"Bilder: {total_images} | Threads: {num_workers} | Batch-Größe: ~{images_per_worker}")
    print("Starte Motoren...\n")

    start_time = time.time()

    # 3. HIER erschaffen wir das Shared-Memory-Objekt im Hauptprozess
    counter = multiprocessing.Value('i', 0)

    # 4. Wir übergeben den Counter via 'initializer' an die Worker
    with multiprocessing.Pool(processes=num_workers, initializer=init_worker, initargs=(counter,)) as pool:
        result_objects = pool.map_async(batch_worker, tasks)

        # ETA-Loop: Läuft, solange die Worker noch rechnen
        while not result_objects.ready():
            # WICHTIG: Wir lesen den echten 'counter' aus dem Hauptprozess aus
            done = counter.value

            if done > 0:
                elapsed = time.time() - start_time
                per_img = elapsed / done
                eta = (total_images - done) * per_img
                print(f"\rFortschritt: {done}/{total_images} | "
                      f"Schnitt: {per_img:.2f}s/Bild | ETA: {int(eta)}s    ", end="")
            else:
                print(f"\rWarte auf erstes Bild...    ", end="")

            time.sleep(1)  # CPU im Hauptthread schonen

        # Ergebnisse einsammeln, wenn alle fertig sind
        results = result_objects.get()

    print("\n\nBerechnung fertig. Führe Ergebnisse zusammen...")

    # --- Ab hier bleibt dein Code exakt gleich (Statistik-Auswertung) ---
    final_acc = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    for res in results:
        final_acc += res


    # --- DEINE AUSFÜHRLICHE STATISTIK-AUSWERTUNG ---
    heatmap_array = final_acc / total_images

    # 1. Gesamtdurchschnitt pro Kanal
    avg_r = np.mean(heatmap_array[:, :, 0])
    avg_g = np.mean(heatmap_array[:, :, 1])
    avg_b = np.mean(heatmap_array[:, :, 2])
    total_avg = (avg_r + avg_g + avg_b) / 3.0

    # 2. Hotspots (Maximalwerte eines einzelnen Pixels über die Zeit)
    max_r = np.max(heatmap_array[:, :, 0])
    max_g = np.max(heatmap_array[:, :, 1])
    max_b = np.max(heatmap_array[:, :, 2])

    max_brightness_map = np.mean(heatmap_array, axis=2)
    absolute_max_pixel = np.max(max_brightness_map)

    print("\n" + "=" * 45)
    print("ERGEBNIS DER BELASTUNGSANALYSE")
    print("=" * 45)

    print(f"1. Gesamtdurchschnittliche Belastung (Skala 0-255)")
    print(f"   Rot:   ~{avg_r:.2f}")
    print(f"   Grün:  ~{avg_g:.2f}")
    print(f"   Blau:  ~{avg_b:.2f}")
    print(f"   INFO:  Helligkeit liegt bei {total_avg:.2f} (~{(total_avg / 255) * 100:.1f}%).")
    print("   Bedeutung: Sehr schonend für OLEDs (Ideal unter 15%).")

    print(f"\n2. Maximal mögliche 'Hotspots' (Skala 0-255)")
    print(f"   (Durchschnittliche Belastung des hellsten Pixels)")
    print(f"   Max Rot:   {max_r:.2f}")
    print(f"   Max Grün:  {max_g:.2f}")
    print(f"   Max Blau:  {max_b:.2f}")
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
    print(f"\nHeatmap wurde als 'oled_stress_test_result.png' gespeichert.")
    print(f"Gesamtdauer: {time.time() - start_time:.1f}s")


if __name__ == "__main__":
    # Jetzt kannst du bedenkenlos hohe Zahlen (200, 500, etc.) reinhauen!
    run_stress_test_ultra_stable(200)