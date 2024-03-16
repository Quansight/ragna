# Release notes

## Version 0.2.0

### Feature changes and enhancements

- Ragna's `0.1.x` releases were built on a task queue backend. This turned out to be a
  premature optimization that limited us in other features we wanted to implement. Thus,
  we removed it without impacting the API. This enabled us to add two new features:
  - The abstract methods on the RAG components, i.e. [ragna.core.SourceStorage.store][],
    [ragna.core.SourceStorage.retrieve][], and [ragna.core.Assistant.answer][], can now
    also be declared as `async def`. Asynchronous methods will be called on the main
    event loop while the synchronous methods (`def`) will be called in a separate thread
    to avoid blocking the main thread.
  - [ragna.core.Assistant.answer][] now returns iterator, which allows streaming an
    answer. Check out the
    [streaming example](../generated/examples/gallery_streaming.md) to learn how you can
    stream answers from the Python and REST API. The Ragna web UI will always stream to
    enhance the UX.
- Ragna gained support for Markdown ([`.md`][ragna.core.PlainTextDocumentHandler]),
  Microsoft Word ([`.docx`][ragna.core.DocxDocumentHandler]), and Microsoft Powerpoint
  ([`.pptx`][ragna.core.PptxDocumentHandler]) documents.
- Ragna now has an official [docker](https://www.docker.com/) image. Try it with

  ```
  $ docker run -p 31476:31476 -p 31477:31477 quay.io/quansight/ragna:0.2.0
  ```

  The web UI can be accessed under `http://localhost:31477`.

- Instead of just returning the location of a source, e.g. page numbers in a PDF
  document but potentially nothing for other formats that don't have this kind of
  information, the REST API now also returns the full source content. This aligns it
  with the Python API. The source view in the web UI now also shows the source content.

### Breaking Changes

- As a result of the removal of the task queue, `ragna worker` is no longer needed and
  was removed. The same applies to the `--start-worker` option of `ragna api` and the
  `queue_url` configuration option (see below).
- The return type of [ragna.core.Assistant.answer][] changed from `str` to
  `Iterator[str]` / `AsyncIterator[str]`. To reflect that in the implementation, replace
  `return` with `yield`. To stream the response, `yield` multiple times.
- The abstract property `ragna.core.Assistant.max_input_size` was removed. This
  information was never used anywhere. Note that you don't have to remove it from
  existing implementations. It will just stay unused by Ragna.
- We introduced a couple of changes to the configuration file.

  - The top level `local_cache_root` option was renamed to `local_root` to align with
    the new [ragna.local_root][] function.
  - The `[core]` section was dissolved and its options merged into the top level. The
    `queue_url` option was removed.
  - The `authentication` option was moved from the `[api]` section to the top level.
  - Both the `[api]` and `[ui]` section gained a `hostname` and `port` parameter that
    are used to bind the application. The `url` option, previously used for the same
    purpose, option was removed from the `[ui]` section. It was retained in the `[api]`
    section, but now only indicates the URL the REST API can be contacted on, e.g. by
    the web UI, and has no effect on how the REST API is bound.
  - The default value of `database_url` in the `[api]` section changed to use a
    persistent database by default. The `"memory"` option is no longer available. Use
    `sqlite://` if you want to retain the non-persistent behavior.
  - The `[api]` section gained a new [`root_path`](config.md#root_path) option to help
    deploying Ragna behind a proxy. By default, the behavior does not change compared to
    before.

  Below you can find a comparison between two equivalent configuration files

  <table>
  <tr>
  <td> v0.1.3 </td>
  <td>

  ```toml
  local_cache_root = "/home/user/.cache/ragna"

  [core]
  queue_url = "memory"
  document = "ragna.core.LocalDocument"
  source_storages = [
      "ragna.source_storages.Chroma",
      ...
  ]
  assistants = [
      "ragna.assistants.Claude",
      ...
  ]

  [api]
  url = "http://127.0.0.1:31476"
  origins = ["http://127.0.0.1:31477"]
  database_url = "memory"
  authentication = "ragna.core.RagnaDemoAuthentication"

  [ui]
  url = "http://127.0.0.1:31477"
  origins = ["http://127.0.0.1:31477"]
  ```

  </td>
  </tr>
  <tr>
  <td> v0.2.0 </td>
  <td>

  ```toml
  local_root = "/home/user/.cache/ragna"
  authentication = "ragna.deploy.RagnaDemoAuthentication"
  document = "ragna.core.LocalDocument"
  source_storages = [
      "ragna.source_storages.Chroma",
      ...
  ]
  assistants = [
      "ragna.assistants.Claude",
      ...
  ]

  [api]
  hostname = "127.0.0.1"
  port = 31476
  root_path = ""
  url = "http://127.0.0.1:31476"
  origins = [
      "http://127.0.0.1:31477",
  ]
  database_url = "sqlite://"

  [ui]
  hostname = "127.0.0.1"
  port = 31477
  origins = [
      "http://127.0.0.1:31477",
  ]
  ```

  </td>
  </tr>
  </table>

- The classes [ragna.deploy.Authentication][], [ragna.deploy.RagnaDemoAuthentication][],
  and [ragna.deploy.Config][] moved from the [ragna.core][] module to a new
  [ragna.deploy][] module.
- [ragna.core.Component][], which is the superclass for [ragna.core.Assistant][] and
  [ragna.core.SourceStorage][], no longer takes a [ragna.deploy.Config][] to
  instantiate. For example

  ```python
  class MyAssistant(ragna.core.Assistant):
      def __init__(self, config):
          super().__init__(config)
  ```

  needs to change to

  ```python
  class MyAssistant(ragna.core.Assistant):
      def __init__(self):
          super().__init__()
  ```

  You can use the new [ragna.local_root][] function as replacement for
  [`config.local_root`](config.md) if needed.

- The database scheme changed and is no longer compatible with the tables used in
  previous releases. The default database set by the configuration wizard is located at
  `~/.cache/ragna/ragna.db`. Please delete it. It will be created anew the next time the
  REST API is started.
- The `/chat/{chat_id}/prepare` and `/chat/{chat_id}/answer` endpoints of the REST API
  now no longer return the chat object, but only the message.

### What's Changed

- fix note in Ragna 101 by [@pmeier](https://github.com/pmeier) in
  [#187](https://github.com/Quansight/ragna/pull/187)
- make config optional when creating a component by [@pmeier](https://github.com/pmeier)
  in [#194](https://github.com/Quansight/ragna/pull/194)
- fix Config source priority and add tests by [@pmeier](https://github.com/pmeier) in
  [#200](https://github.com/Quansight/ragna/pull/200)
- add smoke tests for source storages by [@pmeier](https://github.com/pmeier) in
  [#201](https://github.com/Quansight/ragna/pull/201)
- docs: improvements to REST API tutorial by [@agilgur5](https://github.com/agilgur5) in
  [#198](https://github.com/Quansight/ragna/pull/198)
- remove task queue by [@pmeier](https://github.com/pmeier) in
  [#205](https://github.com/Quansight/ragna/pull/205)
- remove [BUG] and [ENH] classifier from issue templates by
  [@pmeier](https://github.com/pmeier) in
  [#228](https://github.com/Quansight/ragna/pull/228)
- Fix timeouts by [@pmeier](https://github.com/pmeier) in
  [#234](https://github.com/Quansight/ragna/pull/234)
- don't return full chat as part of message output by
  [@pmeier](https://github.com/pmeier) in
  [#249](https://github.com/Quansight/ragna/pull/249)
- code quality improvements of the API wrapper by [@pmeier](https://github.com/pmeier)
  in [#250](https://github.com/Quansight/ragna/pull/250)
- add functionality to format CSS stylesheets by [@pmeier](https://github.com/pmeier) in
  [#257](https://github.com/Quansight/ragna/pull/257)
- Cleanup UI code by [@pmeier](https://github.com/pmeier) in
  [#261](https://github.com/Quansight/ragna/pull/261)
- Add support for markdown files (#210) by [@paskett](https://github.com/paskett) in
  [#270](https://github.com/Quansight/ragna/pull/270)
- fix source view on messages that were generated in a previous session by
  [@pmeier](https://github.com/pmeier) in
  [#273](https://github.com/Quansight/ragna/pull/273)
- add forward slashes to the auth and logout endpoints by
  [@pmeier](https://github.com/pmeier) in
  [#276](https://github.com/Quansight/ragna/pull/276)
- implement streaming for assistants by [@pmeier](https://github.com/pmeier) in
  [#215](https://github.com/Quansight/ragna/215)
- return source content from the REST API by [@pmeier](https://github.com/pmeier) in
  [#264](https://github.com/Quansight/ragna/264)
- Fix environment-dev.yml by [@nenb](https://github.com/nenb) in
  [#282](https://github.com/Quansight/ragna/282)
- Support using .docx files by [@paskett](https://github.com/paskett) in
  [#281](https://github.com/Quansight/ragna/281)
- dockerize by [@pmeier](https://github.com/pmeier) in
  [#283](https://github.com/Quansight/ragna/283)
- add workflow to update the docker requirements by [@pmeier](https://github.com/pmeier)
  in [#287](https://github.com/Quansight/ragna/287)
- add write permissions for GHA bot by [@pmeier](https://github.com/pmeier) in
  [#288](https://github.com/Quansight/ragna/288)
- add workflow actor as reviewer rather than assignee by
  [@pmeier](https://github.com/pmeier) in [#293](https://github.com/Quansight/ragna/293)
- Fix relative path handling for ragna panel app by [@aktech](https://github.com/aktech)
  in [#280](https://github.com/Quansight/ragna/280)
- Pptx support by [@davidedigrande](https://github.com/davidedigrande) in
  [#296](https://github.com/Quansight/ragna/296)
- Increase API timeout and add custom message by
  [@smokestacklightnin](https://github.com/smokestacklightnin) in
  [#299](https://github.com/Quansight/ragna/299)
- add Google assistants by [@pmeier](https://github.com/pmeier) in
  [#301](https://github.com/Quansight/ragna/301)
- RTD git debug by [@pmeier](https://github.com/pmeier) in
  [#302](https://github.com/Quansight/ragna/302)
- bump minimum panel version to 1.3.8 by [@pmeier](https://github.com/pmeier) in
  [#284](https://github.com/Quansight/ragna/pull/284)
- move BC policy into documentation by [@pmeier](https://github.com/pmeier) in
  [#309](https://github.com/Quansight/ragna/pull/309)
- remove invalid font CSS declaration by [@pmeier](https://github.com/pmeier) in
  [#308](https://github.com/Quansight/ragna/pull/308)
- make arrays in config multiline by [@pmeier](https://github.com/pmeier) in
  [#311](https://github.com/Quansight/ragna/pull/311)
- [ENH] - add support for Cohere assistants by
  [@smokestacklightnin](https://github.com/smokestacklightnin) in
  [#307](https://github.com/Quansight/ragna/pull/307)
- fix invalid escape warning when building docs by [@pmeier](https://github.com/pmeier)
  in [#314](https://github.com/Quansight/ragna/pull/314)
- [ENH] - Add support for AI21labs assistants by
  [@smokestacklightnin](https://github.com/smokestacklightnin) in
  [#303](https://github.com/Quansight/ragna/pull/303)
- re-add Authentication documentation by [@pmeier](https://github.com/pmeier) in
  [#316](https://github.com/Quansight/ragna/pull/316)
- Set up git-lfs and track relevant files by
  [@pavithraes](https://github.com/pavithraes) in
  [#315](https://github.com/Quansight/ragna/pull/315)
- document default login credentials by [@pmeier](https://github.com/pmeier) in
  [#168](https://github.com/Quansight/ragna/pull/168)
- Remove duplicate call to answer method when not streaming by
  [@nenb](https://github.com/nenb) in
  [#325](https://github.com/Quansight/ragna/pull/325)
- use truly-sane-lists plugin by [@pmeier](https://github.com/pmeier) in
  [#324](https://github.com/Quansight/ragna/pull/324)
- use FastAPI test client for testing by [@pmeier](https://github.com/pmeier) in
  [#322](https://github.com/Quansight/ragna/pull/322)
- update outdated actions by [@pmeier](https://github.com/pmeier) in
  [#321](https://github.com/Quansight/ragna/pull/321)
- remove memory option for state db by [@pmeier](https://github.com/pmeier) in
  [#320](https://github.com/Quansight/ragna/pull/320)
- only send sources on first chunk when streaming by
  [@pmeier](https://github.com/pmeier) in
  [#317](https://github.com/Quansight/ragna/pull/317)
- refactor config docs by [@pmeier](https://github.com/pmeier) in
  [#318](https://github.com/Quansight/ragna/pull/318)
- restrict accepted files in file uploader by [@pmeier](https://github.com/pmeier) in
  [#319](https://github.com/Quansight/ragna/pull/319)
- add 'why should I use Ragna?' to FAQ by [@pmeier](https://github.com/pmeier) in
  [#335](https://github.com/Quansight/ragna/pull/335)
- ignore httpx deprecation warning by [@pmeier](https://github.com/pmeier) in
  [#342](https://github.com/Quansight/ragna/pull/342)
- use mkdocs-gallery for example / tutorial documentation by
  [@pmeier](https://github.com/pmeier) in
  [#89](https://github.com/Quansight/ragna/pull/89)
- set LanceDB config dir in Dockerfile by [@pmeier](https://github.com/pmeier) in
  [#330](https://github.com/Quansight/ragna/pull/330)
- Prevent creation of large \_stylesheet class variable by
  [@nenb](https://github.com/nenb) in
  [#341](https://github.com/Quansight/ragna/pull/341)
- Config refactor by [@pmeier](https://github.com/pmeier) in
  [#328](https://github.com/Quansight/ragna/pull/328)
- add option to not open the browser when starting the web UI by
  [@pmeier](https://github.com/pmeier) in
  [#345](https://github.com/Quansight/ragna/pull/345)
- use root_path in api.url by [@pmeier](https://github.com/pmeier) in
  [#346](https://github.com/Quansight/ragna/pull/346)
- Add option to ignore unavailable components by [@pmeier](https://github.com/pmeier) in
  [#333](https://github.com/Quansight/ragna/pull/333)
- decrease default number of tokens in UI by [@pmeier](https://github.com/pmeier) in
  [#351](https://github.com/Quansight/ragna/pull/351)
- improve error handling for builtin assistants by [@pmeier](https://github.com/pmeier)
  in [#350](https://github.com/Quansight/ragna/pull/350)
- add test for a streaming assistant by [@pmeier](https://github.com/pmeier) in
  [#349](https://github.com/Quansight/ragna/pull/349)
- remove max_input_size property from assistants by [@pmeier](https://github.com/pmeier)
  in [#362](https://github.com/Quansight/ragna/pull/362)
- Add overview video to docs & README by [@pavithraes](https://github.com/pavithraes) in
  [#363](https://github.com/Quansight/ragna/pull/363)
- fix typo in FAQ by [@pmeier](https://github.com/pmeier) in
  [#348](https://github.com/Quansight/ragna/pull/348)
- fix release notes link in project metadata by [@pmeier](https://github.com/pmeier) in
  [#361](https://github.com/Quansight/ragna/pull/361)
- break recursion cycle for chat message repr by [@pmeier](https://github.com/pmeier) in
  [#360](https://github.com/Quansight/ragna/pull/360)
- use JSONL streaming over SSE by [@pmeier](https://github.com/pmeier) in
  [#357](https://github.com/Quansight/ragna/pull/357)

### New Contributors

- [@paskett](https://github.com/paskett) made their first contribution in
  [#270](https://github.com/Quansight/ragna/270)
- [@aktech](https://github.com/aktech) made their first contribution in
  [#280](https://github.com/Quansight/ragna/280)
- [@davidedigrande](https://github.com/davidedigrande) made their first contribution in
  [#296](https://github.com/Quansight/ragna/296)
- [@smokestacklightnin](https://github.com/smokestacklightnin) made their first
  contribution in [#299](https://github.com/Quansight/ragna/299)

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
  [#244](https://github.com/Quansight/ragna/pull/244)
- [@nenb](https://github.com/nenb) made their first contribution in
  [#252](https://github.com/Quansight/ragna/pull/252)

## Version 0.1.2

### Breaking changes

- The `/document` endpoints on the REST API have changed

  - The `GET /document` endpoint of the REST API to register the document and get the
    upload information changed to `POST /document`. The document name now needs to be
    passed as part of the body as JSON rather than as query parameter.
  - The JSON object returned by the new `POST /document` endpoint of the REST API now
    bundles the `url` and `data` fields under one `parameters` fields. In addition, the
    `parameters` field also now includes a `method` field that specifies how the upload
    request should be sent.
  - The `POST /document` endpoint of the REST API to upload documents stored locally
    changed to `PUT /document`.

  For example

  ```python
  document_upload = client.get("/document", params={"name": name}).json()
  client.post(
      document_upload["url"],
      data=document_upload["data"],
      files={"file": ...},
  )
  ```

  needs to change to

  ```python
  document_upload = client.post("/document", json={"name": name}).json()
  parameters = document_upload["parameters"]
  client.request(
      parameters["method"],
      parameters["url"],
      data=parameters["data"],
      files={"file": ...},
  )
  ```

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
