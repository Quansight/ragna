# Release notes

## Version 0.1.3

### What's Changed

- fix large upload by [@peachkeel](https://github.com/peachkeel) in
  [#244](https://github.com/Quansight/ragna/pull/244)
- Fix rendering of chat info button [@nenb](https://github.com/nenb) in
  [#252](https://github.com/Quansight/ragna/pull/252)
- Bump panel minimum version by [@nenb](https://github.com/nenb) in
  [#259](https://github.com/Quansight/ragna/pull/259)

### New Contributors

- [@peachkeel](https://github.com/peachkeel) made their first contribution in
  [#184](https://github.com/Quansight/ragna/pull/244)
- [@nenb](https://github.com/nenb) made their first contribution in
  [#252](https://github.com/Quansight/ragna/pull/252)

## Version 0.1.2

### What's Changed

- pin pymupdf to latest release by [@pmeier](https://github.com/pmeier) in
  [#169](https://github.com/Quansight/ragna/pull/169)
- Update assistant timeout to accomodate longer response time. by
  [@petrpan26](https://github.com/petrpan26) in
  [#184](https://github.com/Quansight/ragna/pull/184)
- cache importlib_metadata_package_distributions by [@pmeier](https://github.com/pmeier)
  in [#188](https://github.com/Quansight/ragna/pull/188)
- fix LanceDB retrieval by [@pmeier](https://github.com/pmeier) in
  [#195](https://github.com/Quansight/ragna/pull/195)
- use model_config over Config class by [@pmeier](https://github.com/pmeier) in
  [#199](https://github.com/Quansight/ragna/pull/199)
- special case LocalDocument more by [@pmeier](https://github.com/pmeier) in
  [#170](https://github.com/Quansight/ragna/pull/170)
- docs: small improvements to "Set Configuration" how-to by
  [@agilgur5](https://github.com/agilgur5) in
  [#197](https://github.com/Quansight/ragna/pull/197)
- docs: various improvements to Python API tutorial by
  [@agilgur5](https://github.com/agilgur5) in
  [#196](https://github.com/Quansight/ragna/pull/196)
- fix chat info by [@pmeier](https://github.com/pmeier) in
  [#220](https://github.com/Quansight/ragna/pull/220)
- change version scheme to increase the minor instead of patch version by
  [@pmeier](https://github.com/pmeier) in
  [#221](https://github.com/Quansight/ragna/pull/221)
- run CI on release branches by [@pmeier](https://github.com/pmeier) in
  [#222](https://github.com/Quansight/ragna/pull/222)
- mark as PEP561 compatible by [@pmeier](https://github.com/pmeier) in
  [#232](https://github.com/Quansight/ragna/pull/232)
- set hard limit of visible document pills by [@pmeier](https://github.com/pmeier) in
  [#235](https://github.com/Quansight/ragna/pull/235)
- supply document name as part of the request body rather than query by
  [@pmeier](https://github.com/pmeier) in
  [#186](https://github.com/Quansight/ragna/pull/186)
- Make document upload method flexible by [@pmeier](https://github.com/pmeier) in
  [#238](https://github.com/Quansight/ragna/pull/238)

### New Contributors

- [@petrpan26](https://github.com/petrpan26) made their first contribution in
  [#184](https://github.com/Quansight/ragna/pull/184)
- [@agilgur5](https://github.com/agilgur5) made their first contribution in
  [#197](https://github.com/Quansight/ragna/pull/197)

## Version 0.1.1

### Feature changes and enhancements

- The optional dependencies needed for the builtin components are now available under
  the `'all'` key. Please install Ragna with `pip install 'ragna[all]'`.
- The functionality of `ragna config` and `ragna config --check` was split into two
  commands: `ragna init` and `ragna check`. Use `ragna init` to start the configuration
  creation wizard and create a configuration file. `ragna check` is used to check the
  availability of the selected components in an existing configuration file.
- In the default configuration, `ragna ui` now starts with
  [`RagnaDemoAuthentication`](https://ragna.chat/en/stable/references/python-api/#ragna.core.RagnaDemoAuthentication)
  enabled. To login, you can use an arbitrary username and the same string for the
  password as well. For example, leaving both fields blank allows you to login.

### Breaking Changes

- The command `ragna config` was removed. Use `ragna init` to create a configuration
  file and `ragna check` to check it.
- The special options `'builtin'` (former default) and `'demo'` were removed from the
  Ragna CLI. Now a configuration file is required and can be created by `ragna init`.
  Note that by default all subcommands will automatically use the `ragna.toml` file in
  the current working directory in case it exists if the `-c` / `--config` flag is not
  used.
- The configuration options `config.api.upload_token_secret` and
  `config.api.upload_token_ttl` were removed. The former can now only be configured with
  the `RAGNA_API_DOCUMENT_UPLOAD_SECRET` environment variable and the latter is now
  fixed at 5 minutes. If you want to keep using your generated configuration files,
  please delete the `upload_token_secret` and `upload_token_ttl` keys in the `[api]`
  section.

### What's Changed

- forward subprocess STDOUT / STDERR to main process by
  [@pmeier](https://github.com/pmeier) in
  [#123](https://github.com/Quansight/ragna/pull/123)
- quote the builtin install instructions by [@pmeier](https://github.com/pmeier) in
  [#122](https://github.com/Quansight/ragna/pull/122)
- fix chroma only retrieving one source by [@pmeier](https://github.com/pmeier) in
  [#132](https://github.com/Quansight/ragna/pull/132)
- fix chat param unpacking by [@pmeier](https://github.com/pmeier) in
  [#133](https://github.com/Quansight/ragna/pull/133)
- refactor config wizard by [@pmeier](https://github.com/pmeier) in
  [#125](https://github.com/Quansight/ragna/pull/125)
- dont create DB session as dependency by [@pmeier](https://github.com/pmeier) in
  [#138](https://github.com/Quansight/ragna/pull/138)
- allow API token secret to be set through env var by
  [@pmeier](https://github.com/pmeier) in
  [#141](https://github.com/Quansight/ragna/pull/141)
- Auth + async answer + loading indicator in placeholder by
  [@pierrotsmnrd](https://github.com/pierrotsmnrd) in
  [#135](https://github.com/Quansight/ragna/pull/135)
- Recommend [builtin] for installation by [@pavithraes](https://github.com/pavithraes)
  in [#134](https://github.com/Quansight/ragna/pull/134)
- make DB connect_args type specific by [@pmeier](https://github.com/pmeier) in
  [#139](https://github.com/Quansight/ragna/pull/139)
- only display unmet packages and env vars of the selected components by
  [@pmeier](https://github.com/pmeier) in
  [#140](https://github.com/Quansight/ragna/pull/140)
- add plausible analytics by [@pmeier](https://github.com/pmeier) in
  [#143](https://github.com/Quansight/ragna/pull/143)
- clarify demo assistant message by [@pmeier](https://github.com/pmeier) in
  [#147](https://github.com/Quansight/ragna/pull/147)
- fix Ragna 101 by [@pmeier](https://github.com/pmeier) in
  [#146](https://github.com/Quansight/ragna/pull/146)
- config quick fix : disable sliders if "Ragna/Demo" by
  [@pierrotsmnrd](https://github.com/pierrotsmnrd) in
  [#155](https://github.com/Quansight/ragna/pull/155)
- Make API / UI origins configurable by [@pmeier](https://github.com/pmeier) in
  [#149](https://github.com/Quansight/ragna/pull/149)
- add prominent note about LLM access and instructions on how to get keys by
  [@pmeier](https://github.com/pmeier) in
  [#159](https://github.com/Quansight/ragna/pull/159)
- Update README.md by [@pavithraes](https://github.com/pavithraes) in
  [#154](https://github.com/Quansight/ragna/pull/154)
- Add testing for docs by [@pavithraes](https://github.com/pavithraes) in
  [#151](https://github.com/Quansight/ragna/pull/151)
- add print for demo auth by [@pmeier](https://github.com/pmeier) in
  [#157](https://github.com/Quansight/ragna/pull/157)
- Up the number of queried documents by Chroma by [@pmeier](https://github.com/pmeier)
  in [#160](https://github.com/Quansight/ragna/pull/160)
- Add announcement banner with link to blog by
  [@pavithraes](https://github.com/pavithraes) in
  [#164](https://github.com/Quansight/ragna/pull/164)

### New Contributors

- [@pierrotsmnrd](https://github.com/pierrotsmnrd) made their first contribution in
  [#135](https://github.com/Quansight/ragna/pull/135)

## Version 0.1.0

Initial release. Read the launch blog post
[here](https://quansight.com/post/unveiling-ragna-an-open-source-rag-based-ai-orchestration-framework-designed-to-scale-from-research-to-production/).
