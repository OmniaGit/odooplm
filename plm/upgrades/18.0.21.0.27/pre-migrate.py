import logging

_logger = logging.getLogger(__name__)

TABLES = ("product_template", "ir_attachment")


def migrate(cr, version):
    """One rule for engineering codes: a set code is unique per revision.

    '' and '-' once stood for "no code", to skip the checks while cloning and
    revising; they become NULL, as the models now store them.

    The unique index was declared with ``engineering_code IS NOT NULL OR
    engineering_code NOT IN ('-','')``, which is the same as ``IS NOT NULL`` but
    reads as something else; it is dropped here and RevisionBaseMixin.init
    recreates it with the plain condition, on product_template too, which never
    had it.
    """
    for table in TABLES:
        cr.execute(
            "UPDATE {table} SET engineering_code = NULL"
            " WHERE engineering_code IN ('', '-')".format(table=table)
        )
        _logger.info("plm: %s %s placeholder codes cleared", cr.rowcount, table)
        cr.execute("DROP INDEX IF EXISTS unique_index_{table}".format(table=table))
