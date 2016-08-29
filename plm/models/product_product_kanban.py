from openerp import models, api, _, fields
import json
import logging


class ProductProductKanban(models.Model):
    _inherit = "product.product"

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_bom_dashboard_datas())

    kanban_dashboard = fields.Text(compute='_kanban_dashboard')

    @api.multi
    def get_bom_dashboard_datas(self):
        number_documents = 0
        number_boms = 0
        if self.ids:
            plm_documents = self.get_related_docs()
            number_documents = len(plm_documents)
            boms = self.get_related_boms()
            number_boms = len(boms)
        return {
            'number_boms': number_boms,
            'number_documents': number_documents,
        }

    @api.multi
    def get_related_boms(self):
        try:
            product_tmpl_id = False
            for prodBrws in self.ids:
                if isinstance(prodBrws, int):
                    prodBrws = self.browse(prodBrws)
                for dictElem in prodBrws.read(['product_tmpl_id']):
                    tmplTuple = dictElem.get('product_tmpl_id', ())
                    if tmplTuple:
                        product_tmpl_id = tmplTuple[0]
            return self.env['mrp.bom'].search([('product_tmpl_id', '=', product_tmpl_id)])
        except Exception, ex:
            logging.warning(ex)
            return self.env['mrp.bom'].browse()

    @api.multi
    def get_related_docs(self):
        try:
            out = []
            for brws in self.ids:
                if isinstance(brws, int):
                    brws = self.browse(brws)
                out.extend(brws.linkeddocuments.ids)
            return list(set(out))
        except Exception, ex:
            logging.warning(ex)
            return []

    @api.multi
    def common_open(self, name, model, view_mode='form', view_type='form', res_id=False, ctx={}, domain=[]):
        # <field name="domain">[('account_id','=', active_id)]</field>
        return {
            'name': _(name),
            'type': 'ir.actions.act_window',
            'view_type': view_type,
            'view_mode': view_mode,
            'res_model': model,
            'res_id': res_id,
            'context': ctx,
            'domain': domain
        }

    @api.multi
    def toggle_favorite(self):
        self.write(
            {'show_on_dashboard': False if self.show_on_dashboard else True})
        return False

    @api.multi
    def open_action(self):
        return self.common_open(_('New Component'), 'product.product', 'form', 'form', self.ids[0], self.env.context)

    @api.multi
    def create_component(self):
        return self.common_open(_('New Component'), 'product.product', 'form', 'form', False, self.env.context)

    @api.multi
    def open_normal_bom(self):
        boms = self.get_related_boms()
        domain = [('id', 'in', boms.ids), ('type', '=', 'normal')]
        return self.common_open(_('Related Boms'), 'mrp.bom', 'tree,form', 'form', boms.ids, self.env.context, domain)

    @api.multi
    def open_engin_bom(self):
        boms = self.get_related_boms()
        domain = [('id', 'in', boms.ids), ('type', '=', 'ebom')]
        return self.common_open(_('Related Boms'), 'mrp.bom', 'tree,form', 'form', boms.ids, self.env.context, domain)

    @api.multi
    def open_spare_bom(self):
        boms = self.get_related_boms()
        domain = [('id', 'in', boms.ids), ('type', '=', 'spbom')]
        return self.common_open(_('Related Boms'), 'mrp.bom', 'tree,form', 'form', boms.ids, self.env.context, domain)

    @api.multi
    def open_new_component(self):
        return self.common_open(_('New Component'), 'product.product', 'form', 'form', False, self.env.context)

    @api.multi
    def open_related_docs_action(self):
        docIds = self.get_related_docs()
        domain = [('id', 'in', docIds)]
        return self.common_open(_('Related Documents'), 'plm.document', 'tree,form', 'form', docIds, self.env.context, domain)

    @api.multi
    def open_related_boms_action(self):
        boms = self.get_related_boms()
        domain = [('id', 'in', boms.ids)]
        return self.common_open(_('Related Boms'), 'mrp.bom', 'tree,form', 'form', boms.ids, self.env.context, domain)

    @api.multi
    def create_normal_bom(self):
        context = self.env.context.copy()
        context.update({'default_type': 'normal'})
        docIds = self.get_related_docs()
        if docIds:
            context.update(
                {'default_product_tmpl_id': self.product_tmpl_id.id})
        return self.common_open(_('Related Boms'), 'mrp.bom', 'form', 'form', False, context)

    @api.multi
    def create_spare_bom(self):
        context = self.env.context.copy()
        context.update({'default_type': 'spbom'})
        docIds = self.get_related_docs()
        if docIds:
            context.update(
                {'default_product_tmpl_id': self.product_tmpl_id.id})
        return self.common_open(_('Related Boms'), 'mrp.bom', 'form', 'form', False, context)

    @api.multi
    def openDocument(self, vals=False):
        print 'Open document'

    @api.multi
    def report_components(self):
        pass

    def computePrevious(self, linkeddocs):
        pass


ProductProductKanban()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
