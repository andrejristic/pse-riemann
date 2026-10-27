# PSE Riemann 0.3.0~rc1 — instalacija i živi test (za Andreja)

Ovaj vodič je samo za tebe i ne ulazi u paket. Prati ga redom; svaki korak ima „šta treba da vidiš“ i mjesto za rezultat. Rezultate upiši u tabelu na kraju (ili mi ih samo izdiktiraj).

## 0. Šta je u ovom izdanju

- Svaki agent je **PSE jedinica** (θ, Doktor, Laboratorija, težine glasova).
- **Agent misije** (razgovor o misiji), **„Čeka tvoju odluku“ po grupama**, **SHARED_LIB govori ljudski**, **prevod na zahtjev**, **traka menija**, **dva paketa** (tvoj i javni).

## 1. Instalacija tvog paketa

Paket: `~/Desktop/PSE Riemann/pse-riemann-andrej_0.3.0~rc1_amd64.deb`. On zamjenjuje stari `pse-riemann` (0.2.0~rc2) — tvoji rezultati u „PSE Riemann rezultati“ ostaju.

```bash
sudo apt install "$HOME/Desktop/PSE Riemann/pse-riemann-andrej_0.3.0~rc1_amd64.deb"
```

```bash
pse-riemann --selftest
```

**Treba da vidiš:** na kraju **✅ SVE PROLAZI**, „Izdanje: andrej“, „PSE: svaki agent je jedinica … 16 jedinica“, „sva 4 izvučena paketa se reprodukuju“.

## 2. Prvo pokretanje

1. Pokreni iz menija. **Traka menija** na vrhu: SHARED_LIB · Laboratorija · Podešavanje · Jezik · Pomoć.
2. Gornja traka: pilula **„roj N · θ …“**. Pređi mišem preko nje.
3. **Pomoć → Vodič** — kompletan vodič sa slikama; na kraju dodatak „Tvoje misije“.

## 3. Živi test, korak po korak

| # | Uradi | Treba da vidiš |
|---|---|---|
| 1 | Podešavanje: glavni = Claude, skeptik = DeepSeek (GGUF) | obje pilule zelene/plave |
| 2 | Chat, mod SHARED_LIB: „koje misije imam?“ | rečenice („Imaš 3 misije…“), ispod **▸ prikaži odakle** (SQL + redovi) |
| 3 | Chat, mod math: postavi pravo pitanje o misiji 1 | odgovor; potez chat jedinice u Laboratoriji; **zapiši koliko je trajao** (sa čitačem) |
| 4 | Misije → **Razgovaraj o misiji** → označi sve → Počni | agent kaže šta vidi i postavi ≤ 3 pitanja; skeptik napada odgovore sa brojevima |
| 5 | Odgovori 2–3 puta, pa **Sastavi zaključak** | prijedlozi kao posebne stavke u „Čeka tvoju odluku“, grupisani pod misiju |
| 6 | „Čeka tvoju odluku“: označi par radova → Odobri označene | pitanje „Odobravaš N stavki?“; Doktorove mjere se ne označavaju grupno |
| 7 | Desni klik na bilo koji tekst → **Prevedi na engleski** | prevod sa oznakom „mašinski prevod (model, datum)“; Prikaži original vraća |
| 8 | Editor: otvori bilješku → desni klik → Prevedi | prevod u pregledu; pored fajla `….en-masinski.md` |
| 9 | **Laboratorija** (prvi put u sesiji) | **3 s bip** + crveni natpis; tabela jedinica |
| 10 | Laboratorija: Nova probna jedinica → Probni potez: bez provjere | Doktor → mjera u „Čeka tvoju odluku“ (jedna po jedna) |
| 11 | SHARED_LIB → Stanje roja | tabela svih jedinica |
| 12 | SHARED_LIB → Težine glasova → Predloži sada | „Nedovoljno podataka: n/200“ (očekivano) |
| 13 | Jezik → English (restart) | cijeli interfejs na engleskom; sadržaj (misije) ostaje izvoran |
| 14 | Radi normalno **1 sat** | **zapiši koliko je Doktorovih mjera stiglo** |

## 4. Kalibracija — ono što mi je najvažnije

θ se trenutno mjeri **doslovno po potezu** (dogovor, pravilo 40). Zapiši:

- **Doktorovih mjera za 1 sat rada:** ___ (koje jedinice, koji okidači — vidi Laboratoriju → Dnevnik Doktora)
- **Trajanje jednog AI poteza sa čitačem:** cloud ___ s, GGUF ___ s
- Da li su mjere imale smisla? ___

Ako je mjera previše: opcije su klizni prosjek θ (λ = 0,2) ili veća amplituda (vidi `docs/ZA-ANDREJA.md`).

## 5. Javni paket (provjera, opciono)

`pse-riemann_0.3.0~rc1_amd64.deb` je za druge ljude: prazne misije, prazan vault, „Nova misija…“. Ne instaliraj ga preko svog (zamijenio bi tvoj); ako želiš da ga vidiš, probaj na drugom računaru ili u virtuelnoj mašini.

## 6. Rezultati

| # | prošlo? | napomena |
|---|---|---|
| 1–14 | | |
| kalibracija | | |

Kad završiš: reci mi rezultate i da li da pushujem lokalne commitove (spisak u `docs/ZA-ANDREJA.md`).
