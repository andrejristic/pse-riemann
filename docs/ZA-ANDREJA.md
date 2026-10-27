# Za Andreja: šta čeka tebe (skuplja se za kraj)

Ovdje upisujem sve što ne mogu uraditi bez tebe dok radim P0–P3. Kad se vratiš, ovo je spisak.

## Git
1. **Push** grane `feature/runda3`. Commitovi se skupljaju lokalno, posle `afcb1e5`: `e15e252` (P0 jezgro) i `f27680b` (P0–P2, svi agenti su jedinice).

## Kalibracija: najvažnije za živi test
2. **Koliko često Doktor zove tebe.** θ se uzima doslovno po potezu, bez izglađivanja, jer izglađivanje nije dogovoreno. Jedan odgovor sa „naravno, evo“ i bez provjere daje θ oko 45. Zamah je tada 15, a to je veće od amplitude 10, pa je atraktor borderline i Doktorova mjera ide tebi.
   - Na mom malom korpusu (23 bezazlena odgovora) okidač je bio na 2 poteza. Nijedan nije postao mjera.
   - U živom radu može biti češće. Ako bude previše, postoje dvije opcije:
     - (a) θ jedinice kao klizni prosjek čitanja (npr. λ = 0,2). Jedan izlet 30→60 tada daje 36, a to nije borderline.
     - (b) Veća amplituda.
   - ✓ (a) je bolje kada želiš da pojedinačni odgovori ne pale alarm. ✗ (a) je slabije kada želiš da vidiš svaki izlet odmah.
3. **Čitač usporava AI poteze.** Po pravilu 18, čitač (drugi model) čita svaki AI potez. Sa GGUF DeepSeek-om to može dodati desetine sekundi po potezu. Treba izmjeriti u živom testu.

## Moja tumačenja (provjeri)
4. **N_max za chat i glas = 1000.** §2 kaže „reaktivne jedinice dobijaju N_max/100“, a to bi bilo 10 poteza. Atraktori tada nikad ne bi imali 30 poteza za procjenu, pa sam uzeo 1000.
5. **Ispravka teksta dogovora.** U pravilima 20(4) i 22 bilo je „atraktor N“ u smislu „zdrav“. U §7 N znači narcis, pa sam to promijenio u „zdrav (H)“.
6. **Doktorova odluka.** Meki znaci su nagli skok, rafal, razlika čitač–pravila i povratna radnja na spoljnom tekstu. Uz zdrav atraktor ti znaci daju „ništa“: zapis u dnevnik, jedinica se odmrzava. Sve ostalo je „loše“, pa mjera ide tebi. Razlika čitač–pravila 3 puta zaredom je takođe „loše“.
7. **Liječenje** (druga stepenica ljestvice) = reset granice + θ prozor kreće ispočetka od 30. Istorija ostaje u SHARED_LIB-u.
8. **Klasifikacija izvora po većini.** Serija čiji je prosjek ≥ 0,5 glasa za svoj oblik. Pobjeđuje najjači oblik, a neriješeno je „nepoznato“.
9. **Težine glasova.** Za sada se uče samo težine čitača (pravila naspram modela). Oznaka je tvoja odluka o Doktorovoj mjeri. Šest glasova ostaje na 1,0, jer za podjelu θ još ne postoji oznaka.
10. **Dodata dva okidača:**
    - 18: štetan izlaz (injekcija, curenje, tvrdnja o dokazu);
    - 19: slabiji znak štetnog izlaza.

    To su „tri zla“ iz starog čuvara, sada pod Doktorom. Rekao si „ako možeš dodaj još“.
11. **Meni.** Aplikacija nema klasičnu traku menija. „SHARED_LIB → Težine glasova“ je u paleti komandi (Ctrl+Shift+P). Ako želiš pravu traku menija, to je mala izmjena.
12. **Zamrznut čuvar mreže** i dalje posmatra saobraćaj (ne otvara mrežu), ali bilježi poteze tek kad se odmrzne.

## Provjere koje radiš ti
13. Živi test sa pravim AI-jem:
    - koliko Doktorovih mjera stigne za sat rada (tačka 2);
    - koliko traje potez sa čitačem (tačka 3).
14. Alarm laboratorije sa zvukom. U testovima i na mojim snimcima je utišan (`PSE_RIEMANN_SILENT`), a na tvom računaru će zasvirati 3 s, prvi put u sesiji.
