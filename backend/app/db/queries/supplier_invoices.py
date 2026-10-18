from sqlalchemy import text

# [M3_Date] is stored as ddmmyy text. Convert it once per row with CROSS APPLY so the
# expression is written once instead of three times, and use TRY_CONVERT so a malformed
# stored value yields NULL rather than aborting the whole query. The century is hard-coded
# to '20' - see docs/app-spec.md section 9.3.
_M3_DATE_APPLY = """
    CROSS APPLY (
        SELECT TRY_CONVERT(
            date,
            CONCAT(
                '20', RIGHT(TRIM([M3_Date]), 2), '-',
                SUBSTRING(TRIM([M3_Date]), 3, 2), '-',
                LEFT(TRIM([M3_Date]), 2)
            )
        ) AS m3_date_value
    ) d
"""

# :from_date is an ISO date supplied by the caller. It is compared directly rather than
# rebuilt from string fragments: CONCAT turns NULL into an empty string, so the old form
# built the literal '20--' whenever no date was given and CONVERT then failed with error 241.
# :from_date and :invoice_no are mutually exclusive - the form disables one once the other is
# filled and the route rejects the pair - so only ever one of them narrows the result set.
_FILTER_AND_ORDER = """
    WHERE [M3_Supplier_Number] = :supplier_no
      AND (:from_date IS NULL OR d.m3_date_value >= :from_date)
      AND (:invoice_no IS NULL OR [M3_Supplier_Invoice_No] = :invoice_no)
    ORDER BY
        CASE WHEN d.m3_date_value IS NULL THEN 1 ELSE 0 END,
        d.m3_date_value
"""

_COLUMNS = """
    SELECT
        [M3_Date],
        [M3_Supplier_Invoice_No],
        [RESOURCENAME],
        [RESOURCECONTENT],
        [LASTCHANGEDUSERID],
        [LASTCHANGEDTS],
        [RESOURCEID]
"""


def _supplier_invoice_sql(table: str):
    return text(f"{_COLUMNS} FROM [idm].[{table}] {_M3_DATE_APPLY} {_FILTER_AND_ORDER}")


CONFIDENTIAL_SQL = _supplier_invoice_sql("DuxSupplierInvoice_Con")
EXPENSES_SQL = _supplier_invoice_sql("DuxSupplierInvoice_Exp")
GENERAL_SQL = _supplier_invoice_sql("DuxSupplierInvoice_Gen")
