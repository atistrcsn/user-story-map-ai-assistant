# Gitlab AI assistant

## Áttekintés, cél
A projekt célja az lenne, hogy egy GitLab AI asszisztens szolgáltatást hozzunk létre, ami segít menedzselni a projekt user-story térképét. Az asszisztensnek képesnek kell lennie a GitLab API-val való interakcióra a Gitlab CLI (glab) segítségével.  

## Funkciók, tudás terv, ötletek
* ./.gemini/commands/gitlab/generate-issue.toml
    Ez várja a felhasználó ötletét, megvalósítani kívánt feladatait a fejlesztéssel kapcsolatban, elemzi azt, majd javaslatot tesz arra, hogy milyen szerkezetre bontsa azt (epics, issues, labels stb.), és az alábbiakra figyel:
    * ha szükséges akkor bontsa le több story-ra, epics-re stb. az agilis bevált gyakorlatok mentén. 
    * meg kell vizsgálnia a már lokálisan elérhető (a Gitlab-ról letöltött és szinkronizált Issue-ból álló user story map-et)
    * elemzést végez, és létrehozza az előre konfigurált helyre és struktúrát használva az új issue-t vagy issuekat.
    * a felhasználó áttekinti, és esetleg javaslatot kér, vagy további finomítást, módosítást.
    * ezután ha kell, akkor létrehozza a szükséges szerkezetet a Go wrapper meghívásával.
    * ha több issue van és esetleg új epics valamin új label, akkor azokat is létrehozza, és az issue-hoz rendeli.
    + ha van olyan funkció vagy elvárás ami már létezik a user story map-ben, akkor azt jelzi, és javaslatot tesz a legoptimálisabb megoldásra.
    * proaktívan segíti az agilis tervezést a user story beillesztésében a jelenlegi struktúrát, az üzleti igényeket, és a gitlab projektból leszinkronizált összes releváns issue figyelembe vételével.  
gy nézne ki egy ilyen Kilocode workflow működés közben:

**A Trigger:**
Te, a felhasználó, beírsz egy promptot a workflow-nak:
> "Szükségünk van egy funkcióra, amivel a felhasználók a partnerekhez több kapcsolattartót is rögzíthetnek, névvel és email címmel."

**A Workflow Lépései:**

1.  **Szinkronizálás (`sync_gitlab_issues` tool):** A workflow első lépése mindig az, hogy a Go wrapperbe ágyazott glab segítségével leszedi a legfrissebb issue-kat és eposzokat, és frissíti a helyi `/spec` könyvtárat. Így biztos, hogy az AI a valósággal dolgozik.

2.  **Elemzés (az AI agya):** Az AI megkapja a te promptodat és a teljes `/spec` könyvtár tartalmát mint kontextust. Felteszi magának a kérdéseket:
    *   "Ez a kérés egy teljesen új koncepció, vagy egy meglévő eposzhoz kapcsolódik?" -> *Válasz: A `Partnerkezelés`-hez kapcsolódik.*
    *   "Ez elég nagy lélegzetvételű ahhoz, hogy saját eposz legyen (`Több kapcsolattartó kezelése`), vagy csak egy user story egy meglévő eposz alatt?" -> *Válasz: Ez egy összetettebb funkció, több story is lehet belőle (hozzáadás, szerkesztés, törlés), ezért legyen inkább egy új eposz a `Partnerkezelés` gerinc alatt.*
    *   "Mik lennének az első, legfontosabb user story-k ebben az új eposzban?" -> *Válasz: 1. "Mint admin, új kapcsolattartót tudok hozzáadni egy partnerhez."*

3.  **Helyi Műveletek (`create_local_files` tool):** Az AI meghívja a saját maga által definiált tool-t, ami:
    *   Létrehozza a `/spec/partnerkezeles/tobb_kapcsolattarto_kezelese` könyvtárat (ha az eposz mellett dönt).
    *   Létrehoz benne egy `01_kapcsolattarto_hozzaadasa.md` fájlt a user story tartalmával.

