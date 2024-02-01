We have at least three scenarios already

1. experimentation
   - User uploads documents for each chat
   - each chat uses a new corpus
2. Selecting documents by name / folder (BX)
   - user wants to list all available documents from VDB
   - user wants to subselect documents by name
3. Selecting documents by tag (new client)
   - https://github.com/Quansight/ragna/issues/246

## ideas

- for all scenarios above we need a different UI. Meaning, the corpus class needs to
  have a `__panel__` method that defines the UI
- Similar for the REST API. WE probably need to give the Corpus object a way to add
  endpoints
- For the Python API, we need to separate Corpus from Chat. I'm now ok with Chat taking
  only a corpus rather than also documents. Users will have to create the corpus before
  they start the chat. That will also move the context manager to the corpus
- I really don't know about source storage yet. Do we make it an attribute of the
  Corpus? Should it have a method to list documents? If not, how are we getting the
  available tags / documents back to the other parts?

maybe have a

```python
class SourceStorage:
    def list(self, corpus_id) -> list[Document]:
        pass
```

- creating the corpus inside the API even needs DB access due to our shitty two step
  process to upload documents
- or is this a general requirement? do we always want to prepare the corpus on creation
  or should this always be a two-step process?

Imageine the scenario of selecting by tags

- On the UI I need a list of available tags / this should also be an endpoint on the API
  - This could be done by the list endpoint of the source storage by just collecting all
    available tags
- I select some tags and create a new corpus from that
  - This corpus has the prepared attribtue on it that determines if we auto prepare next
    in the UI.
  - In the API we don't auto-prepare or at least not by default. We should keep the
    prepare endpoint

!!! A corpus does not have to be a table in a VDB, but could also be just a subset in
!!! Meaning, we never filter by corpus ID inside the VDB, because each document could
potentially belong to multiple corpora

Assuming we have multiple tables (dev / prod, different embedding models, ...), how are
going to select which table to operate on?

Table in arrow, collection in chroma, index in pinecone

---

Do we actually need a way to list existing metadata? Wouldn't it be enough to attach a
metadata filter to a corpus and just submit all the document metadata with each chunk

on store we put everything in on retrieve we query and apply the metadata filter

for example each document has tag when the filter contains multiple tags we just filter
on that

each SourceStorage can offer metadata filtering, if it can't it is not worth using

Open Questions:

1. Can we build a filter abstraction that each SourceStorage can translate into its own
   dialect?
2. Can we wire up the builtin source storages to work with both use cases?

for 2:

if we have one collection for embedding model (i.e. currently only one) we should be
fine

- for the experimentation use case we use a filename filter

## current understanding

- SS collections are based on the embedding model, i.e. we'll only have one for now
- store just takes a list of documents
- retrieve takes metadata filter

-> No corpus needed?

Chat object

documents is None and metadata_filter is None: raise

documents is not None and metadata_filter is None: store documents in SS and create a
filter based on the names => current scenario

documents is None and metadata_filter is not None: set chat to being prepared and use
the filter => tag based with existing SS

documents is not None and metadata_filter is not None: raise

maybe use input as parameter name? input might be either a metadata filter, a document
or a list of documents

---

FOr the API new chat will take both parameters and error in case both or none are send

For the UI we need redesign the interface into two phases

1. Upload documents / selecting source storage / selecting parameters for the source
   storage / select a metadata filter
2. Select assistant / select assistant parameters

Phase 1. needs to be flexible from a user perspective. Meaning completely disable this
to always use all documents Or replace upload through tag selection

we also need a /upload page that handles the doc upload in case the new chat only
returns a metadata filter
