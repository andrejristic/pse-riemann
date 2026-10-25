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
- **auto-nastavak**: zakazani zadatak svaka 2 sata čita `CLAUDE.md` + PLAN + WORKLOG i nastavlja; **brava** (`.worklock` sa otkucajem) sprečava dva istovremena rada; zadatak se sam isključuje kad je plan gotov. Uslov: aplikacija Claude otvorena, računar budan.

## 4. Procjena
Oko **40–60 sati rada**, kalendarski realno **2–4 dana**. Mogu produžiti: kompajliranje `llama-cpp-python` (20–40 min po buildu), PyInstaller sa sympy/scipy, .exe preko CI, preuzimanje DeepSeek-a (~6 GB).

## 5. Ograde
- Sve oko QRH je nerecenzirano (radovi i naši računi).
- Automatsko izvlačenje sistema eksponenata iz rada od 200 strana je teško; zato test reprodukcije odlučuje, ne model.
- `app/.venv` je pokvaren od ranije — prvi korak je `./setup.sh`.

---

## 6. Runda 3 (dogovorena 2026-10-25, čeka „kreni“)

Završni proizvod: **.deb i .exe** (verzija 0.2.0, tag `v0.2.0`, `.exe` kao GitHub Release). Oznake: S = od Svaroga, P = od Peruna, A = greška nađena poređenjem. Brojevi S/P odgovaraju redovima B/C u [`SLJEDECA-VERZIJA.md`](SLJEDECA-VERZIJA.md) (S2 = B2, P1 = C1 …).

**P4 (prava prijava) je izbačen** (Andrej, 2026-10-25: „zaboravi p4“). Operater ostaje **samo ime**; nema lozinki, šefa ni ranga.

### Faza 0 · Početak
1. Spajanje trenutnog stanja u `main` (lokalno i GitHub); novi rad na novoj grani, spajanje na kraju uz odobrenje.
2. Zakazani zadatak: auto-nastavak je **ugašen** (2026-10-25); zadatak je sada sedmični podsjetnik koji pita da li ga ponovo aktivirati. Kontroliše se samo iz Claude aplikacije.

### Faza 1 · Temelj: popravke i integritet odluka
3. Popravke A1–A4: „→ ∞“ čuvar se zaista pokreće; detekcija vrtnje prekida generisanje u toku; timeout pokriva i generisanje; nema trke u redu odluka.
4. Odobrenje se troši jednom (S2) i atomično rješavanje stavki (P5, **bez ranga**): jedna odluka = jedno izvršenje.
5. Svaki alat i akcija deklariše povratnost; nedeklarisano = nepovratno (S4). Od toga zavisi šta čuvari i liječenje smiju sami, a šta ide čovjeku.
6. Ponovljive odluke (P1): svaka odluka se može ponovo izvesti iz dnevnika; neslaganje = narušen integritet.
7. Ograničena retencija + sidra arhive (S8 + P3): dnevnik se skraćuje bez gubitka dokaza; arhiva dobija sha256 i pečat; lanac se nastavlja preko sidra.

### Faza 2 · Operater i početno podešavanje
8. Početno podešavanje pri prvom otvaranju, prije glavnog prozora:
   1. ime operatera (samo ime);
   2. glavni AI: OpenAI ili kompatibilni (proizvoljna adresa), Claude, Gemini ili GGUF sa bilo kog mjesta (po putanji i hash-u, bez kopiranja);
   3. skeptik: drugi model;
   4. deklaracije za svaki izabrani model (GGUF hash poređen sa objavljenim; nova cloud adresa kao prijedlog koji operater potvrđuje);
   5. „bez AI za sada“, uz jasan spisak šta radi, a šta ne;
   6. da li čuvar kreće sam pri prijavi u sistem.
   Sve se kasnije može mijenjati.

