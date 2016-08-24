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

from types import *
import logging
from openerp        import models, fields, api, SUPERUSER_ID, _, osv
_logger         =   logging.getLogger(__name__)
# Customized Automation to standardize and normalize descriptions and characteristics.
# It will allow to insert unit of measure (or label) and values, so to allow search on parts
# and it will build standardized description and labels and values to compose part description.

class plm_description(models.Model):
    _name = "plm.description"
    _description = "PLM Descriptions"

    name            = fields.Char(_('Note to Description'), size=128)
    description     = fields.Char(_('Standard Description'), size=128)
    description_en  = fields.Char(_('Description English'), size=128)
    umc1            = fields.Char(_('UM / Feature 1'), size=32,  help=_("Allow to specify a unit measure or a label for the feature."))
    fmt1            = fields.Char(_('Format Feature 1'), size=32, help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    umc2            = fields.Char(_('UM / Feature 2'), size=32, help=_("Allow to specify a unit measure or a label for the feature."))
    fmt2            = fields.Char(_('Format Feature 2'), size=32, help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    umc3            = fields.Char(_('UM / Feature 3'), size=32, help=_("Allow to specify a unit measure or a label for the feature."))
    fmt3            = fields.Char(_('Format Feature 3'), size=32, help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    fmtend          = fields.Char(_('Format Feature Composed'), size=32, help=_("Allow to represent a normalized composition of technical features : %s%s allows to build chained values."))
    unitab          = fields.Char(_('Normative Rule'), size=32, help=_("Specify normative rule (UNI, ISO, DIN...). It will be queued to build the product description."))
    sequence        = fields.Integer(_('Sequence'), help=_("Assign the sequence order when displaying a list of product categories."))

    _defaults = {
        'description': lambda *a: False,
        'fmt1': lambda *a: False,
        'fmt2': lambda *a: False,
        'fmt3': lambda *a: False,
        'fmtend': lambda *a: False,
        'unitab': lambda *a: False,
    }
#
#    Meanings and usage
#
#    umc    : field containing a string to express unit of measure of a characteristic.
#    fmt    : field describing composition of umc with its value (when inserted in plm.compoent form)
#    fmtend : field describing composition of umcs to compose a normalized description.
#
#    Sample :
#
#name,description,description_en,umc1,fmt1,umc2,fmt2,fmtend
#Albero liscio , ALBERO, SHAFT , d. , %s %s , Lungh. , %s %s , %s x %s , 
#Vite testa esagona interamente filettata, VITE,  , M , %s%s , L. , %s , %sx%s , UNI 5739
#
# They will be composed like :
#    ALBERO d. 10 x L. 200
#    VITE M10x55 UNI 5739


plm_description()

class plm_component(models.Model):
    _inherit = 'product.product'

    std_description     =   fields.Many2one('plm.description',_('Standard Description'), required=False, change_default=True, help=_("Select standard description for current product."))
    std_umc1            =   fields.Char(_('UM / Feature 1'), size=32, help=_("Allow to specifiy a unit measure for the first feature."))
    std_value1          =   fields.Float(_('Value 1'), help=_("Assign value to the first characteristic."))
    std_umc2            =   fields.Char(_('UM / Feature 2'), size=32, help=_("Allow to specifiy a unit measure for the second feature."))
    std_value2          =   fields.Float(_('Value 2'), help=_("Assign value to the second characteristic."))
    std_umc3            =   fields.Char(_('UM / Feature 3'), size=32, help=_("Allow to specifiy a unit measure for the third feature."))
    std_value3          =   fields.Float(_('Value 3'), help=_("Assign value to the second characteristic."))

    # Don't overload std_umc1, std_umc2, std_umc3 setting them related to std_description because odoo try to set value
    # of related fields and integration users doesn't have write permissions in std_description. The result is that
    # integration users can't create products if in changed values there is std_description

    _defaults = {
        'std_description': lambda *a: False,
        'std_umc1': lambda *a: False,
        'std_value1': lambda *a: False,
        'std_umc2': lambda *a: False,
        'std_value2': lambda *a: False,
        'std_umc3': lambda *a: False,
        'std_value3': lambda *a: False,
    }
#   Internal methods
    def _packfinalvalues(self,fmt,value=False,value2=False,value3=False):
        """
            Pack a string formatting it like specified in fmt
            mixing both label and value or only label.
        """
        retvalue=''
        
        if value3:
            if (type(value3) is FloatType):
                svalue3="%g" %value3
            else:
                svalue3=value3
        else:
            svalue3=''

        if value2:
            if (type(value2) is FloatType):
                svalue2="%g" %value2
            else:
                svalue2=value2
        else:
            svalue2=''

        if value:
            if (type(value) is FloatType):
                svalue="%g" %value
            else:
                svalue=value
        else:
            svalue=''

        if svalue or svalue2 or svalue3:
            cnt=fmt.count('%s')
            if cnt == 3:
                retvalue = fmt %(svalue, svalue2, svalue3)
            if cnt == 2:
                retvalue = fmt %(svalue, svalue2)
            elif cnt == 1:
                retvalue = fmt %(svalue)
        return retvalue

    def _packvalues(self,fmt,label=False,value=False):
        """
            Pack a string formatting it like specified in fmt
            mixing both label and value or only label.
        """
        retvalue=''
        
        if value:
            if (type(value) is FloatType):
                svalue="%g" %value
            else:
                svalue=value
        else:
            svalue=''

        if label:
            if (type(label) is FloatType):
                slabel="%g" %label
            else:
                slabel=label
        else:
            slabel=''

        if svalue:
            cnt=fmt.count('%s')

            if cnt == 2:
                retvalue = fmt %(slabel, svalue)
            elif cnt == 1:
                retvalue = fmt %(svalue)
        return retvalue

##  Customized Automations
    def on_change_stddesc(self, cr, uid, _id, std_description=False, context={}):
        values = {
                  'description': False,
                  'std_umc1': False,
                  'std_value1': False,
                  'std_umc2': False,
                  'std_value2': False,
                  'std_umc3': False,
                  'std_value3': False}
        if std_description:
            thisDescription = self.pool.get('plm.description')
            thisObject = thisDescription.browse(cr, uid, std_description, context)
            if thisObject.description:
                values['description'] = thisObject.description
                if thisObject.umc1:
                    values['std_umc1'] = thisObject.umc1
                if thisObject.umc2:
                    values['std_umc2'] = thisObject.umc2
                if thisObject.umc3:
                    values['std_umc3'] = thisObject.umc3
                if thisObject.unitab:
                    values['description'] = values['description'] + " " + thisObject.unitab
        return {'value': values}

    def on_change_stdvalue(self, cr, uid, _id, std_description=False, std_umc1=False, std_value1=False,\
                           std_umc2=False, std_value2=False, std_umc3=False, std_value3=False, context={}):
        if std_description:
            thisDescription = self.pool.get('plm.description')
            thisObject = thisDescription.browse(cr, uid, std_description, context)
            if thisObject.description:
                description = self.computeDescription(thisObject, thisObject.description, std_umc1, std_umc2, std_umc3, std_value1, std_value2, std_value3)
                return {'value': {'description': description}}
        return {}
    
    def computeDescription(self, thisObject, initialVal, std_umc1, std_umc2, std_umc3, std_value1, std_value2, std_value3):
        description1 = False
        description2 = False
        description3 = False
        description = initialVal
        if thisObject.fmtend:
            if std_umc1 and std_value1:
                description1 = self._packvalues(thisObject.fmt1, std_umc1, std_value1)
            if std_umc2 and std_value2:
                description2 = self._packvalues(thisObject.fmt2, std_umc2, std_value2)
            if std_umc3 and std_value3:
                description3 = self._packvalues(thisObject.fmt3, std_umc3, std_value3)
            description = description + " " + self._packfinalvalues(thisObject.fmtend, description1, description2, description3)
        else:
            if std_umc1 and std_value1:
                description = description + " " + self._packvalues(thisObject.fmt1, std_umc1, std_value1)
            if std_umc2 and std_value2:
                description = description + " " + self._packvalues(thisObject.fmt2, std_umc2, std_value2)
            if std_umc3 and std_value3:
                description = description + " " + self._packvalues(thisObject.fmt3, std_umc3, std_value3)
        if thisObject.unitab:
            description = description + " " + thisObject.unitab
        return description
        
##  Customized Automations
plm_component()

