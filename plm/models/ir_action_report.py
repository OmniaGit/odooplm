'''
Created on 20 Oct 2017

@author: mboscolo
'''
from odoo import api
from odoo import fields
from odoo import models


class PlmIrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection([('qweb-html', 'HTML'),
                                    ('qweb-pdf', 'PDF'),
                                    ('drawing-pdf', 'DPDF')], required=True, default='qweb-pdf',
                                   help='The type of the report that will be rendered, each one having its own rendering method.'
                                        'HTML means the report will be opened directly in your browser'
                                        'PDF means the report will be rendered using Wkhtmltopdf and downloaded by the user.'
                                        'DPDF used from odooPLM module to render pdf drawings')

    def render_qweb_pdf(self, res_ids=None, data=None):
        if self.report_type == 'drawing-pdf':
            return self.render_drawing_pdf(res_ids, data)
        else:
            return super(PlmIrActionsReport, self).render_qweb_pdf(res_ids, data)

    @api.multi
    def render_drawing_pdf(self, res_ids=None, data=None):
        report_model_name = 'report.%s' % self.report_name
        report_model = self.env.get(report_model_name)
        if report_model is not None:
            data = report_model.get_report_values(res_ids, data=data)
        return data, 'pdf'
