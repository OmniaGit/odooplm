'''
Created on May 30, 2016

@author: Daniel Smerghetto
'''

from openerp.osv import osv
from openerp.report import report_sxw


class bom_structure_overload(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(bom_structure_overload, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_children': self.get_children,
        })

    def get_children(self, lineBrwsList, level=0):
        result = []

        def _get_line_ids(lineBrws):
            outLineIds = []
            myNewBom = None
            if lineBrws:
                for bomBws in lineBrws.product_id.bom_ids:
                    if bomBws.type == lineBrws.bom_id.type:
                        myNewBom = bomBws
                        outLineIds = myNewBom.bom_line_ids
                        break
            return outLineIds

        def _get_rec(lineBrwsListRec, level):
            for lineBrws in lineBrwsListRec:
                res = {}
                res['pname'] = lineBrws.product_id.name
                res['pcode'] = lineBrws.product_id.default_code
                res['pqty'] = lineBrws.product_qty
                res['uname'] = lineBrws.product_uom.name
                res['level'] = level
                res['code'] = lineBrws.bom_id.code
                result.append(res)
                if lineBrws.child_line_ids:
                    if level < 6:
                        level += 1
                    lines = _get_line_ids(lineBrws)
                    _get_rec(lines, level)
                    if level > 0 and level < 6:
                        level -= 1
            return result

        children = _get_rec(lineBrwsList, level)

        return children


class report_mrpbomstructure_overload(osv.AbstractModel):
    _name = 'report.mrp.report_mrpbomstructure'
    _inherit = 'report.mrp.report_mrpbomstructure'
    _template = 'mrp.report_mrpbomstructure'
    _wrapped_report_class = bom_structure_overload
