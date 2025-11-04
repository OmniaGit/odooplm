import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info("Start migrationg ild field")
    cr.execute("DELETE FROM ir_model_fields WHERE name IN ('to_state', 'from_state') AND model = 'plm.automatedwfaction';") 
    cr.commit()
    _logger.info("Delete old field done")