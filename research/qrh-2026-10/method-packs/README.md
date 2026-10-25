# Paketi metoda (extraction za PSE Riemann)

Izvučeni recepti četiri QRH metode kao paketi metode (plan F8/F10). Svaki paket
je recept iz kog aplikacija sama ponovo izvodi broj iz rada (test reprodukcije,
`pse_r.methods.pack.reproduce`). Paket ulazi u aplikaciju **samo kroz vrata**
(`pse_r.methods.door.import_pack`): prvo test reprodukcije, pa ljudski red.

| paket | familija | tvrđeno B | kako se provjerava |
|---|---|---|---|
| `liu.json` | liu | 0.874957019420 | optimum E_liu (kubna) |
| `xu-sang.json` | xs | 0.874886647040 | optimum E_xs, w=1/4 (kvartna) |
| `openai-11-12.json` | line | 0.9166666666666666 (11/12) | tačka ℓ=0 prave B=11/12−ℓ/4 |
| `openai-7-8.json` | line | 0.875 (7/8) | tačka ℓ=1/6 prave B=11/12−ℓ/4 |

Liu i Xu–Sang imaju razrješiv arXiv id → ulaze kroz vrata kao CITED kartice
(nivo PREPRINT). OpenAI 11/12 i 7/8 nemaju razrješiv id u našem materijalu, pa
se provjeravaju kao tačke prave (reprodukcija), a u biblioteci stoje kao
orijentacioni FOLKLORE izvori (vidi `vault/qrh_seed.py`).

Provjera svih paketa (iz `app/`):

```bash
.venv/bin/python -c "
from pathlib import Path
from pse_r.methods.pack import MethodPack, reproduce
for p in sorted(Path('../research/qrh-2026-10/method-packs').glob('*.json')):
    r = reproduce(MethodPack.from_file(p))
    print(p.name, 'OK' if r['ok'] else 'NE', f\"B*={r['computed_B']:.12f}\")
"
```
