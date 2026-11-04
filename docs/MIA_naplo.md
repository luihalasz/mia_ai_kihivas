# MIA (Manyika 2) – AI kihívás munkanapló

- **Készítette:** Halász Lui · Equipment R&D · Polinvent
- **AI eszköz:** Claude (Anthropic) – első két este Claude Chat, a harmadik napon Claude Code (asztali alkalmazás, Code fül)
- **Eredmény:** <https://luihalasz.github.io/mia_ai_kihivas/> · <https://github.com/luihalasz/mia_ai_kihivas>

---

## 1. Összefoglaló

A cél egy új burst-pouch töltő–klipszelő–hegesztő gép (MIA, azaz Manyika 2) koncepciójának bemutatása volt úgy, hogy a vezetés zöld utat adjon neki. Én adtam a gépészeti tudást: méreteket, folyamatot, a Manyika 1 problémáit. Az AI-val együtt raktuk össze ebből:

- a **parametrikus 3D modellt** (Blender + Python, `blender/mia_model_v2.py`),
- a **böngészős 3D konfigurátort** a ciklus animációjával (Three.js, `configurator.html`),
- a **renderképeket** (Blender Cycles),
- a **honlapot** három nyelven (HU/EN/IT),
- egy **~40 másodperces bemutatóvideót**,
- és ezt a **naplót**.

Szinte semmit nem rajzoltam kézzel: mindent kód generál, így minden méret egy helyen, paraméterként változtatható.

## 2. Felhasznált eszközök

| Eszköz | Mire |
|---|---|
| Claude Chat (claude.ai) | 1–2. este: gépkoncepció, parametrikus Blender modell, a konfigurátor alapjai |
| Claude Code (asztali app, Code fül) | 3. nap: honlap, renderek a saját gépemen, videó, napló, git push |
| Blender 5.x + Python (bpy) | Parametrikus modell, Cycles renderek, videó jelenetek és vágás (VSE) |
| Three.js (r128) | Interaktív 3D konfigurátor a böngészőben |
| GitHub + GitHub Pages | Verziókezelés és a honlap hosztolása |
| Saját laptop: NVIDIA RTX 1000 Ada | GPU-s renderelés (OptiX + OIDN zajszűrés) |

## 3. Az út

### 1. este – Claude Chat: a gép megfogalmazása és a modell

Először szövegesen leírtam a gépet: a zacskóméreteket (PE 550×180 / 800×180, alu 285×220 / 450×220), a klipsz és a hegesztés helyét, a töltőmagasságokat kiszerelésenként, a két töltőhengert (ISO és vízüveg), a vákuumkorongokat, a simító pofákat és a burkolatot. A Claude ebből írt egy **parametrikus Blender Python szkriptet**, amely a teljes gépet felépíti, és renderképeket is készít.

Ezt sok körben finomítottuk. Én mondtam meg, mi nem felel meg a valóságnak, az AI javította. Néhány példa:
- a töltőcső sose merüljön bele az anyagba, és kihúzva is maradjon 25 mm a fólia felett;
- a vákuum az oldalvarratokat ne húzza szét, csak a zacskó szája nyíljon ki;
- a gép magasságát mindkét kiszerelésnél a nagy tasakhoz kell méretezni.

**Ahol elakadtunk:**
- **Blender a felhőben:** a Blendert nem lehetett letölteni a Chat felhős homokozójába, ezért a `bpy` Python csomaggal, csak processzoron renderelt. Ez lassú volt: egy kép percekig készült.
- **Feltöltés:** a Chat homokozójából nem lehetett a GitHubra pusholni. Ezért a fájlokat letöltöttem, és a GitHub webes felületén kézzel töltöttem fel („Add file → Upload files”). Egyszer elfelejtettem a végén a „Commit changes” gombot.

### 2. este – Claude Chat: a vezérlő és a konfigurátor alapjai

A modell mellé kellett valami, amit bárki kipróbálhat telepítés nélkül. A Claude egy **egyfájlos Three.js konfigurátort** írt:
- kiszerelés-választó, mind a 8 kiszereléssel (330 ml – 2,25 l);
- a teljes 17 lépéses ciklus animációja: vákuum, töltés, simítás, klipsz, hegesztés, kiadás;
- sebességállítás és Start gomb;
- figyelmeztetés, ha egy méret ütközne a töltőcsővel.

Itt rögzítettük a vezérlés logikáját is: a két zöld gombos kétkezes indítást, a lépések sorrendjét és időzítését.

**Ahol elakadtunk:**
- Átlátszó fóliák villogtak egymáson (z-fighting). Ezt fix rajzolási sorrenddel és `depthWrite:false` beállítással oldottuk meg.

### 3. nap – Claude Code: ugyanaz, csak sokkal gyorsabban

Itt derült ki számomra, hogy **kód módban** (Claude Code) sokkal jobb eredményt érek el. Az AI ugyanis közvetlenül a saját gépemen dolgozik:
- maga telepítette a Gitet, és klónozta a repót;
- a saját videokártyámon renderelt a Blenderrel, percek helyett másodpercek alatt;
- a beépített böngészőben rögtön meg is nézte, amit csinált: képernyőképet készített, telefonos nézetben is ellenőrzött;
- én csak mondtam, mit szeretnék, és képernyőképen vagy rajzon mutattam meg, ha valami nem stimmelt.

