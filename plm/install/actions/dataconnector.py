
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

###
# map_name : ['LangName','label Out', 'OE Lang']        '
_LOCALLANGS = {                 
    'french':  ['French_France','fr_FR',],
    'italian': ['Italian_Italy','it_IT',],
    'polish':  ['Polish_Poland','pl_PL',],
    'svedish': ['Svedish_Svenska','sw_SE',],
    'russian': ['Russian_Russia','ru_RU',],
    'english': ['English USA','en_US',],
    'spanish': ['Spanish_Spain','es_ES',],
    'german':  ['German_Germany','de_DE',],
}
###

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
    _name = 'product.product'
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
                    },
                'types':
                    {
                    'name'                  : 'char',
                    'engineering_revision'  : 'int',
                    'description'           : 'char',
                    },
                'exitorder' : ['name','engineering_revision','description',],
                'exitTrans' : ['description',],
                'exitLang'  : ['english','french',],
                'exitnumber': ['engineering_revision',],
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
                    },
                'types':
                    {
                    'itemnum'               : 'int',
                    'product_qty'           : 'float',
                    },
                'exitnumber': ['engineering_revision',],
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
    def _get_last_session(self):
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
            self._set_last_session
        return lastDate.strftime('%Y-%m-%d %H:%M:%S')

    @property
    def _set_last_session(self):
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

    def _rectify_data(self, cr, uid, tmpDataPack={}, part_data_transfer={}):
 
        if tmpDataPack.get('datas'):
            fieldsNumeric=[]
            fieldsTranslated=[]
            languageNames=[]
            indexFields={}
            rectifiedData=[]
            labelNames=[]
            
            if 'exitorder' in part_data_transfer:
                fieldNames=part_data_transfer['exitorder']
            else:
                fieldNames=part_data_transfer['fields'].keys()
            if 'exitnumber' in part_data_transfer:
                fieldsNumeric=part_data_transfer['exitnumber']
            if 'exitTrans' in part_data_transfer:
                fieldsTranslated=part_data_transfer['exitTrans']
            if 'exitLang' in part_data_transfer:
                languageNames=part_data_transfer['exitLang']

            for fieldName in fieldNames:                                # Sort field names to fix the exit data recordset
                indexFields[fieldName]=fieldNames.index(fieldName)
                labelNames.append(fieldName)
                
            for languageName in languageNames:                          # Sort field names to fix the exit data recordset
                labelNames.append(languageName)
                
            for rowData in tmpDataPack['datas']:
                rectData=[]
                for fieldName in fieldNames:
                    dataValue=rowData[indexFields[fieldName]]
                    if not dataValue:
                        if fieldName in fieldsNumeric:
                            rectData.append(0)
                        else:
                            rectData.append('')
                    else:
                        rectData.append(dataValue)

                for languageName in languageNames:
                    for fieldTranslated in fieldsTranslated:
                        dataValue=rowData[indexFields[fieldTranslated]]
                        if not dataValue:
                            rectData.append('')
                        else:
                            rectData.append(self._translate(cr, uid, dataValue,languageName))
                                       
                rectifiedData.append(rectData)
            
            return {'datas': rectifiedData, 'labels':labelNames}
        
        return tmpDataPack
    
    def _translate(self, cr, uid, dataValue="",languageName=""):
        
        if languageName in _LOCALLANGS:
            language=_LOCALLANGS[languageName][1]
            transObj=self.pool.get('ir.translation')
            resIds = transObj.search(cr,uid,[('src','=',dataValue),('type','=','code'),('lang','=',language)])
            for trans in transObj.browse(cr, uid, resIds):
                return trans.value
        return ""

    def TransferData(self, cr, uid, ids=False, context=None):
        """
            Exposed method to execute data transfer to other systems.
        """ 
        operation=False
        reportStatus='Failed'
        updateDate=self._get_last_session
        logging.debug("[TransferData] Start : %s" %(str(updateDate)))
        transfer=self.get_data_transfer
        part_data_transfer=self.get_part_data_transfer
        datamap=part_data_transfer['fields']
        if 'exitorder' in part_data_transfer:
            fieldsListed=part_data_transfer['exitorder']
        else:
            fieldsListed=datamap.keys()
        allIDs=self._query_data(cr, uid, updateDate, part_data_transfer['status'])
        tmpData=self._exportData(cr, uid, allIDs, fieldsListed)
        if tmpData.get('datas'):
            bom_data_transfer=self.get_bom_data_transfer
            tmpData=self._rectify_data(cr, uid, tmpData, part_data_transfer)
            if 'db' in transfer:
                import dbconnector
                dataTargetTable=part_data_transfer['table']
                datatyp=part_data_transfer['types']
                connection=dbconnector.get_connection(transfer['db'])
            
                checked=dbconnector.saveParts(self,cr, uid, connection, tmpData.get('datas'), dataTargetTable, datamap, datatyp)
    
                if checked:
                    bomTargetTable=bom_data_transfer['table']
                    bomdatamap=bom_data_transfer['fields']
                    bomdatatyp=bom_data_transfer['types']
                    parentName=bom_data_transfer['PName']
                    childName=bom_data_transfer['CName']
                    kindBomname=bom_data_transfer['kind']
                    operation=dbconnector.saveBoms(self, cr, uid, connection, checked, allIDs, dataTargetTable, datamap, datatyp, kindBomname, bomTargetTable, parentName, childName, bomdatamap, bomdatatyp)  
                     
            if 'file' in transfer:
                bomfieldsListed=bom_data_transfer['fields'].keys()
                kindBomname=bom_data_transfer['kind']
                operation=self._extract_data(cr, uid, allIDs, kindBomname, tmpData, fieldsListed, bomfieldsListed, transfer['file'])

        if operation:
            updateDate=self._set_last_session
            reportStatus='Successful'
            
        logging.debug("[TransferData] %s End : %s" %(reportStatus,str(updateDate)))
        return False

    def _query_data(self, cr, uid, updateDate, statuses=[]):
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

    def _extract_data(self,cr,uid,allIDs, kindBomname='normal', anag_Data={}, anag_fields=False, rel_fields=False, transferdata={}):
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
        if not self._export_csv(filename, anag_Data['labels'], anag_Data, True):
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
                
                if not self._export_csv(filename, ext_fields, expData, True):
                    raise osv.except_osv(_('Export Data Error'), _("No Bom extraction files was generated, about entity (%s)." %(fname)))
                    return False
        return True

    def _export_csv(self, fname, fields=[], result={}, write_title=False):
        import csv, stat
        if not ('datas' in result) or not result:
            logging.error("_export_csv : No 'datas' in result.")
            return False

        if not fields:
            logging.error("_export_csv : No 'fields' in result.")
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
                    if (type(data) is types.StringType):
                        row.append(str(data).replace('\n',' ').replace('\t',' '))
                    if (type(data) is types.UnicodeType):
                        row.append(unicode(str(data),'utf8').replace('\n',' ').replace('\t',' '))
                    else:
                        row.append(str(data) or '')
                writer.writerow("%r" %(row))
            fp.close()
            os.chmod(fname, stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG)
            return True
        except IOError, (errno, strerror):
            logging.error("_export_csv : IOError : "+str(errno)+" ("+str(strerror)+").")
            return False

    def _exportData(self, cr, uid, ids, fields=[]):
        """
            Export data about product and BoM
        """
        listData=[]
        oid=self.browse(cr,uid,ids,context=None)
        if oid:
            if len(oid.bom_line_ids):
                prod_names=oid.bom_line_ids[0].product_id._all_columns.keys()
                bom_names=oid.bom_line_ids[0]._all_columns.keys()
                for bom_line in oid.bom_line_ids:
                    row_data={}
                    for field in fields:
                        if field in prod_names:
                            row_data[field]=bom_line.product_id[field]
                        if field in bom_names:
                            row_data[field]=bom_line[field]
                    if row_data:
                        listData.append(row_data)
        return {'datas':listData}

plm_component()


