# Finomított Terv 2.0: Intelligens Fejlesztési Kontextus Menedzsment Rendszer

Ez a dokumentum a GitLab-alapú fejlesztési munkafolyamat támogatására tervezett intelligens kontextusmenedzsment rendszer részletes műszaki tervét írja le. A terv a kezdeti ötletelés során felmerült javaslatok és finomítások alapján készült.

## 1. Architekturális Kockázatok Kezelése

### a. Kontextus Méret és LLM Input Limit

A "context summarizer" réteg beépítése kritikus a skálázódáshoz.

*   **Implementáció:** A szinkronizációs szkript kap egy `--summarize` opciót. Hosszú issue leírások esetén meghív egy (akár lokális, kisebb) LLM-et, hogy készítsen egy sűrített, kulcsszavakkal ellátott kivonatot.
*   **Gyorsítótárazás:** A `/.gemini_cache/` könyvtárban minden issue IID-hez letároljuk az eredeti leírás hash-ét és a generált összefoglalót. A kivonatolás csak akkor fut le újra, ha a forrás hash megváltozik.

### b. Kontextus Szinkronizálás

Az `updated_at` alapú inkrementális frissítés alapvető lesz a hatékonyság érdekében.

*   **Implementáció:** A `/.gemini_cache/` fogja tárolni az issue-k metaadatait, beleértve a legutóbb látott `updated_at` időbélyeget. A szkript `--mode=map` futtatásakor először csak a metaadatokat kéri le a GitLab API-tól, összehasonlítja a cache-sel, és csak a megváltozott issue-k teljes tartalmát (kommentek, leírás) kéri le a függőségi gráf frissítéséhez. Ez drasztikusan csökkenti az API-hívások számát.

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
    *   `gemini-cli sync map`: Frissíti a `project_map.yaml`-t a cache alapján. **Implementálva:** Lekéri a GitLab issue-kat, elemzi a leírásokat és kommenteket a `/blocked by #<IID>` és `/blocking #<IID>` minták alapján, `networkx` gráffá alakítja, és egyedi linkekkel menti a `project_map.yaml` fájlba.
    *   `gemini-cli sync fetch --iid 123 --depth 2`: Letölti a fókuszált kontextust.
    *   `gemini-cli query "Melyik issue-k blokkolják a #123-at?`: Lekérdezéseket futtat a `project_map.yaml` alapján.

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

*   **Implementáció:** Létrehozzuk a `/.gemini_prompts/` könyvtárat, olyan sablonokkal, mint:
    *   `planning.prompt`: A következő feladat stratégiai kiválasztásához.
    *   `implementation_plan.prompt`: Egy adott story technikai tervének elkészítéséhez.
    *   `code_review.prompt`: Merge requestek AI-alapú véleményezéséhez.

## 5. Biztonság és CI/CD Integráció

### a. Token Security

*   **Implementáció:** A szkript a `python-dotenv` könyvtárat használja a `.env` fájl beolvasásához. A CI/CD környezetben a tokent a pipeline "secrets" vagy "variables" tárolójából kell injektálni környezeti változóként.

### b. CI/CD Horgonyzás

A kontextus-ellenőrzés mint minőségi kapu beépítése növeli a megbízhatóságot.

*   **Implementáció:** A CI pipeline (pl. GitLab CI) minden `merge_request` eseményre lefut. Egy `verify_context` nevű job meghívja a `gemini-cli sync map --fail-on-stale` parancsot. Ha a MR-ben érintett issue-k a `project_map.yaml`-ban elavultak, a pipeline hibával leáll.

## 6. Továbbgondolható Fejlesztési Irányok

*   **Vector Store Integráció:** A `/.gemini_cache/` kiegészíthető egy lokális vector store-ral (pl. ChromaDB) a szemantikus kereséshez.
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