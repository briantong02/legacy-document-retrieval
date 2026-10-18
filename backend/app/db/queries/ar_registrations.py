from sqlalchemy import text

SEARCH_SQL = text(
    """
    SELECT
        [RESOURCENAME],
        [RESOURCECONTENT],
        [LASTCHANGEDUSERID],
        [RESOURCEID]
    FROM [idm].[DUX_AR_Registrations]
    WHERE [M3_CUNO] = :customer_no
    """
)