### Faza 3 · Modeli, strujanje, naplata, prekidač
9. Provajderi: OpenAI i kompatibilni (gotove postavke za Mistral, Groq, DeepSeek, xAI, OpenRouter, Together, Fireworks), Claude, Gemini i GGUF, za obje uloge.
10. Strujanje za sve pozive kroz Guardian egress, sa pravim prekidom veze.
11. Savjetovanje o naplati: po provajderu opcije + šta je najbolje (prekid strujanja zaustavlja naplatu kod Anthropic, OpenAI, DeepSeek, xAI, Together, Fireworks; **ne** kod Gemini, Mistral, Groq; bez strujanja uvijek puna naplata; ulazni tokeni se uvijek naplaćuju); stroži `max_tokens` i limit ulaza za provajdere bez prekida; budžet računa najgori slučaj kad nema podatka o potrošnji.
12. Prekidač za online AI: dugme u gornjoj traci, u meniju ikone u traci i Ctrl+K; zatvara put u egress-u, prekida pozive u toku, briše ključeve iz memorije (po izboru ih trajno zaboravlja); prelazi na GGUF ili „bez AI“; preživljava restart, uključuje ga samo operater; automatski se okida na „→ ∞“ broja, veličine i troška poziva, uz alarm i link za opoziv ključa.
13. Lokalni model ne smije se obraćati nijednoj adresi osim ovog računara (P8).

### Faza 4 · SSH čuvar i zaštita domaćina
14. SSH čuvar (PSE jedinica, radi uvijek): čita SSH dnevnik bez root-a, otporno na rotaciju (S6); računa po izvoru, uz „→ ∞“; theta blizu 30, ali ne ravna; skupi, prijavi SHARED_LIB-u i ukloni smetnju; kad su tri principa narušena, blokira prekršioca.
15. Povratno zadržavanje sa automatskim poništavanjem (S3): prekid sesije i privremena IP blokada 24 h (sama se skida, preživljava restart) su automatski. Gašenje SSH-a i trajne blokade su prijedlog operateru sa tačnom komandom.
16. Bez sudoers pravila → opasno upozorenje: veliki prozor, crvena pilula, SHARED_LIB i uporno bip-bip-bip dok operater ne klikne „U redu“, uz tačnu komandu.
17. Šablonske poruke za kritične stvari (P6): alarmi, liječenje i upozorenja koriste samo provjerene šablone, ne tekst modela.
18. Uputstvo za usko sudoers pravilo (ufw deny/delete od IP, systemctl stop/start ssh), korak po korak.
19. Pozadinski rad i gašenje: čuvar je proces sa ikonom u traci (Otvori · Stanje θ · Prekini online AI · Ugasi čuvara); pri zatvaranju pitanje „Ugasi sve“ ili „Zatvori prozor, čuvar ostaje“; korisnički servis po izboru, sa systemd hardeningom (S9).

### Faza 5 · Pametniji Fizičar i mjerenje
20. Statistički jača dijagnoza (S5) u liječenju i čuvarima: CUSUM, posterior i pravilo 3-od-3, manje lažnih „infekcija“.
21. Budžeti otkrivanja + takmičenje hipoteza (P7).
22. Mjereni benchmark (S7): označeni primjeri za tri zla, SSH napade i prekidač; lažno pozitivni i lažno negativni ulaze u izvještaj.

### Faza 6 · Interfejs i mašina
23. SR/EN prekidač za cijeli interfejs.
24. Automatski profil mašine (Dell i5-6600 / Acer i3, oba 16 GB): ograničenja se sama prilagode, kartice „kad birati“ upozore da je DeepSeek spor na Aceru, testovi rade i sa simuliranim Acerom.

### Faza 6b · Druga misija, inspiracije, grafovi (dodato 2026-10-25, radi se prije Faze 7)
Sve iz ove faze mora biti u završnom .deb i .exe.

