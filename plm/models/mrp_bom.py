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

"""
Created on 25 Aug 2016

@author: Daniel Smerghetto
"""
import logging
import sys
import odoo.addons.decimal_precision as dp
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.osv.expression import AND
import copy


class MrpBomExtension(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

    def _father_compute(self, name='', arg={}):
        """ Gets father bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        bom_type = ''
        bom_line_obj_type = self.env['mrp.bom.line']
        for bom_obj in self:
            result = []
            bom_type = bom_obj.type
            if bom_type == '':
                bom_children_lines = bom_line_obj_type.search([('product_id', '=', bom_obj.product_id.id)])
            else:
                bom_children_lines = bom_line_obj_type.search([
                    ('product_id', '=', bom_obj.product_id.id),
                    ('type', '=', bom_type)
                ])
            for bom_line_brws in bom_children_lines:
                if bom_line_brws.bom_id.id:
                    if not (bom_line_brws.bom_id.id in result):
                        result.extend([bom_line_brws.bom_id.id])
            bom_obj.father_complete_ids = self.env['mrp.bom'].browse(list(set(result)))

    state = fields.Selection(related="product_tmpl_id.state",
                             string=_("Status"),
                             help=_("The status of the product in its LifeCycle."),
                             store=False)
    description = fields.Char(related="product_tmpl_id.name",
                              string=_("Description"),
                              store=False)
    father_complete_ids = fields.Many2many('mrp.bom',
                                           compute=_father_compute,
                                           string=_("BoM Hierarchy"),
                                           store=False)
    create_date = fields.Datetime(_('Creation Date'),
                                  readonly=True)
    source_id = fields.Many2one('ir.attachment',
                                'engineering_document_name',
                                ondelete='no action',
                                readonly=True,
                                index=True,
                                help=_('This is the document object that declares this BoM.'))
    type = fields.Selection(selection_add=[('normal', _('Normal BoM'))], required=True)
    weight_net = fields.Float('Weight',
                              digits='Stock Weight',
                              help=_("The BoM net weight in Kg."),
                              default=0.0)

    engineering_revision = fields.Integer(related="product_tmpl_id.engineering_revision",
                                          string=_("Revision"),
                                          help=_("The revision of the product."),
                                          store=True)

    bom_revision_count = fields.Integer(related='product_tmpl_id.revision_count')
    
    att_count = fields.Integer(compute='attch_count')
    
    def attch_count(self):
        for bom in self:
            doc_ids = bom.get_related_attachments()
            bom.att_count = len(doc_ids)

    def get_related_attachments(self):
        for bom in self:
            domain = [
                '|',
                '&', ('res_model', '=', 'product.product'), ('res_id', '=', bom.product_id.id),
                '&', ('res_model', '=', 'product.template'), ('res_id', '=', bom.product_id.product_tmpl_id.id)]
            sudo_att = self.env['ir.attachment'].sudo()
            out_att = sudo_att.search(domain)
            out_att += bom.product_id.linkeddocuments
            return out_att
        return self.env['ir.attachment']

    def open_attachments(self):
        out_att  = self.get_related_attachments()
        return {
            'name': _('Attachments'),
            'domain': [('id', 'in', out_att.ids)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'views': [
                (self.env.ref('plm.document_kanban_view').id, 'kanban'),
                (self.env.ref('plm.view_attachment_form_plm_hinerit').id, 'form'),
                (self.env.ref('plm.ir_attachment_tree').id, 'tree'),
                ],
            'help': _('''<p class="o_view_nocontent_smiling_face">
                        Upload files to your product
                    </p><p>
                        Use this feature to store any files, like drawings or specifications.
                    </p>'''),
            'limit': 80,
        }

    @api.model
    def _get_in_bom(self, pid, sid=False, bom_types=[]):
        bom_l_type = self.env['mrp.bom.line']
        if not bom_types:
            bom_line_brws_list = bom_l_type.search([
                ('product_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')
            ])
            if not bom_line_brws_list:
                bom_line_brws_list = bom_l_type.search([
                    ('product_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')
                ])
                if not bom_line_brws_list:
                    bom_line_brws_list = bom_l_type.search([('product_id', '=', pid), ('type', '=', 'normal')])
        else:
            bl_filter = [('product_id', '=', pid), ('type', 'in', bom_types)]
            if sid:
                bl_filter.append(('source_id', '=', sid))
            bom_line_brws_list = bom_l_type.search(bl_filter)
        return bom_line_brws_list

    @api.model
    def _get_bom(self, pid, sid=False):
        if sid is None:
            sid = False
        bom_brws_list = self.search([('product_tmpl_id', '=', pid), ('source_id', '=', sid), ('type', '=', 'normal')])
        if not bom_brws_list:
            bom_brws_list = self.search([
                ('product_tmpl_id', '=', pid), ('source_id', '=', False), ('type', '=', 'normal')
            ])
            if not bom_brws_list:
                bom_brws_list = self.search([('product_tmpl_id', '=', pid), ('type', '=', 'normal')])
        return bom_brws_list

    def get_list_ids_from_structure(self, structure):
        """
            Convert from [id1,[[id2,[]]]] to [id1,id2]
        """
        out_list = []

        if isinstance(structure, (list, tuple)) and len(structure) == 2:
            if structure[0]:
                out_list.append(structure[0])
            for item in structure[1]:
                out_list.extend(self.get_list_ids_from_structure(item))
        return list(set(out_list))

    @api.model
    def _get_pack_datas(self, rel_datas):
        prt_datas = {}
        tmp_ids = self.get_list_ids_from_structure(rel_datas)
        if len(tmp_ids) < 1:
            return prt_datas
        comp_type = self.env['product.product']
        tmp_datas = comp_type.browse(tmp_ids).read([])
        for tmp_data in tmp_datas:
            for key_data in tmp_data.keys():
                if tmp_data[key_data] is None:
                    del tmp_data[key_data]
            prt_datas[str(tmp_data['id'])] = tmp_data
        return prt_datas

    @api.model
    def _get_pack_rel_datas(self, rel_datas, prt_datas):
        rel_ids = {}
        relation_datas = {}
        tmp_ids = self.get_list_ids_from_structure(rel_datas)
        if len(tmp_ids) < 1:
            return prt_datas
        for key_data in prt_datas.keys():
            tmp_data = prt_datas[key_data]
            if len(tmp_data['bom_ids']) > 0:
                rel_ids[key_data] = tmp_data['bom_ids'][0]

        if len(rel_ids) < 1:
            return relation_datas
        for key_data in rel_ids.keys():
            relation_datas[key_data] = self.browse(rel_ids[key_data]).read()[0]
        return relation_datas

    @api.model
    def get_where_used(self, res_ids):
        """
            Return a list of all fathers of a Part (all levels)
        """
        rel_datas = []
        if len(res_ids) < 1:
            return None
        sid = False
        if len(res_ids) > 1:
            sid = res_ids[1]
        oid = res_ids[0]
        rel_datas.append(oid)
        rel_datas.append(self._implode_bom(self._get_in_bom(oid, sid)))
        prt_datas = self._get_pack_datas(rel_datas)
        return rel_datas, prt_datas, self._get_pack_rel_datas(rel_datas, prt_datas)

    def where_used_header(self, mpr_bom_line_id):
        """
        over-loadable function in order to customise the where used bom
        :mpr_bom_line_id mrp_bom_line browse object
        """
        product_id = mpr_bom_line_id.product_id
        out = {'bom_type': mpr_bom_line_id.type,
               'bom_qty': mpr_bom_line_id.product_qty,
               'bom_line_id': mpr_bom_line_id.id,
               'bom_id': mpr_bom_line_id.bom_id.id}
        out.update(self.where_used_header_p(product_id))
        return out

    def where_used_header_p(self, product_id):
        """
        over-loadable function in order to customise the where used bom
        :product_id mrp_bom_line browse object
        """
        return {'name': product_id.name,
                'product_id': product_id.id,
                'label_product_id': "c" + str(product_id.id),
                'part_number': product_id.engineering_code,
                'part_revision': product_id.engineering_revision,
                'part_description': product_id.name}

    @api.model
    def get_where_used_structure(self, filter_bom_type=''):
        out = []
        for product in self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)]):
            bom_line_filter = [('product_id', '=', product.id)]
            if filter_bom_type:
                bom_line_filter.append(('type', '=', filter_bom_type))
            parent_lines = self.env['mrp.bom.line'].search(bom_line_filter)
            if parent_lines:
                for parent_line in parent_lines:
                    row = self.where_used_header(parent_line)
                    if not filter_bom_type:
                        children = parent_line.bom_id.get_where_used_structure(filter_bom_type)
                        out.append((row, children))
                    else:
                        if parent_line.bom_id.type == filter_bom_type:
                            children = parent_line.bom_id.get_where_used_structure(filter_bom_type)
                            out.append((row, children))
            else:
                row = {'bom_type': self.type}
                row.update(self.where_used_header_p(product))
                out.append((row, ()))
        return out

    @api.model
    def get_explode(self, values=[]):
        """
            Returns a list of all children in a Bom (all levels)
        """
        obj_id, _source_id, last_rev = values
        # get all ids of the children product in structured way like [[id,child_ids]]
        rel_datas = [obj_id, self._explode_bom(self._get_bom(obj_id), False, last_rev)]
        prt_datas = self._get_pack_datas(rel_datas)
        return rel_datas, prt_datas, self._get_pack_rel_datas(rel_datas, prt_datas)

    @api.model
    def _explode_bom(self, bids, check=True, last_rev=False):
        """
            Explodes a bom entity  ( check=False : all levels, check=True : one level )
        """
        output = []
        _packed = []
        for bid in bids:
            for bom_line in bid.bom_line_ids:
                if check and (bom_line.product_id.id in _packed):
                    continue
                tmpl_id = bom_line.product_id.product_tmpl_id.id
                prod_id = bom_line.product_id.id
                if last_rev:
                    newer_comp_brws = self.get_last_comp_id(prod_id)
                    if newer_comp_brws:
                        prod_id = newer_comp_brws.id
                        tmpl_id = newer_comp_brws.product_tmpl_id.id
                inner_ids = self._explode_bom(self._get_bom(tmpl_id), check)
                _packed.append(prod_id)
                output.append([prod_id, inner_ids])
        return output

    
    def get_last_comp_id(self, comp_id):
        prod_prod_obj = self.env['product.product']
        comp_brws = prod_prod_obj.browse(comp_id)
        if comp_brws:
            prod_brws_list = prod_prod_obj.search(
                [('engineering_code', '=', comp_brws.engineering_code)],
                order='engineering_revision DESC'
            )
            for prod_brws in prod_brws_list:
                return prod_brws
        return False

    @api.model
    def get_tmplt_id_from_product_id(self, product_id=False):
        if not product_id:
            return False
        tmpl_dict_list = self.env['product.product'].browse(product_id).read(['product_tmpl_id'])
        # tmpl_dict = {'product_tmpl_id': (tmpl_id, u'name'), 'id': product_product_id}
        for tmpl_dict in tmpl_dict_list:
            tmpl_tuple = tmpl_dict.get('product_tmpl_id', {})
            if len(tmpl_tuple) == 2:
                return tmpl_tuple[0]
        return False

    @api.model
    def GetExploseSum(self, values=[]):
        """
            Return a list of all children in a Bom taken once (all levels)
        """
        comp_id, _source_id, latest_flag = values
        prod_tmpl_id = self.get_tmplt_id_from_product_id(comp_id)
        bom_id = self._get_bom(prod_tmpl_id)
        explosed_bom_ids = self._explode_bom(bom_id, True, latest_flag)
        rel_datas = [comp_id, explosed_bom_ids]
        prt_datas = self._get_pack_datas(rel_datas)
        return rel_datas, prt_datas, self._get_pack_rel_datas(rel_datas, prt_datas)

    @api.model
    def _implode_bom(self, bom_line_objs, source_id=False, bom_types=[]):
        """
            Execute implosion for a a bom object
        """
        _packed=[]
        def get_product_id(bom_local_obj):
            out_prod = False
            prod_id = bom_local_obj.product_id.id
            if not prod_id:
                trmpl_brws = bom_local_obj.product_tmpl_id
                if trmpl_brws:
                    for variant_brws in trmpl_brws.product_variant_ids:
                        out_prod = variant_brws.id
            else:
                out_prod = prod_id
            return out_prod

        pids = []
        for bom_line_obj in bom_line_objs:
            if not bom_line_obj.bom_id:
                continue
            bom_obj = bom_line_obj.bom_id
            parent_bom_id = bom_obj.id
            if parent_bom_id in _packed:
                continue
            _packed.append(parent_bom_id)
            bom_fth_obj = bom_obj.with_context({})
            prod_from_bom = get_product_id(bom_fth_obj)
            bom_line_from_prod = self._get_in_bom(prod_from_bom, source_id, bom_types)
            inner_ids = self._implode_bom(bom_line_from_prod)
            prod_id = bom_fth_obj.product_id.id
            if not prod_id:
                prod_brws_ids = bom_fth_obj.product_tmpl_id.product_variant_ids
                if len(prod_brws_ids) == 1:
                    prod_id = prod_brws_ids[0].id
                else:
                    logging.error(
                        '[_implode_bom] Unable to compute product id, more than one product found: {0}'.format(
                            prod_brws_ids)
                    )
            pids.append((prod_id, inner_ids))
        return pids

    @api.model
    def GetWhereUsedSum(self, res_ids):
        """
            Return a list of all fathers of a Part (all levels)
        """
        rel_datas = []
        if len(res_ids) < 1:
            return None
        sid = False
        if len(res_ids) > 1:
            sid = res_ids[1]
        oid = res_ids[0]
        rel_datas.append(oid)
        bom_line_brws_list = self._get_in_bom(oid, sid)
        rel_datas.append(self._implode_bom(bom_line_brws_list))
        prt_datas = self._get_pack_datas(rel_datas)
        return rel_datas, prt_datas, self._get_pack_rel_datas(rel_datas, prt_datas)

    
    def get_exploded_bom(self, level=0, curr_level=0):
        """
            Return a list of all children in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        result = []
        if level == 0 and curr_level > 1:
            return result
        for bom_id in self:
            for bom in bom_id.bom_line_ids:
                children = self.get_exploded_bom([bom.id], level, curr_level + 1)
                result.extend(children)
            if len(str(bom_id.bom_id)) > 0:
                result.append(bom_id.id)
        return result

    @api.model
    def SaveStructure(self, relations, level=0, curr_level=0, kind_bom='normal'):
        """
            Save EBom relations
        """
        t_bom_line = self.env['mrp.bom.line']
        t_product_product = self.env['product.product']
        eco_module_installed = self.env.get('mrp.eco', None)

        evaluated_boms = {}
        alreadyCreated = []

        def clean_old_eng_bom_lines(relations):

            for _parent_name, product_product_parent_id, _child_name, product_product_child_id, source_id, _rel_args in relations:
                check_level(product_product_parent_id, [source_id], product_product_child_id)

        def check_level(product_product_parent_id, source_ids, product_product_child_id):
            logging.info('parent_id: {0}, source: {1}, child_id: {2}'.format(
                product_product_parent_id,
                source_ids,
                product_product_child_id
            ))
            evaluated = []
            if product_product_parent_id is None or source_ids is None:
                return False
            to_check = (product_product_parent_id, source_ids, product_product_child_id)
            if to_check in evaluated:
                return
            obj_part = t_product_product.with_context({}).browse(product_product_parent_id)
            bom_brws_list = self.search([
                "|",
                ('product_id', '=', product_product_parent_id),
                ('product_tmpl_id', '=', obj_part.product_tmpl_id.id),
                ('source_id', 'in', source_ids)
            ])
            bom_line_brws_list = t_bom_line.search([
                ('bom_id', 'in', bom_brws_list.ids),
                ('source_id', 'in', source_ids)
            ])
            for bom_line_brws in bom_line_brws_list:
                logging.info('Line: {0} product {1}'.format(bom_line_brws.id, bom_line_brws.product_id.id))
                check_level(bom_line_brws.product_id.id, bom_line_brws.product_id.linkeddocuments.ids, False)
            bom_line_brws_list.unlink()
            for bom_brws in bom_brws_list:
                evaluated_boms[bom_brws.id] = bom_brws
            evaluated.append(to_check)
            return False

        def to_compute(parent_name, relations, kind_bom='normal'):
            """
                Processes relations
            """
            bom_id = False
            nex_relation = []

            def divide_by_parent(element):
                if element[0] == parent_name:
                    return True
                nex_relation.append(element)

            sub_relations = list(filter(divide_by_parent, relations))
            if len(sub_relations) < 1:  # no relation to save
                return
            parent_name, parent_id, _child_name, _child_id, source_id, _rel_args = sub_relations[0]
            existing_boms = self.search([
                ('product_id', '=', parent_id),
                ('source_id', '=', source_id),
                ('active', '=', True)
            ])
            if existing_boms:
                new_bom_brws = existing_boms[0]
                parent_vals = get_parent_vals(parent_name, parent_id, source_id, bom_type=new_bom_brws.type)
                new_bom_brws.write(parent_vals)
                save_children_boms(sub_relations, new_bom_brws.id, nex_relation, new_bom_brws.type)
                if eco_module_installed is not None:
                    for eco_brws in self.env['mrp.eco'].search([('bom_id', '=', new_bom_brws.id)]):
                        eco_brws._compute_bom_change_ids()
            elif not existing_boms:
                bom_id = save_parent(parent_name, parent_id, source_id, kind_bom)
                save_children_boms(sub_relations, bom_id, nex_relation, kind_bom)

            return bom_id

        def save_children_boms(sub_relations, bom_id, next_relation, kindBom):
            for parentName, parentID, childName, childID, sourceID, relArgs in sub_relations:
                if parentName == childName:
                    logging.error('toCompute : Father (%s) refers to himself' % (str(parentName)))
                    raise Exception(_('saveChild.toCompute : Father "%s" refers to himself' % (str(parentName))))
                save_child(childName, childID, sourceID, bom_id, args=relArgs)
                if (parentID, childID) not in alreadyCreated:
                    to_compute(childName, next_relation, kindBom)
                    alreadyCreated.append((parentID, childID))
            self.rebase_product_weight(bom_id, self.browse(bom_id).rebase_bom_weight())

        def repair_qty(value):
            """
            from CAD application some time some value are string with strange value
            so we need to fix it in some way
            """
            if not isinstance(value, (float, int)) or (value < 1e-6):
                return 1.0
            return float(value)

        def check_cloned_from(product_id, bom_type):
            prod_env = self.env['product.product']
            prod_brws = prod_env.browse(product_id)
            if prod_brws.source_product:
                for bom_brws in prod_brws.source_product.bom_ids:
                    if bom_brws.source_id:
                        return bom_brws.type, bom_brws.routing_id.id
            return bom_type, False

        def get_parent_vals(parent_name, part_id, source_id, args=None, bom_type='normal'):
            """
                Saves the relation ( parent side in mrp.bom )
            """
            res = {}
            obj_part = t_product_product.with_context({}).browse(part_id)
            res['product_tmpl_id'] = obj_part.product_tmpl_id.id
            res['product_id'] = part_id
            res['source_id'] = source_id
            res['type'], res['routing_id'] = check_cloned_from(part_id, bom_type=bom_type)
            return res

        def save_parent(name, part_id, source_id, kind_bom='normal'):
            """
            Create o retrieve parent bom object
            :return: id of the bom retrieved / created
            """
            try:
                vals = get_parent_vals(name, part_id, source_id, bom_type=kind_bom)
                return self.create(vals).id
            except Exception as ex:
                logging.error(
                    "save_parent :  unable to create a relation for part: ({0}) with source: ({1})  exception: {2}".format(
                        name, source_id, ex)
                )
                raise AttributeError(
                    _("save_parent :  unable to create a relation for part ({0}) with source ({1}) : {2}.".format(
                        name, source_id, str(sys.exc_info()))))

        def save_child(name, part_id, source_id, bom_id=None, args=None):
            """
                Saves the relation ( child side in mrp.bom.line )
            """
            try:
                res = {}
                if bom_id is not None:
                    res['bom_id'] = bom_id
                res['type'] = kind_bom
                res['product_id'] = part_id
                res['source_id'] = source_id
                if args is not None:
                    for arg in args:
                        res[str(arg)] = args[str(arg)]
                if 'product_qty' in res:
                    res['product_qty'] = repair_qty(res['product_qty'])
                return t_bom_line.create(res)
            except Exception as ex:
                logging.error(ex)
                logging.error(
                    "save_child :  unable to create a relation for part ({0}) with source ({1}) : {2}.".format(
                        name, source_id, str(args))
                )
                raise AttributeError(_(
                    "save_child :  unable to create a relation for part ({0}) with source ({1}) : {2}.".format(
                        name, source_id, str(sys.exc_info())
                    )
                ))

        def clean_empty_boms():
            for _bom_id, bom_brws in evaluated_boms.items():
                if not bom_brws.bom_line_ids:
                    bom_brws.unlink()
        if len(relations) < 1:  # no relation to save
            return False

        parent_name, _parent_id, _child_name, child_id, _source_id, rel_args = relations[0]
        if eco_module_installed is None:
            clean_old_eng_bom_lines(relations)
        if len(relations) == 1 and not child_id: # Case of not children, so no more BOM for this product
            return False
        bom_id = to_compute(parent_name, relations, kind_bom)
        clean_empty_boms()
        return bom_id

    def _sum_bom_weight(self, bom_obj):
        """
            Evaluates net weight for assembly, based on BoM object
        """
        weight = 0.0
        for bom_line in bom_obj.bom_line_ids:
            weight += (bom_line.product_qty * bom_line.product_id.weight)
        return weight

    @api.model
    def rebase_product_weight(self, parent_bom_id, weight=0.0):
        """
            Evaluates net weight for assembly, based on product ID
        """
        if not (parent_bom_id is None) or parent_bom_id:
            bom_obj = self.browse(parent_bom_id)
            self.env['product.product'].browse([bom_obj.product_id.id]).write({'weight': weight})

    def rebase_bom_weight(self):
        """
            Evaluates net weight for assembly, based on BoM ID
        """
        weight = 0.0
        for bom_brws in self:
            weight = bom_brws._sum_bom_weight(bom_brws)
            super(MrpBomExtension, bom_brws).write({'weight_net': weight})
        return weight

    def read(self, fields=[], load='_classic_read'):
        fields = self.plm_sanitize(fields)
        return super(MrpBomExtension, self).read(fields=fields, load=load)
    
    def write(self, vals):
        vals = self.plm_sanitize(vals)
        ret = super(MrpBomExtension, self).write(vals)
        for bom_brws in self:
            bom_brws.rebase_bom_weight()
        return ret

    @api.model
    def create(self, vals):
        vals = self.plm_sanitize(vals)
        ret = super(MrpBomExtension, self).create(vals)
        ret.rebase_bom_weight()
        return ret

    
    def copy(self, default={}):
        """
            Return new object copied (removing source_id)
        """
        new_bom_brws = super(MrpBomExtension, self).copy(default)
        if new_bom_brws:
            for bom_line in new_bom_brws.bom_line_ids:
                if not bom_line.product_id.product_tmpl_id.engineering_code:
                    bom_line.sudo().write({'state': 'draft',
                                           'source_id': False,})   
                    continue
                late_rev_id_c = self.env['product.product'].GetLatestIds([
                    (bom_line.product_id.product_tmpl_id.engineering_code,
                     False,
                     False)
                ])  # Get Latest revision of each Part
                bom_line.sudo().write({
                    'state': 'draft',
                    'source_id': False,
                    'name': bom_line.product_id.product_tmpl_id.name,
                    'product_id': late_rev_id_c[0]
                })
            new_bom_brws.sudo().with_context({'check': False}).write({
                'source_id': False,
                'name': new_bom_brws.product_tmpl_id.name
            })
        return new_bom_brws

    def delete_child_row(self, document_id):
        """
        delete the bom child row
        """
        for bom_line in self.bom_line_ids:
            if bom_line.source_id.id == document_id and bom_line.type == self.type:
                bom_line.unlink()

    @api.model
    def add_child_row(self, child_id, source_document_id, relation_attributes, bom_type='normal'):
        """
            add children rows
        """
        if self.id and child_id and source_document_id:
            cutted_type = 'none'
            if relation_attributes.get('CUTTED_COMP'):
                cutted_type = 'client'
            relation_attributes.update({'bom_id': self.id,
                                        'product_id': child_id,
                                        'source_id': source_document_id,
                                        'type': bom_type,
                                        'cutted_type': cutted_type})
            return self.env['mrp.bom.line'].create(copy.deepcopy(relation_attributes))

    def open_related_bom_lines(self):
        for bom_brws in self:
            def recursion(bom_brws_list):
                out_bom_lines = []
                for bom_brws in bom_brws_list:
                    line_brws_list = bom_brws.bom_line_ids
                    out_bom_lines.extend(line_brws_list.ids)
                    for line_brws in line_brws_list:
                        boms_found = self.search([
                            ('product_tmpl_id', '=', line_brws.product_id.product_tmpl_id.id),
                            ('type', '=', line_brws.type),
                            ('active', '=', True)
                        ])
                        bottom_line_ids = recursion(boms_found)
                        out_bom_lines.extend(bottom_line_ids)
                return out_bom_lines

            bom_line_ids = recursion(self)
            return {'name': _('B.O.M. Lines'),
                    'res_model': 'mrp.bom.line',
                    'view_type': 'form',
                    'view_mode': 'pivot,tree',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', bom_line_ids)],
                    'context': {"group_by": ['bom_id']},
                    }

    
    def open_related_bom_revisions(self):
        bom_ids = self.search([('product_tmpl_id', 'in', self.product_tmpl_id.getAllVersionTemplate().ids)])
        return {'name': _('B.O.M.S'),
                'res_model': 'mrp.bom',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', bom_ids.ids)],
                'context': {}}

    @api.model
    def saveRelationNew(self,
                        clientArgs):
        product_product = self.env['product.product']
        ir_attachment_relation = self.env['ir.attachment.relation']
        try:
            domain = [('state', 'in', ['installed', 'to upgrade', 'to remove']), ('name', '=', 'plm_engineering')]
            apps = self.env['ir.module.module'].sudo().search_read(domain, ['name'])
            bomType = 'normal'
            if apps:
                bomType = 'ebom'
            parentOdooTuple, childrenOdooTuple  = clientArgs
            l_tree_document_id, parent_product_product_id, parent_ir_attachment_id = parentOdooTuple
            if not parent_ir_attachment_id:
                parent_ir_attachment_id = l_tree_document_id
            parent_product_product_id = product_product.browse(parent_product_product_id)
            product_tmpl_id = parent_product_product_id.product_tmpl_id.id
            ir_attachment_relation.removeChildRelation(parent_ir_attachment_id)  # perform default unlink to HiTree, need to perform RfTree also
            ir_attachment_relation.removeChildRelation(parent_ir_attachment_id, linkType='RfTree')
            mrp_bom_found_id = self.env['mrp.bom']
            for mrp_bom_id in self.search([('product_tmpl_id', '=', product_tmpl_id),
                                           ('type', '=', bomType)]):
                mrp_bom_found_id = mrp_bom_id
            if not mrp_bom_found_id:
                if product_tmpl_id:
                    mrp_bom_found_id = self.create({'product_tmpl_id': product_tmpl_id,
                                                    'product_id': parent_product_product_id.id,
                                                    'type': bomType})
            else:
                mrp_bom_found_id.delete_child_row(parent_ir_attachment_id)
            #
            # add rows
            #
            summarize_bom =  self.env.context.get('SUMMARIZE_BOM', False)
            cache_row = {}
            for product_product_id, ir_attachment_id, relationAttributes in childrenOdooTuple:
                if mrp_bom_found_id and not relationAttributes.get('EXCLUDE', False) and product_product_id:
                    key = "%s_%s" % (product_product_id, parent_ir_attachment_id)
                    if summarize_bom and key in cache_row:
                        cache_row[key].product_qty += relationAttributes.get('product_qty', 1)
                    else:
                        mrp_bom_line_id = mrp_bom_found_id.add_child_row(product_product_id,
                                                                         parent_ir_attachment_id,
                                                                         relationAttributes,
                                                                         bomType)
                        if summarize_bom:
                            cache_row[key] = mrp_bom_line_id
                link_kind = relationAttributes.get('link_kind', 'HiTree')
                if relationAttributes.get('RAW_COMP'):
                    link_kind = 'RfTree'
                ir_attachment_relation.saveDocumentRelationNew(parent_ir_attachment_id,
                                                               ir_attachment_id,
                                                               link_kind=link_kind)
                if l_tree_document_id and product_product_id:
                    self.env['plm.component.document.rel'].createFromIds(self.env['product.product'].browse(product_product_id),
                                                                         self.env['ir.attachment'].browse(l_tree_document_id))
            if not mrp_bom_found_id.bom_line_ids:
                mrp_bom_found_id.unlink()
            return True
        except Exception as ex:
            logging.error(ex)
            raise ex

    def plm_sanitize(self, vals):
        all_keys = self._fields
        if isinstance(vals, dict):
            valsKey = list(vals.keys())
            for k in valsKey:
                if k not in all_keys:
                    del vals[k]
            return vals
        else:
            out = []
            for k in vals:
                if k in all_keys:
                    out.append(k)
            return out

    @api.model
    def _bom_find_domain(self, products, picking_type=None, company_id=False, bom_type=False):
        domain = super(MrpBomExtension, self)._bom_find_domain(products, picking_type, company_id, bom_type)
        if not bom_type:
            available_types = ['engineering', 'spare']
            domain = AND([domain, [('type', 'not in', available_types)]])
        return domain
    