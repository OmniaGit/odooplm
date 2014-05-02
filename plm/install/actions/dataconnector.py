
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
import os
import types
import cPickle as pickle
from datetime import datetime

import logging
from openerp.osv import osv, fields
from openerp.tools.translate import _

def normalize(value):
    if type(value)==types.StringType or type(value)==types.UnicodeType:
        return unicode(str(value).replace('"','\"').replace("'",'\"').replace("%","%%").strip(), 'Latin1')
    else:
        return str(value).strip()

class plm_temporary(osv.osv_memory):
    _inherit = "plm.temporary"
##  Specialized Actions callable interactively
    def action_transferData(self, cr, uid, ids, context=None):
        """
            Call for Transfer Data method
        """
        if not 'active_id' in context:
            return False
        self.pool.get('product.product').TransferData(cr, uid)
        return False
#         return {
#               'name': _('Products'),
#               'view_type': 'form',
#               "view_mode": 'tree,form',
#               'res_model': 'product.product',
#               'type': 'ir.actions.act_window',
#               'domain': "[]",
#          }
    
plm_temporary()


class plm_component(osv.osv):
    _inherit = 'product.product'

###################################################################
#   Override these properties to configure TransferData process.  #
###################################################################

    @property
    def get_part_data_transfer(self):
        """
            Map OpenErp vs. destination Part data transfer fields
        """
        return {
                'table' : 'PARTS',                          # Used with 'db' transfer
                'status': ['released',],
                'fields':
                    {
                    'name'                  : 'revname',
                    'engineering_revision'  : 'revprog',
                    'description'           : 'revdes',
                    }
                }

    @property
    def get_bom_data_transfer(self):
        """
            Map OpenErp vs. destination BoM data transfer fields
        """
        return {
                'kind' : 'normal',                         # Bom type name to export
                'table': 'BOMS',                           # Destination table name. Used with 'db' transfer
                'PName': 'parent',                         # Parent column name.     Used with 'db' transfer
                'CName': 'child',                          # Child column name.      Used with 'db' transfer
                'fields':
                    {
                    'itemnum'               : 'relpos',
                    'product_qty'           : 'relqty',
                    }
                }

    @property
    def get_data_transfer(self):
        """
            Map OpenErp vs. destination Connection DB data transfer values
        """
        return {
                'db':
                    {
                    'protocol'              : 'mssql+pymssql',
                    'user'                  : 'dbamkro',
                    'password'              : 'dbamkro',
                    'host'                  : 'SQL2K8\SQLEXPRESS',
                    'database'              : 'Makro',
                    },
                
                'file':
                    {
                    'exte'                  : 'csv',
                    'separator'             : ',',
                    'name'                  : 'transfer',
                    'bomname'               : 'transferbom',
                    'directory'             : '/tmp',
                    }
                }

