import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        "UPDATE ir_attachment SET (res_model, res_id) = ('plm.access', 1) where is_plm=true and res_id is null"
    )
    _logger.info("Updated %s attachments", cr.rowcount)
