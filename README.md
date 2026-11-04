# MIA – AI kihívás (Polinvent)

Burst pouch töltő–klipszelő–hegesztő berendezés új koncepciójának 3D modellje, reveal-videója és bemutató weboldala.
Készült az AI kihívásra, Claude segítségével.

- `index.html` – főoldal (GitHub Pages): fekete menüszalag, fekete→metál→fehér hero a géppel
- `mia.html` (Manyika 2 · MIA), `manyika.html` (első generáció), `accessories.html`, `contacts.html`, `career.html`, `store.html` – aloldalak; `img/` – a weboldal képei
- `assets/site.css`, `assets/site.js` – közös menüszalag és lábléc (egy helyen definiálva, minden oldal betölti), `assets/erd-logo.svg` – Equipment R&D logó
- `configurator.html` – interaktív, sematikus 3D konfigurátor (Three.js): kiszerelés-presetek, ciklusanimáció
- `blender/mia_model.py` – paraméteres Blender-szkript, ebből épül a teljes modell (bpy / Blender 4.2+)
- `model/MIA_model.blend`, `model/MIA_model.glb` – a generált modell
- `renders/` – előnézeti renderek verziónként
- `docs/` – napló (eszközök, promptok, elakadások)
