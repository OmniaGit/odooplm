##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2010 OmniaSolutions (<https://www.omniasolutions.website>). All Rights Reserved
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
from odoo import api
from odoo import models


class ReportProductPdf(models.AbstractModel):
    _name = 'report.plm.product_pdf'
    _description = 'Report for producing pdf'

    @api.model
    def _render_qweb_pdf(self, products=None, level=0, checkState=False):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for p_id in products.ids:
            return "%s/plm/get_production_printout/%s/%s/%s" % (base_url,
                                                                p_id,
                                                                level,
                                                                int(checkState))
    @api.model
    def _get_report_values(self, docids, data=None):
        products = self.env['product.product'].browse(docids)
        return {'docs': products,
                'get_content': self._render_qweb_pdf}


class ReportOneLevelProductPdf(ReportProductPdf):
    _name = 'report.plm.one_product_pdf'
    _description = 'Report pdf'


class ReportAllLevelProductPdf(ReportProductPdf):
    _name = 'report.plm.all_product_pdf'
    _description = 'Report pdf'


class ReportProductionProductPdf(ReportProductPdf):
    _name = 'report.plm.product_production_pdf_latest'
    _description = 'Report pdf'


class ReportProductionOneProductPdf(ReportProductPdf):
    _name = 'report.plm.product_production_one_pdf_latest'
    _description = 'Report pdf'


class ReportProductionAllProductPdf(ReportProductPdf):
    _name = 'report.plm.product_production_all_pdf_latest'
    _description = 'Report pdf'
