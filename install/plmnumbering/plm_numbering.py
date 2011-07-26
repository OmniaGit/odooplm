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

from osv import osv, fields
from tools.translate import _

##              Tomorrow Technology customizations

class plm_number1(osv.osv):
    _name = "plm.number1"
    _description = "PLM Number1"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True, translate=True),
                'description': fields.char('Description', size=128, required=True, translate=True),
                'category': fields.integer('Category'),
                'auto_code': fields.char('Code Part', size=64, required=True, translate=True),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Part Number has to be unique !'),
    ]
plm_number1()

class plm_number2(osv.osv):
    _name = "plm.number2"
    _description = "PLM Number2"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True, translate=True),
                'description': fields.char('Description', size=128),
                'auto_code': fields.char('Code Part', size=64),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
#    _sql_constraints = [
#        ('name_uniq', 'unique(name)', 'Part Number has to be unique !'),
#    ]
plm_number2()

class plm_number3(osv.osv):
    _name = "plm.number3"
    _description = "PLM Number3"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True, translate=True),
                'description': fields.char('Description', size=128, required=True, translate=True),
                'auto_code': fields.char('Code Part', size=64, required=True, translate=True),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Part Number has to be unique !'),
    ]
plm_number3()

class plm_number4(osv.osv):
    _name = "plm.number4"
    _description = "PLM Number4"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True, translate=True),
                'description': fields.char('Description', size=128),
                'auto_code': fields.char('Code Part', size=64, required=True),
                'comp_type': fields.char('Component Type', size=64, required=True),
    }
    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
        'comp_type': lambda *a: 'p',
    }
    _sql_constraints = [
        ('auto_code_uniq', 'unique(auto_code,comp_type)', 'Code Part & Component Type have to be unique !'),
    ]
plm_number4()

class plm_number5(osv.osv):
    _name = "plm.number5"
    _description = "PLM Number5"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True, translate=True),
                'description': fields.char('Description', size=128, required=True, translate=True),
                'auto_code': fields.char('Code Part', size=64, required=True, translate=True),
                'auto_codeid': fields.integer('Code Part ID'),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Part Number has to be unique !'),
    ]
plm_number5()

class plm_number6(osv.osv):
    _name = "plm.number6"
    _description = "PLM Number6"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True, translate=True),
                'description': fields.char('Description', size=128, required=True, translate=True),
                'auto_code': fields.char('Code Part', size=64, required=True),
                'auto_codeid': fields.integer('Code Part ID', required=True),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
#    _sql_constraints = [
#        ('name_uniq', 'unique(name)', 'Part Number has to be unique !'),
#    ]
plm_number6()

class plm_number7(osv.osv):
    _name = "plm.number7"
    _description = "PLM Number7"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True, translate=True),
                'description': fields.char('Description', size=128),
                'auto_code': fields.char('Code Part', size=64, required=True),
                'category': fields.integer('Category'),
#                'auto_codeid': fields.integer('Code Part ID', required=True),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
    _sql_constraints = [
        ('auto_code_uniq', 'unique(auto_code)', 'Code Part has to be unique !'),
    ]
plm_number7()

class plm_number8(osv.osv):
    _name = "plm.number8"
    _description = "PLM Number8"
    _columns = {
                'name': fields.char('Part Number', size=64, required=True),
                'description': fields.char('Description', size=128),
                'auto_code': fields.char('Code Part', size=64),
#                'auto_codeid': fields.integer('Code Part ID', required=True),
    }
#    _defaults = {
#        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'plm.material'),
#    }
#    _sql_constraints = [
#        ('name_uniq', 'unique(name)', 'Part Number has to be unique !'),
#    ]
plm_number8()

##              Tomorrow Technology customizations
