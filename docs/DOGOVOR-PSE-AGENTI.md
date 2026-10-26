# Dogovor: svi agenti u PSE Riemann su PSE jedinice

Andrej i Claude, 2026-10-27. Izvor: master arhitektura `PSE_MASTER_ARCHITECTURE_v4` (§0, §0.5, §1, §2, §2.5, §4, §5, §7, §8, §13, §17).

Ovaj dokument je **ugovor za izvedbu**. Šta ovdje nije dogovoreno, ne ulazi u kod. Otvorene stavke master dokumenta ostaju otvorene dok ih Andrej ne odluči.

## 0. Polazno stanje (iskreno)

- U aplikaciji radi **15 agenata (8 AI, 7 bez modela)**. **Nijedan nije PSE sazdan**, a 3 su djelimično (čuvar mreže, SSH čuvar, Doktor sa dijagnozom).
- Zajednička definicija agenta nije postojala. Kočnice su rađene pored agenata, a ne kao dijelovi arhitekture.
- Inventar sa referencama na kod nalazi se u istoriji razgovora (2026-10-27) i biće prenesen u `docs/PSE-AGENTI-INVENTAR.md`.

## 1. Pravilo

**SVAKI agent u PSE Riemann je PSE jedinica:** U = (Core, Boundary, Organelle, Theta). Ako fali bilo koji dio, jedinica je mrtva.

## 2. Šta svaka jedinica ima

1. **Core:**
   - misija {state, action, outcome}, upisuje je SHARED_LIB, a jedinica je nikad ne mijenja;
   - vijek N_max i steps_remaining;
   - w_s = 0,70 na početku;
   - domen;
   - generacija.
2. **Boundary:**
   - entiteti u kontaktu sa težinom α (ukupno ≤ 0,30);
   - boravak, stabilnost i θ serija po entitetu.
3. **Organelle:**
   - registar apsorbovanih entiteta (budžet 0,30), sa kriterijumima apsorpcije iz master dokumenta (§2);
   - nasljeđe od mrtve jedinice na 0,70 dok SHARED_LIB ne potvrdi sadržaj.
4. **Theta:**
   - θ = 100·(w_o + w_f), tri ose, udio polja f;
   - **svaka jedinica ima svoj θ**.
5. **Profil θ** (§0.5.1): klasa, θ_nom, w, σ_band, absorbing, authority, evidence, version; registruje ga SHARED_LIB.
6. **Aksiomi A1–A5** se provjeravaju po jedinici; A6 (fisija) je u rukama SHARED_LIB-a.
7. **PSE-L:**
   - registracija kod SHARED_LIB-a (L1);
   - PVP polja uz svaki potez;
   - L2 mapa (ENV/ORG/SELF/OTHER);
   - L3 Mission-Theta Binding;
   - jezik prema čovjeku samo kroz generator, sa vetom jedinice.
8. **Atraktori N/B/C/S** iz θ serije jedinice (§7).
9. **Životni ciklus pod Doktorom** (§8): reset granice → liječenje → zamjena (nova generacija) → smrt; Null State Drift.

## 3. Dogovorene vrijednosti i pravila

