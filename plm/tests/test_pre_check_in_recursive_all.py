# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2024 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################
'''
Tests for _preCheckInRecursive_all — correctness and timing baseline.

Run with:
    python odoo-bin --test-tags=odoo_plm_pre_check_in -d <db> --stop-after-init

Two test classes:
    PreCheckInCorrectnessTest  — small assembly (14 docs), functional assertions.
    PreCheckInTimingTest       — large assembly (1000+ docs, 4 levels), timing only.
'''
import time
import logging
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.plm.tests.entity_creator import PlmEntityCreator
from odoo.addons.plm.tests.entity_creator import DUMMY_CONTENT

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _batch_checkout(env, docs, user_id, hostname='test_host', hostpws='test_pws'):
    """Create plm.checkout records for all docs in a single batch INSERT."""
    env['plm.checkout'].sudo().create([
        {
            'userid': user_id,
            'hostname': hostname,
            'hostpws': hostpws,
            'documentid': doc.id,
        }
        for doc in docs
    ])


def _build_tree(env, depth, branching):
    """
    Build a balanced tree assembly using batch DB operations.

    Each 3D node has one 2D drawing linked via LyTree.
    3D nodes are connected parent→child via HiTree.

    Returns (root_3d, all_docs_recordset).

    Example counts (depth=4, branching=5):
        3D nodes : 1 + 5 + 25 + 125 + 625 = 781
        2D nodes : 781
        Total    : 1562 docs
    """
    # --- Step 1: generate tree topology (index-based, no ORM yet) ----------
    # nodes[i] = parent index, or None for root
    nodes = [None]          # root at index 0
    current_level = [0]
    for _ in range(depth):
        next_level = []
        for parent_idx in current_level:
            for _ in range(branching):
                nodes.append(parent_idx)
                next_level.append(len(nodes) - 1)
        current_level = next_level

    n_3d = len(nodes)

    # --- Step 2: batch-create all ir.attachment records --------------------
    vals_list = []
    for i in range(n_3d):
        vals_list.append({
            'datas': DUMMY_CONTENT,
            'name': f'perf_3d_{i}',
            'engineering_code': f'ec_3d_{i}',
            'res_model': 'ir.attachment',
            'res_id': 0,
            'document_type': '3d',
        })
    for i in range(n_3d):
        vals_list.append({
            'datas': DUMMY_CONTENT,
            'name': f'perf_2d_{i}',
            'engineering_code': f'ec_2d_{i}',
            'res_model': 'ir.attachment',
            'res_id': 0,
            'document_type': '2d',
        })

    records = env['ir.attachment'].create(vals_list)
    docs_3d = records[:n_3d]
    docs_2d = records[n_3d:]

    # document_type is a stored compute field driven by file extension from
    # the name.  Our test names have no extension so the compute sets them all
    # to 'other'.  Force the correct type with a bulk write.
    docs_3d.write({'document_type': '3d'})
    docs_2d.write({'document_type': '2d'})

    # --- Step 3: batch-create all ir.attachment.relation links -------------
    link_vals = []
    # HiTree: parent 3D → child 3D
    for i, parent_idx in enumerate(nodes):
        if parent_idx is not None:
            link_vals.append({
                'parent_id': docs_3d[parent_idx].id,
                'child_id': docs_3d[i].id,
                'link_kind': 'HiTree',
            })
    # LyTree: each 3D → its 2D drawing
    for i in range(n_3d):
        link_vals.append({
            'parent_id': docs_3d[i].id,
            'child_id': docs_2d[i].id,
            'link_kind': 'LyTree',
        })

    env['ir.attachment.relation'].create(link_vals)

    return docs_3d[0], docs_3d + docs_2d


# ---------------------------------------------------------------------------
# Correctness tests  (small assembly, 14 docs)
# ---------------------------------------------------------------------------

