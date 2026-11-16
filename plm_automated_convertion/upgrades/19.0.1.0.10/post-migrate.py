# -*- coding: utf-8 -*-
"""One state for every job of the queue (cad_agent_state), and who asked for it.

19.0 kept the state of a job in its own field, state (Draft, Done), which is
replaced by the state of the queue (decided 2026-11-16):

- Done: conversion_done and the state Done; a job with an error: Error; the
  others: To Do. The column cad_agent_state is new here, created with its
  default (To Do) on every row, so every row is set from state.
- The requester of the existing jobs is the user who created them.
- The column state, whose field is gone, is dropped.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'plm_convert_stack' AND column_name = 'state'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            UPDATE plm_convert_stack
               SET conversion_done = (state = 'done'),
                   cad_agent_state = CASE
                       WHEN state = 'done' THEN 'done'
                       WHEN COALESCE(error_string, '') != '' THEN 'error'
                       ELSE 'to_do'
                   END
            """
        )
        cr.execute("ALTER TABLE plm_convert_stack DROP COLUMN state")
    cr.execute("UPDATE plm_convert_stack SET requester_id = create_uid WHERE requester_id IS NULL")
