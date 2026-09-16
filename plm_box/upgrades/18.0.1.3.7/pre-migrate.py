import logging

_logger = logging.getLogger(__name__)

TABLES = ("plm_box",)


def migrate(cr, version):
    """plm_box inherits RevisionBaseMixin, so it carries the same unique index,
    declared with the condition that reads as something other than what it does.
    '' and '-' become NULL, as the mixin now stores them, and the index is
    dropped for RevisionBaseMixin.init to recreate it.
    """
    for table in TABLES:
        cr.execute(
            "UPDATE {table} SET engineering_code = NULL"
            " WHERE engineering_code IN ('', '-')".format(table=table)
        )
        _logger.info("plm_box: %s %s placeholder codes cleared", cr.rowcount, table)
        cr.execute("DROP INDEX IF EXISTS unique_index_{table}".format(table=table))
