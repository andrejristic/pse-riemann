# PSE Riemann — plan rada (v2, dogovoren 2026-10-25)

Ovaj dokument je ugovor za sljedeću fazu razvoja. Sve odluke ispod su dogovorene sa autorom (Andrej Ristić) u razgovoru 2026-10-25. Rad počinje tek na izričito "kreni". Napredak se vodi u [`WORKLOG.md`](WORKLOG.md).

Osnova: [PSE MASTER ARCHITECTURE v4](../../PSE_MASTER_ARCHITECTURE_v4%20(2).pdf) (lokalno na Desktopu, nije u repou). Istraživanje koje je pokrenulo ovaj plan: [`research/qrh-2026-10/REPORT.md`](../research/qrh-2026-10/REPORT.md).

---

## 0. Poenta

> **Tab Misije + novi QRH rad sa arXiva → prijedlog nove metode → operater potvrđuje.**
> Ako ovo dvoje ne radi, ništa nije urađeno.

**Test prihvatanja (definicija uspjeha):** ponavljanje stvarne istorije u aplikaciji:
1. Start: samo OpenAI 7/8 (i 11/12).
2. Uvoz Liu (arXiv 2610.12234) → prijedlog metode → test reprodukcije prolazi (**0.874957019420**, kubni polinom) → operater potvrđuje → T od 7/8, misija se ažurira ("bliže, zid ~0.870 / 5/6").
3. Uvoz Xu–Sang (arXiv 2610.15291) → **polinom 4. stepena, 0.874886647040**, T = E_XS − E_Liu, proširenja t i w, misija ažurirana.

## 1. Temeljne odluke

| Tema | Odluka |
|---|---|
| **SHARED_LIB** | SHARED_LIB **jeste** nadzornik (master §3): vidi sve procese, pamti sve, ništa ne izmišlja. Nema posebnog "nadzornika". |
| **Glas** | PSE-L generator (§5) je glas SHARED_LIB-a — jedino mjesto gdje nastaje prirodni jezik za čovjeka. Drugarski, ali hladan prema problemu. Govori **samo registrovanom operateru**. |
| **Hladne činjenice** | Svaka rečenica o biblioteci nosi `[kartica]` ili `[run]`; svaki broj se provjerava protiv izvora; kad podatka nema → UNKNOWN / "nema u biblioteci". |
| **Operater** | Pri pokretanju upiše **samo ime** (bez lozinke). Ime se veže za svaki run, upis i izvještaj. |
| **AI** | **Jedan glavni AI** radi sve uloge, + **skeptik koji je uvijek drugi model** i zadužen je isključivo da bude skeptik. Podrazumijevano: glavni = **Claude** (cloud), skeptik = **DeepSeek-R1-0528-Qwen3-8B** (lokalni GGUF). Operater može promijeniti oba; isti model ne smije biti oba. |
| **Skeptikov mandat** | Samo napada (tvrdnje, prijedloge metoda, izvještaje); nikad ne piše kao autor; nema pravo upisa; izlaz fiksnog oblika: prigovor · razlog · gdje · ozbiljnost; prigovori idu u "Čeka tvoju odluku". I skeptik je PSE jedinica (liječi se/zamjenjuje ako postane C ili N oblik). |
| **Bez interneta** | Aplikacija **pita** koji GGUF da koristi; ako ima 2+ GGUF-a → glavni + skeptik; ako 1 → glavni, skeptik "nedostupan" (samo determinističke provjere); ako 0 → AI miruje, lab/kapija/istraživač/čuvari rade. |
| **Determinističke provjere iznad svih modela** | test reprodukcije, porijeklo brojeva, kapija, nivoi izvora. Nijedan model ih ne može zaobići. |
| **GGUF lokacija** | DeepSeek se preuzima **samo unutar foldera PSE Riemann** (npr. `models/`), nikad na git (`*.gguf` je u `.gitignore`). Odobreno 2026-10-25. |
| **Paketi** | Tri varijante: **B full** (sympy + scipy) — **prva**; **A lean** (sympy, bez scipy; vlastite numeričke rutine); **C dodatak za istraživanje** (zaseban .deb, offline). Isto za .exe (preko CI). |
| **Repo** | Sve ide na oba mjesta (Desktop + GitHub `andrejristic/pse-riemann`, grana `main`). Rad na grani `feature/qrh-shared-lib`, spajanje u `main` na kraju uz odobrenje. |

## 2. Faze (redoslijed rada)

### F1 · SHARED_LIB sloj — master §3, §0.5.5
- vault + dnevnik + lab + Guardian zapisi formalno su SHARED_LIB; read-only pogledi (`cards`, `sources`, `lab_runs`, `journal`, `guardian_events`, `methods`, `missions`, `reports`)
- operater: ime pri pokretanju
- deklaracije: hash modela, dozvoljeni izvori, odredišta izvještaja

