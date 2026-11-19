# Geofisica

Le fette, le sezioni e i volumi di una prospezione geofisica — GPR, ERT,
magnetometria — portati nel grafo come **documenti**:

- una **pila** è un'acquisizione (`DTCAcquisitionNode`), ogni file sorgente
  la sua risorsa;
- ogni **fetta** (una banda di profondità) o **sezione** (un profilo
  verticale) è un documento: ruolo *analitico*, contenuto *oggetto 2D*,
  geometria da chi dice dove sta (*reality based* dallo strumento,
  *observable* da una pianta o da una figura, *asserted* a occhio);
- un'**anomalia** che leggi su una fetta diventa un'unità **USD** con il suo
  **estrattore** (una fetta) o **combinatore** (più fette). Il pacchetto porta
  dentro le misure e aiuta a tracciare; il giudizio archeologico resta tuo.

Ogni immagine che il pacchetto deriva (il PNG di una fetta, la cache, un
drappeggio) esce con il suo **timbro** accanto (`<file>.stamp.json`): da cosa
è fatta, come, con quale versione.