Ezen a napon készült el:
1. **Honlap**:
   - fekete menüszalag minden oldalon, saját Equipment R&D logóval;
   - Termékek menü (Manyika 2 · MIA, Manyika), Kiegészítők, Kapcsolat, Karrier, BOLT;
   - a kezdőlapon fekete–metál–fehér színátmenetes hős-szekció, rajta a renderelt géppel.
2. **Háromnyelvűség**: HU/EN/IT választó a jobb felső sarokban. A választás oldalról oldalra megmarad, a konfigurátorba is átmegy.
3. **Konfigurátor átdolgozás**:
   - letisztult felület: csak a kiszerelés-választó, az automata animáció és a forgatható modell maradt;
   - árnyékolt, kontúros megjelenés a vázlatos helyett;
   - a tablet karra került, mert korábban belelógott a gép falába.
4. **Új renderek** a saját GPU-n: kihúzott fiók tasakkal; a gép állványon, teljes háromszínű jelzőlámpával, fekete kijelzővel.
5. **Klipszpár rajz** az én kézi vázlatom alapján. Kétszer kellett javítani, mire a C-profil vége pontosan egy vonalba került a nyolcas derekával.
6. **~41 másodperces videó**, teljesen Blenderben, kódból: 5 jelenet, 900 képkocka, magyar feliratok, zárókártya. Ezeket az előnyöket mutatja be a Manyika 1-hez képest:
   - nyomásos töltés fröcsögés nélkül a direkt perisztaltika helyett;
   - zárt burkolat: a munkahenger nem csípheti oda a kezet;
   - fiókos fóliabehelyezés vakon fűzés helyett;
   - kétkezes zöld gombos indítás;
   - két állítható zacskóméret;
   - simító pofák: nem fordulnak be a sarkok;
   - vákuumkorongok a hengeres szorítás helyett, így nem csúszik le a fólia;
   - 4 MIA elfér egy Manyika 1 helyén, és 5 helyett 1 operátor kezeli őket.
7. **Letöltések**: a 3D modell (.glb, .blend), a modell Python kódja, a GitHub link és ez a napló, a MIA és a Kapcsolat oldalon.

**Ahol elakadtunk:**
- **Git hiányzott** a gépről: a Claude feltelepítette (winget), én jóváhagytam.
- **Push jogosultság:** a GitHubra bejelentkezni csak én tudok. A Claude mindent előkészített és commitolt, a `git push`-t én futtattam a terminálban, böngészős bejelentkezéssel. Kértem azt is, hogy addig ne commitoljon, amíg át nem néztem: ezt betartotta.
- **Windows PowerShell sajátosságok:** ékezetes szkriptek elromlottak, és a kis- és nagybetűt nem megkülönböztető változónevek miatt egy kép üresre íródott felül. A Claude észrevette és javította.
- **Blender 5.2 API változás:** a videó exportnál megváltozott a beállítás neve (`media_type = 'VIDEO'`). Hibaüzenet alapján egy sorral javítva.
- **Képkivágás:** a hős-képen először levágódott a jelzőlámpa teteje, és a kijelzőn egy furcsa kék téglalap volt. Kamera-állítás és „teljesen fekete, menő” kijelző lett belőle.
- **Szóhasználat:** a „Skid” szót nem ismertem, ezért „Ellátóegység” lett belőle.

## 4. Példa promptok (szó szerint, a 3. napról)

> Csinálj egy menüszalagot ami minden pagen rajta van a honlapon, menüszalagot szeretnék fentre feketéből, bal oldalt a logó helyén legyen Equipment R&D nek valami logó, mellette Products fülön (legördülőben Manyika, Manyika 2) …

> Legyen fent a jobb felső sarokban egy nyelv választás HU EN IT ahol be lehet állítani hogy a honlap milyen nyelven legyen. Akármelyik oldalon állítod is át, viszi magával a többire a választást.

> A konfigurátor egy kicsit túl szürke és homályos, esetleg kontúrokat ha tudnál tenni rá vagy erősebb árnyékokat, hogy szebb legyen

> a klipsz pár így néz ki, az accessories.html-en *(kézi vázlattal)* – majd: ez a zárva részen egy vonalban van, nem beljebb!

> Az új kép jó, de meh. Az előző beállítás és fények jobbak voltak, also a kijelző legyen fekete teljesen … legyen menő

> generálj egy kb. 40másodperces videót arról ami bemutatja hogyan használja ezt egy operátor majd és mennyivel jobb ez mint az előző Manyika egyes. Fő előnyök: …

> most elmegyek enni, ugyhogy ne akadj meg visszakérdésen *(a videó ezalatt készült el, kb. 80 perc GPU-renderrel)*

## 5. Tanulságok

- **A Chat jó a gondolkodásra, a Code jó a csinálásra.** A koncepciót és a modell logikáját Chatben jól ki lehetett dolgozni. Amint a saját gépen kellett fájlokkal, renderrel, gittel és böngészővel dolgozni, a kód mód sokszor gyorsabb volt.
- **Képpel többet lehet mondani.** Egy képernyőkép vagy egy kézi rajz piros vonallal gyorsabban célba ért, mint bármilyen leírás.
- **A parametrikus modell megtérül.** A konfigurátor, a renderek és a videó ugyanabból a kódból készülnek, így egy méretváltozás mindenhol egyszerre jelenik meg.
- **A kontroll nálam marad.** A commit és a push csak az én jóváhagyásommal történt, a bejelentkezést is én végeztem.

---

*Még mindig nincs kész. :) Ez AI által generált tartalom, amiért semmilyen büntetőjogi felelősséget nem vállalunk.*