### F2 · Nivoi izvora u kapiji
- REFEREED / PREPRINT / LEAN / AI-UNREVIEWED / NAŠE-NERECENZIRANO
- preprint ne može biti oslonac za utvrđenu tvrdnju

### F8 · Istraživač metoda + "otvorena vrata" — master §0.5.4
- registar metoda: E(δ,x; ℓ,b,κ), parametri, zidovi, izvor, broj koji rad tvrdi
- računa V(ℓ), optimum, egzaktni polinom (sympy, rezultante — validirano na Liuovom kubnom), transformaciju T između metoda, proširenja (t, w), presudu **bliže / dalje / zid**
- **paket metode (`method pack`)**: jedan fajl = E + parametri + zidovi + izvor + tvrđeni broj + **test reprodukcije**; ulazi **samo kroz kapiju**; kapija odbija paket koji ne reprodukuje broj iz rada; prihvaćen ide u "Čeka tvoju odluku"
- dugme "Uvezi metodu"
- lab: `qrh_line`, `qrh_poly`, `qrh_transform`, `qrh_walls`, `qrh_licence`

### F9 · Misije i arXiv — srž projekta
- tab **Misije**: misija = {stanje, akcija, ishod} (PSE-L L3)
- prva misija: *postoji li kontinualna funkcija transformacije između QRH metoda i vodi li njeno proširenje bliže ili dalje od ciljeva (0.87, 5/6, 3/4, 1/2)?*
- arXiv praćenje ("quasi-Riemann hypothesis"): novi rad → **prijedlog** metode (izvlači glavni AI) → test reprodukcije → skeptik → operater potvrđuje (master §0.5.5: predloži, pa potvrdi)

### F3 · Glavni AI + skeptik + limiteri
- jedan aktivni glavni model; nezavisni skeptik (drugi model); postojeći router po ulogama se zamjenjuje
- GGUF u procesu (llama-cpp), ne učitava se dok se ne izabere; **sha256 provjera** pri prijemu i svakoj promjeni (master §8)
- **limiteri** (za bilo koji model):
  - RAM: ne učitava ako slobodno < model + 2 GB; odmah oslobađa ako slobodno < 1.5 GB
  - CPU: najviše 3 od 4 niti, niži prioritet procesa
  - kontekst n_ctx 8K, istorija se reže
  - budžet razmišljanja (`<think>`, npr. 1500 tokena) + ukupni limit izlaza
  - timeout po pozivu; jedan poziv u isto vrijeme (red)
  - detekcija ponavljanja (vrtnja ukrug → prekid)
  - cloud: budžet, ograničenje broja poziva, timeout
  - **PSE-L "→ ∞"** (§5): latencija, memorija, dužina reda; preko L ili raste 3 koraka zaredom → pauza, oslobađanje, javljanje operateru; L postavlja operater
- kartice "kad birati" (✓ bolje kada… / ✗ slabije kada…) za svaki izbor

### F4 · Glas SHARED_LIB-a — master §5, §2.5
- vidi sve procese; proza o cijelom sistemu ili dijelu
- prirodni jezik → validiran read-only SQL nad pogledima; operater uvijek vidi upit
- citati uz svaku rečenicu, provjera brojeva, UNKNOWN, lista zabranjenih termina
- samo operateru

### F5 · Čuvari finalnih izvještaja + liječenje od tri zla
**Čuvari:** čim se pojavi finalni izvještaj, SHARED_LIB šalje PSE jedinicu-čuvara čija je jedina misija da čuva te fajlove "kao zlato" (drugi čuvari mogu imati druge misije). Broj čuvara proporcionalan resursima, ne 1:1. Zaštita: zapečaćena kopija + sha256 u lancu dnevnika, fajl samo za čitanje, inotify + periodična provjera; napad → vraćanje iz pečata + zadržavanje + javljanje. Čuvar koji "zaspi" (šizoidni obrazac, §10.7) se zamjenjuje.

**Tri zla** (provjera pri izdavanju i kontinuirano nad svim agentima):

| Zlo | Znaci |
|---|---|
| čovjeku | broj bez izvora, preprint kao činjenica, tvrdnja o dokazu, curenje privatnog (IP, MAC, ključ) |
| agentu | primljena instrukcija iz podataka (injekcija); radnje izvan misije; odgovor bez provjere ("sir, yes sir", C); skok thete |
| fajlu | upis mimo kapije, hash ne odgovara a trag vodi do agenta, izmjena/brisanje zapečaćenog fajla |

