# Analysis of [`doc_rag_init.py`](doc_rag_init.py)

## Successes

1. **Advanced text scraping and cleaning**: [`trafilatura`](doc_rag_init.py:11) library integrated for robust extraction and boilerplate removal, replacing basic WebBaseLoader.

2. **Source URL metadata**: Correctly added as `doc.metadata['url'] = url` ([`doc_rag_init.py`](doc_rag_init.py:77)).

3. **Improved publish date extraction**: Now checks position within first 300 characters and uses enhanced regex for accuracy ([`doc_rag_init.py`](doc_rag_init.py:64-75)).

4. **Logging for verification**: Added logging for publish date extraction with position info ([`doc_rag_init.py`](doc_rag_init.py:75)).

## Remaining Gaps

1. **Deduplication**: No deduplication implemented before adding to vectorstore; potential for duplicate content.

2. **Further tuning**: Chunk size set to 300, but may need adjustment based on document types.

## Current Flow

```mermaid
graph LR
    A[Load URLs from [`config/comms.json`](config/comms.json)] --> B{For each URL}
    B --> C[[`trafilatura.fetch_url`](doc_rag_init.py:24) & [`trafilatura.extract`](doc_rag_init.py:25)]]
    C --> D[[`clean_text`](doc_rag_init.py:26): normalize whitespace]]
    D --> E[[Date extraction with position check <300 chars](doc_rag_init.py:64-75)]]
    E --> F[metadata.url = url]
    F --> G[[`RecursiveCharacterTextSplitter`](doc_rag_init.py:49)]]
    G --> H[Filter empty -> [`vectorstore.add_documents`](doc_rag_init.py:89)]]
```

## Recommended Fixes

1. **Advanced Cleaning**:
   - Integrate `trafilatura` library (add to pyproject.toml: `trafilatura`).
   - Replace indexing_pipeline:

      ```python
      import trafilatura
      def indexing_pipeline(url):
          try:
              downloaded = trafilatura.fetch_url(url)
              text = trafilatura.extract(downloaded)
              if text:
                  from langchain_core.documents import Document
                  return [Document(page_content=text)]
              return []
          except Exception as e:
              logger.error(f"Error processing {url}: {e}")
              return []
      ```

      Trafilatura automatically cleans boilerplate, extracts main text.

2. **Fix Publish Date**:
   - Extract only if first match within opening lines.
   - Replace lines 57-61:

      ```python
      from dateutil import parser as date_parser
      date_regex = r'\\b(?:\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}|\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}|\\w+ \\d{1,2}, \\d{4})\\b'
      match = re.search(date_regex, doc.page_content)
      if match and match.start() < 300:  # First 300 chars as opening lines
          try:
              parsed_date = date_parser.parse(match.group(0))
              doc.metadata['publish_date'] = parsed_date.isoformat()
          except ValueError:
              pass
      ```

   - Enhanced regex, position check.

3. **Additional Improvements**:
   - Deduplication: Before adding to vectorstore, use a set or langchain dedupe.
   - Logging: Log extracted date and position: `logger.info(f"Extracted publish_date: {doc.metadata.get('publish_date')} at pos {match.start() if match else 'N/A'}")`.
   - Chunk size tune for docs.

## Verification Status

Current implementation **mostly successful**:

- ✅ Scrapes and cleans text effectively with trafilatura
- ✅ Adds URL metadata
- ✅ Publish date position-checked and logged
- ❌ Deduplication not implemented

**Overall**: Performs tasks successfully with minor gaps.

## Proposed Todo for Fixes

- [x] Add trafilatura to pyproject.toml and implement advanced cleaning
- [x] Update date extraction with position check
- [x] Add logging for verification
- [x] Re-run doc_rag_init.py and inspect ChromaDB metadata
- [x] Switch to code mode for implementation
