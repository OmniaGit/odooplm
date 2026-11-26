# -*- coding: utf-8 -*-
"""The frames and title blocks a group names reach its members' CAD client,
each code at its highest revision (plm.client get_sheet_templates and
get_sheet_template_files, 2026-11-26)."""
import base64

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-standard", "plm_client_sheet_templates")
class SheetTemplates(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env["res.groups"].create({"name": "Sheet templates A"})
        cls.other_group = cls.env["res.groups"].create({"name": "Sheet templates B"})
        cls.user = cls.env["res.users"].create({
            "name": "Sheet template user",
            "login": "sheet_template_user",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, cls.group.id])],
        })
        cls.client = cls.env["plm.client"].with_user(cls.user)

    def document(self, code, revision=0, state="draft", name=None):
        document = self.env["ir.attachment"].create({
            "raw": ("%s %s" % (code, revision)).encode(),
            "name": name or "%s.dwg" % code,
            "engineering_code": code,
            "engineering_revision": revision,
            "is_plm": True,
            "res_model": "ir.attachment",
            "res_id": 0,
            "document_type": "2d",
        })
        document.with_context(check=False).engineering_state = state
        return document

    def test_the_highest_revision_of_the_code_linked(self):
        rev_0 = self.document("ST_FRAME_A3", 0, "released")
        rev_1 = self.document("ST_FRAME_A3", 1)
        self.group.plm_frame_document_ids = [(6, 0, [rev_0.id])]
        rows = self.client.get_sheet_templates()
        self.assertEqual([(rev_1.id, "frame", 1, "ST_FRAME_A3.dwg")],
                         [(r["id"], r["kind"], r["engineering_revision"], r["file_name"]) for r in rows])

    def test_frames_and_title_blocks_apart_sorted_by_name(self):
        frame = self.document("ST_FRAME_B")
        block_z = self.document("ST_TB_Z")
        block_a = self.document("ST_TB_A")
        self.group.plm_frame_document_ids = [(6, 0, [frame.id])]
        self.group.plm_titleblock_document_ids = [(6, 0, [block_z.id, block_a.id])]
        rows = self.client.get_sheet_templates()
        self.assertEqual([("frame", frame.id), ("titleblock", block_a.id), ("titleblock", block_z.id)],
                         [(r["kind"], r["id"]) for r in rows])

    def test_the_groups_of_the_user_together_each_document_once(self):
        shared = self.document("ST_TB_SHARED")
        own = self.document("ST_TB_OWN")
        self.user.group_ids = [(4, self.other_group.id)]
        self.group.plm_titleblock_document_ids = [(6, 0, [shared.id])]
        self.other_group.plm_titleblock_document_ids = [(6, 0, [shared.id, own.id])]
        self.assertEqual({shared.id, own.id}, {r["id"] for r in self.client.get_sheet_templates()})

    def test_an_implied_group_counts(self):
        implied = self.env["res.groups"].create({"name": "Sheet templates implied"})
        self.group.implied_ids = [(4, implied.id)]
        frame = self.document("ST_FRAME_IMPLIED")
        implied.plm_frame_document_ids = [(6, 0, [frame.id])]
        self.assertEqual([frame.id], [r["id"] for r in self.client.get_sheet_templates()])

    def test_a_group_the_user_is_not_in_gives_nothing(self):
        self.other_group.plm_frame_document_ids = [(6, 0, [self.document("ST_FRAME_NOT_MINE").id])]
        self.assertEqual([], self.client.get_sheet_templates())

    def test_the_files_only_of_the_templates_offered(self):
        rev_0 = self.document("ST_TB_FILE", 0, "released")
        rev_1 = self.document("ST_TB_FILE", 1)
        stranger = self.document("ST_TB_STRANGER")
        self.group.plm_titleblock_document_ids = [(6, 0, [rev_0.id])]
        files = self.client.get_sheet_template_files([rev_0.id, rev_1.id, stranger.id])
        self.assertEqual([str(rev_1.id)], list(files))
        self.assertEqual(b"ST_TB_FILE 1", base64.b64decode(files[str(rev_1.id)]))
