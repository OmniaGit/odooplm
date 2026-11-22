# -*- coding: utf-8 -*-
"""One state for every job of the queue, and who asked for it.

- The jobs Odoo converts itself had only Conversion Done and the error text:
  they get the state of the queue (done, error, to do), like the jobs of
  the CAD workstations.
- The requester of the existing jobs is the user who created them.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE plm_convert_stack
           SET cad_agent_state = CASE
                   WHEN conversion_done THEN 'done'
                   WHEN COALESCE(error_string, '') != '' THEN 'error'
                   ELSE 'to_do'
               END
         WHERE cad_agent_state IS NULL
        """
    )
    cr.execute("UPDATE plm_convert_stack SET requester_id = create_uid WHERE requester_id IS NULL")