@tagged('-standard', 'odoo_plm_pre_check_in')
class PreCheckInCorrectnessTest(TransactionCase, PlmEntityCreator):
    """
    Functional correctness tests for _preCheckInRecursive_all.

    Assembly (3D shown; each has one 2D via LyTree):

        root_3d
        ├── l1a_3d
        │   ├── l2a_3d
        │   │   └── l3a_3d
        │   └── l2b_3d
        └── l1b_3d
            └── l2c_3d

    Total: 7 × 3D + 7 × 2D = 14 documents.
    """

    def setUp(self):
        super().setUp()
        def make(name):
            doc3d = self.create_document(f'{name}_3d', doc_type='3d')
            doc2d = self.create_document(f'{name}_2d', doc_type='2d')
            self.create_link_document(doc3d, doc2d, 'LyTree')
            return doc3d, doc2d

        self.root_3d, self.root_2d = make('root')
        self.l1a_3d,  self.l1a_2d  = make('l1a')
        self.l1b_3d,  self.l1b_2d  = make('l1b')
        self.l2a_3d,  self.l2a_2d  = make('l2a')
        self.l2b_3d,  self.l2b_2d  = make('l2b')
        self.l2c_3d,  self.l2c_2d  = make('l2c')
        self.l3a_3d,  self.l3a_2d  = make('l3a')

        self.create_link_document(self.root_3d, self.l1a_3d, 'HiTree')
        self.create_link_document(self.root_3d, self.l1b_3d, 'HiTree')
        self.create_link_document(self.l1a_3d,  self.l2a_3d, 'HiTree')
        self.create_link_document(self.l1a_3d,  self.l2b_3d, 'HiTree')
        self.create_link_document(self.l1b_3d,  self.l2c_3d, 'HiTree')
        self.create_link_document(self.l2a_3d,  self.l3a_3d, 'HiTree')

        self.all_docs = [
            self.root_3d, self.root_2d,
            self.l1a_3d,  self.l1a_2d,
            self.l1b_3d,  self.l1b_2d,
            self.l2a_3d,  self.l2a_2d,
            self.l2b_3d,  self.l2b_2d,
            self.l2c_3d,  self.l2c_2d,
            self.l3a_3d,  self.l3a_2d,
        ]

    def test_all_checked_out_by_me(self):
        """All docs checked out by me → all in to_check_3d / to_check_2d, none in info."""
        _batch_checkout(self.env, self.all_docs, self.env.uid)

        res = self.root_3d._preCheckInRecursive_all(self.root_3d)

        self.assertEqual(len(res['to_check_3d']), 7,
                         f"Expected 7 3D docs, got {len(res['to_check_3d'])}")
        self.assertEqual(len(res['to_check_2d']), 7,
                         f"Expected 7 2D docs, got {len(res['to_check_2d'])}")
        self.assertEqual(len(res['info']), 0,
                         f"Expected 0 info entries, got {len(res['info'])}")

    def test_some_already_checked_in(self):
        """Checked-in docs move from to_check_* to info."""
        _batch_checkout(self.env, self.all_docs, self.env.uid)
        self.l3a_3d._check_in()
        self.l3a_2d._check_in()

        res = self.root_3d._preCheckInRecursive_all(self.root_3d)

        self.assertEqual(len(res['to_check_3d']), 6)
        self.assertEqual(len(res['to_check_2d']), 6)
        self.assertEqual(len(res['info']), 2,
                         f"Expected 2 already-checked-in info entries, got {len(res['info'])}")

    def test_checked_out_by_other_user(self):
        """Docs checked out by another user appear in info, not to_check_*."""
        other_user = self.env.ref('base.default_user')
        my_docs = [d for d in self.all_docs if d not in (self.l3a_3d, self.l3a_2d)]
        _batch_checkout(self.env, my_docs, self.env.uid)
        _batch_checkout(self.env, [self.l3a_3d, self.l3a_2d], other_user.id)

        res = self.root_3d._preCheckInRecursive_all(self.root_3d)

        self.assertEqual(len(res['to_check_3d']), 6)
        self.assertEqual(len(res['to_check_2d']), 6)
        self.assertEqual(len(res['info']), 2)
        info_names = {d['name'] for d in res['info']}
        self.assertIn(self.l3a_3d.name, info_names)
        self.assertIn(self.l3a_2d.name, info_names)

    def test_no_checkouts(self):
        """Nothing checked out → everything in info as already_checkin."""
        res = self.root_3d._preCheckInRecursive_all(self.root_3d)

        self.assertEqual(len(res['to_check_3d']), 0)
        self.assertEqual(len(res['to_check_2d']), 0)
        self.assertEqual(len(res['info']), 14,
                         f"Expected 14 already-checked-in info entries, got {len(res['info'])}")