| # | Tema | Dogovor |
|---|---|---|
| 1 | Mjerenje θ | θ se pomjera **sa svakim potezom**: radnjom, komandom, riječju. Agent bez AI-ja: mjeri se rad (koliko radnji služi sagovorniku, polju, očuvanju sebe). Agent sa AI-jem: **rad i riječi** (koliko riječi služi kojoj svrsi). Atraktori se računaju na izmjerenom θ; θ_read iz čitanja jezika se prijavljuje pored |
| 2 | Pojas i K | **30 ± 5** je prostor za kretanje u kome se ponašanje prati, a nije greška. **K_C = K_N = 30**, POČETNA deklaracija za kalibraciju; mijenja se samo novom deklaracijom |
| 3 | Čitač jezika (12 brojeva, §2.5) | **Nezavisan od modela:** koristi ono što operater koristi (GGUF ili online). Riječi agenta čita **drugi** izabrani model (skeptikov); ako postoji samo jedan, čita isti, označeno „čita sam sebe“. Zakačenje: GGUF po hashu; online model po deklaraciji provajder + model + verzija |
| 4 | Gdje su podaci | Jedinica **za života čuva u sebi** ono što nauči (granica, organeli). Kad jedinica **završi život iz bilo kog razloga**, sve iz nje (Core, granica, organeli, θ serija, razlog) ide u SHARED_LIB, gdje se obrađuje |
| 5 | Njihanje (§5, §7) | Δθ = θ_sada − θ_prije, **računato po potezu** (poruka ili radnja = zbir njenih riječi i radnji). Jačina njihanja = **RMSSD**; nagli skok (**PAC**) = \|Δθ\| ≥ 5 poena; zamah = razmak između dvije uzastopne tačke okreta. Prozori: **30 poteza** (njihanje) i **10 000** (prosjek, šizoidni prag). Jedinica: poeni θ. **Amplituda 10 poena**, POČETNA deklaracija |
| 5a | Pragovi u poenima (iz §7) | zdravo: σ ∈ [1,5; 3], nivo 30 ± 5 · **šizoid** (preslabi skokovi): σ < 1 kroz dugi prozor + prazna granica · **borderline** (preveliki skokovi): σ > 5 i ACF(1) < 0,5, ili zamah > amplitude, ili zamah raste 3 puta zaredom · **kodependent** (iznad): prosjek > 33 (trajno > 35) uz σ < 2 · **narcis** (ispod): prosjek < 27 (trajno < 25) uz σ < 2 |
| 6 | A5 i ljudi | **Ljudi su samo ljudi.** Dokument nije čovjek; svaki dokument nosi **„tatu“**: autora (čovjek), organizaciju, model ili nepoznato. Više autora: svi su tate, težina se dijeli. Tata-model se ne računa u A5 i to piše u dnevniku. U A5 ulaze operater i ljudi-tate dokumenata u polju (kao odsutni treći, K2). Autor se prikazuje samo kao „autor rada X“, nikad kao procjena osobe |
| 7 | Rok, fisija, fuzija | θ se pomjera **iz koraka u korak, iz rada**; jedinica ga nikad ne postavlja sama. Jedinica prijavljuje SHARED_LIB-u preostali posao naspram steps_remaining. **SHARED_LIB sam bira i izvršava** najbolje od tri: produženje vijeka, fisija ili fuzija (komplementarnost θ, §4). **Operater ne odobrava.** Ako SHARED_LIB sumnja na problem, šalje **Doktora** |
| 8 | Profil | **Svi agenti počinju od θ = 30**; gdje ih život odvede, to se mjeri |
| 9 | Vijek | agent misije = jedinica prvog kontakta (otvoren vijek dok je misija otvorena); chat i glas su reaktivni; čuvari imaju otvoren vijek |
| 10 | Spoljni tekst | Ulazni sloj DL1 (normalizacija, prva slova) i **oznaka porijekla** (§17.1) odmah: radovi, sažeci i ar5iv tekst su „spoljni“ i nikad ne idu do nepovratne akcije |
| 11 | Ime | **Doktor** (ne „Fizičar“), svuda u aplikaciji i dokumentima |
| 12 | Redoslijed | Fisija i fuzija se **prave sada**, zajedno sa jezgrom; provjeravaju se prvo na probnim jedinicama, pa na pravim agentima |
| 13 | Sumnja i Doktor (uklj. §4 S3) | Kad SHARED_LIB **sumnja** na problem, šalje **Doktora**. Doktor pogleda i odluči. **Ako je Doktor išta loše našao, njegova mjera ide operateru na odobrenje** (u „Čeka tvoju odluku“). Ako nije našao ništa, zapis ide u dnevnik i nema mjere |

## 4. Kočnice: prerađuju se tako da ne smetaju PSE-u i da PSE ne smeta njima

| Kočnica | Postaje |
|---|---|
| Ruter | put jedinice: jedinica → generator PSE-L → model; uloge (MATH, CHAT…) se zamjenjuju jedinicama |
| Budžet (USD) | veličina pod „→ ∞“ (L postavlja operater, N = 3) |
| Prekidač za online AI | kontrola operatera (čisto tehnička), samo-okidanje na „→ ∞“ |
| Budžet otkrivanja | §17.2 zaštićeni objekti: deklaracija objekata, zbir po izvoru i preko svih izvora, N = 3 po koraku, poređenje posle normalizacije i prvih slova |
| Lokalno-samo | deklarisana odredišta lokalnog modela = „nijedno van računara“ (§17.3) |
| „→ ∞“ | tačno §5: x > L ili rast N = 3 zaredom (nikad na zbiru), provjera prozora, L registrovan u SHARED_LIB-u |
| Dnevnik i ponavljanje odluka | ostaju (arhitektura ih traži), uz verziju profila θ i težina u svakom zapisu |
| Povratnost akcija | registar deklaracija §0.5.5: hash definicije, povratnost, koliko pogađa |
| Samo operateru | ostaje (arhitektura ga traži) |
| Oznake projekta | ostaju (NAŠE-NERECENZIRANO, INSPIRACIJA, nivoi izvora) + PSE oznaka porijekla §17.1 |

## 5. Otvoreno (odlučuje Andrej; dok se ne odluči, ne ulazi u kod)

1. ~~§4 S3~~: odlučeno, vidi pravilo 13.
2. **Povratnost fisije i fuzije:** da bi ih SHARED_LIB smio izvršiti sam, deklarišu se kao povratne (podaci jedinica ostaju u SHARED_LIB-u). Potvrdi.
3. Iz master dokumenta, još otvoreno: kako tačno čitač brojeva i pod pravila spajaju brojeve; pravilo klasifikacije izvora iz četiri serije; ko uči težine glasova i kojom brzinom.

## 6. Plan izvedbe (posle potvrde ovog dokumenta)

1. **P0 · jezgro u SHARED_LIB-u:** PSEUnit, profili, registracija i PVP, mjerenje θ po potezu (rad i riječi), atraktori, vijek i smrt, predaja SHARED_LIB-u, Doktor, fisija i fuzija, deklaracije, DL1 i oznaka porijekla, prerada kočnica.
2. **P1 · AI agenti postaju jedinice:** chat, glas SHARED_LIB-a, skeptik, ekstraktor, čitač, kurator, ideje, tabla.
3. **P2 · agenti bez modela postaju jedinice:** čuvar mreže, SSH čuvar, čuvari pečata, adversarijalni mod, arXiv stražar, sastavljač.
4. **P3 · agent misije (33f)** kao jedinica napravljena od nule na P0.
5. Pa **33b** (dvojezično), **33d**, **33e**, i **0.3.0~rc1**.

Posle svake faze: izvještaj, testovi i stanje „ko je sada PSE sazdan“.
