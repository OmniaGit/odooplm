
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
import os,sys
import types
import cPickle as pickle
from datetime import datetime

import logging
from openerp        import models, fields, api, SUPERUSER_ID, _, osv
_logger         =   logging.getLogger(__name__)

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
    if (type(value) is types.StringType):
        return str(value).replace('"','\"').replace("'",'\"').replace("%","%%").strip()
    elif (type(value) is types.UnicodeType):
        return unicode(str(value).replace('"','\"').replace("'",'\"').replace("%","%%").strip(), 'Latin1')
    else:
        return str(value).strip()

class plm_temporary(osv.osv.osv_memory):
    _inherit = "plm.temporary"
##  Specialized Actions callable interactively
    def action_transferData(self, cr, uid, ids, context=None):
        """
            Call for Transfer Data method
        """
        if 'active_id' not in context:
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


class plm_component(models.Model):
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
                'fixed' : True,                             # Uses fixded format (specify lenghts)
                'append' : True,                            # append to existing transfer files (only for part data)
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
               'lengths':
                    {
                    'name'                  : 10,
                    'engineering_revision'  : 2,
                    'description'           : 40,
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
                'fixed' : True,                            # Uses fixded format (specify lenghts)
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
                'lengths':
                    {
                    'parent'                : 10,           # To be considered also if not mapped explicitely
                    'child'                 : 10,           # To be considered also if not mapped explicitely
                    'itemnum'               : 2,
                    'product_qty'           : 5,
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
                    'textquoted'            : False,
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
#         return "2015-01-01 12:00:00"
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
                    dataValue=rowData[fieldName]
                    if not dataValue:
                        if fieldName in fieldsNumeric:
                            rectData.append(0)
                        else:
                            rectData.append('')
                    else:
                        rectData.append(dataValue)

                for languageName in languageNames:
                    for fieldTranslated in fieldsTranslated:
                        dataValue=rowData[fieldTranslated]
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
#         Reset default encoding. to allow to work fine also as service.
        reload(sys)
        sys.setdefaultencoding('utf-8')
#         Reset default encoding. to allow to work fine also as service.
        operation=False
        fixedformat=False
        queueFiles={'anagrafica':False, 'distinte':False}
        partfieldsLength=False
        bomfieldsLength=False
        reportStatus='Failed'
        updateDate=self._get_last_session
        logging.debug("[TransferData] Start : %s" %(str(updateDate)))
        transfer=self.get_data_transfer
        part_data_transfer=self.get_part_data_transfer
        bom_data_transfer=self.get_bom_data_transfer
        datamap=part_data_transfer['fields']
        if 'fixed' in part_data_transfer:
            fixedformat=part_data_transfer['fixed']            
            if 'lengths' in part_data_transfer:
                partfieldsLength=part_data_transfer['lengths']
        if 'exitorder' in part_data_transfer:
            fieldsListed=part_data_transfer['exitorder']
        if 'append' in part_data_transfer:
            queueFiles['anagrafica']=part_data_transfer['append']
        if 'append' in bom_data_transfer:
            queueFiles['distinte']=part_data_transfer['append']
        else:
            fieldsListed=datamap.keys()
        allIDs=self._query_data(cr, uid, updateDate, part_data_transfer['status'])
        tmpData=self._exportData(cr, uid, allIDs, fieldsListed, bom_data_transfer['kind'])
        if tmpData.get('datas'):
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
                if 'lengths' in bom_data_transfer:
                    bomfieldsLength=bom_data_transfer['lengths']
                kindBomname=bom_data_transfer['kind']
                operation=self._extract_data(cr, uid, allIDs, queueFiles, fixedformat, kindBomname, tmpData, fieldsListed, bomfieldsListed, transfer['file'],partLengths=partfieldsLength,bomLengths=bomfieldsLength)

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
        objTempl=self.pool.get('product.template')           
        allIDs=objTempl.search(cr,uid,[('write_date','>',updateDate),('state','in',statusList)],order='engineering_revision')
        allIDs.extend(objTempl.search(cr,uid,[('create_date','>',updateDate),('state','in',statusList)],order='engineering_revision'))
        return list(set(allIDs))

    def _extract_data(self,cr,uid,allIDs, queueFiles, fixedformat, kindBomname='normal', anag_Data={}, anag_fields=False, rel_fields=False, transferdata={},partLengths={},bomLengths={}):
        """
            action to be executed for Transmitted state.
            Transmit the object to ERP Metodo
        """
        
        def getChildrenBom(component, kindName):
            for bomid in component.bom_ids:
                if not (str(bomid.type).lower()==kindName.lower()):
                    continue
                return bomid.bom_line_ids
            return []
        
        delimiter=','
        textQuoted=False
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
            if 'separator' in transferdata:
                delimiter="%s" %(str(transferdata['separator']))
            if 'textquoted' in transferdata:
                textQuoted=transferdata['textquoted']
            
        if outputpath==None:
            return True
        if not os.path.exists(outputpath):
            raise osv.except_osv(_('Export Data Error'), _("Requested writing path (%s) doesn't exist." %(outputpath)))
            return False 

        filename=os.path.join(outputpath,fname)
        if fixedformat and (partLengths and bomLengths):
            if not self._export_fixed(filename, anag_Data['labels'], anag_Data, False, partLengths, bomLengths,queueFiles['anagrafica']):
                raise osv.except_osv(_('Export Data Error'), _("No Bom extraction files was generated, about entity (%s)." %(fname)))
                return False
        else:
            if not self._export_csv(filename, anag_Data['labels'], anag_Data, True, delimiter, textQuoted, queueFiles['anagrafica']):
                raise osv.except_osv(_('Export Data Error'), _("Writing operations on file (%s) have failed." %(filename)))
                return False
        
        ext_fields=['parent','child']
        ext_fields.extend(rel_fields)
        for oic in self.browse(cr, uid, allIDs, context=None):
            dataSet=[]
            if not queueFiles['distinte']:
                fname="%s-%s.%s" %(bomname,str(oic.name),exte)
            else:
                fname="%s.%s" %(bomname,exte)
            filename=os.path.join(outputpath,fname)
            for oirel in getChildrenBom(oic, kindBomname):
                rowData=[oic.name,oirel.product_id.name]
                for rel_field in rel_fields:
                    rowData.append(eval('oirel.%s' %(rel_field)))
                dataSet.append(rowData)
            if dataSet:
                expData={'datas': dataSet}
                
                if fixedformat and (partLengths and bomLengths):
                    if not self._export_fixed(filename, ext_fields, expData, False, partLengths, bomLengths):
                        raise osv.except_osv(_('Export Data Error'), _("No Bom extraction files was generated, about entity (%s)." %(fname)))
                        return False
                else:
                    if not self._export_csv(filename, ext_fields, expData, True, delimiter, textQuoted, queueFiles['distinte']):
                        raise osv.except_osv(_('Export Data Error'), _("No Bom extraction files was generated, about entity (%s)." %(fname)))
                        return False
        return True

    def _export_fixed(self, fname, fields=[], result={}, write_title=False, partLengths={}, bomLengths={}, appendFlag=False):
        import csv, stat
        if not ('datas' in result) or not result:
            logging.error("_export_csv : No 'datas' in result.")
            return False

        if not fields:
            logging.error("_export_csv : No 'fields' in result.")
            return False
        
        try:
            existsFile=False
            if os.path.exists(fname):
                existsFile=True
            operational='wb+'
            if appendFlag:
                operational='ab+'
            fp = file(fname, operational)
            results=result['datas']
            for datas in results:
                row = ""
                count=0
                for data in datas:
                    fieldLen=-1
                    if (type(data) is types.StringType):
                        value=str(data).replace('\n',' ').replace('\t','').strip()
                    if (type(data) is types.UnicodeType):
                        value=data.decode('utf8','ignore').replace('\n','').replace('\t','').strip()
                    else:
                        value=(str(data).strip() or '')
                    fieldName=fields[count]
                    if fieldName in partLengths.keys():
                        fieldLen=partLengths[fieldName]
                    elif fieldName in bomLengths.keys():
                        fieldLen=bomLengths[fieldName]                        
                    if (fieldLen<0):
                        continue
                    row +=value.ljust(fieldLen)[:fieldLen]
                    count+=1
                fp.write(row+'\n')
            fp.close()
            os.chmod(fname, stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG)
            return True
        except IOError, (errno, strerror):
            logging.error("_export_csv : IOError : "+str(errno)+" ("+str(strerror)+").")
            return False

    def _export_csv(self, fname, fields=[], result={}, write_title=False, delimiter=',', textQuoted=False, appendFlag=False):
        import csv, stat
        if not ('datas' in result) or not result:
            logging.error("_export_csv : No 'datas' in result.")
            return False

        if not fields:
            logging.error("_export_csv : No 'fields' in result.")
            return False
        
        try:
            quoting=csv.QUOTE_MINIMAL
            existsFile=False
            if os.path.exists(fname):
                existsFile=True
            operational='wb+'
            if appendFlag:
                operational='ab+'
            if textQuoted:
                quoting=csv.QUOTE_NONNUMERIC
            fp = file(fname, operational)
            writer = csv.writer(fp,delimiter=delimiter,quoting=quoting)
            if write_title:
                if not appendFlag:
                    writer.writerow(fields)
                else:
                    if not existsFile:
                        writer.writerow(fields)
            results=result['datas']
            for datas in results:
                row = []
                for data in datas:
                    if (type(data) is types.StringType):
                        row.append(str(data).replace('\n','').replace('\t','').strip())
                    elif (type(data) is types.UnicodeType):
                        row.append(data.decode('utf8','ignore').replace('\n','').replace('\t','').strip())
                    elif (type(data) is types.IntType) or (type(data) is types.LongType):
                         row.append(int(str(data).strip() or 0))
                    elif (type(data) is types.FloatType):
                         row.append(float(str(data).strip() or 0.0))
                    else:
                        row.append(str(data).strip() or '')
                writer.writerow(row)
            fp.close()
            os.chmod(fname, stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG)
            return True
        except IOError, (errno, strerror):
            logging.error("_export_csv : IOError : "+str(errno)+" ("+str(strerror)+").")
            return False

    def _exportData(self, cr, uid, ids, fields=[], bomType='normal'):
        """
            Export data about product and BoM
        """
        listData=[]
        oids=self.browse(cr,uid,ids,context=None)
        for oid in oids:
            row_data={}
            prod_names=oid._all_columns.keys()
            for field in fields:
                if field in prod_names:
                    row_data[field]=oid[field]
            if row_data:
                listData.append(row_data)
                
        return {'datas':listData}

plm_component()