# ---------------------------------------------------------------------------
# Timing / performance baseline  (large assembly, 4 levels, 1000+ docs)
# ---------------------------------------------------------------------------

@tagged('-standard', 'odoo_plm_pre_check_in')
class PreCheckInTimingTest(TransactionCase):
    """
    Timing baseline for _preCheckInRecursive_all on a large assembly.

    Tree shape: depth=4 levels, branching=5 children per node.
        Level 0 (root):   1  3D  +  1  2D
        Level 1:          5  3D  +  5  2D
        Level 2:         25  3D  + 25  2D
        Level 3:        125  3D  + 125 2D
        Level 4:        625  3D  + 625 2D
        ─────────────────────────────────
        Total:          781  3D  + 781 2D  =  1562 documents

    This test never fails on assertions — its purpose is to emit timing numbers
    to the Odoo log so the baseline can be recorded before any optimisation.
    Read the log lines tagged [preCheckInRecursive_all] and [perf_test].
    """

    DEPTH = 4
    BRANCHING = 5

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._t_setup = time.perf_counter()
        cls.root_3d, cls.all_docs = _build_tree(cls.env, cls.DEPTH, cls.BRANCHING)
        cls._t_setup = time.perf_counter() - cls._t_setup
        n_3d = (cls.BRANCHING ** (cls.DEPTH + 1) - 1) // (cls.BRANCHING - 1)
        _logger.warning(
            '[perf_test] assembly built: depth=%d branching=%d  3d=%d 2d=%d total=%d  setup=%.3fs',
            cls.DEPTH, cls.BRANCHING, n_3d, n_3d, n_3d * 2, cls._t_setup)

    def setUp(self):
        super().setUp()
        # Checkout all documents as the current user before each test
        t0 = time.perf_counter()
        _batch_checkout(self.env, self.all_docs, self.env.uid)
        _logger.warning('[perf_test] checkout batch=%.3fs  docs=%d',
                     time.perf_counter() - t0, len(self.all_docs))

    def test_timing_all_checked_out(self):
        """
        All documents checked out by current user.
        Measures the full _preCheckInRecursive_all wall-clock time.
        The function emits per-helper cumulative timings to the log automatically.
        """
        t0 = time.perf_counter()
        res = self.root_3d._preCheckInRecursive_all(self.root_3d)
        elapsed = time.perf_counter() - t0

        n_to_check = len(res['to_check_3d']) + len(res['to_check_2d'])
        n_info = len(res['info'])
        n_total = n_to_check + n_info
        per_doc = elapsed / n_total if n_total else 0.0

        _logger.warning(
            '[perf_test] all_checked_out: wall=%.3fs  to_check=%d  info=%d  per_doc=%.4fs',
            elapsed, n_to_check, n_info, per_doc)

    def test_timing_half_checked_in(self):
        """
        Half the documents already checked in (simulates a partial check-in scenario).
        Measures how the mix of to_check vs info affects timing.
        """
        # Check in 2D docs only — leaving 3D docs still checked out
        checkin_docs = self.all_docs[len(self.all_docs) // 2:]
        for doc in checkin_docs:
            self.env['plm.checkout'].sudo().search(
                [('documentid', '=', doc.id)]).unlink()

        t0 = time.perf_counter()
        res = self.root_3d._preCheckInRecursive_all(self.root_3d)
        elapsed = time.perf_counter() - t0

        n_to_check = len(res['to_check_3d']) + len(res['to_check_2d'])
        n_info = len(res['info'])
        n_total = n_to_check + n_info
        per_doc = elapsed / n_total if n_total else 0.0

        _logger.warning(
            '[perf_test] half_checked_in: wall=%.3fs  to_check=%d  info=%d  per_doc=%.4fs',
            elapsed, n_to_check, n_info, per_doc)
