import os
import json
import re
import datetime
import urllib.request
import threading
import tkinter as tk
from tkinter import ttk, messagebox

class MCInstanceGeneratorPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Coding-Assistent: Portable Instance Creator")
        self.root.geometry("600x550")
        
        # 1. Dynamische Pfad-Ermittlung (Wichtig für portable Nutzung)
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.instances_dir = os.path.join(self.base_path, "instances")
        
        # 2. Selbstheilungs-Logik: Erstellt alles Nötige beim ersten Start
        self.setup_environment()
        
        self.create_widgets()
        
        # Hintergrund-Thread für API-Daten
        threading.Thread(target=self.fetch_mc_versions, daemon=True).start()

    def setup_environment(self):
        """Prüft und erstellt die Ordnerstruktur im aktuellen Verzeichnis."""
        try:
            if not os.path.exists(self.instances_dir):
                os.makedirs(self.instances_dir)
                # Optional: Eine Info-Datei für den Nutzer erstellen
                with open(os.path.join(self.base_path, "README_Zuerst_Lesen.txt"), "w") as f:
                    f.write("Dieser Ordner wurde automatisch erstellt.\n")
                    f.write("Alle Instanzen werden im Unterordner 'instances' gespeichert.")
        except Exception as e:
            print(f"Fehler beim Initialisieren: {e}")

    def get_json(self, url):
        """Sicherer API-Abruf mit User-Agent."""
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())

    def fetch_mc_versions(self):
        """Lädt die Versionen von Mojang."""
        try:
            self.set_status("Lade Mojang-Daten...")
            data = self.get_json("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json")
            # Nur die neuesten 30 Releases für die Übersichtlichkeit
            versions = [v['id'] for v in data['versions'] if v['type'] == 'release'][:30]
            self.version_combo['values'] = versions
            if versions: self.version_var.set(versions[0])
            self.set_status("Bereit.")
        except:
            self.set_status("Offline-Modus oder API-Fehler.")

    def set_status(self, text):
        self.status_var.set(f"Status: {text}")

    def clean_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def create_widgets(self):
        container = ttk.Frame(self.root, padding="30")
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Portable Instance Creator", font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Eingabefelder
        ttk.Label(container, text="Name der neuen Instanz:").pack(anchor="w")
        self.name_entry = ttk.Entry(container, textvariable=self.name_var := tk.StringVar())
        self.name_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(container, text="Wähle Minecraft Version:").pack(anchor="w")
        self.version_combo = ttk.Combobox(container, textvariable=self.version_var := tk.StringVar(value="Lade..."), state="readonly")
        self.version_combo.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(container, text="Wähle Mod-Loader:").pack(anchor="w")
        self.loader_combo = ttk.Combobox(container, textvariable=self.loader_var := tk.StringVar(value="Vanilla"), values=["Vanilla", "Fabric", "Quilt"], state="readonly")
        self.loader_combo.pack(fill=tk.X, pady=(0, 15))

        self.status_var = tk.StringVar(value="Status: Initialisierung...")
        ttk.Label(container, textvariable=self.status_var, font=("Arial", 9, "italic")).pack(pady=10)
        
        self.btn_create = ttk.Button(container, text="Instanz-Paket generieren", command=self.start_creation)
        self.btn_create.pack(pady=20, fill=tk.X)

    def start_creation(self):
        threading.Thread(target=self.generate_instance, daemon=True).start()

    def generate_instance(self):
        name = self.name_var.get().strip()
        version = self.version_var.get()
        loader = self.loader_var.get()

        if not name or version == "Lade...":
            messagebox.showwarning("Achtung", "Bitte gib einen Namen ein.")
            return

        safe_name = self.clean_filename(name)
        inst_path = os.path.join(self.instances_dir, safe_name)

        if os.path.exists(inst_path):
            messagebox.showerror("Fehler", "Dieser Instanz-Name existiert bereits!")
            return

        try:
            self.set_status(f"Generiere '{name}'...")
            
            # 1. Erstelle die Verzeichnisstruktur (Kompatibel mit MultiMC/Prism)
            # Viele Launcher erwarten die Spieldaten im Unterordner .minecraft oder einfach im Root
            subfolders = [".minecraft", ".minecraft/mods", ".minecraft/resourcepacks", ".minecraft/saves"]
            for folder in subfolders:
                os.makedirs(os.path.join(inst_path, folder), exist_ok=True)

            # 2. Erstelle die mmc-pack.json (Das Herzstück für den Import)
            components = [{"cachedName": "Minecraft", "cachedVersion": version, "important": True, "uid": "net.minecraft"}]
            
            if loader != "Vanilla":
                self.set_status(f"Rufe {loader}-Metadaten ab...")
                api_url = f"https://meta.fabricmc.net/v2/versions/loader/{version}" if loader == "Fabric" else f"https://meta.quiltmc.org/v3/versions/loader/{version}"
                meta = self.get_json(api_url)
                if meta:
                    loader_ver = meta[0]['loader']['version']
                    uid = "net.fabricmc.fabric-loader" if loader == "Fabric" else "org.quiltmc.quilt-loader"
                    components.append({"cachedName": f"{loader} Loader", "cachedVersion": loader_ver, "uid": uid})

            pack_data = {"components": components, "formatVersion": 1}
            with open(os.path.join(inst_path, "mmc-pack.json"), "w") as f:
                json.dump(pack_data, f, indent=4)

            # 3. Erstelle die instance.cfg für Launcher-Metadaten
            with open(os.path.join(inst_path, "instance.cfg"), "w") as f:
                f.write(f"InstanceType=Instance\n")
                f.write(f"name={name}\n")
                f.write(f"iconKey=default\n")
                f.write(f"notes=Generiert am {datetime.datetime.now()}\n")

            self.set_status("Erfolg!")
            messagebox.showinfo("Fertig", f"Instanz '{name}' wurde im Ordner 'instances' erstellt.\n\nDu kannst diesen Ordner jetzt einfach in deinen Launcher ziehen!")
            
        except Exception as e:
            self.set_status("Fehler beim Erstellen.")
            messagebox.showerror("Fehler", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = MCInstanceGeneratorPro(root)
    root.mainloop()

