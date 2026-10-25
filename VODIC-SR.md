# PSE Riemann — vodič

Poređano po važnosti: prvo ono što ti treba danas, na kraju detalji.

---

## 1. Pokretanje

**Prvi put, jednom:**

```bash
cd ~/Desktop/PSE/PSE\ Riemann/app
./setup.sh
```

Pravi venv u `app/.venv` i u njega instalira PySide6-Essentials, mpmath, numpy i
matplotlib. Ništa se ne dira sistemski — Mint blokira pip u sistemski Python
(PEP 668), pa je venv jedini ispravan put. Brisanje foldera `app/.venv`
poništava sve. Traje par minuta i **treba internet**, pa uradi kod kuće.

**Poslije toga, uvijek:**

```bash
cd ~/Desktop/PSE/PSE\ Riemann/app
./run.sh
```

`run.sh` sam nađe interpreter: prvo `$PSE_PYTHON` ako ga postaviš, pa
`app/.venv/bin/python`, pa sistemski `python3` ako slučajno ima sve. Ako nema
ništa od toga, ispiše tačno šta da pokreneš umjesto da pukne u traceback.

Iz terminala, bez GUI-ja:

```bash
./run.sh --selftest        # provjera numerike, kapije, Guardiana, journala
./run.sh --lab             # spisak eksperimenata
./run.sh --lab explicit    # pokreni jedan
./run.sh --harvest         # jedan ciklus skupljanja literature
./run.sh --briefing        # jutarnji briefing u terminal
./run.sh --report          # sedmični izvještaj
```

---

## 2. ⚠ Uradi OVO prije puta

Ovo je jedina stvar u vodiču koja ima rok.

1. **`./setup.sh`** — jednom, kod kuće, sa internetom.
2. **Pokreni aplikaciju kod kuće**, na mreži kojoj vjeruješ; u čarobnjaku unesi
   ključeve i klikni **Testiraj** na svakom provajderu.
3. Otvori **Corpus → ⬇ Skupi** i pusti jedan ciklus da prođe.
4. Otvori **Guardian → Test mreže**.
5. `./run.sh --selftest` — mora reći **SVE PROLAZI**.

Zašto: aplikacija pamti javne ključeve (TLS pinove) svakog servera pri **prvom
kontaktu**, i poslije odbija da razgovara sa serverom koji ih ne pokazuje. To je
odbrana od presretanja na tuđem WiFi-ju — ali vrijedi tačno onoliko koliko
vrijedi mreža na kojoj je prvi kontakt napravljen. Ako prvi kontakt uradiš na
hotelskom WiFi-ju, zapamtićeš presretača.

Uz to, u Guardian tabu provjeri i host: ako `ufw` nije uključen ili nešto sluša
izvan loopbacka, tamo piše tačna komanda.

---

## 3. Dnevni ritam

**Ujutru** — aplikacija se otvori na tabu **Plan**: šta si radio juče, šta je
otvoreno, šta plan kaže za danas, i šta traži pažnju (kartice koje je skeptik
oborio, ili FOLKLORE na koji se drugi oslanjaju).

**Tokom dana** — jedno pravilo: **bar jedan `COMPUTED` rezultat dnevno.**
Čitanje bez računanja se ne broji. Statusna traka dolje ti to i mjeri.

**Uveče** — Editor → *Dnevnik danas*. Tri naslova su već tu.

---

## 4. Lab — jedini izvor istine koju aplikacija sama proizvodi

Dvanaest eksperimenata, poređanih pedagoški. Prođi ih odozgo naniže prvih par
dana i predmet se sam sklopi.

| ključ | pitanje na koje odgovara |
|---|---|
| `selftest` | Da li se ovoj mašini može vjerovati? **Pokreni prvi.** |
| `z_curve` | Gdje su nule i kako izgledaju |
| `zeros` | Razmaci; ima li opasno bliskih parova (Lehmer) |
| `counting` | Da li je broj nula NA pravoj = ukupan broj u traci (prava provjera RH) |
| `gram` | Da li svaki Gramov interval ima tačno jednu nulu |
| `explicit` | **Kako iz nula izlaze primovi.** Najvažniji demo. |
| `prime_counting` | π(x) vs li(x) vs R(x) |
| `gue` | Da li se nule ponašaju kao svojstvene vrijednosti slučajnih matrica |
| `robin` | σ(n) < e^γ n log log n — RH prevedena na cijele brojeve |
| `mertens` | Slutnja koja je pala poslije sto godina |
| `s_of_t` | Koliko S(T) odstupa od glatke formule |
| `strip` | ζ na kritičnoj traci |