4.  **Feltöltés (`upload_to_gitlab` tool):** Az AI most meghívja a `glab`-et használó tool-t, a megfelelő paraméterekkel:
    *   `glab epic create -t "Több kapcsolattartó kezelése" --label "Gerinc::Partnerkezelés","Típus::Eposz"`
    *   Miután ez sikeres és megkapja az új eposz ID-ját, meghívja a következőt:
    *   `glab issue create -t "Új kapcsolattartó hozzáadása partnerhez" -d "$(cat ...)" --label "Típus::User Story" --epic <ID>`

5.  **Visszajelzés:** A workflow a végén kiírja neked:
    > "Létrehoztam a 'Több kapcsolattartó kezelése' eposzt és a hozzá tartozó első user story-t. Itt találod őket a GitLab-ben: [linkek]"


** Workflow javaslatok, megjegyzések **
* javaslat: a /spec könyvtár helye és neve configurálható lenne, a default értéke lehetne a projekt gyökerében, azon belül is a ./docs/spec úton.
* javaslat: jó lenne azonosítani a főbb célokat, a lehetséges felhasználói szerepköröket (actor-okat), ezeket egy külön.md vagy JSON struktúrában tárolni és naprakészen tartani, amiből dolgozhat az AI.
* a gitlab szinkronizáció során érdemes lehet egy helyi JSON-ben struktúráltan felsorakoztatni a törzsadatokat azonosítokkal együtt, pl a labels, epics, release, sprint stb.
* javaslat: ha van élő dokumentáció egy config-ban megadott könyvtárban, vagy könyvtárakban, pl. /docs/businedd-functions-and-brief.md és hasonló anyagok, akkor azokat mindig vegye figyelembe a tervezés, értelmezés során. Csak utána kezdje el végiggondolni, hogy az új story-k hova illene bele a nagy képbe.
* javaslat: az egyes story .md fájlokban lehetne frontmattert használni, amiben elhelyezve lenne a sok meta info, pl issue név, blocked by, created_at, status stb.
* arra is figyelni kellene,hogy melyik issue blokkolja a másikat, ezt feltérképezni.
* amikor egy issue-t frissít az AI a Gitlabon, akkor minden ilyen módosítást a végén le kellene tölteni a lokális user story map állapotba is. Erről jelzést adni a felhasználónak.

## A Go Wrapper feladatai:
* Parancs Értelmezése: Fogadja a Gemini command-tól érkező hívást (pl. sync_gitlab_issues).
* glab hívása: A háttérben lefuttatja a megfelelő glab parancsot.
* Kimenet Elkapása: Elkapja a glab standard output-ját és standard error-ját.
* Feldolgozás és Szűrés (a "mágia"):
* * Parsing: A nyers szöveges kimenetet strukturált adattá alakítja (pl. regex-szel vagy string-műveletekkel).
* * Redaction: Kicseréli a szenzitív adatokat placeholder-ekre (egy előre configurálható szabálrend szerint). Például:
https://gitlab.ce.mycompany.com/mygroup/my-project/issues/123 -> [INTERNAL_GITLAB_URL_AND_PROJECT]/issues/123
* * * Assigned to: @john.doe -> Assigned to: [USER]
* * Formatting: A megtisztított adatokat egy konzisztens, egyszerű formátumba (pl. JSON vagy letisztított Markdown) csomagolja.
* Válasz Visszaadása: A feldolgozott, biztonságos kimenetet kiírja a saját standard output-jára, amit a Gemini command már biztonságosan felhasználhat.

## Technikai feltételek
* amikor a Gitlab CLI (glab) vagy a Gitlap API működésével kapcsolatban kell információ, dokumentáció, akkor mindig használja az mcp eszközt, a context7 segítségét a naprakész doc eléréséért.
* * a Gitlab CLI context7 id: cli_github
* * a Gitlab API context7 id: docs_gitlab_com
* * a Gemini CLI context7 id: geminicli


## Végső gondolatok
A fentiek csak hanyag ötletek, bár nagyon pontosnak és kidolgozottnak tűnnek. Nem kell elsőre elfogadni mindent, mérlegeld, elemezd mélyrehatóan, és tegély fel minél több kérdést, ha nem egyértelmű valami, főleg a projekt célját illetően. Biztos hogy hagytam ki fontos részleteket, ami most nincs az eszemben.