# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2026 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""Where a PLM document lives, and who may do what with it.

Odoo gives access to an attachment through the record it is attached to: to
read it one must be able to read that record, to write, create or delete it one
must be able to write it. Every PLM document is attached to a ``plm.access``
node, so the nodes are what separates companies and departments.

The nodes form a tree per company: the root is the company's own
(``res.company.plm_access_id``), the children are departments. For each of
read, write, create and unlink a node either names the groups allowed or names
none and inherits its parent's; a root naming none leaves the company open.
The record rules read the ``effective_*`` groups this resolves to.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

PERMISSIONS = ("read", "write", "create", "unlink")


def _groups_field(permission, effective=False):
    prefix = "effective_" if effective else ""
    return fields.Many2many(
        "res.groups",
        "plm_access_%s%s_group_rel" % (prefix, permission),
        "access_id",
        "group_id",
        string="%s%s groups" % ("Effective " if effective else "", permission.title()),
        compute="_compute_effective_groups" if effective else None,
        store=True,
        recursive=effective,
        help=(
            "The groups this node really grants %s to: its own when it names "
            "some, its parent's otherwise. Empty means the whole company."
            % permission
        )
        if effective
        else (
            "The groups allowed to %s the documents of this node and of the "
            "children that name no groups of their own. Leave empty to inherit "
            "from the parent node." % permission
        ),
    )


class PlmAccess(models.Model):
    _name = "plm.access"
    _description = "PLM Access"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "complete_name"

    name = fields.Char("Name", required=True)
    complete_name = fields.Char(
        "Full Name", compute="_compute_complete_name", recursive=True, store=True
    )
    parent_id = fields.Many2one("plm.access", "Parent", index=True, ondelete="restrict")
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("plm.access", "parent_id", "Children")
    company_id = fields.Many2one(
        "res.company",
        "Company",
        compute="_compute_company_id",
        store=True,
        readonly=False,
        recursive=True,
        index=True,
        help="Set on the root node; every node below belongs to the same company.",
    )
    document_count = fields.Integer(compute="_compute_document_count")

    read_group_ids = _groups_field("read")
    write_group_ids = _groups_field("write")
    create_group_ids = _groups_field("create")
    unlink_group_ids = _groups_field("unlink")
    effective_read_group_ids = _groups_field("read", effective=True)
    effective_write_group_ids = _groups_field("write", effective=True)
    effective_create_group_ids = _groups_field("create", effective=True)
    effective_unlink_group_ids = _groups_field("unlink", effective=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for node in self:
            if node.parent_id:
                node.complete_name = "%s / %s" % (node.parent_id.complete_name, node.name)
            else:
                node.complete_name = node.name

    @api.depends("parent_id.company_id")
    def _compute_company_id(self):
        for node in self:
            if node.parent_id:
                node.company_id = node.parent_id.company_id
            else:
                node.company_id = node.company_id

    @api.depends(
        *("%s_group_ids" % permission for permission in PERMISSIONS),
        *("parent_id.effective_%s_group_ids" % permission for permission in PERMISSIONS),
    )
    def _compute_effective_groups(self):
        for node in self:
            for permission in PERMISSIONS:
                own = node["%s_group_ids" % permission]
                inherited = node.parent_id["effective_%s_group_ids" % permission]
                node["effective_%s_group_ids" % permission] = own or inherited

    def _compute_document_count(self):
        counts = dict(
            self.env["ir.attachment"]
            .sudo()
            ._read_group(
                [("plm_access_id", "in", self.ids)], ["plm_access_id"], ["__count"]
            )
        )
        for node in self:
            node.document_count = counts.get(node, 0)

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_("A PLM access node cannot be its own ancestor."))

    @api.constrains("parent_id", "company_id")
    def _check_root_company(self):
        for node in self:
            if not node.company_id:
                raise ValidationError(
                    _("The PLM access node %s must belong to a company.", node.name)
                )
            if not node.parent_id and self.sudo().search_count(
                [
                    ("parent_id", "=", False),
                    ("company_id", "=", node.company_id.id),
                    ("id", "!=", node.id),
                ]
            ):
                raise ValidationError(
                    _(
                        "%s already has its root PLM access node: add this one "
                        "below it.",
                        node.company_id.name,
                    )
                )

    def write(self, vals):
        # Writing on a node is what Odoo requires to write a document attached
        # to it, so every PLM user holds the write access right on the model.
        # Changing the nodes themselves is the PLM administrator's business.
        # The write rule on the nodes names who may write their documents, not
        # who manages the tree: the administrator changes a node through sudo,
        # after the check above.
        if not self.env.su:
            if not self.env.user.has_group("plm.group_plm_admin"):
                raise UserError(_("Only a PLM administrator can change PLM access nodes."))
            self = self.sudo()
        if "parent_id" in vals or "company_id" in vals:
            self._refuse_company_move(vals)
        return super(PlmAccess, self).write(vals)

    def _refuse_company_move(self, vals):
        """A node with documents below it cannot move to another company: the
        documents would change company behind the products they describe."""
        parent = self.browse(vals.get("parent_id")) if vals.get("parent_id") else None
        for node in self:
            if parent is not None:
                company = parent.company_id
            elif "company_id" in vals and not node.parent_id:
                company = self.env["res.company"].browse(vals["company_id"])
            else:
                continue
            if company == node.company_id:
                continue
            subtree = self.sudo().search([("id", "child_of", node.id)])
            if self.env["ir.attachment"].sudo().search_count(
                [("plm_access_id", "in", subtree.ids)], limit=1
            ):
                raise UserError(
                    _(
                        "%s holds documents: it cannot move to another company.",
                        node.complete_name,
                    )
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_root_or_documents(self):
        for node in self:
            if not node.parent_id:
                raise UserError(
                    _("%s is the root PLM access node of its company.", node.name)
                )
        if self.env["ir.attachment"].sudo().search_count(
            [("plm_access_id", "in", self.ids)], limit=1
        ):
            raise UserError(_("A PLM access node holding documents cannot be deleted."))

    def action_open_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Documents"),
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": [("plm_access_id", "=", self.id)],
        }

    @api.model
    def _ensure_company_roots(self):
        """Give every company its root node. The one the module always shipped,
        plm_basic_access_model, becomes the root of the main company. Run at
        every update of the module, so companies created while it was not
        installed get theirs too."""
        basic = self.env.ref("plm.plm_basic_access_model", raise_if_not_found=False)
        main_company = self.env.ref("base.main_company", raise_if_not_found=False)
        companies = self.env["res.company"].sudo().with_context(active_test=False).search([])
        for company in companies:
            if company.plm_access_id:
                continue
            if (
                basic
                and not basic.parent_id
                and (
                    basic.company_id == company
                    or (not basic.company_id and company == main_company)
                )
            ):
                if not basic.company_id:
                    basic.sudo().write({"company_id": company.id})
                company.plm_access_id = basic
            else:
                company._create_plm_access_root()
