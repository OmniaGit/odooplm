# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<http://omniasolutions.eu>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime
from dateutil import tz

from book_collector import BookCollector, packDocuments, external_pdf
from odoo.report.interface import report_int
from odoo import _
from odoo.exceptions import UserError
import odoo


def getBottomMessage(user, context):
        to_zone = tz.gettz(context.get('tz', 'Europe/Rome'))
        from_zone = tz.tzutc()
        dt = datetime.now()
        dt = dt.replace(tzinfo=from_zone)
        localDT = dt.astimezone(to_zone)
        localDT = localDT.replace(microsecond=0)
        return "Printed by " + str(user.name) + " : " + str(localDT.ctime())


def commonInfos(cr, uid, ids, context):
    env = odoo.api.Environment(cr, uid, context or {})
    docRepository = env['plm.document']._get_filestore()
    componentType = env['product.product']
    user = env['res.users'].browse(uid)
    msg = getBottomMessage(user, context)
    output = BookCollector(jumpFirst=False,
                           customTest=(False, msg),
                           bottomHeight=10)
    documents = []
    components = componentType.browse(ids)
    return components, documents, docRepository, output, componentType


class component_custom_report(report_int):
    """
        Return a pdf report of each printable document attached to given Part ( level = 0 one level only, level = 1 all levels)
    """
    def create(self, cr, uid, ids, datas, context=None):
        components, documents, docRepository, output, _componentType = commonInfos(cr, uid, ids, context)
        for component in components:
            documents.extend(component.linkeddocuments)
        if len(documents):
            return packDocuments(docRepository, documents, output)
        if context.get("raise_report_warning", True):
            # To avoid error when no PDF is returned
            import StringIO
            from reportlab.pdfgen import canvas
            pdf_string = StringIO.StringIO()
            c = canvas.Canvas(pdf_string)
            c.drawString(20, 20, str('      '))
            c.showPage()
            c.save()
            obj = external_pdf(pdf_string.getvalue())
            obj.render()
            pdf_string.close()
            return (obj.pdf, 'pdf')

component_custom_report('report.product.product.pdf')


class component_one_custom_report(report_int):
    """
        Return a pdf report of each printable document attached to children in a Bom ( level = 0 one level only, level = 1 all levels)
    """

    def create(self, cr, uid, ids, datas, context=None):
        components, documents, docRepository, output, componentType = commonInfos(cr, uid, ids, context)
        children = []
        for component in components:
            documents.extend(component.linkeddocuments)
            idcs = componentType._getChildrenBom(component, 0, 1)
            children = componentType.browse(idcs)
            for child in children:
                documents.extend(child.linkeddocuments)
        if len(documents):
            return packDocuments(docRepository, list(set(documents)), output)
        if context.get("raise_report_warning", True):
            raise UserError(_("No Document found"))

component_one_custom_report('report.one.product.product.pdf')


class component_all_custom_report(report_int):
    """
        Return a pdf report of each printable document attached to children in a Bom ( level = 0 one level only, level = 1 all levels)
    """

    def create(self, cr, uid, ids, datas, context=None):
        components, documents, docRepository, output, componentType = commonInfos(cr, uid, ids, context)
        children = []
        for component in components:
            documents.extend(component.linkeddocuments)
            idcs = componentType._getChildrenBom(component, 1)
            children = componentType.browse(idcs)
            for child in children:
                documents.extend(child.linkeddocuments)
        if len(documents):
            return packDocuments(docRepository,
                                 list(set(documents)),
                                 output)
        if context.get("raise_report_warning", True):
            raise UserError(_("No Document found"))

component_all_custom_report('report.all.product.product.pdf')


class component_custom_report_latest(report_int):
    """
        Return a pdf report of each printable document attached to given Part ( level = 0 one level only, level = 1 all levels)
    """

    def create(self, cr, uid, ids, datas, context={}):
        components, documents, docRepository, output, _componentType = commonInfos(cr, uid, ids, context)
        for component in components:
            for idDoc in component.linkeddocuments:
                if idDoc.state in ['released', 'undermodify']:
                    documents.extend(idDoc)
        if len(documents):
            return packDocuments(docRepository, documents, output)
        if context.get("raise_report_warning", True):
            raise UserError(_("No Document found"))
        return False, False

component_custom_report_latest('report.product.product.pdf.latest')
