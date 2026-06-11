import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Start recovering legacy data")
    cr.execute("select id,from_state, to_state, apply_to from plm_automatedwfaction")
    for row in cr.fetchall():
        if row[3] == "product.product":
            cr.execute(
                """UPDATE plm_automatedwfaction
                   SET product_from_state = %s, product_to_state = %s
                   WHERE id = %s""",
                (row[1], row[2], row[0]),
            )
        elif row[3] == "ir.attachment":
            cr.execute(
                """UPDATE plm_automatedwfaction
                   SET attachment_from_state = %s, attachment_to_state = %s
                   WHERE id = %s""",
                (row[1], row[2], row[0]),
            )
    cr.commit()
    _logger.info("End recovering legacy data")