###################################################################
#   Override these properties to configure TransferData process.  #
###################################################################

    @property
    def get_last_session(self):
        """
            Get last execution date & time as stored.
                format => '%Y-%m-%d %H:%M:%S'
        """
        lastDate=datetime.now()
        fileName=os.path.join(os.environ.get('HOME'),'ttsession.time')
        if os.path.exists(fileName):
            try:
                fobj=open(fileName)
                lastDate=pickle.load(fobj)
                fobj.close()
            except:
                try:
                    fobj.close()
                except:
                    pass
                os.unlink(fileName)
        else:
            self.set_last_session
        return lastDate.strftime('%Y-%m-%d %H:%M:%S')

    @property
    def set_last_session(self):
        """
            Get last execution date & time as stored.
                format => '%Y-%m-%d %H:%M:%S'
        """
        lastDate=datetime.now()
        fileName=os.path.join(os.environ.get('HOME'),'ttsession.time')
        if os.path.exists(fileName):
            os.unlink(fileName)
        fobj=open(fileName,'w')
        pickle.dump(lastDate,fobj)
        fobj.close()
        return lastDate.strftime('%Y-%m-%d %H:%M:%S')

    def TransferData(self, cr, uid, ids=False, context=None):
 
        operation=False
        reportStatus='Failed'
        updateDate=self.get_last_session
        logging.debug("[TransferData] Start : %r" %(updateDate))
        transfer=self.get_data_transfer
        datamap=self.get_part_data_transfer['fields']
        datatyp=self.get_part_data_transfer['types']
        fieldsListed=datamap.keys()
        allIDs=self.query_data(cr, uid, updateDate, self.get_part_data_transfer['status'])
        tmpData=self.export_data(cr, uid, allIDs, fieldsListed)
        if tmpData.get('datas'):
            if 'db' in transfer:
                import dbconnector
                dataTargetTable=self.get_part_data_transfer['table']
                connection=dbconnector.get_connection(transfer['db'])
            
                checked=dbconnector.saveParts(self,cr, uid, connection, tmpData.get('datas'), dataTargetTable, datamap,datatyp)
    
                if checked:
                    bomTargetTable=self.get_bom_data_transfer['table']
                    bomdatamap=self.get_bom_data_transfer['fields']
                    bomdatatyp=self.get_bom_data_transfer['types']
                    parentName=self.get_bom_data_transfer['PName']
                    childName=self.get_bom_data_transfer['CName']
                    kindBomname=self.get_bom_data_transfer['kind']
                    operation=dbconnector.saveBoms(self, cr, uid, connection, checked, allIDs, dataTargetTable, datamap, datatyp, kindBomname, bomTargetTable, parentName, childName, bomdatamap, bomdatatyp)  
                     
            if 'file' in transfer:
                bomfieldsListed=self.get_bom_data_transfer['fields'].keys()
                kindBomname=self.get_bom_data_transfer['kind']
                operation=self.extract_data(cr, uid, allIDs, kindBomname, fieldsListed, bomfieldsListed, transfer['file'])

        if operation:
            updateDate=self.set_last_session
            reportStatus='Successful'
            
        logging.debug("[TransferData] %r End : %r." %(reportStatus,updateDate))
        return False

    def query_data(self, cr, uid, updateDate, statuses=[]):
        """
            Query to return values based on columns selected.
                updateDate => '%Y-%m-%d %H:%M:%S'
        """
        if not statuses:
            statusList=['released']
        else:
            statusList=statuses
            
        allIDs=self.search(cr,uid,[('write_date','>',updateDate),('state','in',statusList)],order='engineering_revision')
        allIDs.extend(self.search(cr,uid,[('create_date','>',updateDate),('state','in',statusList)],order='engineering_revision'))
        return list(set(allIDs))

    def extract_data(self,cr,uid,allIDs, kindBomname='normal', anag_fields=False, rel_fields=False, transferdata={}):
        """
            action to be executed for Transmitted state.
            Transmit the object to ERP Metodo
        """
        
        def getChildrenBom(component, kindName):
            for bomid in component.bom_ids:
                if not (str(bomid.type).lower()==kindName):
                    continue
                return bomid.bom_lines
            return []
        
        if not anag_fields:
            anag_fields=['name','description']
        if not rel_fields:
            rel_fields=['bom_id','product_id','product_qty','itemnum']

        if not transferdata:
            outputpath=os.environ.get('TEMP')
            tmppws=os.environ.get('OPENPLMOUTPUTPATH')
            if tmppws!=None and os.path.exists(tmppws):
                outputpath=tmppws
            exte='csv'
            fname=datetime.now().isoformat(' ').replace('.','').replace(':','').replace(' ','').replace('-','')+'.'+exte
            bomname="bom"
        else:
            outputpath=transferdata['directory']
            exte="%s" %(str(transferdata['exte']))
            fname="%s.%s" %(str(transferdata['name']),exte)
            bomname="%s" %(str(transferdata['bomname']))
            
        if outputpath==None:
            return True
        if not os.path.exists(outputpath):
            raise osv.except_osv(_('Export Data Error'), _("Requested writing path (%s) doesn't exist." %(outputpath)))
            return False 

        filename=os.path.join(outputpath,fname)
        expData=self.export_data(cr, uid, allIDs,anag_fields)
        if not self.export_csv(filename, anag_fields, expData, True):
            raise osv.except_osv(_('Export Data Error'), _("Writing operations on file (%s) have failed." %(filename)))
            return False
        
        ext_fields=['parent','child']
        ext_fields.extend(rel_fields)
        for oic in self.browse(cr, uid, allIDs, context=None):
            dataSet=[]
            fname="%s-%s.%s" %(bomname,str(oic.name),exte)
            filename=os.path.join(outputpath,fname)
            for oirel in getChildrenBom(oic, kindBomname):
                rowData=[oic.name,oirel.product_id.name]
                for rel_field in rel_fields:
                    rowData.append(eval('oirel.%s' %(rel_field)))
                dataSet.append(rowData)
            if dataSet:
                expData={'datas': dataSet}
                
                if not self.export_csv(filename, ext_fields, expData, True):
                    raise osv.except_osv(_('Export Data Error'), _("No Bom extraction files was generated, about entity (%s)." %(fname)))
                    return False
        return True

    def export_csv(self, fname, fields=[], result={}, write_title=False):
        import csv, stat
        if not ('datas' in result) or not result:
            logging.error("export_csv : No 'datas' in result.")
            return False

        if not fields:
            logging.error("export_csv : No 'fields' in result.")
            return False
        
        try:
            fp = file(fname, 'wb+')
            writer = csv.writer(fp)
            if write_title:
                writer.writerow(fields)
            results=result['datas']
            for datas in results:
                row = []
                for data in datas:
                    if type(data)==types.StringType:
                        row.append(data.replace('\n',' ').replace('\t',' '))
                    else:
                        row.append(data or '')
                writer.writerow(row)
            fp.close()
            os.chmod(fname, stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG)
            return True
        except IOError, (errno, strerror):
            logging.error("export_csv : IOError : "+str(errno)+" ("+str(strerror)+").")
            return False

plm_component()


