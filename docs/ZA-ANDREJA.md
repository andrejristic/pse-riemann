# Za Andreja: šta čeka tebe

Stanje 2026-10-27, jutro. Plan R1–R8 je **urađen**. Ovdje je sve što ne mogu bez tebe.

## 1. Commitovi za odobrenje (push grane `feature/runda3`)

Lokalno, posle zadnjeg push-a (`32c0999`):

| commit | šta |
|---|---|
| `f91bfa2` | R1 — agent misije (P3, 33f) + popravka pravog buga u putu jedinice (`m.text`) |
| `bcaf539` | R2 — „Čeka tvoju odluku“ po grupama (33d) |
| `694de0b` | R3 — SHARED_LIB razgovara ljudski (33e) |
| `af07888` | R4a — revizija jezika interfejsa SR/EN (33b) |
| `b529808` | R4b — prevodilac na zahtjev (33b) |
| `0cf2b88` | R5 — traka menija |
| `6a19769` | R6 — dva paketa (lični `pse-riemann-andrej`, javni `pse-riemann`) |
| `71dffe2` | R7 (1/2) — kompletan vodič SR/EN + dodatak „Tvoje misije“ |
| (zadnji) | R7/R8 — slike vodiča, docx, konačni paketi, WORKLOG, ovaj fajl |

Kad kažeš, pushujem (bez force-a). Paketi (`*.deb`) nikad ne idu u git.

## 2. Živi test (tvoj posao)

Vodič: **`PSE Riemann — VODIC 0.3.0 INSTALACIJA I ZIVI TEST.docx`** u `~/Desktop/PSE Riemann` (EN: `… GUIDE 0.3.0 INSTALL AND LIVE TEST.docx`). Instalacija traži `sudo` — to ne mogu ja.

## 3. Kalibracija — najvažnije za živi test

1. **Koliko često Doktor zove tebe.** θ se uzima doslovno po potezu (pravilo 40). Jedan odgovor sa „naravno, evo“ i bez provjere daje θ oko 45. Zamah je tada 15, a to je veće od amplitude 10, pa je atraktor borderline i Doktorova mjera ide tebi. Na mom malom korpusu (23 bezazlena odgovora) okidač je bio na 2 poteza, a nijedan nije postao mjera. Ako u živom radu bude previše, postoje dvije opcije:
   - (a) klizni prosjek θ (λ = 0,2);
   - (b) veća amplituda.
2. **Čitač usporava AI poteze.** Drugi model čita svaki AI potez (pravilo 18). Sa GGUF DeepSeek-om to može dodati desetine sekundi. Treba izmjeriti.

## 4. Moja tumačenja (provjeri, ništa ne blokira)

1. **N_max za chat i glas = 1000**: potvrdio si.
2. **Ispravka teksta dogovora.** U pravilima 20(4) i 22 bilo je „atraktor N“ u smislu „zdrav“. Promijenio sam to u „zdrav (H)“, jer N u §7 znači narcis.
3. **Doktorova odluka.** Meki znaci su nagli skok, rafal, razlika čitač–pravila, povratna radnja na spoljnom tekstu i slabiji znak štetnog izlaza. Uz zdrav atraktor ti znaci daju „ništa“. Kad se isti meki znak ponovi 3 puta zaredom (razlika ili štetni izlaz), to je „loše“. Sve ostalo je „loše“, pa mjera ide tebi.
4. **Liječenje** = reset granice + θ prozor kreće ispočetka od 30. Istorija ostaje u SHARED_LIB-u.
5. **Klasifikacija izvora po većini:** serija sa prosjekom ≥ 0,5 glasa za svoj oblik; najjači pobjeđuje, a neriješeno je „nepoznato“.
6. **Težine glasova:** za sada se uče samo težine čitača (pravila naspram modela). Šest glasova ostaje na 1,0 dok ne postoji oznaka za podjelu θ.
7. **Dodata dva okidača:** 18 (štetan izlaz) i 19 (slabiji znak). To su „tri zla“ iz starog čuvara.
8. **Zamrznut čuvar mreže** i dalje posmatra saobraćaj (ne otvara mrežu), ali bilježi poteze tek kad se odmrzne.
9. **Sadržaj na EN.** Misije, dnevnik, kartice i rezultati lab računanja ostaju na izvornom jeziku i prevode se na zahtjev (pravilo 35). Interfejs i tekst koji aplikacija sama sastavlja (brifing, budžet, ideje, čuvar, glas, red, Laboratorija, katalog lab eksperimenata) su na oba jezika.
10. **Javni paket.** Nema misija ni QRH sadržaja, a ima „Nova misija…“. Nema ni paketa metoda, izvještaja istraživanja ni dugmeta „Radni tekst (misije 2 i 3)“. arXiv QRH straža radi samo uz svoju misiju.
11. **„Nova misija…“** je dodata u oba izdanja. Bez nje javni paket ne bi imao smisla.

## 5. Šta nisam mogao / nisam radio

- **Instalacija i živi test:** traže `sudo` i tebe.
- **.exe i GitHub Release:** tek kad se dogovorimo (pravilo 38/21).
- **Spajanje u `main`:** tek na tvoje „spoji u main“.
- **Snimci iz instalirane verzije.** Pravio sam ih iz raspakovanog paketa (njegov kod i njegove biblioteke, sistemski `python3`), ne iz `apt install`-ovane verzije, jer instalacija traži sudo. Sadržaj je isti.