Svako pokretanje sam upisuje `COMPUTED` karticu sa parametrima, brojevima,
grafikom, **sha256 skripte koja ga je proizvela** i verzijom mpmath. To znači da
možeš mjesecima kasnije uzeti `vault/lab/<run_id>/script.py` i dobiti isti broj.

Kapija ne pušta `COMPUTED` karticu bez toga — i to je namjerno: neprovjerljiv
broj u bazi znanja gori je od nikakvog, jer za šest mjeseci izgleda isto kao
provjeren.

---

## 5. Kapija — zašto ovo nije wiki

Sve što ulazi u vault prolazi kroz jednu funkciju. Statusi:

| status | znači | uslov |
|---|---|---|
| `COMPUTED` | mi smo izračunali | lab_run + sha256 skripte |
| `CITED` | neko drugi je, i možemo naći gdje | bar jedan razrješiv izvor |
| `FOLKLORE` | tvrdnja bez izvora | prolazi, ali obilježena; ništa provjereno se ne smije osloniti na nju |
| `SPECULATION` | tvoja ili modelova ideja | ide u `speculation/`, **nikad** u `knowledge/` |
| `SUSPECT` | skeptik je pogodio | prigovor stoji u tijelu kartice |
| `REFUTED` | pokazano netačnim | **ne briše se** — negativan rezultat je rezultat |

Razrješivi oblici izvora:
`arxiv:2405.12345` · `doi:10.xxxx/yyy` · `lmfdb:...` · `oeis:A000040` ·
`openalex:W...` · `mathoverflow:12345` · `wikipedia:Riemann_hypothesis` ·
`book:Edwards 1974, ch. 6` · `url:https://...`

**Anti-crank pravilo.** Kartica koja tvrdi dokaz RH (ili Collatza, Goldbacha,
BSD, P vs NP) biva odbijena, ko god je napisao. Filter razumije kontekst: tačne
tvrdnje prolaze —

- „Weil je dokazao analogon RH nad funkcijskim poljima" ✅
- „Dokaz RH ne bi razbio RSA" ✅
- „Pod pretpostavkom RH, greška u π(x) je O(√x log x)" ✅
- „Rodgers i Tao su dokazali da je Λ ≥ 0" ✅
- „Dokazao sam Riemannovu hipotezu" ⛔

Ako ti se ikad učini da si nešto dokazao — to je znak da nešto ne razumiješ.
Zapiši u `speculation/` i idi dalje.

---

## 6. Chat (desnih 30%)

- Polje za unos **raste sa tekstom do pola visine panela**, pa skroluje.
- **Kontekst je eksplicitan.** Šta je u traci — to model vidi. Nema skrivenog
  dohvatanja. Kartice dodaješ dugmetom *→ u kontekst chata* u Corpusu.
- Model **ne piše u vault.** Predlaže karticu, a ti vidiš **presudu kapije
  prije nego klikneš** — „⛔ nema izvora" stoji tu prije nego što išta potrošiš.
- Uloga (`math`/`chat`/`summarize`) bira koji model odgovara.

---

## 7. Ruter — zašto ovo košta skoro ništa

| uloga | ko radi | zašto |
|---|---|---|
| `math` | Claude → Gemini → Mistral → Groq | jedino mjesto gdje se greška stvarno plaća |
| `vision` (tabla) | Claude → Gemini | samo oni vide slike |
| `triage` | **Groq** → Mistral → Gemini → Claude | stotine apstrakata, besplatan tier |
| `curate` | **Groq** → … | isto |
| `skeptic` | **Mistral** → Groq → … | namjerno drugi model od onog koji je pisao |
| `summarize` | **Groq** → … | jeftino |

Skeptik ide na **drugog** provajedera od onog koji je napisao karticu. Model koji
ocjenjuje sopstveni rad nije provjera.

