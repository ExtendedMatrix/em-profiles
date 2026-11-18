# Licences

| What | Where | Licence |
|---|---|---|
| The text of the specification and of the documents | `*.md` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| JSON schemas, `core-types.json` | `schemas/`, `core-types.json` | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Examples | `examples/` | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), unless an example's own `LICENSE`, envelope or `parts` say otherwise (the synthetic statuary examples: CC BY 4.0 for the data, EUPL-1.2 for the example plugin) |
| Tools and tests | `tools/`, `tests/`, `.github/` | [EUPL-1.2](https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12) |
| Community packages | `profiles/<id>/` | what each package declares: its `license`, its `parts`, the licence and tier of every vocabulary it carries |

**Why CC BY 4.0 for the text.** A specification is cited: the attribution
keeps the name of whoever wrote it attached to it. It is the licence of the
0.1 text in ExtendedMatrix/vocabularies.

**Why CC0 for the schemas and examples.** They are there to be implemented
and copied into anybody's code and tests without a notice.

**Why EUPL-1.2 for the tools.** They come from the same family as the tools
of ExtendedMatrix/vocabularies and stratigraph-templates, under the EUPL-1.2.

**A package's own licence is its own.** The validator checks that what a
package says of its licences holds together — every part it names exists,
every vocabulary it carries has a licence and a tier that licence allows —
and never relicenses anything.

Copyright 2026 Consiglio Nazionale delle Ricerche — Istituto di Scienze del
Patrimonio Culturale (CNR-ISPC), and the contributors named in each package
and in the history of this repository.
