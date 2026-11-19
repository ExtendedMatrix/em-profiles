# Contributing

Thank you for wanting to bring your community's way of recording to Extended
Matrix. This page says what a community package must carry and how it is
reviewed. When something is not covered, open an issue and ask.

## How a package arrives

1. **Open an issue.** Say who the community is, what it records, and why the
   EM core and the existing packages are not enough — checked, not assumed:
   a vocabulary that already lives in
   [ExtendedMatrix/vocabularies](https://github.com/ExtendedMatrix/vocabularies),
   the Getty AAT, PeriodO or a national thesaurus is cited, not restated.
2. **Send a pull request** that adds `profiles/<id>/`:
   - the folder named as the package's `id` (= the profile's `name`);
   - `em-extension.toml` and `profile.json` (SPEC.md §4, §6), with your
     prefix — two packages never share one;
   - your own vocabularies in `vocab/`, carried in `[[data.vocabularies]]`
     with licence, tier and digest (`python -m s3dgraphy.extensions build`
     writes them);
   - at least one example document in `examples/` that uses the package;
   - labels in every language you declare in `languages`;
   - a line in `.github/CODEOWNERS`: `/profiles/<id>/ @you @your-co-curator`.
3. **The CI validates it** (`tools/validate.py`, `pytest`): the one validator
   of the EM tools, plus the place of the package in this repository.
4. **The editor reviews the first version** of every package, to keep the
   language one: a type the core should have becomes a proposal for the core,
   not a type of a package. From then on the package's curators review it.

## Versions

Semantic versioning (SPEC.md §7): patch for labels and styles, minor for new
terms, major when a meaning changes. **A version is never reused**: a change
is a new version. A package stays at `0.x` while it is `proposed`.

## What does not belong here

- **Code without data** (a plugin alone) is listed in
  [ExtendedMatrix/em-extensions](https://github.com/ExtendedMatrix/em-extensions).
  Code that serves a package may travel in the same archive, as its `[code]`
  section (SPEC.md §6.4); it is reviewed with the package and installed with
  its own question of trust. **Good practice** (encouraged, not required): code that makes
  files from other files — a PNG from a slice, a cache, a baked drape, an
  export — writes the stamp of each beside it with `ctx.stamp` (SPEC.md §6.7);
  the validator only advises the code that writes files and stamps none.
- **Node and edge types of your own**: suspended in EM 1.6 (SPEC.md §5.11).
  A `stable` package that declares them is refused.
- **Vocabularies you may not redistribute** (tier C): the package carries a
  pointer, never the file (SPEC.md §6.3).
