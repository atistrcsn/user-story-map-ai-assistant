# Finomított Terv 2.0: Intelligens Fejlesztési Kontextus Menedzsment Rendszer

Ez a dokumentum a GitLab-alapú fejlesztési munkafolyamat támogatására tervezett intelligens kontextusmenedzsment rendszer részletes műszaki tervét írja le. A terv a kezdeti ötletelés során felmerült javaslatok és finomítások alapján készült.

## 1. Architekturális Kockázatok Kezelése

### a. Kontextus Kezelés és LLM Input Limit (Kétfázisú Elemzés)

A nagy méretű kontextus kezelése és az LLM token limitjének betartása érdekében egy kétfázisú elemzési stratégiát alkalmazunk.

*   **1. Fázis: Előszűrés:** Ahelyett, hogy a teljes kontextust egyből a fő LLM-nek adnánk, egy kisebb, gyorsabb modellt használunk a releváns információk kiszűrésére. Ez a modell megkapja a felhasználói kérést és a projektben lévő összes dokumentum/issue listáját (címekkel és rövid összefoglalókkal), majd visszaadja a legrelevánsabb 10-15 fájl listáját.
*   **2. Fázis: Mélyelemzés:** A fő, nagy teljesítményű LLM már csak ezzel a szűkített, releváns kontextussal dolgozik, ami növeli a válaszok pontosságát és csökkenti a költségeket.
*   **Automatikus Összefoglalás:** A szinkronizációs folyamat során a hosszú issue leírásokról és dokumentumokról a rendszer automatikusan rövid összefoglalókat generál és ezeket a `/.gemini_cache/` könyvtárban tárolja. Az előszűrési fázis elsősorban ezekkel a sűrített kivonatokkal dolgozik.

### b. Intelligens Kontextus Szinkronizálás (Smart Sync)

A `create feature` parancs gyors és reszponzív működése érdekében a folyamat elején nem teljes, hanem "intelligens" szinkronizációt végzünk.

*   **Implementáció:** A parancs indításakor a rendszer csak az issue-k `updated_at` időbélyegét kéri le a GitLab API-tól, összehasonlítja a `/.gemini_cache/`-ben tárolt állapottal, és csak a megváltozott issue-k teljes tartalmát tölti le újra. Ez biztosítja, hogy a kontextus naprakész legyen, de a várakozási idő minimális.

## 2. AI-munkafolyamat és Konzisztencia

### a. Tudásrétegek Keveredése

A `GEMINI.md` verziózása és a commit hash beemelése a kontextusba biztosítja a reprodukálhatóságot.

*   **Implementáció:** A `project_map.yaml` gyökerében lesz egy `doctrine` szekció, ami tartalmazza a `GEMINI.md` fájl elérési útját és a `git rev-parse HEAD:path/to/GEMINI.md` paranccsal kinyert commit hash-t. Az LLM prompt expliciten megkapja ezt az információt.

### b. Story–Epic–Task Láncolat

A gráf-adatszerkezet és a paraméterezhető mélység elengedhetetlen a komplex függőségek kezeléséhez.

*   **Implementáció:** A Python szkript a `networkx` könyvtárat fogja használni a függőségi gráf memóriában történő felépítésére.
*   **Adatformátum:** A `project_map.yaml` a gráfot `node-link` formátumban fogja tárolni:
    ```yaml
    nodes:
      - id: 123
        title: "User Login"
        type: "Story"
    links:
      - source: 123
        target: 456
        type: "blocks"
    ```
*   **CLI:** A szkript kap egy `--depth=N` paramétert a fókuszált kontextus letöltéséhez, ami a gráfból N szint mélységig gyűjti ki a releváns issue-kat.

## 3. Implementációs Részletek

### a. Fájlstruktúra

A háromrétegű struktúrát teljes mértékben adoptáljuk:
*   `/docs/spec/`: Statikus, verziókezelt dokumentáció (pl. `GEMINI.md`).
*   `/.gemini_context/`: Dinamikus, futásidejű kontextus. Minden futtatáskor tisztul és újraépül.
*   `/.gemini_cache/`: Perzisztens, de eldobható gyorsítótár az API-hívások minimalizálására.
*   A `.gitignore` fájlba a `/.gemini_context/` és `/.gemini_cache/` könyvtárak bekerülnek.

