# -*- encoding: utf-8 -*-
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

'''
Created on 15 Jun 2016

@author: Daniel Smerghetto
'''

from openerp import models
from openerp import api
from openerp import fields
from openerp import _


class ProductProductExtension(models.Model):
    _inherit = 'product.product'

    @api.multi
    def copy(self, default=None):
        '''
            Set flag to skip translation creation because super copy function makes the trick
        '''
        for prodBrws in self:
            newContext = self.env.context.copy()
            newContext['skip_translations'] = True
            return super(ProductProductExtension, prodBrws.with_context(newContext)).copy(default)

    @api.model
    def create(self, vals):
        '''
            Force create and/or set up description translations
        '''
        productBrws = super(ProductProductExtension, self).create(vals)
        if self.env.context.get('skip_translations', False):
            return productBrws
        if productBrws:
            templateId = productBrws.product_tmpl_id.id
            std_description_id = vals.get('std_description', False)
            ir_translation_obj = self.env['ir.translation']
            if std_description_id:
                self.commonTranslationSetUp(templateId, std_description_id)
                self.commonSpecialDescriptionCompute(vals, productBrws.product_tmpl_id.id, self.env['plm.description'].browse(std_description_id))
            elif 'description' in vals.keys():
                description = vals['description']
                if description:
                    userLang = self.env.context.get('lang', 'en_US')
                    translationObjs = ir_translation_obj.search([('name', '=', 'product.template,description'),
                                                                 ('value', '=', description),
                                                                 ('lang', '=', userLang)],
                                                                limit=1)
                    for ranslationObj in translationObjs:
                        oldDescObjs = ir_translation_obj.search([('res_id', '=', ranslationObj.res_id),
                                                                ('name', '=', ranslationObj.name)])
                        for oldDescObj in oldDescObjs:
                            ir_translation_obj.create({'src': oldDescObj.src,
                                                       'res_id': templateId,
                                                       'name': 'product.template,description',
                                                       'type': 'model',
                                                       'lang': oldDescObj.lang,
                                                       'value': oldDescObj.value})
        return productBrws

    @api.multi
    def write(self, vals):
        '''
            - Set up translations every time description changes
        '''
        ir_translation_obj = self.env['ir.translation']
        for prodBrws in self:
            templateId = prodBrws.product_tmpl_id.id
            if 'std_description' in vals:
                std_description_id = vals.get('std_description', False)
                self.commonTranslationSetUp(templateId, std_description_id)
            if 'description' in vals:
                description = vals.get('description', '')
                if not description:
                    translationObjs = ir_translation_obj.search([('name', '=', 'product.template,description'),
                                                                 ('res_id', '=', templateId)])
                    translationObjs.write({'value': ''})
                    vals['description'] = ' '
            if 'name' in vals.keys():
                translationObjs = ir_translation_obj.search([('name', '=', 'product.template,name'),
                                                             ('res_id', '=', templateId)])
                translationObjs.write({'value': vals['name']})
            self.commonSpecialDescriptionCompute(vals, templateId, prodBrws.std_description)
        return super(ProductProductExtension, self).write(vals)

    def commonSpecialDescriptionCompute(self, vals, templateId, std_description_obj):
        for prodWriteObj in self:
            ir_translation_obj = self.env['ir.translation']
            vals_std_value1 = vals.get('std_value1', False)
            vals_std_value2 = vals.get('std_value2', False)
            vals_std_value3 = vals.get('std_value3', False)
            std_value1 = prodWriteObj.std_value1
            std_value2 = prodWriteObj.std_value2
            std_value3 = prodWriteObj.std_value3
            if vals_std_value1 is not False:
                std_value1 = vals_std_value1
            if vals_std_value2 is not False:
                std_value2 = vals_std_value2
            if vals_std_value3 is not False:
                std_value3 = vals_std_value3
            if std_description_obj and (vals_std_value1 is not False or vals_std_value2 is not False or vals_std_value3 is not False):
                userLang = prodWriteObj.env.context.get('lang', 'en_US')
                for langBrwsObj in self.env['res.lang'].search([]):
                    thisObject = std_description_obj.with_context({'lang': langBrwsObj.code})
                    initVal = thisObject.name
                    if not initVal:
                        initVal = thisObject.description
                    description = prodWriteObj.computeDescription(thisObject, initVal, thisObject.umc1, thisObject.umc2, thisObject.umc3, std_value1, std_value2, std_value3)
                    translationObjs = ir_translation_obj.search([('name', '=', 'product.template,description'),
                                                                 ('res_id', '=', templateId),
                                                                 ('lang', '=', langBrwsObj.code)])
                    if translationObjs:
                        translationObjs.write({'value': description})
                    else:
                        ir_translation_obj.create({
                                                  'src': description,
                                                  'res_id': templateId,
                                                  'name': 'product.template,description',
                                                  'type': 'model',
                                                  'lang': userLang,
                                                  'value': description})

    def commonTranslationSetUp(self, templateId, std_description_id):
        '''
            Set standard description correctly, called from write and create
        '''
        ir_translation_obj = self.env['ir.translation']
        descTransBrwsList = ir_translation_obj.search([('name', '=', 'plm.description,name'),             # field to translate
                                                       ('res_id', '=', std_description_id)])
        if not descTransBrwsList:
            descTransBrwsList = ir_translation_obj.search([('name', '=', 'plm.description,description'),             # field to translate
                                                           ('res_id', '=', std_description_id)])
        for transDescBrws in descTransBrwsList:
            alreadyPresentTranslations = ir_translation_obj.search([('name', '=', 'product.template,description'),
                                                                    ('lang', '=', transDescBrws.lang),
                                                                    ('res_id', '=', templateId)])
            if alreadyPresentTranslations:
                alreadyPresentTranslations.write({'value': transDescBrws.value})
            else:
                ir_translation_obj.create({
                                          'src': transDescBrws.src,
                                          'res_id': templateId,
                                          'name': 'product.template,description',
                                          'type': 'model',
                                          'lang': transDescBrws.lang,
                                          'value': transDescBrws.value})

ProductProductExtension()
