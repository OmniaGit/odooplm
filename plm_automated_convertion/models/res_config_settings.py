# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    conversion_server_ip = fields.Char("Server IP Address")
    conversion_server_protocol = fields.Char("Server Protocol", default="http")
    conversion_server_port = fields.Char("Server Port")



    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()

        res.update({
            'conversion_server_ip': IrConfigParam.get_param('conversion_server_ip', default=''),
            'conversion_server_protocol': IrConfigParam.get_param('conversion_server_protocol', default='http'),
            'conversion_server_port': IrConfigParam.get_param('conversion_server_port', default=''),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()

        IrConfigParam.set_param('conversion_server_ip', self.conversion_server_ip or '')
        IrConfigParam.set_param('conversion_server_protocol', self.conversion_server_protocol or 'http')
        IrConfigParam.set_param('conversion_server_port', self.conversion_server_port or '')
