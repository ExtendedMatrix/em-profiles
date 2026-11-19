# Pilota della statuaria — sintetico (D-5) · Statuary pilot — synthetic (D-5)

**ESEMPIO SINTETICO — non citare. · SYNTHETIC EXAMPLE — not to be cited.**

Le teste qui non sono statue: le genera `make_head.py`, e per questo sappiamo
dove stanno i loro punti canonici (la **verità per costruzione**). Il pilota
vero, con i dati e i curatori della statuaria, resta una riga aperta (D-5).

*These heads are not statues: `make_head.py` generates them, which is why we
know where their canonical points are (the **truth by construction**). The real
pilot, with the data and curators of statuary, remains open (D-5).*

## Che cosa prova · What it tries

La strada intera di un pacchetto di comunità con il suo plugin, **nelle due
forme** (D-20), con le sole librerie che ogni strumento usa:

| forma | archivi | che cosa si misura in più |
|---|---|---|
| **separata** | `esempio-statuaria` 0.1.0 (dati) + `facemesh_fit` 0.3.0 (codice) | il plugin installato **prima** dei dati: «incompleto», e il suo comando dice che cosa manca |
| **mista** | `esempio-statuaria` 0.1.0 (lo stub di prima, da `HEAD`) → 0.1.1 | l'aggiornamento cambia **solo il codice** (0.1.0 → 0.2.0), i dati restano 0.1.0; nello stesso processo: «riavvia» |

Su tre teste — **canonica** (proporzioni vicine al riferimento dell'insieme),
**girata** (35° attorno a y, spostata), **fuori-misura** (occhi più larghi e
bassi, naso e mento più lunghi, −20°) — in ciascuna forma:

1. il plugin **propone** i sei punti di `stat:volto` (volatili: `ingest-batch`);
2. la persona li **conferma** (la strada dello strumento di posa: `place_landmark`
   con il suo ORCID, `proposed_by` che nomina il plugin) — le proposte tolte
   prima, in un atto loro;
3. i **combinatori** calcolano (larghezza biorbitale, altezza del volto, indice);
4. i punti a più di **0,5 mm** dalla verità sono **riposati**: i combinatori
   ricalcolano;
5. la **superficie d'integrazione** (un tipo del pacchetto) sul naso, la sua area
   come valore con la sua catena, fase e lavorazione dai vocabolari del pacchetto;
6. il documento è **salvato e riletto**; la **scheda** del pacchetto riempita
   dal grafo e disegnata (IT, EN).

`bridge_pilot.py` rifà i passi 1–3 nell'**ospite vero di EMStudio** (un suo
bridge su una porta libera, mai la pila di sviluppo).

## Come si lancia · How to run

```
export PYTHONPATH=../s3Dgraphy/src          # s3Dgraphy accanto a questo repository
python pilots/statuaria-sintetica/run_pilot.py /tmp/pilota            # cartella NUOVA
python pilots/statuaria-sintetica/bridge_pilot.py /tmp/pilota/bridge /tmp/pilota/heads
```

La scheda usa `stratigraph-templates` accanto a questo repository
(`STRATIGRAPH_TEMPLATES_SRC` per un'altra posizione). Ogni forma gira in un
suo processo con le sue cartelle-macchina (`S3DGRAPHY_*`, `EM_VOCABULARIES_DIR`
sotto la cartella d'uscita): `~/.s3dgraphy` non viene mai scritto.

## Che cosa c'è · What is here

| file | |
|---|---|
| `make_head.py` | la testa sintetica (puro Python, deterministica): `.glb`, `.truth.json`, `.em.json` |
| `run_pilot.py` | il collaudo nelle due forme; scrive `summary.json` |
| `bridge_pilot.py` | il plugin e la posa nel bridge di EMStudio |
| `risultati/` | l'ultimo giro: `summary.json`, `bridge-*.json`, le verità, due documenti posati, le schede IT/EN |

Nessun binario: le teste si rigenerano byte per byte (il digest è in
`risultati/summary.json`, e un test lo controlla). Licenze: le teste, le
verità e i risultati CC0 1.0; gli script EUPL-1.2 (LICENSING.md).
