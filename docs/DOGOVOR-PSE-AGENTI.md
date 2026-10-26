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
| 14 | Povratnost fisije i fuzije | Deklarisane kao **povratne** (podaci jedinica ostaju u SHARED_LIB-u), pa ih SHARED_LIB izvodi sam. **Poništavanje** fisije ili fuzije ide samo preko operatera |
| 15 | Spajanje čitača i pravila (§2.5) | **Sa AI-jem:** θ riječi = **prosjek** čitača i pravila (50/50; težine kasnije uči pravilo 17). **Bez AI-ja:** **samo pravila**, u dnevniku „bez čitača“. **Nikad samo čitač.** Pod ne obavezuje: poenta je da je θ oko 30. Razlika čitač–pravila > 10 poena = sumnja → Doktor |
| 16 | Klasifikacija izvora (četiri serije) | većina od četiri serije; neriješeno = „nepoznato“ = spoljno (§17.1) |
| 17 | Težine glasova | SHARED_LIB **predlaže jednom sedmično**, operater odobrava. Prijedlog samo uz ≥ 200 odlučenih slučajeva od prošlog (inače „nedovoljno podataka“); jedna težina se po prijedlogu pomjera najviše **±10 %**; dugme „Predloži sada“. Meni: **SHARED_LIB → Težine glasova** (prijedlog, istorija, trenutne težine) |
| 18 | Ko mjeri θ riječi | drugi model (skeptikov) raspoređuje riječi na svrhe; to je poziv modela po potezu (pod budžetom i „→ ∞“) |
| 19 | Dok Doktorova mjera čeka | jedinica radi dalje, ali **bez nepovratnih akcija**; **na bilo šta sumnjivo odmah se zamrzava** (pravilo 20). Mjera nema rok |
| 20 | Sumnjivo (okidači zamrzavanja) | (1) PAC \|Δθ\| ≥ 5; (2) pokušaj nepovratne akcije; (3) radnja zasnovana na spoljnom tekstu; (4) atraktor nije N; (5) „→ ∞“ bilo koje kočnice; (6) pokušaj promjene svoje misije; (7) pokušaj da sama postavi θ; (8) budžet granice ili organela > 0,30; (9) kontakt van deklarisanih odredišta; (10) pokušaj iznošenja zaštićenog objekta (§17.2); (11) govor čovjeku mimo generatora PSE-L; (12) potez bez PVP polja; (13) rad posle steps_remaining = 0; (14) rafal: > 20 poteza u 10 s; (15) ista greška u kodu 3 puta zaredom; (16) razlika čitač–pravila > 10 poena; (17) borderline njihanje (5a) |
| 21 | N_max | **1 000 poteza** za skeptika, ekstraktora, čitača, kuratora, ideje i tablu (POČETNA deklaracija) |
| 22 | Izbor produženje / fisija / fuzija | produženje ako je preostali posao ≤ 1,5 × steps_remaining i atraktor N; fisija ako je posla više, a misija se da podijeliti; fuzija ako postoji jedinica komplementarnog θ sa preklapajućom misijom. Najviše **3 produženja zaredom**, pa Doktor |
| 23 | Kratka istorija | šizoidni prag se ne računa ispod **300 poteza** („nedovoljno istorije“) |
| 24 | θ_nom | **30 za sve klase**, bez razlike |
| 25 | Samo PSE native | kad agent postane jedinica, **stari kod se briše**; nema prekidača ni dvostrukog puta. Sve ispravke se rade odmah: ništa od starog, sve radi i ne lomi se (svi stari testovi prolaze, svaki agent ima testove kao jedinica, pretraga za starim ulazima agenata je prazna). Put nazad: samo prethodni deb ili ispravka |
| 26 | Tab „Laboratorija“ | probne jedinice, θ uživo, ručna fisija/fuzija, slanje Doktora, zamrzni/odmrzni, smrt jedinice, dnevnik Doktora. **Utiče i na prave agente.** Pri otvaranju: **alarm 3 s jakog bipa (samo prvi put u sesiji)** i crveni natpis „LABORATORIJA AKTIVNA — utiče na prave agente“ dok je tab otvoren. Svaka radnja ide u dnevnik kao „operater, iz laboratorije“ |

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

## 5. Otvoreno

Ništa. Sve stavke su odlučene 2026-10-27 (pravila 13–26). Andrej je dao „kreni“ za izvedbu.

## 6. Plan izvedbe (posle potvrde ovog dokumenta)

1. **P0 · jezgro u SHARED_LIB-u:** PSEUnit, profili, registracija i PVP, mjerenje θ po potezu (rad i riječi), atraktori, vijek i smrt, predaja SHARED_LIB-u, Doktor, fisija i fuzija, deklaracije, DL1 i oznaka porijekla, prerada kočnica.
2. **P1 · AI agenti postaju jedinice:** chat, glas SHARED_LIB-a, skeptik, ekstraktor, čitač, kurator, ideje, tabla.
3. **P2 · agenti bez modela postaju jedinice:** čuvar mreže, SSH čuvar, čuvari pečata, adversarijalni mod, arXiv stražar, sastavljač.
4. **P3 · agent misije (33f)** kao jedinica napravljena od nule na P0.
5. Pa **33b** (dvojezično), **33d**, **33e**, i **0.3.0~rc1**.

Posle svake faze: izvještaj, testovi i stanje „ko je sada PSE sazdan“.

**Bez međuizdanja (pravilo 25):** P0–P3 se rade do kraja, pa tek onda jedan deb. Na kraju: svi testovi, provjera u pokrenutoj aplikaciji, živi test po vodiču.