### b. Adat-reprezentáció

A váltás YAML-ra indokolt az olvashatóság és a diffelhetőség miatt.

*   **Implementáció:** A `project_map` fájl formátuma `yaml` lesz.
*   **CLI Bővítés:** Létrehozunk egy egyszerű CLI eszközt (`gemini-cli`) a rendszer kezelésére:
    *   `gemini-cli create feature`: Interaktív munkafolyamatot indít egy új funkció megtervezésére. A parancs az optimalizált, "Enhanced Workflow"-t követi: 1. Smart Sync. 2. Felhasználói bevitel. 3. Kétfázisú AI analízis. 4. Strukturált, lépésenkénti párbeszéd a jóváhagyáshoz. 5. Lokális fájlok generálása. **6. Robusztus, tranzakciószerű visszatöltés a GitLab-re.**
        *   **Implementáció:** A `create-feature` parancs a jóváhagyott terv alapján meghívja a `gitlab_service.upload_artifacts_to_gitlab(project_map)` függvényt. Ez a függvény felelős az új címkék, issue-k és a közöttük lévő "Related items" (issue linkek) létrehozásáért a GitLab-en.
        *   **Tesztelési Stratégia:** A feltöltési funkcionalitást a `scripts/tests/test_gemini_cli.py` fájlban dedikált tesztesetekkel ellenőrizzük. Ezek a tesztek mockolják a `gitlab_service.upload_artifacts_to_gitlab` függvényt, hogy szimulálják a sikeres és hibás feltöltéseket, és ellenőrzik a CLI kimenetét, valamint a kilépési kódokat.

## 4. AI Stratégiai Működése

### a. Kontextus-keverés Veszélye

A prompt higiénia kulcsfontosságú.

*   **Implementáció:** A `/.gemini_context/current_task` mappa minden `fetch` parancs előtt törlésre kerül.
*   **Prompt Struktúra:** Minden prompt expliciten tagolt lesz Markdown kommentekkel:
    ```markdown
    <!-- DOCTRINE (GEMINI.md @ hash) -->
    ...
    <!-- GLOBAL MAP CONTEXT -->
    ...
    <!-- FOCUSED TASK CONTEXT (IID: #123) -->
    ...
    <!-- SOURCE CODE CONTEXT -->
    ...
    <!-- MY INSTRUCTION -->
    ...
    ```

### b. Prompt Controllability

A `/.gemini_prompts/` könyvtár bevezetése szabványosítja és skálázhatóvá teszi a rendszert.

*   **Implementáció:** Ahelyett, hogy a prompt sablonokat külső fájlokban tárolnánk (ami a `gemini-cli` környezetben hozzáférési problémákat okozott), a promptok közvetlenül az `ai_service.py` szkriptben, f-string formátumban kerülnek definiálásra. Ez a megközelítés biztosítja a megbízható működést és a könnyű karbantarthatóságot, mivel a prompt logikája és a Python kód egy helyen található. A jövőben, ha a rendszer komplexitása indokolja, ez a döntés újraértékelhető.


## 5. Biztonság és CI/CD Integráció

### a. Token Security

*   **Implementáció:** A szkript a `python-dotenv` könyvtárat használja a `.env` fájl beolvasásához. A CI/CD környezetben a tokent a pipeline "secrets" vagy "variables" tárolójából kell injektálni környezeti változóként.

### b. CI/CD Horgonyzás

A kontextus-ellenőrzés mint minőségi kapu beépítése növeli a megbízhatóságot.

*   **Implementáció:** A CI pipeline (pl. GitLab CI) minden `merge_request` eseményre lefut. Egy `verify_context` nevű job meghívja a `gemini-cli sync map --fail-on-stale` parancsot. Ha a MR-ben érintett issue-k a `project_map.yaml`-ban elavultak, a pipeline hibával leáll.

### c. Robusztus Feltöltés Kezelés

A GitLab-re történő visszatöltés hibatűrése kritikusan fontos, hogy a rendszer ne kerüljön inkonzisztens állapotba.

