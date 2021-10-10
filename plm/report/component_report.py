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
from .book_collector import BookCollector
from .book_collector import packDocuments
from datetime import datetime
from dateutil import tz
import base64
from odoo import _
from odoo import api
from odoo import models
from odoo.exceptions import UserError
from odoo.addons.plm.report.book_collector import getBottomMessage


def getEmptyDocument():
    return base64.b64decode(b"""JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwvTGVuZ3RoIDMgMCBSL0ZpbHRlci9GbGF0ZURl
Y29kZT4+CnN0cmVhbQp4nG2NTQvCMBBE7/kVexYSZ2M2aSEErG0P3goBD+LNj5tgL/59t/QgiCzM
Djx4A8f0Ni8CQZu04jw1gV1D882cNvRcmd78MF01EhWlGFyieqXtyOQ91fs5gwtneOyK1b9mgCAi
lks9mqGa6a+Lgw7/uJKKBM1ibIv1GfulShHJ6EpKGQf0GDCiLzZkhmLm785EH25LLk8KZW5kc3Ry
ZWFtCmVuZG9iagoKMyAwIG9iagoxNTAKZW5kb2JqCgo1IDAgb2JqCjw8L0xlbmd0aCA2IDAgUi9G
aWx0ZXIvRmxhdGVEZWNvZGUvTGVuZ3RoMSAxMDU5Mj4+CnN0cmVhbQp4nOV5f1hb15XgvffptwR6
EkIICdCTH49fkhBG/LBjMM8gQAQMGIwjsAHJSPxwDMKS7MROGpM28Q9S1+40zSSTr60nm2nTjSd+
OJ4Jme7GpHG6O9O69X7pzkybeuLOZOfrbEOdzib90sSGPfdJYDuTdubb2e/bP/YhvXfOueece+65
55x7HkolDsaQAc0hBolj05FZsVzgEEI/QAibxw6luLPi/TzA1xEiqvHZieky/9u/Qoj5BUJq5cT+
w+M/P1z+EkK69xEyPz8Zi0SbXvrreoQKnwQddZNACK0cVgMO+lDx5HTqwT7Vww2AAz8K7o+PRa5X
/NdyhIo2AV4yHXlwdrfyUQbwMODcTGQ69j9KfgXzF80hpJmdjSdTb6DiVWCl8txsIja7f+FUFKFS
FuzbDjQMf/QyAKiiOGEUSpVao9XpDVnZRtaE/j+7lKdQLoorG5Exc7/rYs6hfHQBodX3KHb7vtK1
+vH/TSs08h2bsQu9iX6L/Zigh3EOGkJRFEcPo3nsv5Mbb8FdMPY59DMYn0GnsPqztWIXLsFZoGFI
5vscuoL+/jMZD6DX0Pt3zwG0p9Dz6Byl4zbQ9SR+A3fhKOigmrvgtuezVJF9cDsN3wfhPk1whnoD
MuZv0R7yGnkXnUEvZezLRu/hADw7wcJXMgo6Uf+/ULoIVujQBDqMjoG0fCkbb/4UaVf/F+i6F70O
hA70EDq1LvERludgdGh1nXbfuo1R8gTOwSXo6+gjFFCa8EWExNbB0MDO/r4dvT3d27s67+0Itre1
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
aXB0b3IvRm9udE5hbWUvQkFBQUFBK0xpYmVyYXRpb25TZXJpZi1Cb2xkCi9GbGFncyA0Ci9Gb250
QkJveFstMTgyIC0zMDMgMTA4MyAxMDA3XS9JdGFsaWNBbmdsZSAwCi9Bc2NlbnQgODkxCi9EZXNj
ZW50IC0yMTYKL0NhcEhlaWdodCAxMDA3Ci9TdGVtViA4MAovRm9udEZpbGUyIDUgMCBSCj4+CmVu
ZG9iagoKOCAwIG9iago8PC9MZW5ndGggMzAxL0ZpbHRlci9GbGF0ZURlY29kZT4+CnN0cmVhbQp4
nF2Ry26DMBBF9/4KL9tFhE0S0kgIKSVBYtGHSvsBxB5SS8VYxlnw97Vn0lbqAnTGc689j6xuj601
IXv1k+og8MFY7WGerl4BP8PFWCZzro0Ktwj/auwdy6K3W+YAY2uHqSxZ9hZzc/ALvzvo6Qz3LHvx
GryxF373UXcx7q7OfcEINnDBqoprGOI9T7177kfI0LVqdUybsKyi5U/wvjjgOcaSSlGThtn1Cnxv
L8BKISpeNk3FwOp/Obkjy3lQn72PUhmlQmzXVeQcuWgSr5F3eeIN8T7xFjkXiQviU+Id8gb5gfSo
2dOdm8QH4iLxI+ll4pr0eH4kDZ6fiPHdhriOLAVxqk1S/cUWm711ldpOe/kZJ1dX7+MocXk4wzQ9
Y4H/LthNLtnw+wb8aJMuCmVuZHN0cmVhbQplbmRvYmoKCjkgMCBvYmoKPDwvVHlwZS9Gb250L1N1
YnR5cGUvVHJ1ZVR5cGUvQmFzZUZvbnQvQkFBQUFBK0xpYmVyYXRpb25TZXJpZi1Cb2xkCi9GaXJz
dENoYXIgMAovTGFzdENoYXIgMTcKL1dpZHRoc1szNjUgNTU2IDUwMCA0NDMgNTAwIDI1MCAyNTAg
NzIyIDU1NiA1NTYgMzMzIDcyMiA1MDAgNTAwIDI3NyAyNzcKNTU2IDQ0MyBdCi9Gb250RGVzY3Jp
cHRvciA3IDAgUgovVG9Vbmljb2RlIDggMCBSCj4+CmVuZG9iagoKMTAgMCBvYmoKPDwvRjEgOSAw
IFIKPj4KZW5kb2JqCgoxMSAwIG9iago8PC9Gb250IDEwIDAgUgovUHJvY1NldFsvUERGL1RleHRd
Cj4+CmVuZG9iagoKMSAwIG9iago8PC9UeXBlL1BhZ2UvUGFyZW50IDQgMCBSL1Jlc291cmNlcyAx
MSAwIFIvTWVkaWFCb3hbMCAwIDU5NSA4NDJdL0dyb3VwPDwvUy9UcmFuc3BhcmVuY3kvQ1MvRGV2
aWNlUkdCL0kgdHJ1ZT4+L0NvbnRlbnRzIDIgMCBSPj4KZW5kb2JqCgo0IDAgb2JqCjw8L1R5cGUv
UGFnZXMKL1Jlc291cmNlcyAxMSAwIFIKL01lZGlhQm94WyAwIDAgNTk1IDg0MiBdCi9LaWRzWyAx
IDAgUiBdCi9Db3VudCAxPj4KZW5kb2JqCgoxMiAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMg
NCAwIFIKL09wZW5BY3Rpb25bMSAwIFIgL1hZWiBudWxsIG51bGwgMF0KL0xhbmcoZW4tR0IpCj4+
CmVuZG9iagoKMTMgMCBvYmoKPDwvQXV0aG9yPEZFRkYwMDREMDA2MTAwNzQwMDc0MDA2NTAwNkYw
MDIwMDA0MjAwNkYwMDczMDA2MzAwNkYwMDZDMDA2Rj4KL0NyZWF0b3I8RkVGRjAwNTcwMDcyMDA2
OTAwNzQwMDY1MDA3Mj4KL1Byb2R1Y2VyPEZFRkYwMDRDMDA2OTAwNjIwMDcyMDA2NTAwNEYwMDY2
MDA2NjAwNjkwMDYzMDA2NTAwMjAwMDM1MDAyRTAwMzI+Ci9DcmVhdGlvbkRhdGUoRDoyMDE3MTAy
NDE3MTgwNiswMicwMCcpPj4KZW5kb2JqCgp4cmVmCjAgMTQKMDAwMDAwMDAwMCA2NTUzNSBmIAow
MDAwMDA4MTYzIDAwMDAwIG4gCjAwMDAwMDAwMTkgMDAwMDAgbiAKMDAwMDAwMDI0MCAwMDAwMCBu
IAowMDAwMDA4MzA2IDAwMDAwIG4gCjAwMDAwMDAyNjAgMDAwMDAgbiAKMDAwMDAwNzI1MCAwMDAw
MCBuIAowMDAwMDA3MjcxIDAwMDAwIG4gCjAwMDAwMDc0NzMgMDAwMDAgbiAKMDAwMDAwNzg0MyAw
MDAwMCBuIAowMDAwMDA4MDc2IDAwMDAwIG4gCjAwMDAwMDgxMDggMDAwMDAgbiAKMDAwMDAwODQw
NSAwMDAwMCBuIAowMDAwMDA4NTAyIDAwMDAwIG4gCnRyYWlsZXIKPDwvU2l6ZSAxNC9Sb290IDEy
IDAgUgovSW5mbyAxMyAwIFIKL0lEIFsgPEMzRDZBMzFBMTcxNkU1QjAyMjkxN0Y4QzkxQUM1MDk3
Pgo8QzNENkEzMUExNzE2RTVCMDIyOTE3RjhDOTFBQzUwOTc+IF0KL0RvY0NoZWNrc3VtIC8wQjMy
RjYxNzJGNDFCNzYwNjRBM0NDQjFEMTgxOTFCQgo+PgpzdGFydHhyZWYKODc0NwolJUVPRgo=""")


