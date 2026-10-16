# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
import base64
import tempfile
import os
from odoo import _, api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    custom_procedure = fields.Binary(string='Client CustomProcedure')
    custom_procedure_fname = fields.Char("CustomProcedure File name")
    custom_read_content = fields.Text('Custom Read Content')

    custom_multicad = fields.Binary(string='Client Multicad')
    custom_multicad_fname = fields.Char("Multicad File name")
    custom_multicad_content = fields.Text('Custom Multicad Content')

    def write(self, vals):
        erase = self.env.context.get('erase_multicad', True)
        erase_custom = self.env.context.get('erase_customprocedure', True)
        if erase and 'custom_multicad_content' in vals:
            self.open_custom_multicad_save(vals)
        if erase_custom and 'custom_read_content' in vals:
            self.open_custommodule_save(vals)
        return super(ResUsers, self).write(vals)

    def open_custommodule_edit(self):
        ctx = self.env.context.copy()
        ctx['erase_customprocedure'] = False
        for groupBrws in self:
            if groupBrws.custom_procedure:
                # the field's value is the file itself on Odoo 20, no longer base64
                fileReadableContent = groupBrws.custom_procedure.content.decode('utf-8', errors='replace')
                if self.custom_read_content:
                    fileReadableContent = ''
                self.with_context({
                    'erase_customprocedure': False
                }).custom_read_content = fileReadableContent

    def open_custom_multicad_edit(self):
        ctx = self.env.context.copy()
        ctx['erase_multicad'] = False
        for groupBrws in self:
            if groupBrws.custom_multicad:
                fileReadableContent = groupBrws.custom_multicad.content.decode('utf-8', errors='replace')
                if self.custom_multicad_content:
                    fileReadableContent = ''
                self.with_context({
                    'erase_multicad': False
                }).custom_multicad_content = fileReadableContent

    def open_custommodule_save(self, vals):
        for groupBrws in self:
            self.commonSave(
                vals,
                'custom_procedure',
                'custom_read_content',
                groupBrws.custom_procedure_fname,
                groupBrws.custom_procedure
            )

    @api.model
    def open_custom_multicad_save(self, vals):
        for groupBrws in self:
            self.commonSave(
                vals,
                'custom_multicad',
                'custom_multicad_content',
                groupBrws.custom_multicad_fname,
                groupBrws.custom_multicad
            )

    @api.model
    def commonSave(self, vals, binary_field, content_field, fname, custom_file):
        # A Binary field takes base64 text on Odoo 20: bytes are refused
        vals[binary_field] = base64.b64encode(vals.get(content_field, '').encode('utf-8')).decode()
        tmpFolder = tempfile.gettempdir()
        if fname and custom_file:
            customFilePath = os.path.join(tmpFolder, fname)
            with open(customFilePath, 'wb') as writeFile:
                writeFile.write(custom_file.content)
        vals[content_field] = ''

    def getCustomProcedure(self):
        """
        The CustomProcedure of the CAD client (called by it over XML-RPC):
        the user's own, else the one of the first of their groups that has
        one; ('', '') when there is none.

        The content goes as base64 text, which the client decodes: XML-RPC
        cannot send an Odoo 20 Binary value. An empty Binary is falsy but is
        not False, so a group is tested for a value, not compared to False.
        """
        CLIENT_FILE_NAME = "CustomProcedure.py"
        user = self.env.user.sudo()
        if user.custom_procedure:
            return user.custom_procedure.to_base64(), CLIENT_FILE_NAME
        logging.info(f"Custom procedure not found for user {user.display_name}")
        for group in user.group_ids:
            if group.custom_procedure:
                logging.info(f"Custom procedure of the group {group.display_name} for user {user.display_name}")
                return group.custom_procedure.to_base64(), CLIENT_FILE_NAME
        logging.warning(f"No user related groups contain custom procedure {user.display_name}")
        return '', ''

    def getCustomMulticad(self):
        """
        The custom Multicad file of the CAD client: the user's own, else the
        one of the first of their groups that has one, with its file name;
        ('', '') when there is none.

        As getCustomProcedure: base64 text, since XML-RPC cannot send an
        Odoo 20 Binary value, and a group tested for a value. The groups are
        group_ids on Odoo 20 (groups_id is gone).
        """
        user = self.env.user.sudo()
        logging.info('Request Multicad file for user %r' % user.id)
        if user.custom_multicad:
            return user.custom_multicad.to_base64(), user.custom_multicad_fname or ''
        for group in user.group_ids:
            if group.custom_multicad:
                logging.info('Got Multicad file from group %r with ID %r' % (group.display_name, group.id))
                return group.custom_multicad.to_base64(), group.custom_multicad_fname or ''
        return '', ''
