from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from app.db.session import docmgmt_engine, idm_engine


@dataclass
class IndexSummary:
    inserted: int = 0
    updated: int = 0


SELECT_INDEX_SOURCE = text(
    """
    SELECT ResourceID AS resource_id, DocumentPath AS document_path
    FROM idm.DocumentIndexSource
    """
)

UPSERT_DOCUMENT = text(
    """
    MERGE dbo.Document AS target
    USING (SELECT :resource_id AS ResourceId, :document_path AS DocumentPath) AS source
    ON target.ResourceId = source.ResourceId
    WHEN MATCHED THEN
        UPDATE SET target.DocumentPath = source.DocumentPath
    WHEN NOT MATCHED THEN
        INSERT (ResourceId, DocumentPath)
        VALUES (source.ResourceId, source.DocumentPath);
    """
)


def index_documents() -> IndexSummary:
    summary = IndexSummary()

    with idm_engine.connect() as source_connection, docmgmt_engine.begin() as target_connection:
        source_rows = source_connection.execute(SELECT_INDEX_SOURCE).mappings().all()

        for row in source_rows:
            resource_id = row.get("resource_id")
            document_path = row.get("document_path")
            if not resource_id or not document_path:
                continue

            before = target_connection.execute(
                text("SELECT COUNT(1) FROM dbo.Document WHERE ResourceId = :resource_id"),
                {"resource_id": resource_id},
            ).scalar_one()

            target_connection.execute(
                UPSERT_DOCUMENT,
                {"resource_id": resource_id, "document_path": document_path},
            )

            if before:
                summary.updated += 1
            else:
                summary.inserted += 1

    return summary


if __name__ == "__main__":
    result = index_documents()
    print(f"Index complete: inserted={result.inserted}, updated={result.updated}")