Dnevni limit je tvrd stop, ne upozorenje (podrazumijevano $5; Ctrl+K →
„Budžet"). Kad se dostigne, plaćeni pozivi staju — besplatni nastavljaju.

---

## 8. Corpus — od interneta do znanja

Tri filtera, svaki skuplji od prethodnog, pa najskuplji vidi najmanje:

1. **gruba** (besplatno, trenutno) — pominje li uopšte ζ / L-funkcije / primove
2. **trijaža** (jedan jeftin poziv po radu) — je li relevantno, koja grana, koliko
3. **promocija** (kroz kapiju) — postaje `source` kartica sa provenijencijom

Sve sirovo pada u `inbox/`. **Inbox nije korpus** — to je jeftin signal. Ništa ne
ulazi u bazu znanja dok ne prođe sva tri koraka.

**📖 Pročitaj rad** (samo arXiv) skida ar5iv HTML — bez PDF parsera, bez 30 MB —
i jaki model izvlači 2–6 kartica, svaka sa arXiv ID-jem kao izvorom. Ovo je
jedino mjesto gdje se skupi model koristi na literaturi.

**⚔ Skeptik** napada karticu. Ako pogodi, kartica postaje `SUSPECT` i prigovor
se upisuje **u samu karticu** — sumnja putuje sa tvrdnjom, a ne ostaje u chat
logu koji nikad nećeš skrolovati unazad.

Izvori: arXiv · ar5iv · **LMFDB** · OEIS · OpenAlex · Crossref · Wikipedia ·
zbMATH · MathOverflow · Numdam · Odlyzko · Tao blog. **Nijedan ne traži plaćen
ključ.**

LMFDB daje nule ζ sa ~32 cifre. `sources.cross_check_zeros()` poredi naš mpmath
sa njima — dva nezavisna izvora koja se slažu su dokaz, jedan je samo broj.

---

## 9. Tabla

Potezi se **uvijek** snimaju kao SVG + PNG i embeduju u md bilješku — sa ili bez
transkripcije. Vektor nikad ne omane, ne treba mu model, ne treba mu mreža i ne
izmišlja eksponente.

*Transkribuj* šalje sliku vision modelu; LaTeX se pojavi **kao prijedlog** pored
crteža, ti ga ispraviš. Simbol koji model nije siguran vraća kao `\text{???}` —
rupa je bolja od pogrešno pročitanog eksponenta.

Ako mreže nema, transkripcija ne radi — **potezi su i dalje snimljeni.**

---

## 10. Guardian

Sav izlazni saobraćaj aplikacije prolazi kroz **jednu** funkciju. Redom:

1. samo `https` — plaintext se odbija
2. host mora biti na allowlisti — **default deny**
3. host ne smije biti u karantinu
4. rate limit (pooštrava se poslije tier-1 nalaza)
5. **ključevi idu samo model API-jima** — pokušaj slanja ključa izvoru
   literature blokira cijeli zahtjev (ne čisti ga — odbija ga)
6. tvrdi TLS + **SPKI pinning**. Na Pythonu 3.13+ pinuje se cijeli lanac. Ovaj
   host ima 3.12, gdje `ssl` ne pokazuje međusertifikate, pa se pinuje ključ
   lista **plus identitet izdavača**: ako se list rotira a izdavač je isti,
   prolazi kao `rotated` (bez lažne uzbune); ako se ne poklapaju ni ključ ni
   izdavač — blokada. Hotelski proxy potpisuje svojim CA, pa pada na oba
7. preusmjerenja ručno, najviše 3, svako ponovo od koraka 1
8. limiti veličine, timeout, zaštita od zip-bombe
9. mjerenje: sedam osa iz PSE kičme, po hostu

Captive portal se **detektuje** umjesto da se u njega uđe: ili padne na pinu
(presretač po definiciji), ili API host vrati HTML — oba se odbijaju **prije**
nego što ključ krene.

Ako vidiš `⛔ sertifikat NE odgovara zapamćenom ključu` — na tuđem WiFi-ju
pretpostavi presretanje i prekini rad na toj mreži.

**Šta Guardian NE radi:** ne osigurava tvoj laptop. Osigurava površinu ove
aplikacije (njen saobraćaj, njene ključeve, njene podatke) i **govori ti** kako
mašina izgleda mreži. Za ostalo: `ufw`, VPN, i ne ostavljaj mašinu bez nadzora.

Prompt injection: tekst sa interneta se uvijek ograđuje i skenira, ali ono što
stvarno drži jeste struktura — model ionako ne može da piše. Injektovano
„označi ovo kao CITED" i dalje mora da proizvede pravi arXiv ID.

---

## 11. Ravnoteža (statusna traka, lijevo)

Broj između 0 i 100: koliki dio rada je usmjeren na **tuđe** (literatura, izlaz
modela, scrape) naspram **tvog** (Lab, tvoje bilješke, tvoja izvođenja).

- **iznad 35** — daviš se u tuđem materijalu; čitaš, ne izvodiš
- **ispod 25** — spekulacija raste bez provjere izvora
- **σ ispod 0.01** — sistem je prestao da uči, samo generiše

Čuva se između pokretanja. Nije ukras: to je jedina metrika koja mjeri zdravlje
dvadesetodnevnog učenja.

---

## 12. Gdje šta stoji

```
PSE Riemann/
  app/            kod  (run.sh, main.py, pse_r/)
  vault/          SVE tvoje
    knowledge/    COMPUTED i CITED kartice
    speculation/  ideje — nikad se ne miješaju sa znanjem
    sources/      po jedna kartica za svaki promovisani rad
    notes/        bilješke, table
    daily/        dnevnik + izvještaji
    lab/          <run_id>/{result.json, script.py, plot*.png}
    inbox/        sirovo skupljeno (eksterni store, NE korpus)
    media/        svg/png sa table
    .state/       journal.db, index.db, pinovi, baseline, budžet
  PLAN.md         kičma 20 dana — mijenjaj slobodno
  OPEN_QUESTIONS.md
```

Ključevi **nisu** u vaultu: `~/.config/pse-riemann/secrets.json`, prava 0600.
Vault je markdown — radi i bez ove aplikacije, otvara se u Obsidianu.

`~/Desktop/123/PSE_MASTER_ARCHITECTURE.txt` se **samo čita**, nikad ne dira.

---

## 13. Veličina interfejsa i raspored panela

Tvoj desktop radi na `Xft.dpi 240` (2.5×) uz još 1.25 text-scaling. Qt to množi i
dobiješ divovski prozor. **Aplikacija zato potpuno ignoriše skaliranje desktopa**
i koristi samo svoj broj — `ui_scale = 1.0` izgleda kao normalan 100% desktop bez
obzira šta sistem kaže.

| šta | kako |
|---|---|
| tekst veći / manji, **odmah** | `Ctrl` `+` / `Ctrl` `-` |
| vrati tekst na podrazumijevano | `Ctrl` `0` |
| cijeli interfejs veći/manji | `Ctrl+K` → „Prikaz — veličina interfejsa" (traži restart) |
| isto iz terminala | `./run.sh --scale 1.25` |
| resetuj raspored panela | `Ctrl+K` → „Prikaz — resetuj raspored panela" |

Ako ti je poslije ovoga sve **premalo** (panel je 1920×1080 na 235 mm, pa je
visok DPI opravdan), digni: `./run.sh --scale 1.3`. Vrijednost se pamti.

**Paneli se vuku na sve strane.** Svaka granica između panela je hvatljiva
(7 px, plavo na prelazu miša) i vodoravno i uspravno:

- glavna podjela radna površina / chat
- Lab: spisak ↕ istorija, i rezultat ↕ grafik
- Corpus: lista ↔ detalj · Editor: izvor ↔ pregled · Tabla: crtež ↔ LaTeX

Veličina prozora i svih panela se **pamti između pokretanja**.

---

## 14. Prečice

`Ctrl+K` paleta komandi · `Ctrl+S` snimi u editoru · `Ctrl+1/2/3` Plan/Lab/Corpus
· `Ctrl +/-/0` veličina teksta · `Enter` šalje u chatu, `Shift+Enter` novi red

---

## 15. Ako nešto pukne

| simptom | šta uraditi |
|---|---|
| `ModuleNotFoundError: No module named 'PySide6'` | nisi pokrenuo `./setup.sh` |
| `nema modela` u traci | Ctrl+K → „Provajderi — čarobnjak" |
| `dnevni limit dostignut` | Ctrl+K → „Budžet", ili radi na besplatnim |
| `sertifikat NE odgovara` | **prekini rad na toj mreži.** Ako si siguran da je rotacija, obriši pin — ali sa mreže kojoj vjeruješ |
| `host u karantinu` | Guardian tab → oslobodi, svjesno |
| API host vratio HTML | captive portal — prijavi se na mrežu; ključ NIJE poslat |
| brojevi izgledaju čudno | `./run.sh --selftest`. Ako `selftest` padne, ne vjeruj ničemu drugom |
| vault izgleda pokvareno | journal je append-only sa hash-lancem; `--report` pokazuje da li je lanac neprekinut |
| hoćeš čist početak | obriši `vault/`, aplikacija se sama zasije pri pokretanju |
| prozor ogroman ili sićušan | `./run.sh --scale 1.0` (pa 1.2, 0.9 … dok ne legne) |

---

## 16. Šta ovo NIJE

- Nije dokazivač teorema. Ne provjerava dokaze formalno (za to bi trebao Lean).
- Nije potpun renderer LaTeX-a. Matematika ide kroz matplotlib mathtext — velik
  podskup, ne sve. Ono što ne umije prikazuje kao izvor, ne guta ćutke.
- Nije endpoint security. Vidi §10.
- Ne zna da li je RH tačna, i neće se pretvarati da zna.

## 17. v2 — kvazi-Rimanova hipoteza (QRH)

Nadogradnja iz 2026-10 dodaje istraživanje QRH (granice "nema nula za Re s > B")
i SHARED_LIB kao nadzornika. Poenta: **novi rad sa arXiva → prijedlog metode →
test reprodukcije → skeptik → ti potvrđuješ.**

**Operater.** Pri pokretanju upišeš **samo ime** (bez lozinke). Ime se veže za
svaki upis, odluku i izvještaj. Glas biblioteke govori samo tebi.

**Tab Misije.** Stojeća pitanja sa frontom (najniže B) i dnevnikom koraka
(stanje → akcija → ishod). Prva misija: postoji li kontinualna transformacija
između QRH metoda i vodi li njeno proširenje prema ciljevima (0.87, 5/6, 3/4,
1/2) ili od njih.

**Red „Čeka tvoju odluku".** Jedino mjesto gdje sve čeka tebe: prijedlozi
metoda, prigovori skeptika, deklaracije, liječenje (stepen 2). *Odobri* /
*Ne odobri* su prave, zapisane odluke.

**Uvezi metodu (otvorena vrata).** Paket metode (jedan JSON: familija, izvor,
tvrđeno B, test reprodukcije) ulazi **samo kroz kapiju**. Prvo ide
**deterministički test reprodukcije** — naš pipeline (`methods/`) ponovo izvede
broj iz rada; ako se ne poklopi, paket se **odbija na vratima** i ne stiže u red.
Nijedan model to ne može zaobići. Primjeri paketa: `research/qrh-2026-10/
method-packs/` (Liu, Xu–Sang, 7/8, 11/12).

**Lab — QRH eksperimenti.** `qrh_line` (V(ℓ) duž prave), `qrh_poly` (egzaktni
minimalni polinom B*), `qrh_transform` (T = E_XS − E_Liu, produženja), `qrh_walls`
(ljestvica zidova ≈ 5/6), `qrh_licence` (iteracija κ). Svaki daje COMPUTED
karticu (NAŠE-NERECENZIRANO).

**Glavni AI + skeptik.** Jedan glavni model radi sve uloge; **skeptik je uvijek
drugi model** (nezavisnost) i samo napada (prigovor · razlog · gdje ·
ozbiljnost), bez prava upisa. Izbor u tabu „Čeka tvoju odluku". Podrazumijevano:
glavni = Claude (oblak), skeptik = DeepSeek GGUF (lokalno). Bez drugog modela →
skeptik „nedostupan", rade samo determinističke provjere.

**Lokalni GGUF.** DeepSeek-R1-0528-Qwen3-8B (Q5_K_M) stavi u `models/` (van
gita). Učitava se u procesu (llama-cpp) tek kad se izabere, uz limitere (RAM, 3
od 4 niti, n_ctx 8K, think-budžet, timeout, jedan poziv u redu, prekid vrtnje,
pravilo „→ ∞"). Deklariši sha256 modela (red „Čeka tvoju odluku") da učitavanje
bude determinističko.

**Nivoi izvora.** REFEREED (doi/book) · LEAN (mašinski dokaz) · PREPRINT
(arxiv/url) · AI-UNREVIEWED (model) · NAŠE-NERECENZIRANO (naš COMPUTED). Preprint
ne može biti oslonac za **utvrđenu** tvrdnju.

**Čuvari i tri zla.** Čim se pojavi finalni izvještaj, biblioteka ga pečati
(sha256 u lancu, read-only, patrola vraća iz pečata ako je dirnut). Svaki agent
se prati na tri zla (čovjeku / agentu / fajlu); zaraženi se **liječi** (ne briše):
zadržavanje → dijagnoza → liječenje → oporavak → imunitet; stepen 2 (fisija,
smrt) odlučuješ ti.

**Paketi.** `./packaging/build_deb_pip.sh full` (B: sympy+scipy, prvi) ·
`… lean` (A: bez scipy) · `… research` (C: + llama-cpp, offline).