*   **API Lassítás (Throttling):** A feltöltő szkriptnek egy minimális (pl. 100-200ms) várakozást kell beiktatnia az API hívások közé a rate limit elkerülése érdekében.
*   **Tranzakciós Logika és Rollback:** A feltöltési folyamat naplózza a tervezett lépéseket. Hiba esetén megpróbálja visszavonni a már végrehajtott műveleteket (pl. letörli a sikeresen létrehozott, de függőségekkel még el nem látott issue-kat), vagy egyértelmű riportot ad a felhasználónak a manuális helyreállításhoz.

### d. Hierarchia-kezelés "Related items" Alapokon

A korábbi, címke-alapú (`Epic::`) hierarchia-kezelést egy robusztusabb, a GitLab "Related items" funkciójára (API nevén: Issue Links) épülő modell váltotta fel. Ez a megközelítés egyértelműbb és jobban skálázható. A helyes fájlrendszer-hierarchia felépítését a `gitlab_service.py` szkript egy többmenetes (multi-pass) feldolgozási logikával biztosítja.

*   **1. Menet (Pass 1): Epik-ek Feldolgozása:** A szkript először végigmegy az összes letöltött issue-n, és kizárólag a `Type::Epic` címkével rendelkezőket dolgozza fel. Létrehozza a hozzájuk tartozó könyvtárakat (`/backbones/<backbone_neve>/<epic_neve>/`) és elmenti az `epic.md` fájlt. Ezzel egy időben egy belső térképet (dictionary) épít, ami az epik issue IID-jét a lokális könyvtárának útvonalához köti.

*   **2. Menet (Pass 2): Sztorik és Kapcsolatok Feldolgozása:** A második körben a szkript a `Type::Story` címkéjű issue-kat dolgozza fel. Minden egyes sztori esetében egy API hívást intéz a GitLab felé (`issue.links.list()`), hogy lekérdezze a hozzá tartozó "Related items"-eket.
    *   Ha a linkek között talál egy olyan issue-t, ami `Type::Epic` címkével rendelkezik, akkor az 1. menetben felépített térkép segítségével megkeresi a szülő epik könyvtárát.
    *   A sztori Markdown fájlját (`story-<sztori_neve>.md`) ezután a megfelelő epik könyvtárába menti, az `epic.md` mellé.
    *   Ezzel egyúttal a `project_map.yaml`-ban is rögzíti a szülő-gyermek (`contains`) kapcsolatot a két issue között.

*   **3. Menet (Pass 3): Szöveges Függőségek Feldolgozása:** Végül a szkript az összes issue leírását és kommentjét elemzi a szövegesen definiált (`/blocking`, `/blocked by`) kapcsolatok után kutatva, és ezeket is hozzáadja a `project_map.yaml`-ban definiált gráfhoz.

Ez a többlépcsős megközelítés garantálja, hogy a sztorik mindig a megfelelő szülő epik alá kerüljenek a fájlrendszerben, pontosan leképezve a GitLab-ben definiált struktúrát.

### e. Új Epicek és Story-k Kezelése a Generálás Során

Az AI által javasolt új funkciók gyakran tartalmaznak egyszerre új Epiceket és a hozzájuk tartozó új Story-kat. Mivel ezek az entitások a helyi generálás pillanatában még nem rendelkeznek GitLab IID-vel, egy speciális mechanizmusra van szükség a hierarchia helyes felépítéséhez.

*   **Ideiglenes `Epic::<name>` Címke:** Az AI a javaslatában egy ideiglenes, `Epic::My New Epic Name` formátumú címkét használ a Story-kon, hogy jelezze a szándékolt hovatartozást.
    *   **Fontos:** Ez a címke egy belső "ragasztó", ami **soha nem kerül létrehozásra** a GitLab-en. Kizárólag a helyi fájlgenerálási logika használja.

