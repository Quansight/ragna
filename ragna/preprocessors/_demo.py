from typing import Optional

from ragna.core import (
    MetadataFilter,
    ProcessedQuery,
    QueryPreprocessor,
    QueryProcessingStep,
)


class RagnaDemoPreprocessor(QueryPreprocessor):
    def process(
        self, query: str, metadata_filter: Optional[MetadataFilter] = None
    ) -> ProcessedQuery:
        """Retrieval query is the original query, answer query is the processed query."""
        print(query)
        print(metadata_filter)
        processed_query = """This is a demo preprocessor. It doesn't do anything to the query. original query: """
        processed_query += query
        return ProcessedQuery(
            original_query=query,
            processed_query=processed_query,
            metadata_filter=metadata_filter or MetadataFilter(),
            processing_history=[
                QueryProcessingStep(
                    original_query=query,
                    processed_query=query,
                    metadata_filter=metadata_filter,
                    processor_name=self.display_name(),
                )
            ],
        )
