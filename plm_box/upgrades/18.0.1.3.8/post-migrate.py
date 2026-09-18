import logging

_logger = logging.getLogger(__name__)

MODULE = "plm_box"
SEQUENCE_XMLIDS = (
    "seq_plm_box",
    "seq_doc_name",
)


def migrate(cr, version):
    """Make the PLM sequences global.

    ir.sequence.company_id defaults to env.company, so the sequences declared by
    the module were bound to the company it was installed in, and next_by_code
    returned False in every other company. The XML now declares them with
    company_id False, but those records are noupdate: this brings the databases
    installed before in line. It touches only the sequences the module created,
    and it runs once: a company an administrator sets on them after the upgrade
    is not undone by the next one.
    """
    cr.execute(
        """
        UPDATE ir_sequence
           SET company_id = NULL
          FROM ir_model_data
         WHERE ir_model_data.model = 'ir.sequence'
           AND ir_model_data.res_id = ir_sequence.id
           AND ir_model_data.module = %s
           AND ir_model_data.name IN %s
           AND ir_sequence.company_id IS NOT NULL
        """,
        (MODULE, SEQUENCE_XMLIDS),
    )
    _logger.info("%s: %s sequences made global", MODULE, cr.rowcount)
