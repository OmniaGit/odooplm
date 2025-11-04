import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info("Start recovering legacy data")
    cr.execute("select id,from_state, to_state, apply_to from plm_automatedwfaction")
    for row in cr.fetchall():
        if row[3]=='product.product':
            cr.execute(f"""update 
                               plm_automatedwfaction 
                           set 
                               product_from_state = '{row[1]}',
                               product_to_state = '{row[2]}'
                           where id = {row[0]}
                        """)
        elif row[3]=='ir.attachment':
            cr.execute(f"""update 
                               plm_automatedwfaction 
                           set 
                               attachment_from_state = '{row[1]}',
                               attachment_to_state = '{row[2]}'
                           where id = {row[0]}
                        """)
    cr.commit()
    _logger.info("End recovering legacy data")

