# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    conversion_server_ip = fields.Char(string='Server IP')
    conversion_server_protocol = fields.Char(string='Server Protocol')
    conversion_server_port = fields.Char(string='Server Port')


    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter']
        ICP.sudo().set_param(
            'conversion_server_ip',
            self.conversion_server_ip
        )
        ICP.sudo().set_param(
            'conversion_server_protocol',
            self.conversion_server_protocol
        )
        ICP.sudo().set_param(
            'conversion_server_port',
            self.conversion_server_port
        )


    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter']
        res.update({
            'conversion_server_ip': ICP.sudo().get_param(
                'conversion_server_ip'
            ),
            'conversion_server_protocol': ICP.sudo().get_param(
                'conversion_server_protocol'
            ),
            'conversion_server_port': ICP.sudo().get_param(
                'conversion_server_port'
            ),

        })

        return res
