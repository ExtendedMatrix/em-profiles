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

**Tracciare.** Nello Spazio i tre strumenti *anomalia puntuale*, *lineare* e
*areale su fetta* disegnano sui piani di una pila: un clic su una fetta è un
punto dell'anomalia. Clic su due fette, o le fette mostrate «fino a» il
cursore, fanno un estrattore per fetta e un combinatore che li unisce. Il
tipo (puntuale, lineare, areale, iperbole di diffrazione, alta o bassa
resistività) dice la forma letta, non che cosa è. Un solo passo di
annullamento toglie tutto.

Ogni immagine che il pacchetto deriva (il PNG di una fetta, la cache, un
drappeggio) esce con il suo **timbro** accanto (`<file>.stamp.json`): da cosa
è fatta, come, con quale versione.