30. **Istraživanje sa izvorima (internet):** geometrijski Langlands (dokaz 2024); aritmetička funkcionalnost (npr. automorfnost simetričnih stepena); zero-free i zero-density rezultati za L-funkcije višeg stepena (GL(2), Artin); šta u dokazima 7/8, Liu i Xu–Sang zavisi od Dirichletovih karaktera, a šta ne. Rezultat: `research/langlands-2026-10/REPORT.md` + kartice izvora sa nivoima (REFEREED / PREPRINT), označeno DJELIMIČNO gdje treba. Kartice idu u seed vaulta, pa ih paketi nose.
31. **Dogovor o cilju druge misije** (Andrej odlučuje, prije ubacivanja u softver). Prijedlozi su u chatu 2026-10-25.
32. **Misija 2 u aplikaciji:** „Prenosi li se metoda 7/8, Liu ili Xu–Sang na L-funkcije višeg stepena? Ako da, kako se E mijenja sa stepenom d i postoji li T_d između porodica?“ Registar metoda dobija polje *porodica / stepen d*; T_d je podatak, ne kod; misija 2 je otvoreno pitanje dok ga račun ne zatvori.
33. **Engine za inspiracije („Ideje“):** posle čitanja onoga što se dešava na internetu (arXiv i izvori sa allowliste, kroz Guardian egress), predlaže **ideje**, ne tvrdnje. Svaka ideja: oznaka INSPIRACIJA, izvor (kartica), za koju misiju i zašto, šta bi trebalo da postane provjerljiva metoda. Nikad ne ulazi u vault kao činjenica. Operater bira: zadrži · odbaci · pretvori u otvoreno pitanje. **Da ne preplavi:** najviše 3 ideje sedmično (operater mijenja), rangirane po vezi sa misijom, bez duplikata, mala značka umjesto iskačućih prozora, sedmični pregled, „odgodi“. Skeptik napada svaku ideju prije nego što je operater vidi.
34. **Interaktivni grafovi** (matplotlib je već dio paketa, radi offline): tab **Grafovi** sa zumom, pomjeranjem i očitavanjem vrijednosti pod mišem; klizači za parametre (ℓ, b, κ, t, w, d) koji odmah crtaju funkcije eksponenata, presjeke, zidove i ciljeve (7/8, 0.87, 5/6, 3/4, 1/2); poređenje metoda jednu preko druge; klik na tačku otvara karticu/izvor; izvoz PNG/SVG + podaci CSV; svaki graf označen nivoom (RAD / NAŠE-NERECENZIRANO). Lab grafovi (sada statični PNG) prelaze na isti interaktivni prikaz.
35. **Graf znanja vizuelno:** tab Graf (sada stablo) dobija i prikaz čvorova i veza (teme, kartice, metode, misije), klik otvara karticu.

### Faza 7 · Dokumentacija i izdanje
25. Uputstvo za instalaciju .deb, vodiči SR/EN ažurirani.
26. Detaljan vodič za živi test sa pravim AI-jem (git i računar). Test radi Andrej.
27. CI koji instalira .deb na čistom sistemu i radi pravi poziv (P9).
28. Verzija 0.2.0, tag `v0.2.0`, .exe samo kao GitHub Release.
29. Tri .deb paketa ponovo izgrađena i provjerena, .exe, testovi, snimci ekrana, oba repoa, spajanje u `main` uz odobrenje, odluka o sedmičnom podsjetniku (ostaje ili se briše).

**Ne ulazi sada** (u `SLJEDECA-VERZIJA.md`, odjeljak E): P4 i S1 (prijava), S10 (mTLS federacija), P2 (vanjski merač sa potpisom).

**Procjena:** oko 62–92 sata rada (bez P4) + oko 26–40 sati za Fazu 6b = **oko 88–132 sata**, kalendarski oko 7–11 dana (bez auto-nastavka sporije: rad ide samo dok je chat otvoren). Napredak faza po fazu u WORKLOG.
