# MIA (Manyika 2) – Diario di lavoro della sfida AI

- **Autore:** Lui Halász · Equipment R&D · Polinvent
- **Strumento AI:** Claude (Anthropic) – Claude Chat nelle prime due serate, Claude Code (app desktop, scheda Code) il terzo giorno
- **Risultato:** <https://luihalasz.github.io/mia_ai_kihivas/> · <https://github.com/luihalasz/mia_ai_kihivas>

---

## 1. Sintesi

L'obiettivo era presentare il concetto di una nuova macchina di riempimento–clippatura–saldatura per burst pouch (MIA, cioè Manyika 2) in modo che la direzione desse il via libera. Io ho portato le conoscenze tecniche: le dimensioni, il processo e i problemi della Manyika 1. Insieme all'AI ne abbiamo ricavato:

- il **modello 3D parametrico** (Blender + Python, `blender/mia_model_v2.py`),
- il **configuratore 3D nel browser** con l'animazione del ciclo (Three.js, `configurator.html`),
- i **render** (Blender Cycles),
- il **sito web** in tre lingue (HU/EN/IT),
- un **video di presentazione di ~1 minuto**,
- e questo **diario**.

Quasi nulla è stato disegnato a mano: tutto è generato dal codice, quindi ogni dimensione è un parametro che si trova in un unico punto.

## 2. Strumenti usati

| Strumento | Per cosa |
|---|---|
| Claude Chat (claude.ai) | Serate 1–2: concetto della macchina, modello Blender parametrico, basi del configuratore |
| Claude Code (app desktop, scheda Code) | Giorno 3: sito web, render sul mio computer, video, diario, git push |
| Blender 5.x + Python (bpy) | Modello parametrico, render Cycles, scene del video e montaggio (VSE) |
| Three.js (r128) | Configuratore 3D interattivo nel browser |
| GitHub + GitHub Pages | Controllo versione e hosting del sito |
| Il mio portatile: NVIDIA RTX 1000 Ada | Render su GPU (OptiX + denoising OIDN) |

## 3. Il percorso

### Serata 1 – Claude Chat: descrivere la macchina e il modello

Per prima cosa ho descritto la macchina a parole: le misure delle buste (PE 550×180 / 800×180, alu 285×220 / 450×220), la posizione della clip e della saldatura, le altezze di riempimento per ogni formato, i due cilindri di riempimento (ISO e silicato di sodio), le ventose, le ganasce lisciatrici e la carenatura. Da questo Claude ha scritto uno **script Python parametrico per Blender** che costruisce l'intera macchina e ne crea i render.

L'abbiamo perfezionato in molti passaggi. Io indicavo cosa non corrispondeva alla realtà, e l'AI lo correggeva. Alcuni esempi:
- il tubo di riempimento non deve mai immergersi nel materiale, e da ritratto deve restare 25 mm sopra il film;
- il vuoto non deve allargare le saldature laterali, solo aprire la bocca della busta;
- l'altezza della macchina va dimensionata sulla busta grande per entrambi i formati.

**Dove ci siamo bloccati:**
- **Blender nel cloud:** Blender non si poteva scaricare nella sandbox cloud di Chat, quindi renderizzava con il pacchetto Python `bpy`, solo su CPU. Era lento: un'immagine richiedeva minuti.
- **Caricamento:** dalla sandbox di Chat non si poteva fare push su GitHub. Quindi scaricavo i file e li caricavo a mano dal sito di GitHub ("Add file → Upload files"). Una volta ho dimenticato di premere "Commit changes" alla fine.

### Serata 2 – Claude Chat: il controllo e le basi del configuratore

Accanto al modello serviva qualcosa che chiunque potesse provare senza installare nulla. Claude ha scritto un **configuratore Three.js in un solo file**:
- scelta del formato con tutti gli 8 formati (330 ml – 2,25 l);
- animazione dell'intero ciclo di 17 passi: vuoto, riempimento, lisciatura, clip, saldatura, rilascio;
- regolazione della velocità e pulsante Start;
- un avviso se un formato collidesse con il tubo di riempimento.

