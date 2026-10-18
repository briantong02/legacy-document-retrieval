from sqlalchemy import text

SEARCH_SQL = text(
    """
  SELECT
        [M3_CINO] AS [Payment#],
        [CREATETS],
        [RESOURCENAME],
        [RESOURCECONTENT],
        [LASTCHANGEDUSERID],
        [RESOURCEID]
    FROM [idm].[DUX_AR_Remittances]
    WHERE [M3_PYNO] = :payer_no
      AND (:created_after IS NULL OR [CREATETS] > :created_after)
      AND (:document_no IS NULL OR [M3_CINO] = :document_no)
  ORDER BY [CREATETS]
    """
)
