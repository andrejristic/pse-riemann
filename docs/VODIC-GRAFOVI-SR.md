# Vodič: tab Grafovi

Tab **Grafovi** crta funkcije i za svaku tačku kaže sve što aplikacija zna o njoj. Uzor je Android aplikacija „Calculus Tools“. Tamo su tri dijela bila tri taba, a ovdje su tri panela jedan pored drugog:

| Panel | Šta radi |
|---|---|
| **Funkcije** (lijevo) | spisak funkcija, svaka u svojoj boji, i klizači parametara |
| **Grafovi** (sredina) | crtež: zum, pomjeranje, očitavanje pod mišem |
| **Kalkulacije** (desno) | „sve o tački“ za tačku na koju klikneš i računi na zahtjev |

**Svaki od tri panela ima svoje dugme ⤢** u zaglavlju (pored naslova „Funkcije“, „Graf“, „Kalkulacije“):
- klik raširi taj panel preko cijelog taba, a ostala dva se sakriju;
- dugme se pretvori u **⤡**, i ponovni klik vraća sva tri panela.

Dugme **⤢ raširi** na vrhu taba radi isto što i ⤢ grafa.

Ako ti treba još mjesta, raširi i sam chat na njegovom ⤢, a chat uvijek vraća Esc. Na ekranu sa krupnim tekstom (npr. Surface, 26 pt) tri panela i chat su tijesni. Tada bočni paneli dobiju klizač, a najbolje je raširiti panel na kome radiš.

---

## 1. Funkcije

### Ugrađene funkcije projekta (dugme „+ ugrađena“)

| Funkcija | Nivo | Šta znači tačka na njoj |
|---|---|---|
| B(ℓ) = 11/12 − ℓ/4 | RAD | zajednička prava: za dato ℓ, granica B. 11/12 je ℓ = 0, 7/8 je ℓ = 1/6 |
| E_Liu(δ) na optimumu | RAD | eksponent visoke strane (Liu) po δ. Ako je max ≤ 0, metoda prolazi |
| E_XS(δ) na optimumu | RAD | isto za Xu–Sang; E_XS = E_Liu + T |
| max_δ E_Liu(ℓ) | NAŠE-NERECENZIRANO | najgori δ za dato ℓ; nula je granica metode ℓ* |
| B*(t) — proširenje t | NAŠE-NERECENZIRANO | granica metode duž proširenja t (misija 1) |
| B*(w) — proširenje w | NAŠE-NERECENZIRANO | granica duž težine w (w = 0,25 je Xu–Sang) |

B*(t) i B*(w) su skupe: oko 4,6 s i 1,9 s po tački na Dellu (na Aceru je procjena oko 1,8 puta sporije). Crtaju se u pozadini iz 9 tačaka, a u naslovu grafa za to vrijeme piše „računam: …“.

### Tvoje funkcije (dugme „+ funkcija“)

Izaberi vrstu i upiši izraz:

| Vrsta | Promjenljiva | Primjer |
|---|---|---|
| realna y = f(x) | `x` | `11/12 - x/4` · `x**3 - 2` · `sin(30*x)/x` |
| kompleksna w = f(s) | `s` | `zeta(s)` · `gamma(s)*zeta(s)` |
| površ z = f(x, y) | `x`, `y` | `x**2 - y**2` |
| parametarska | `u` | `cos(u); sin(u)` (x i y razdvojeni sa `;`) |
| polarna r = f(θ) | `th` | `1 + cos(th)` |

**Šta je dozvoljeno:**
- operacije `+ − * / **` (može i `^`);
- funkcije `sin cos tan exp log sqrt abs atan asin acos sinh cosh tanh re im arg conj floor min max zeta Z gamma`;
- konstante `pi e i`;
- klizači `l b k t w d low delta`.

Sve ostalo se odbija **prije** prevođenja: atributi, uvoz, liste, tekst i slično. Tako upisani tekst ne može uraditi ništa osim računa. Ogroman broj (npr. `10**10**10`) postaje praznina u krivoj, a ne zaglavljen računar.

Domen „od/do“ koristi se za račune (korijeni, površina, pomak do cilja). Upisane funkcije crtaju se preko cijelog vidljivog dijela.

**Uređivanje:**
- dvoklik ili „Uredi“ mijenja funkciju; „Boja“ bira boju; „Ukloni“ je briše;
- kvačica uključuje ili isključuje prikaz;
- spisak se pamti u SHARED_LIB-u, pa preživi restart i ulazi u bilješku „gdje si stao“ misije.

### Klizači (parametri)

ℓ, b, κ, t, w, d, **niska strana** i **Δ**. Pomjeranjem klizača graf se odmah precrtava. Pored „niske strane“ piše **σ\* = 11/16 + niska strana**. Klizač niske strane je pripremljen za korak 4 ove stavke (povezani prikazi), a u izrazu se klizač koristi imenom, npr. `11/12 - x/4 + low`.

---

## 2. Kretanje po grafu

| Želiš | Miš | Tastatura (klikni na graf) | Dugme |
|---|---|---|---|
| pomjeriti lijevo / desno | prevuci lijevim tasterom | ← / → | ◀ / ▶ |
| pomjeriti gore / dolje | prevuci lijevim tasterom | ↑ / ↓ | ▲ / ▼ |
| veći korak | — | **Shift** + strelica (40 % umjesto 10 %) | — |
| uvećati / umanjiti | točkić (oko kursora) | + / − | + / − |
| vratiti početni pogled | — | Home | ⌂ |