Qui abbiamo fissato anche la logica di controllo: l'avvio a due mani con due pulsanti verdi, l'ordine e i tempi dei passi.

**Dove ci siamo bloccati:**
- I film trasparenti sfarfallavano l'uno sull'altro (z-fighting). Risolto con un ordine di disegno fisso e `depthWrite:false`.

### Giorno 3 – Claude Code: lo stesso, solo molto più veloce

Qui ho scoperto che in **modalità codice** (Claude Code) ottengo risultati molto migliori, perché l'AI lavora direttamente sul mio computer:
- ha installato Git da sola e clonato il repository;
- ha renderizzato con Blender sulla mia scheda grafica, in secondi invece che in minuti;
- ha controllato subito il proprio lavoro nel browser integrato: screenshot e verifica anche della vista da telefono;
- io dicevo solo cosa volevo, e mostravo con uno screenshot o uno schizzo quando qualcosa non andava.

Cosa è stato fatto quel giorno:
1. **Sito web**:
   - barra del menu nera su ogni pagina, con un logo Equipment R&D proprio;
   - menu Prodotti (Manyika 2 · MIA, Manyika), Accessori, Contatti, Carriere, NEGOZIO;
   - in home page una sezione hero con sfumatura nero–metallo–bianco e la macchina renderizzata.
2. **Tre lingue**: selettore HU/EN/IT in alto a destra. La scelta resta valida da una pagina all'altra e passa anche al configuratore.
3. **Configuratore rivisto**:
   - interfaccia pulita: restano solo la scelta del formato, l'animazione automatica e il modello girevole;
   - aspetto ombreggiato con contorni invece di quello schematico;
   - il tablet è stato montato su un braccio, perché prima entrava nella parete della macchina;
   - la telecamera ruota attorno al centro del film, nel punto in cui si trova dentro la macchina.
4. **Nuovi render** sulla mia GPU: il cassetto estratto con la busta; la macchina sul suo supporto con la colonna luminosa a tre colori completa e lo schermo nero.
5. **Disegno della coppia di clip** in base al mio schizzo a mano. Sono servite due correzioni perché l'estremità del profilo a C si allineasse esattamente con la vita dell'otto.
6. **Video di ~1 minuto**, fatto interamente in Blender, da codice. La prima versione durava 41 s, a 720p, con sottotitoli in ungherese. Dopo il mio feedback è diventato:
   - 61 s, 5 scene, 1400 fotogrammi, sottotitoli in inglese, compressione migliore e più campioni di render. Il 1080p avrebbe richiesto ~4,5 ore di render, quindi per la scadenza è rimasto a 720p (~2 ore);
   - l'oggetto di cui si parla riceve un contorno giallo che lampeggia due volte (fatto nel compositor da un livello di render "maschera" separato);
   - nella scena delle quattro macchine tutti i cassetti sono aperti, e l'operatore li chiude uno alla volta da sinistra a destra;
   - alla fine il logo Polinvent e "Coming soon in 2027";
   - una colonna sonora "hype" da trailer sintetizzata da codice (numpy), con un effetto sonoro a ogni lampeggio.

   Il video mostra questi vantaggi rispetto alla Manyika 1:
   - riempimento a pressione senza schizzi, invece del riempimento peristaltico diretto;
   - carenatura chiusa: il cilindro non può pizzicare la mano dell'operatore;
   - caricamento del film con un cassetto invece di infilarlo alla cieca;
   - avvio a due mani con due pulsanti verdi;
   - due formati di busta regolabili;
   - ganasce lisciatrici: gli angoli non si ripiegano;
   - ventose invece del serraggio con un cilindro, così il film non scivola;
   - 4 MIA stanno nello spazio di una Manyika 1, e serve 1 operatore invece di 5.
7. **Download**: il modello 3D (.glb, .blend, STEP), il codice Python del modello, il link GitHub e questo diario, nelle pagine MIA e Contatti. Il diario si può leggere in tutte e tre le lingue.