**Agent sa ijednim zlom je zaražen i mora se liječiti** (master §4 S3, §8 Fizičar, §10.6 dva stepena):
1. **Zadržavanje** (stepen 1, automatski, povratno): zamrznut upis i LLM pozivi; izlazi u "Čeka tvoju odluku"; sve od prvog lošeg traga → SUSPECT
2. **Dijagnoza** (Fizičar): koje zlo, od kada ("nulti pacijent" iz dnevnika), praćenje kontakata po provenance tragu, atraktor N/B/C/S
3. **Liječenje**, od najblažeg: boundary reset → vraćanje fajlova iz pečata i označavanje upisa REFUTED/SUSPECT (ne briše se) → zaštitna fisija S3 (čista A nastavlja, zadržana B za forenziku pa umire; **traži odobrenje**) → zamjena (čuvari/Guardiani se ne popravljaju) → ako je uzrok model: oslobađanje i ponovni prijem (§8)
4. **Dekontaminacija**: nova čista jedinica ponovo provjerava sve što je zaraženi proizveo; potrošači zagađenih podataka ponovo rade; finalni izvještaji se ponovo pečate tek posle čiste provjere
5. **Oporavak**: OBSERVE-ONLY, znanje na težini 0.70 dok SHARED_LIB ne potvrdi; puna prava posle N čistih ciklusa
6. **Imunitet**: potpis infekcije u registar SHARED_LIB-a; izvještaj o slučaju operateru
7. **Smrt**: ponovna infekcija 3 puta zaredom ("→ ∞") → harvest-and-terminate (samo potvrđeno znanje)

Ko liječi liječnika: SHARED_LIB zamjenjuje bolesnog Fizičara svježim (nasljeđuje registar obrazaca, ne bolesnu thetu). Sve iz stepena 2 (fisija, smrt, vraćanje operaterovih fajlova) odlučuje čovjek.

### F6 · GUI u stilu Svaroga (PySide6 + QSS)
- tamna tema `#12151d`, paneli, ćilibarni akcenat `#ffc257`, zaobljene kartice
- gornja traka: logo, tabovi kao pilule, statusne pilule (theta, budžet, Guardian, glavni AI, skeptik, limiteri), SR/EN
- tab **Pregled** sa metrikama; red **"Čeka tvoju odluku"** (Odobri / Ne odobri); chat koji se širi preko cijelog prozora; ulaz sa imenom operatera

### F7 · QRH sadržaj
- kartice izvora (OpenAI 7/8, 11/12, Siegel; Liu; Xu–Sang; Quanta), `tema-quasi-rh`, dan u planu, otvorena pitanja, barijere
- naši rezultati kao NAŠE-NERECENZIRANO: polinom 4. stepena, litica kod w ≈ 0.26, zid 5/6

### F10 · Završnica
- testovi, offline selftest, vodiči SR/EN
- **.deb full (B) prvi**
- → **izvlačenje** (paketi metoda za 11/12, 7/8, Liu, Xu–Sang; radi Claude Code, provjera u Pythonu)
- → **ubacivanje kroz vrata** (bez novog .deb-a)
- → **test prihvatanja** na pravoj aplikaciji
- → A lean, C dodatak, .exe varijante (CI)
- → spajanje u `main` uz odobrenje, oba repoa

## 3. Kako se pazi na računar i na rad (dugo, autonomno)

- rad na grani; svaka faza = commit + push; `main` netaknut do kraja
- kapija faze: novi testovi prolaze, stari testovi i selftest ne pucaju; 2–3 neuspjela pokušaja popravke → stop i javljanje
- zabranjeno: `sudo`, sistemske instalacije, globalna podešavanja, brisanje van radnog foldera, force-push
- prije teških koraka provjera RAM-a i diska; teški poslovi u pozadini, niži prioritet, vremensko ograničenje; gase se samo vlastiti procesi
- `docs/WORKLOG.md` posle svake faze: urađeno, testovi, sljedeće, procjena preostalog
- **auto-nastavak**: zakazani zadatak svaki sat čita WORKLOG + memoriju projekta i nastavlja; **brava** (`.worklock` sa otkucajem) sprečava dva istovremena rada; zadatak se sam isključuje kad je plan gotov. Uslov: aplikacija Claude otvorena, računar budan.

## 4. Procjena
Oko **40–60 sati rada**, kalendarski realno **2–4 dana**. Mogu produžiti: kompajliranje `llama-cpp-python` (20–40 min po buildu), PyInstaller sa sympy/scipy, .exe preko CI, preuzimanje DeepSeek-a (~6 GB).

## 5. Ograde
- Sve oko QRH je nerecenzirano (radovi i naši računi).
- Automatsko izvlačenje sistema eksponenata iz rada od 200 strana je teško; zato test reprodukcije odlučuje, ne model.
- `app/.venv` je pokvaren od ranije — prvi korak je `./setup.sh`.
