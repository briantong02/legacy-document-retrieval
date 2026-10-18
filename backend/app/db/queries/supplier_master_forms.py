from sqlalchemy import text

SEARCH_SQL = text(
    """
    SELECT
        [RESOURCENAME],
        [RESOURCECONTENT],
        [LASTCHANGEDUSERID],
        [LASTCHANGEDTS],
        [RESOURCEID]
    FROM [idm].[DUX_Supplier_Master_Forms]
    WHERE [M3_Supplier_Number] = :supplier_no
    """
)