Prevlačenje pomjera pogled. **Klik bez prevlačenja** na krivu bira tačku. **Dvoklik** na krivu otvara njenu karticu izvora, ako je ima.

**Ciljevi** (isprekidane linije 7/8, 0,87, 5/6, 3/4, 1/2) i **zidovi** (crvene tačkaste linije B ≥ 0,87 i ℓ ≤ 1/5) uključuju se kvačicama na vrhu.

Naslov grafa uvijek pokazuje **nivo** onoga što je nacrtano, npr. „nivo: KORISNIK · RAD“.

---

## 3. Sve o tački

**Kad pređeš mišem** preko krive, ispod grafa piše: koja funkcija, koordinate, nivo i najbliži cilj sa razlikom.

**Kad klikneš** na krivu, panel Kalkulacije pokaže sve što se zna o toj tački:
- koordinate x i y;
- koja funkcija ili metoda, njen nivo i link na karticu izvora (klik otvara karticu);
- **značenje** tačke (npr. „ℓ → granica B“);
- šta je tačka: nula, presjek (sa kojom funkcijom), zid, stacionarna tačka (moguć optimum), za eksponente „E ≤ 0: metoda prolazi“ ili „E > 0: ne prolazi“;
- f′ u tački;
- **udaljenost do svih ciljeva** (sa predznakom);
- vrijednosti svih klizača.

---

## 4. Računi na zahtjev

Ispod „sve o tački“ stoje **najviše 4 ponude** koje odgovaraju vrsti tačke. Ostale su pod „više…“.

| Tačka | Ponuda |
|---|---|
| bilo gdje na krivoj | izvod i tangenta · drugi izvod (konkavnost) · Taylorov polinom |
| presjek | tačan presjek + interval-certifikat |
| nula | tačan korijen (sympy) + interval-certifikat |
| stacionarna (f′ ≈ 0) | drugi izvod: da li je optimum i koliko je oštar |
| B blizu cilja | pomak parametra do cilja, ili dokaz da ga domen ili zid sprečava |
| proširenje B*(t), B*(w) | kuda proširenje pomjera B: bliže ili dalje od cilja (misija 1) |
| dvije funkcije | osjenčana površina između njih („rezerva“) |

**Procjena trajanja.** Uz svaku ponudu stoji „(odmah)“, „(~N s)“ ili „(~N min)“. Procjena je broj potrebnih izračunavanja pomnožen vremenom jednog izračunavanja:
- za upisane funkcije to vrijeme se izmjeri;
- za ugrađene je izmjereno na Dellu, a Acer je procjena.

Što je jeftino (do 0,3 s) računa se odmah. Skuplje aplikacija samo **nudi** pitanjem „Želiš li da izračunam … (~N s)?“.

**Kako se računa:**
- Računa **Python, deterministički**. AI samo objašnjava, i to kad ga pitaš.
- Račun ide **u pozadini**, jedan po jedan. Dugme **Prekini** zaustavlja sve.
- Pozadinski red poštuje limitere: stoji dok je aktivna „→ ∞“ pauza ili dok je slobodne memorije manje od 0,5 GB.
- Svaki rezultat se **kešira** (isti račun drugi put je trenutan) i zapisuje u SHARED_LIB (tabela `graph_runs`) sa oznakom **NAŠE-NERECENZIRANO** i tvojim imenom.

**Šta znači interval-certifikat.** f se računa intervalnom aritmetikom na krajevima malog intervala oko korijena. Ako su vrijednosti strogo suprotnog znaka **kao intervali**, korijen sigurno postoji (zaokruživanje to ne može lažirati). Ako interval izvoda ne sadrži 0, korijen je **jedinstven**. Certifikat važi samo za upisane izraze, jer ugrađene funkcije su kod. Primjer: Liuov kubni polinom `-7884*x**3 + 18819*x**2 - 14643*x + 3686` na domenu [0,87, 0,88] daje korijen B\* = 0,874957019420, certifikovan i tačan (sympy).

**Taylorov polinom:**
- upisane funkcije idu kroz mpmath sa 40 cifara;
- ugrađene se dobijaju fitom na malom simetričnom uzorku, što piše uz rezultat („procjena“).

---

## 5. Izvoz

- **PNG / SVG**: slika grafa kakav je na ekranu, na tamnoj pozadini, sa oznakom nivoa u naslovu.
- **CSV**: tačke svih vidljivih krivih u trenutnom pogledu, kolone `function, level, x, y`.

---

## 6. Šta dolazi (stavka 29, koraci 3–6)

- parametarske putanje (ℓ(t), B(t)), vektorsko polje nad ravni parametara (kuda proširenje gura B), osjenčana „rezerva“, polarni graf;
- kompleksne funkcije: fazni portret, krive Re f = 0 i Im f = 0, presjeci duž prave (|ζ(1/2+it)|, Z(t)), oblasti, nule u pravougaoniku, rezidui; povezani prikazi (σ, eksponent) ↔ kompleksna ravan; klizač „niska strana + Δ“;
- 3D površi (|ζ| iznad ravni, dvije površi eksponenata), 4. dimenzija kao boja, dalje kao klizači ili animacija, male slike, paralelne koordinate; Acer dobija rjeđu mrežu;
- Lab grafovi prelaze na ovaj prikaz.

Ovaj vodič se dopunjava sa svakim korakom.