class ReportProductPdf(models.AbstractModel):
    _name = 'report.plm.product_pdf'
    _description = 'Report for producing pdf'


    def commonInfos(self):
        docRepository = self.env['ir.attachment']._get_filestore()
        to_zone = tz.gettz(self.env.context.get('tz', 'Europe/Rome'))
        from_zone = tz.tzutc()
        dt = datetime.now()
        dt = dt.replace(tzinfo=from_zone)
        localDT = dt.astimezone(to_zone)
        localDT = localDT.replace(microsecond=0)
        msg = "Printed by '%(print_user)s' : %(date_now)s State: %(state)s"
        msg_vals = {
            'print_user': 'user_id.name',
            'date_now': localDT.ctime(),
            'state': 'doc_obj.state',
                }
        mainBookCollector = BookCollector(jumpFirst=False,
                                          customText=(msg, msg_vals),
                                          bottomHeight=10,
                                          poolObj=self.env)
        return docRepository, mainBookCollector

    def getDocument(self, product, check):
        out = []
        for doc in product.linkeddocuments:
            if check:
                if doc.state in ['released', 'undermodify']:
                    out.append(doc)
                continue
            out.append(doc)
        return out

    @api.model
    def _render_qweb_pdf(self, products=None, level=0, checkState=False):
        docRepository, mainBookCollector = self.commonInfos()
        documents = []

        for product in products:
            documents.extend(self.getDocument(product, checkState))
            if level > -1:
                for childProduct in product._getChildrenBom(product, level):
                    childProduct = self.env['product.product'].browse(childProduct)
                    documents.extend(self.getDocument(childProduct, checkState))
        if len(documents) == 0:
            content = getEmptyDocument()
        else:
            documentContent = packDocuments(docRepository,
                                            documents,
                                            mainBookCollector)
            content = documentContent[0]
        return content
    
    def render_qweb_pdf(self, products=None, level=0, checkState=False):
        content = self._render_qweb_pdf(products, level, checkState)
        byteString = b"data:application/pdf;base64," + base64.b64encode(content)
        return byteString.decode('UTF-8')

    @api.model
    def _get_report_values(self, docids, data=None):
        products = self.env['product.product'].browse(docids)
        return {'docs': products,
                'get_content': self.render_qweb_pdf}


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