**Dove ci siamo bloccati:**
- **Mancava Git** sul computer: Claude l'ha installato (winget), io ho approvato.
- **Permessi di push:** solo io posso accedere a GitHub. Claude ha preparato e fatto il commit di tutto, e io ho eseguito `git push` nel terminale con l'accesso dal browser. Gli ho anche chiesto di non fare commit finché non avessi controllato le modifiche, e l'ha rispettato.
- **Particolarità di Windows PowerShell:** gli script con caratteri accentati si rompevano, e poiché i nomi delle variabili non distinguono maiuscole e minuscole un'immagine è stata sovrascritta con una vuota. Claude se n'è accorto e l'ha corretto.
- **Modifica dell'API di Blender 5.2:** l'impostazione per l'esportazione video è stata rinominata (`media_type = 'VIDEO'`). Corretto con una riga, in base al messaggio di errore.
- **Inquadratura:** all'inizio nell'immagine hero era tagliata la parte alta della colonna luminosa, e lo schermo mostrava uno strano rettangolo blu. Una regolazione della telecamera e uno schermo "tutto nero, figo" hanno risolto.
- **Contorno giallo:** nel livello maschera gli altri pezzi da evidenziare (es. la carenatura in vetro) coprivano il film come un muro nero, e il suo contorno non appariva. Ora quei pezzi sono trasparenti finché non tocca a loro.
- **Copia delle quattro macchine:** avevo già spostato la macchina originale prima di copiarla, così le copie sono finite nel posto sbagliato. Si vedeva nel fotogramma di prova, e si è risolto cambiando l'ordine.
- **Terminologia:** non conoscevo la parola "Skid", quindi è diventata "Ellátóegység" (unità di alimentazione).

## 4. Esempi di prompt (dal giorno 3, tradotti dall'ungherese)

> Fai una barra del menu che sia su ogni pagina del sito. Voglio una barra del menu nera in alto; a sinistra, al posto del logo, un qualche logo per Equipment R&D, accanto una scheda Products (con menu a tendina: Manyika, Manyika 2) …

> Metti in alto a destra un selettore di lingua HU EN IT con cui scegliere la lingua del sito. Su qualunque pagina lo cambi, la scelta si porta anche sulle altre.

> Il configuratore è un po' troppo grigio e sfocato. Potresti aggiungere dei contorni o ombre più forti, per renderlo più bello?

> La coppia di clip è fatta così, su accessories.html *(con uno schizzo a mano)* – poi: da chiusa questa è in linea, non più all'interno!

> L'immagine nuova va bene, ma meh. L'impostazione e le luci di prima erano migliori; inoltre lo schermo deve essere completamente nero … rendilo figo

> Genera un video di circa 40 secondi che mostri come lo userà un operatore e quanto è migliore della precedente Manyika 1. Vantaggi principali: …

> Ora vado a mangiare, quindi non bloccarti a fare domande *(nel frattempo il video è stato completato, con circa 80 minuti di render su GPU)*

> Correggi il video: sottotitoli in inglese, che non sia così veloce e pixelato, e il contorno dell'oggetto di cui si parla deve lampeggiare in giallo due volte di fila … Aggiungi una musica di sottofondo da trailer tech "hype".

> Il configuratore non deve zoomare sul centro della macchina, ma sul punto che sarebbe il centro del film quando è dentro la macchina

## 5. Cosa ho imparato

- **Chat è buona per pensare, Code per fare.** Il concetto e la logica del modello si sono sviluppati bene in Chat. Appena entravano in gioco file, render, git e un browser sul mio computer, la modalità codice era spesso più veloce.
- **Un'immagine dice di più.** Uno screenshot o uno schizzo a mano con una linea rossa arrivavano al punto più in fretta di qualsiasi descrizione.
- **Il modello parametrico ripaga.** Il configuratore, i render e il video nascono tutti dallo stesso codice, quindi una modifica di misura compare ovunque contemporaneamente.
- **Il controllo resta a me.** Commit e push sono avvenuti solo con la mia approvazione, e l'accesso l'ho fatto io.

---

*Ancora non è finito. :) Questo è un contenuto generato dall'AI per il quale non ci assumiamo alcuna responsabilità penale.*
