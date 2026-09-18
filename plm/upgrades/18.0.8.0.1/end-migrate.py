import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # "attached to nothing" is res_id 0 as often as it is NULL, so a condition on
    # NULL alone left part of the documents behind. res_field keeps out the
    # attachments that are the storage of a binary field: those must go on
    # pointing at their field, not at a PLM access node.
    cr.execute(
        "UPDATE ir_attachment SET (res_model, res_id) = ('plm.access', 1)"
        " WHERE is_plm = true AND coalesce(res_id, 0) = 0 AND res_field IS NULL"
    )
    _logger.info("Updated %s attachments", cr.rowcount)