*   **Kétfázisú Helyi Generálás:** A `gemini-cli create-feature` parancs a `_generate_local_files` függvényen keresztül egy kétlépcsős folyamatot hajt végre:
    1.  **Epicek Feltérképezése:** Először feldolgozza az összes `Type::Epic` címkével rendelkező új issue-t, létrehozza a könyvtáraikat, és egy belső térképen összerendeli az ideiglenes `Epic::<name>` címkét a frissen létrehozott könyvtár elérési útjával és ideiglenes ID-jével.
    2.  **Story-k Elhelyezése és Linkek Létrehozása:** Ezután feldolgozza a `Type::Story` issue-kat. A bennük található `Epic::<name>` címke alapján kikeresi a térképről a szülő Epic könyvtárát és ideiglenes ID-jét, majd a Story fájlját a megfelelő helyre generálja. Ezzel egyidejűleg a `_generate_local_files` függvény **létrehozza a `contains` típusú linket**, valamint **hozzáadja a `description` mezőt is** a `project_map.yaml` fájlban a szülő Epic és a Story ideiglenes ID-i között, rögzítve a hierarchikus kapcsolatot és a tartalmat a helyi térképen is.

*   **Konverzió Feltöltéskor:** A `gemini-cli upload story-map` parancs felelős a konverzióért:
    1.  Létrehozza az issue-kat a GitLab-en a megfelelő (`Type::Epic`, `Type::Story`) címkékkel, de az `Epic::<name>` címke nélkül.
    2.  A `project_map.yaml`-ban lévő `contains` linkek alapján azonosítja a szülő-gyermek kapcsolatot. A feltöltési logika intelligensen szűri ezeket a linkeket, és **csak azokat a kapcsolatokat hozza létre, amelyek újonnan generált (`NEW_`) issue-kat érintenek**, elkerülve a már létező linkek újra-létrehozásából fakadó API hibákat.
    3.  A frissen kapott IID-k segítségével létrehozza a hivatalos **"Related items"** kapcsolatot az Epic és a Story között a GitLab API-n keresztül.

## 6. Továbbgondolható Fejlesztési Irányok

*   **Vector Store Integráció:** A `/.gemini_cache/` kiegészíthető egy lokális vector store-ral (pl. ChromaDB) a szemantikus kereséshez. **Megjegyzés:** Ez egy jövőbeli, opcionális fejlesztés. A kezdeti implementáció a 1.a pontban leírt, LLM-alapú előszűrést alkalmazza.
*   **Natural Language Query:** A `gemini-cli query` parancs fejleszthető, hogy természetes nyelvi kérdéseket LLM segítségével gráf-lekérdezéssé alakítson.
*   **Adaptive Depth Fetch:** A `--depth` paraméter viselkedése lehet adaptív, a csomópont központisága alapján.

## 7. Tesztelési Stratégia

A projekt minőségének és megbízhatóságának biztosítása érdekében automatizált tesztek bevezetését javasoljuk a következő fázisban.

### a. Egységtesztek

*   **Cél:** Az `_slugify`, `_generate_markdown_content`, és `_get_issue_filepath` függvények izolált tesztelése, valamint a `parse_relationships` függvény (jövőbeli) tesztelése.
*   **Tesztelési területek:**
    *   `_slugify`: Szöveg URL-barát slug-gá alakítása, speciális karakterek és szóközök kezelése.
    *   `_generate_markdown_content`: Markdown tartalom generálása YAML frontmatterrel, különböző issue mezőkkel (hiányzó mezők is).
    *   `_get_issue_filepath`: Fájlútvonal meghatározása issue címkék és hierarchia alapján, beleértve az `_unassigned` logikát és a Backbone, Epic, Story, Task címkeformátumok helyes kezelését.
    *   `parse_relationships` (jövőbeli): A GitLab issue-k közötti kapcsolatok helyes azonosítása (`/blocking #<IID>` és `/blocked by #<IID>` minták).
*   **Eszköz:** `pytest`.

### b. Integrációs tesztek (`sync map` parancs)

*   **Cél:** A teljes `sync map` pipeline (GitLab API lekérés, elemzés, gráfépítés, YAML kimenet) helyes működésének ellenőrzése, élő GitLab példány nélkül.
*   **Tesztelési területek:**
    *   A `project_map.yaml` fájl generálásának ellenőrzése a várt struktúrával.
    *   A generált `nodes` és `links` tartalmának ellenőrzése egy előre definiált mock GitLab adatkészlet alapján.
*   **Eszköz:** `pytest` a `unittest.mock` vagy `pytest-mock` segítségével a GitLab API hívások mockolásához.