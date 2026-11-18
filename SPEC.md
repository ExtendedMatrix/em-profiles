# EM Profiles — how a community extends Extended Matrix

**Version 0.2 · Editor's Draft · 18 November 2026**

| | |
|---|---|
| This version | `SPEC.md` in [ExtendedMatrix/em-profiles](https://github.com/ExtendedMatrix/em-profiles) |
| Previous version | 0.1 (25 October 2026), frozen in [ExtendedMatrix/vocabularies](https://github.com/ExtendedMatrix/vocabularies/blob/main/profiles/SPEC.md) |
| Schemas | [`schemas/profile.v0.2.schema.json`](schemas/profile.v0.2.schema.json), [`schemas/profile.v0.1.schema.json`](schemas/profile.v0.1.schema.json) (served at `https://w3id.org/extendedmatrix/schemas/<name>`) |
| Reference implementation | `s3dgraphy.profiles` and `s3dgraphy.extensions` ([s3Dgraphy](https://github.com/ExtendedMatrix/s3Dgraphy) 1.6) |
| Editor | Emanuel Demetrescu (CNR-ISPC), ORCID [0000-0002-5065-7970](https://orcid.org/0000-0002-5065-7970) |
| Licence | Text: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Schemas and examples: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), unless an example's own files say otherwise — see [LICENSING.md](LICENSING.md) |
| Status | **Editor's Draft.** Implemented by the EM tools of the 1.6 beta; it may still change before it becomes a Release. |
| Related | [em.json — the Extended Matrix document format](https://w3id.org/extendedmatrix/spec/em-json/), version 1.1 |

**Two names, one thing.** In the interface of the EM tools an EM Profile is a
**community package** («pacchetto di comunità»); this specification calls it
a *profile*, its technical name. The two words name the same object.

## 1. What it is for

Extended Matrix is one formal language. Scientific communities use it with
things of their own: the values they record, the ways they read their
sources and combine those readings, the documents and files only they
produce, the recording sheet they work on, the colours with which they look
at their data, the languages in which they name it. An **EM Profile** is the
package in which a community declares all of that, so that:

- the language stays **one**: a stratigraphic unit stays the unit of EM, with
  its relations and its propagation; a profile changes **what is recorded of
  the units and how it is read**, never the units;
- a file that uses a profile **says so**, and a tool that does not have the
  profile still opens the file, draws every node and loses nothing;
- the profile has an identity, a version and curators of its own, and can
  change without touching the version of the core or of the file format.

A profile is **data and declarations only**. Where a community needs a
behaviour the data cannot express (a reader for a new file format, a
computation outside the closed set of §5.4), the profile **declares a
dependency on a plugin**; a plugin is code, it is installed with its own
question of trust, and it may travel in the same archive as the profile
(§6.4) without ever being part of the profile.

**The boundary.** s3Dgraphy is the ontological authority of EM. A profile
never modifies the core's definitions: its types live under its prefix
(`<prefix>:<name>`) and the core reads them as an **overlay** that can be
taken away. When a community needs something that holds for everybody, it
becomes a proposal for the core, with its own version bump, and does not
enter through a profile.

## 2. What changed since 0.1

Every key of 0.1 keeps its meaning; the keys of 0.2 are additive, and a 0.1
reader ignores them (0.1 §3, «Readers ignore manifest keys they do not
know»). A 0.1 manifest is still read by every 0.2 tool.

| | 0.1 | 0.2 |
|---|---|---|
| qualia vocabularies | yes | unchanged; a profile's own qualia (`qualia`) with `data_type` and `units` |
| extractors | `input_formats`, `source_documents`, `produces` | + **`geometry`**, the 3D component (§5.2); `input_formats` optional |
| landmark sets | — | **`landmark_sets`** (§5.3) |
| combiners | — | **`combiner_types`**, a closed set of operations (§5.4) |
| documents | yes | unchanged |
| file types | inside extractors and documents | + **`file_types`** with their **reader** (§5.6) |
| recording sheets | — | **`forms`**: source and compiled definition with its digest (§5.7) |
| colour schemes | — | **`color_schemes`** (§5.8) |
| visual rules | yes | unchanged |
| labels, help, examples | texts in the manifest | `languages`, `i18n/`, `help/`, `examples/` (§5.10) |
| node and edge types | yes | **suspended in EM 1.6** (§5.11) |
| plugins | pointers | unchanged; a plugin a profile needs is in `requires.plugins` |
| dependencies | — | **`requires`** (§4.3) |
| licences | one `license` | `license` + **`parts`** (§4.4) |
| distribution | the folder | the folder **and** the archive with its envelope `em-extension.toml` (§6) |
| the core checked against | — | **`datamodel_checked`** (§4.2) |

## 3. A profile in PROF terms

The specification follows the W3C vocabulary
[*The Profiles Vocabulary*](https://www.w3.org/TR/dx-prof/) (PROF). An EM
Profile is a **`prof:Profile`** that is a profile of (`prof:isProfileOf`) the
em.json format and of the EM core; its parts are **resources** described by
`prof:ResourceDescriptor`, each with a **role**:

| Manifest | PROF |
|---|---|
| `iri` | the `prof:Profile` |
| `prefix` | `prof:hasToken` |
| `is_profile_of[]` | `prof:isProfileOf` |
| `qualia_vocabularies[]`, the vocabularies an archive carries (§6.3) | resource, role `role:vocabulary`, artifact = the SKOS scheme |
| `qualia[]`, `extractor_types[]`, `combiner_types[]`, `document_types[]`, `file_types[]`, `node_types[]`, `edge_types[]` | resource, role `role:vocabulary` (the profile's own terms); their `mapping` IRIs: role `role:mapping` |
| `landmark_sets[]` | resource, role `emrole:landmark-set` |
| `forms[]` | resource, role `role:specification` (the sheet's definition) |
| `visual_rules`, `color_schemes[]` | resource, role `emrole:visual-rules` |
| `plugins[]`, `requires.plugins[]` | resource, role `emrole:plugin` |
| `i18n`, `help` | resource, role `role:guidance` |
| `examples[]` | resource, role `role:example` |
| `profile.json` and the schema it validates against | resource, role `role:specification` and `role:validation` |

`role:` is `http://www.w3.org/ns/dx/prof/role/`; `emrole:` is
`https://w3id.org/extendedmatrix/profiles/role#` (PROF has no role for visual
rules, landmark sets or plugins).

## 4. The manifest

### 4.1 The folder

```
<name>/
  profile.json               the manifest
  vocab/*.ttl                the profile's own SKOS modules (when they do not live in ExtendedMatrix/vocabularies)
  landmarks/*.json           the landmark sets (§5.3)
  forms/<id>/template.yaml   the source of a recording sheet (stratigraph-templates)
  forms/<id>/<version>.json  its compiled definition, with its digest (§5.7)
  colors/*.emc               the colour schemes (§5.8)
  i18n/<lang>.json           the interface strings of the profile
  help/<lang>/*.md           its help
  examples/*.em.json         example documents (at least one)
  reference/*.glb            reference models (optional, §5.3)
  LICENSE, CHANGELOG.md
```

A 0.1 folder (`profile.json`, `vocab/`, `example.em.json`) is a valid 0.2
folder of format 0.1. A folder becomes an **archive** to distribute with its
envelope, `em-extension.toml` (§6).

### 4.2 The keys of the head

| key | what |
|---|---|
| `profile_format` | the version of this specification the manifest follows: `"0.2"` (or `"0.1"`) |
| `iri` | the identity of the profile; real profiles live under `https://w3id.org/extendedmatrix/profile/<name>` |
| `name` | equal to the folder name, and to the `id` of the envelope |
| `prefix` | a short token (2–16 lowercase letters or digits, starting with a letter): the profile's types are written `<prefix>:<name>` |
| `version` | semantic versioning (§7) |
| `lifecycle` | `proposed`, `stable` or `deprecated` |
| `title`, `description` | language-tagged texts (`{"en": "…", "it": "…"}`) |
| `curators` | who answers for the profile (GitHub handles, ORCIDs) |
| `license` | the default licence of the profile's content, an SPDX identifier; CC BY 4.0 unless there is a reason |
| `is_profile_of` | `[{iri, version}]`: the em.json format and the EM core it was written for |
| `example` | `true` for a profile that only illustrates this specification; never cited by real data |
| `languages` | **0.2** — the languages the profile speaks: a label is **required** in each of them, for every type |
| `unverified_languages` | **0.2** — the declared languages no person has reviewed yet (a subset of `languages`) |
| `datamodel_checked` | **0.2** — the core datamodel versions the profile was checked against (`{"nodes": "1.6.49", "connections": "1.6.55", "qualia": "1.6.13"}`, from `s3dgraphy.datamodel.datamodel_fingerprint`) |
| `requires` | **0.2** — dependencies (§4.3) |
| `parts` | **0.2** — licences per part (§4.4) |

**`datamodel_checked` is never a reason to refuse.** A tool whose core has
another version says «checked against 1.6.49, the core is now 1.6.52» and
reads the profile all the same.

**Types are prefixed.** Every type a profile introduces — quale, extractor,
combiner, document, file type, landmark set, colour scheme, node, edge — is
written `<prefix>:<name>` (`stat:larghezza_biorbitale`), so that it never
collides with a core type nor with another profile's. Core types are written
bare (`US`, `document`, `3d_model`, `is_after`), as the core writes them. **A
profile never redefines an id of the core**, and **two profiles never share a
prefix**: the second is not activated, and the tool says so.

Readers ignore manifest keys they do not know.

### 4.3 Dependencies (`requires`)

```json
"requires": {
  "core":     {"em": ">=1.6,<1.7"},
  "profiles": [{"iri": "https://w3id.org/extendedmatrix/profile/iccd-ra", "version": "^1.0"}],
  "plugins":  [{"id": "org.example.facemesh-fit", "version": "^0.3", "optional": true}]
}
```

Version ranges are those of npm and Blender: `^`, `~`, `>=`/`<`, `=`, `*`.
A profile whose **mandatory** dependency is missing **is installed all the
same** and shown as *incomplete, X is missing*: its data stay readable. An
`optional` dependency only unlocks functions (a command, a reader). In an
archive, `[requires]` of the envelope takes this place for the whole archive
(§6.5); `build` copies what concerns profiles back into `profile.json`, so
that a 0.2 reader without the envelope finds it.

### 4.4 Licences per part (`parts`)

`license` is the default; `parts` changes it for a file or a folder (a key
ending in `/`), because a profile holds things of different nature — a
vocabulary under CC BY, a reference model with a museum's rights, an example
dataset under CC0:

```json
"license": "CC-BY-4.0",
"parts": {
  "reference/volto-medio.glb": {"license": "CC-BY-NC-4.0", "attribution": "…", "redistributable": true},
  "examples/":                 {"license": "CC0-1.0"}
}
```

Identifiers are SPDX. `redistributable: false` means the part is never
republished by a node or a repository: it is installed only from a local
source (a zip, a folder). A part named in `parts` must exist (a warning
otherwise).

## 5. What a profile may contain

### 5.1 Qualia and their vocabularies

A **quale** is the value of an EM property. `qualia_vocabularies` says which
property type (`property_type`: a core one, or the profile's own
`<prefix>:<name>`) takes its values from which SKOS scheme (`scheme`, its IRI,
and `version`, its `owl:versionInfo`): such a quale is a **controlled field**,
and a value written as plain text in it is said *not controlled*. A core
quale bound by a profile to one of its schemes stays the core's, with the
binding beside it.

`qualia` declares the profile's **own** qualia, beside the core's: `id`,
`label`, `data_type` (`float`, `integer`, `string`, `boolean`, `date`,
`controlled_vocabulary`), `units`, `mapping`.

A vocabulary that serves **several** communities is born in
[ExtendedMatrix/vocabularies](https://github.com/ExtendedMatrix/vocabularies)
and the profile cites it by IRI; a vocabulary that serves **only** this
profile may live in its `vocab/` and follows the same rules (a version, a
source on every concept, definitions in our own words). How the Turtle files
travel is said by the envelope (§6.3); 0.1's `qualia_vocabularies[].path` is
still read, and `build` moves it there.

**The value of a controlled field is double, always**: the concept's IRI and
the label written when the value was entered (with its language), plus the
vocabulary and its version. A file stays readable — with the labels it saved
— on a machine where the vocabulary is not installed.

### 5.2 Extractors and their 3D component

`extractor_types` are the ways the community **reads** its sources: each
`specializes` the core `extractor`, may say which `input_formats` it reads
(media types and extensions), from which `source_documents` (a profile's own
document type or a core one, such as `3d_model`), and which qualia it
`produces`.

**0.2: the geometry says WHAT is produced, the vocabulary what it MEANS.** A
point placed on a model produces a position (hence an elevation); whether it
is «the glabella» or «a level point of the bedding plane» is said by a
concept, not by the primitive. So the same primitive serves different
communities:

```json
"extractor_types": [{
  "id": "stat:distanza_tra_punti",
  "specializes": "extractor",
  "label": {"it": "Distanza tra due punti", "en": "Distance between two points"},
  "geometry": {"primitive": "line", "produces": "length", "unit": "m",
               "vertices": {"min": 2, "max": 2}, "snap": "surface", "frame": "model"},
  "produces": ["stat:distanza"],
  "source_documents": ["3d_model"]
}]
```

| `primitive` | `produces` | unit |
|---|---|---|
| `point` | `position`, `elevation` | m |
| `line` | `length` | m |
| `polyline` | `length` | m |
| `surface` | `area` | m² |
| `volume` | `volume` | m³ |

- `primitive` and `produces` are **closed sets**, and `produces` must agree
  with the primitive (the table): a primitive no tool draws would be a dead
  button.
- `unit` — the unit of the measure shown; the graph stays in metres.
- `vertices` — `min` ≤ `max` clicks; the placing tool knows when it is done.
- `snap` — `surface`, `vertex` or `free`: where a click lands.
- `frame` — `model` (the coordinates of the model, as `data.coords` of the
  annotation) or `graph` (the graph's georeference applied before the
  elevation is read).
- **The elevation** of a point is orthometric/absolute when the graph is
  georeferenced (its `GeoPositionNode`), otherwise the z of the model's
  frame; the value says which of the two it is. `surface` and the measures
  of elevation, area and volume belong to the **core** (decision D-3), not to
  a profile.

In the graph, an extractor of a profile kind is a **core `extractor` node**
naming its kind in `data.em_kind` (`"stat:punto_canonico"`), with the chain
the core already uses for every reading: extractor —`extracted_from`→
annotation region (`data.geometry_kind`, `data.coords` in metres) —
`is_on_resource`→ the model. **One extractor reads one place**: a set of
points is one extractor per point.

### 5.3 Landmark sets

A **landmark set** is an ordered list of named points, each with its
concept, that a tool lets a person place **in a guided sequence**. It lives
in `landmarks/<id>.json` and the manifest names it:

```json
"landmark_sets": [{"id": "stat:volto", "path": "landmarks/volto.json", "extractor_type": "stat:punto_canonico"}]
```

The `extractor_type` is one of the profile's own, with primitive `point`. The
file:

```json
{
  "id": "stat:volto",
  "label": {"it": "Punti canonici del volto", "en": "Canonical points of the face"},
  "scheme": "https://w3id.org/extendedmatrix/profile/esempio-statuaria/vocab/punti-volto/",
  "order": "listed",
  "reference": {"frame": "normalized", "description": {"en": "…"}, "model": "reference/volto-medio.glb"},
  "points": [
    {"id": "nasion",        "concept": "…/punti-volto/nasion",       "required": true, "ref": [0.0, 0.0, 0.0]},
    {"id": "exocanthion_r", "concept": "…/punti-volto/exocanthion", "side": "right", "mirror": "exocanthion_l", "ref": [-0.42, -0.08, -0.12]},
    {"id": "exocanthion_l", "concept": "…/punti-volto/exocanthion", "side": "left",  "mirror": "exocanthion_r", "ref": [0.42, -0.08, -0.12]}
  ]
}
```

- `concept` gives the meaning; the **side** is on the point, not in the
  concept (exocanthion is one concept, right and left are two positions).
- `ref` — an optional reference position (three numbers) in the normalised
  frame `reference.description` describes: a tool may show where a point is
  *expected*. A reference is an aid, **never a value**: a point no person
  placed never enters the graph.
- `mirror` — the symmetric point, which must exist in the set.
- `required` — an incomplete set is saved; the tool says which points are
  missing.
- Point ids are unique in the set.

A placed point writes an extractor (`data.em_kind` = the set's extractor
type) with `data.landmark = {"set": "stat:volto", "point": "exocanthion_r",
"concept": "<IRI>", "label": "esocantion destro", "lang": "it"}` and its
`point` annotation region on the model. The points of one act of placing may
stand under one core `combiner` node that gathers them.

### 5.4 Combiners

The core says *that* sources were combined, not *how*. A profile declares
`combiner_types`, each with an **operation taken from a closed set** the core
knows how to compute — no free formulas, no code in the data:

```json
"combiner_types": [{
  "id": "stat:larghezza_biorbitale",
  "label": {"it": "Larghezza biorbitale", "en": "Biorbital width"},
  "operation": "distance",
  "inputs": [{"landmark": "stat:volto/exocanthion_r"}, {"landmark": "stat:volto/exocanthion_l"}],
  "produces": "stat:larghezza_biorbitale",
  "unit": "m"
}]
```

| operation | inputs |
|---|---|
| `distance` | 2 landmarks |
| `angle` | 3 landmarks (the vertex in the middle) |
| `ratio` | 2 qualia |
| `mean` | 1 or more inputs, landmarks or qualia |
| `area_of_polygon` | 3 or more landmarks, in order |
| `elevation_difference` | 2 landmarks |
| `angle_between_planes` | 6 landmarks (two planes of three) |
| `symmetry_index` | 2 or more landmarks |

An input names a landmark (`<set>/<point>`, which must exist) or a quale
(core or the profile's own). The result is a property whose provenance
chain is complete (property → combiner → extractors → document), so a
computed value is defended as a measured one. In the graph a combiner of a
profile kind is a **core `combiner` node** with `data.em_kind`. An operation
outside the set comes from a **plugin**, or becomes a proposal for the core.

### 5.5 Documents

`document_types` are the documents **peculiar** to the community: each
`specializes` the core `document`, says its `content_nature` (`2d_object` or
`3d_object`) and its `formats`. In the graph a document of a profile kind is a
core `document` node with `data.em_kind`.

### 5.6 File types and readers

```json
"file_types": [{
  "id": "stat:rti", "label": {"en": "RTI image", "it": "Immagine RTI"},
  "media_type": "application/x-rti", "extensions": [".rti", ".ptm"],
  "document_type": "stat:rilievo_rti", "content_nature": "2d_object",
  "reader": "plugin:org.example.rti-viewer"
}]
```

`reader` is **`builtin:<id>`** — a reader the tools have: `gltf`, `glb`,
`mesh`, `pointcloud`, `image`, `pdf`, `3tz`, `iiif`, `text`, `svg`, `video`,
`audio` (another id is a warning: one tool may have it, another not) — or
**`plugin:<id>`**, a plugin the profile names in `requires.plugins` (an
error otherwise: nobody would know to offer it). Without its reader a file
still enters as a resource, with its hash: it is seen, not opened.

### 5.7 Recording sheets (`forms`)

A profile does not invent a sheet format: it carries a definition of
**stratigraph-templates** (`template.yaml`), which binds each field to a quale
or to a vocabulary scheme, **and** its compiled form with its digest:

```json
"forms": [{"id": "stat-scheda-superficie", "source": "forms/stat-scheda-superficie/template.yaml",
           "compiled": "forms/stat-scheda-superficie/0.1.0.json", "digest": "sha256:…"}]
```

The compiled form travels because the web tools and the field tools have no
compiler at hand; a tool recomputes the digest and refuses a compiled form
that does not match it. (The rule «ship the sources, never the index»
concerns the index of the vocabularies, which depends on what is installed
on a machine; a compiled sheet is a versioned artefact.)

### 5.8 Colour schemes

`color_schemes` points at `.emc` files, the format `s3dgraphy.color_schemes`
writes and reads and that EM Tools and EMStudio share, bound to a `property`.
In a profile's scheme the keys of `color_mapping` are the **concept IRIs**,
not the labels, so a scheme holds in every language. The two special keys of
EM Tools (empty value, without the property) remain.

### 5.9 Visual rules

`visual_rules` says how the profile's types are drawn, in the format of the
core's `em_visual_rules.json` (`node_styles`, `2d_glyphs`, `edge_style`,
`matrix`), keyed by the profile type — unchanged from 0.1 §4.4.

### 5.10 Labels, interface strings, help, examples

- **Labels of types**: in the manifest, as a language map, **required in
  every language of `languages`**.
- **Labels of concepts**: in the SKOS modules (`skos:prefLabel@it` …), never
  copied into the manifest.
- **Interface strings** of the profile (the steps of a guided placing, its
  messages): `i18n/<lang>.json`, keys under the prefix (`stat.posa.prossimo`).
- **Help**: `help/<lang>/*.md`.
- **Examples**: at least one `examples/*.em.json` (0.1: `example.em.json`)
  that uses the profile, declares it in `header.profiles` and carries the
  keys of §8. Required in 0.2; a warning in 0.1.

### 5.11 Node and edge types — suspended in EM 1.6

0.1 lets a profile bring node and edge types of its own, each a species of a
core type (0.1 §4.3). **In EM 1.6 they are suspended** (decision D-1: the
unit node is the same for everybody):

- the schema still accepts them, so that a file written with a 0.1 profile
  stays valid;
- the validator **warns** for a `proposed` or `deprecated` profile that
  declares them and **refuses** a `stable` one;
- the tools of 1.6 do not draw them as types of their own: they apply the
  fallback of 0.1 §4.4 (the rules of the core type they specialise) and keep
  them, with their data, when they write the file back.

A profile type that changes what the core derives (the Matrix, the
propagation, the RDF) is where «the language stays one» breaks; a community
that needs one opens an issue for the core. `core-types.json` (generated,
§11) lists the core types a species would specialise.

### 5.12 Plugins

`plugins` (0.1 §4.5) points at tools that view or interpret the profile's
media — a **pointer, never code**: `id`, `kind` (`viewer`, `interpreter`,
`connector`), `href`, the types it `handles`, its `descriptor` (where it runs,
how it is reached, its capabilities from the closed set of the EM plugin
architecture, the versions it speaks, whether it `writes`). A plugin that
declares `writes: false` declares no writing capability. A plugin the
profile **needs** is named in `requires.plugins`; one that travels with it is
the `[code]` section of the same archive (§6.4).

## 6. The archive and its envelope (`em-extension.toml`)

A profile travels as an **archive** — a folder or a zip — with an envelope at
its root, `em-extension.toml`, modelled on Blender's extension manifest. The
envelope says *who it is*, *which EM it goes with*, *what it carries* and
*what it asks*. Its form is **1.0.0**.

### 6.1 The head and the two sections

```toml
schema_version = "1.0.0"
id          = "esempio-statuaria"            # unique in a repository; = `name` of the profile
version     = "0.1.0"                        # the version of the ARCHIVE (semver)
name        = "Statuaria antica (ESEMPIO)"
tagline     = "Vocabolari e punti del volto per la statuaria"   # ≤ 64 characters, no final period
maintainer  = "Curatori di esempio (ESEMPIO)"
license     = ["SPDX:CC-BY-4.0"]             # one per section when they differ
em_api_min  = "1.0"                          # the version of the EM extensions API
type        = "community-package"            # optional and redundant: community-package | plugin | mixed

[data]
version  = "0.1.0"                           # optional, default = version
root     = "."                               # "data/" when [code] is there too
profile  = "profile.json"
```

An archive has **at least one** of two sections:

| sections | what it is | question of trust |
|---|---|---|
| `[data]` only | a community package — a profile | none |
| `[code]` only | a plugin | yes |
| `[data]` and `[code]` | a **mixed package** | yes, **for the code only** |

`type`, when present, must agree with the sections; when absent, `build`
writes it. With one section its `root` is `.`; with two, each has its own
root (`data/`, `code/`) and the roots do not overlap.

### 6.2 The partition: data never carry code

**No executable file lives under the data root**: `.py`, `.pyc`, `.pyo`,
`.so`, `.dylib`, `.dll`, `.js`, `.mjs`, `.wasm`, `.whl`, `.exe`. Outside the
roots only the envelope, `LICENSE*`, `README*` and `CHANGELOG.md` may stand.
This is what gives the word «data» its sense: a community package — and the
data of a mixed package installed alone (§9) — is installed **without the
question of trust**, because it is verified to contain nothing that runs.

`[data]`: `id` equals the profile's `name`; `[data].version` equals the
profile's `version`.

### 6.3 The vocabularies an archive carries, and their tiers

The profile says *which* vocabulary a quale uses (`qualia_vocabularies`:
scheme IRI and version); the envelope says *which files* the archive carries
for the machine's vocabulary manager:

```toml
  [[data.vocabularies]]
  path    = "vocab/punti-volto.ttl"
  scheme  = "https://w3id.org/extendedmatrix/profile/esempio-statuaria/vocab/punti-volto/"
  version = "0.1.0"
  license = "SPDX:CC-BY-4.0"
  tier    = "A"                              # `fascia` is read as the same key
  digest  = "sha256:…"
```

The validator checks the three things together: every scheme the profile
cites is **carried** (same version, an error otherwise) or **required** in
`[requires].vocabularies` (a version outside the range is a warning) or,
in 0.1, still named by `path`; every carried file declares a
`skos:ConceptScheme` with that IRI and that `owl:versionInfo`; the digest
matches.

**Tiers** (decision D-16 of 20 September 2026: what may travel):

| tier | licences | how it travels |
|---|---|---|
| **A** | CC0, CC BY, ODC-By, PDDL — PeriodO, Getty, ChronOntology, the EM modules | distributed with the attribution; the terms a file uses may be copied into it |
| **B** | share-alike and other conditional licences — CC BY-SA (ICCD, the EM datamodel), BY-NC, BY-ND, ODbL | distributed **only as a separate, unmodified file**, its licence beside it |
| **C** | not redistributable, or terms unknown — `LicenseRef-*`, proprietary | **never distributed**: the archive carries a pointer, the person fetches a local copy |

The curator **declares** the tier and the validator **checks** it against the
SPDX licence: a tier **more prudent** than the licence allows is accepted (a
CC BY put in B by choice), a **less prudent** one is refused — the omission
must make noise. A tier-C entry has no file, only a pointer:

```toml
  [[data.vocabularies]]
  scheme  = "http://vocab.getty.edu/aat/"
  version = "2026-10"
  tier    = "C"
  fetch   = { url = "https://…/aat-2026-10.ttl", digest = "sha256:…", terms = "https://…" }
```

and a `.ttl` of tier C inside an archive is refused. **The sources travel,
the index is compiled locally**: no archive ships the index of a vocabulary.
Licences are read **per record** where a source says so (`effective_terms`,
`aggregates`), not only per authority.

### 6.4 The code section (informative)

`[code]` is the plugin a mixed package carries: `version` (default: the
archive's), `root`, `license`, `entry` (`module:object`), `hosts`
(`emstudio`, `blender`, `server`), `platforms` and the **wheels** of its
dependencies inside the archive (never `pip` at install time),
`[code.permissions]` — `files`, `network`, `clipboard`, `processes` — **each
with its short reason** (≤ 64 characters, no final period, shown when
installing: decision D-14), `[code.descriptor]` and `[[code.commands]]`. Its
full form belongs to the specification of EM plugins; this specification
only fixes how it sits beside the data: its own root, its own version, its
own question of trust.

### 6.5 Dependencies of the archive (`[requires]`)

```toml
[requires]
core         = { em = ">=1.6,<1.7" }
extensions   = [{ id = "iccd-ra", version = "^1.0", part = "data" },
                { id = "rti-viewer", version = "^0.3", part = "code", optional = true }]
vocabularies = [{ scheme = "https://w3id.org/extendedmatrix/vocab/em-us-definizione/", version = "^1.0" }]
```

- `part` says **which section** of the other archive is needed: `data`,
  `code`, `any` (default). A package that needs the data of `iccd-ra` is
  satisfied when the code of `iccd-ra` has been removed.
- **Data never depend on code as a must**: a dependency with `part = "code"`
  is always `optional = true` (the validator imposes it). A missing function
  is said («the RTI reader is missing»), it never blocks.
- The code section depends implicitly on the data of its own archive.
- A package does not require itself; a cycle of mandatory dependencies is
  refused at installation, written out in full.

### 6.6 Building an archive

`python -m s3dgraphy.extensions build <folder>` writes
`<id>-<version>.zip`, deterministically (same folder, same bytes): it writes
`type`, moves `qualia_vocabularies[].path` into `[[data.vocabularies]]` with
licence, tier and digest, computes the digests of compiled forms, gives a
bare 0.1 profile its envelope, and validates the result in memory before
writing. `[build]` (`paths`, `paths_exclude_pattern`) chooses the files, as
in Blender. The folder is never written.

## 7. Versions

Three axes, independent, never mixed:

- **the format** — em.json `header.version` (1.1): changes only with the
  form of the document;
- **the core** — the EM language: its datamodels (`header.datamodel_versions`)
  and the ontologies they map to; a profile names in `is_profile_of` the
  core version it was written for (`"1.6"`) and in `datamodel_checked` the
  versions it was checked against;
- **each profile** — its own `version`, in semantic versioning: **patch** for
  labels, descriptions, styles; **minor** for new types, new concepts, new
  landmarks, new combiners; **major** when a type is removed or changes its
  meaning, its primitive or its operation. A profile stays at `0.x` while it
  is `proposed`.

**A version is never reused**: the same id and version with another content
is refused. In an archive each section has its own version (`[data].version`,
`[code].version`): the curator raises only the one of the part that changed.

Updating a profile changes neither the number of the core nor that of the
format. A file stays bound to the version it declares; a file written with
1.2 of a profile is read by a tool that has 1.0 of it, with the fallback for
what it does not know (the newest compatible version is used, and the tool
says so).

## 8. Using a profile in an em.json file

A file that uses a profile **declares it in its header**, with the version
it was written with (em.json 1.1, §2.7):

```json
"header": {
  "format": "em.json",
  "version": "1.1",
  "profiles": [
    {"iri": "https://w3id.org/extendedmatrix/profile/esempio-statuaria", "version": "0.1.0"}
  ]
}
```

- an **extractor, combiner or document of a profile kind** is a core node
  naming its kind in `data.em_kind`; a placed landmark adds `data.landmark`
  (§5.3);
- a **property of a profile quale** is a core property node whose name is
  `<prefix>:<quale>`;
- (suspended in 1.6, §5.11) a **node of a profile type** keeps its type in
  `node_type` and names the core type it specialises in
  `data.em_specializes`; an **edge of a profile type** carries
  `attributes.em_family` and `attributes.em_propagates`.

**A writer** declares in `header.profiles` every profile whose prefix the
content uses, and **keeps** every declaration the file already had, even for
a profile it does not have: removing one is the person's choice. **A reader**
that does not have a declared profile opens the file all the same: it says
which profiles are missing, reads what it can, and writes back what it read.
**A missing profile is never a reason to refuse a file.**

## 9. Installing (informative)

How the EM tools install an archive; the reference is
`s3dgraphy.extensions.install`. The EM tools on one machine — EMStudio, EM
Tools in Blender, a node — share **one folder per machine**, as fonts are
shared:

```
esempio-statuaria-0.1.0.zip
 ├─ data/vocab/*.ttl  → the vocabulary manager → its folder, <scheme>/<version>/
 ├─ data/ (the rest)  → ~/.s3dgraphy/profiles/<id>/<data version>/        (S3DGRAPHY_PROFILES_DIR)
 └─ code/             → ~/.s3dgraphy/plugins/<source>/<id>/<code version>/
                       + the register ~/.s3dgraphy/extensions/installed.json
```

1. **Everything is validated before anything is written.** An error of the
   data installs nothing; an error of the code alone lets the data in and
   records *code not installed: <reason>*.
2. **Vocabularies first, then data, then code.** The vocabulary manager
   keeps versions side by side and records who carried each.
3. **Data only.** For a mixed package the confirmation shows the data and
   the code in two panels; *Data only* installs the data with the guarantee
   of the partition (§6.2) and leaves no code file on the machine (decision
   D-18).
4. **The question of trust** is asked for code only, and asked again only
   when its permissions, capabilities or source change. In the 1.6 beta,
   trust is a list of plugins reviewed by the editor and by the curators of
   the package that requires them; signatures come later (decision D-6).
5. **The same vocabulary from two packages**: same digest — one copy, one
   more carrier; another version — side by side; same version, another
   digest — **the owner of the IRI's namespace wins** (a `…/profile/<name>/vocab/`
   IRI belongs to `<name>`), otherwise the first installed, **always with a
   warning** (decision D-17).
6. **Removing**: the code alone, the data (with their code), or the whole
   package. **Vocabularies stay** on the machine, like fonts; a box, off by
   default, removes those nobody else carries (decision D-19).

## 10. Conformance

- A **manifest** conforms when it validates against the schema of its
  `profile_format` and holds together: its types carry its prefix and are
  declared once; it redefines no core id; each `specializes` names a core
  type; every type a rule, a connection, a landmark set, a combiner, a file
  type or a plugin names is declared; every label exists in every declared
  language; every file it names is there; compiled forms match their digest;
  the example declares the profile.
- An **archive** conforms when its envelope is well formed, its partition
  holds, its carried vocabularies match their files, digests and tiers, its
  `[requires]` is sound, and its profile conforms.
- A **document** that uses profiles conforms when it conforms to em.json, its
  header declares every profile whose types it uses, and every node of a
  profile kind carries the keys of §8.
- A **reader** conforms when it reads such a document without the profile,
  draws every node, and writes back what it read.

**One validator.** The EM tools validate with one implementation,
`s3dgraphy.extensions.validate_archive`: the Extensions window shows its
words before installing, `python -m s3dgraphy.extensions validate <path>`
prints them (exit 1 on an error, `--json`, `--lang en|it`), and the CI of this
repository runs it on every pull request (`tools/validate.py`). Every problem
has a code and a sentence in English and Italian. Errors refuse; warnings
never do.

## 11. This repository

| here | elsewhere |
|---|---|
| `SPEC.md` (this document, from 0.2 on), `schemas/`, `core-types.json` (generated by `tools/core_types.py`) | 0.1, frozen, in `vocabularies/profiles/` for whoever cites it |
| `examples/` — archives written to illustrate this specification, not to be cited | the SKOS modules shared by several communities: [ExtendedMatrix/vocabularies](https://github.com/ExtendedMatrix/vocabularies) |
| `profiles/<id>/` — the community packages, each with its curators in `.github/CODEOWNERS` | the **index** of packages and plugins to download (phase 2): [ExtendedMatrix/em-extensions](https://github.com/ExtendedMatrix/em-extensions) (decision D-12) |
| `tools/validate.py`, `tests/` — what the CI runs | the validator itself: `s3dgraphy.extensions` |

The schemas here are byte for byte those the library ships (the CI checks
it): the validator must work inside Blender and offline, so the library
carries them, and this repository publishes them.

## 12. Contributing a profile

Open an issue that says who the community is, what it records and why the
core and the existing profiles are not enough. Then a pull request that adds
`profiles/<id>/` — the folder named as the package id, with its envelope, its
manifest, its vocabularies, at least one example document — and a line in
`.github/CODEOWNERS` that makes its curators the reviewers of its folder. The
CI validates it (§10) and checks its place in the repository: folder = id,
one prefix per package, a curators' line, data (a pure plugin is listed in
em-extensions, not here). The editor of this specification reviews the
first version of every profile, to keep the language one: a type the core
should have becomes a proposal for the core. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## 13. Examples

All invented, marked as such in their texts, not to be cited:

- [`examples/example-toolmarks/`](examples/example-toolmarks/) — the 0.1
  example, unchanged: tool marks on dressed stone. A bare profile (no
  envelope), read by every 0.2 tool; its node and edge types show the
  suspension of §5.11 (two warnings).
- [`examples/esempio-statuaria/`](examples/esempio-statuaria/) — a 0.2
  community package (D-5, synthetic): three vocabularies carried (tier A),
  four qualia, three extractors (point, polyline, surface), the landmark set
  `stat:volto`, three combiners, a document type, a file type, a recording
  sheet with its compiled form, a colour scheme, strings and help in two
  languages, an example document.
- [`examples/facemesh_fit/`](examples/facemesh_fit/) — a plugin alone that
  requires the data of `esempio-statuaria` (`part = "data"`); its module does
  nothing.
- [`examples/esempio-statuaria-misto/`](examples/esempio-statuaria-misto/) —
  the two in **one** archive, `data/` and `code/` (a mixed package).

The real pilot (statuary, with its curators and data) will be a community
package in `profiles/`.

## 14. Open points

- The **name** «EM Profiles» is provisional.
- The **IRI of the EM core** (`https://w3id.org/extendedmatrix/core/`), the
  namespace of real profiles (`https://w3id.org/extendedmatrix/profile/<name>`)
  and of the schemas are proposed and not yet registered at w3id.org.
- The **arithmetic** of `angle_between_planes` and `symmetry_index`, and the
  measures of elevation, area and volume in the core, are being written; the
  validator already accepts them.
- **Repositories, the index and updates** (phase 2): an index in the form of
  Blender's Extension Listing API, generated by the CI of em-extensions;
  until then archives are installed from disk.

## 15. Changes

- **0.2 — 18 November 2026 (Editor's Draft).** The specification moves from
  ExtendedMatrix/vocabularies to its own repository (decision D-2). New:
  `languages`, `datamodel_checked`, `requires`, `parts`; a profile's own
  `qualia`; the 3D component of extractors; landmark sets; combiners over a
  closed set of operations; file types and readers; recording sheets;
  colour schemes; interface strings and help; the archive and its envelope
  `em-extension.toml` with data and code sections, the partition, the
  vocabularies carried and their tiers; the installation by parts. Node and
  edge types suspended in EM 1.6. The validator moves from this repository's
  tests into the library, s3Dgraphy.
- **0.1 — 25 October 2026 (Editor's Draft).** First draft: the manifest, the
  PROF correspondence, the five kinds of content, the fallback, the three axes
  of version, the declaration in the em.json header.

## 16. How to cite

Demetrescu, E. (ed.) (2026). *EM Profiles — how a community extends Extended
Matrix*, version 0.2 (Editor's Draft). CNR-ISPC.
https://github.com/ExtendedMatrix/em-profiles/blob/main/SPEC.md
