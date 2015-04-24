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
from datetime import datetime
from sqlalchemy import *
import logging

from openerp.osv import osv, fields

def normalize(value):
    if (type(value) is types.StringType):
        return str(value).replace('"','\"').replace("'",'\"').replace("%","%%").strip()
    elif (type(value) is types.UnicodeType):
        return unicode(str(value).replace('"','\"').replace("'",'\"').replace("%","%%").strip(), 'Latin1')
    else:
        return str(value).strip()


def get_connection(dataConn):
    """
        Get last execution date & time as stored.
            format => '%Y-%m-%d %H:%M:%S'
    """
    connection=False
    try:
        connectionString=r'%s://%s:%s@%s/%s' %(dataConn['protocol'],dataConn['user'],dataConn['password'],dataConn['host'],dataConn['database'])
        engine = create_engine(connectionString, echo=False)
        connection = engine.connect()
    except Exception,ex:
        logging.error("[get_connection] : Error to connect (%s)." %(str(ex)))
    return connection

def saveParts(ObjectOE, cr, uid, connection, prtInfos, targetTable, datamap, datatyp):
    """
        Updates parts if exist in DB otherwise it create them.
    """
    checked={}
    if connection:
        trans = connection.begin()
        for prtInfo in prtInfos:
            prtDict=dict(zip(datamap.keys(),prtInfo))

            if 'name' in prtDict:
                prtName=prtDict['name']
            else:
                continue

            string1="delete from %s where %s='%s'" %(targetTable,datamap['name'],normalize(prtName))
            connection.execution_options(autocommit=False).execute(string1)
                             
            separator=""
            namesString=""
            valuesString=""
            for column in prtDict.keys():
                if (datatyp[column] == 'datetime'):
                    namesString+="%s %s" %(separator,datamap[column])
                    if prtDict[column]:
                        valuesString+="%s '%s'" %(separator,datetime.strptime(prtDict[column],"%Y-%m-%d %H:%M:%S"))
                    else:
                        valuesString+="%s '%s'" %(separator,datetime.strptime(datetime.now(),"%Y-%m-%d %H:%M:%S"))
                elif (datatyp[column] == 'int'):
                    if not prtDict[column]:
                        tmpVal=0
                    else:
                        tmpVal=prtDict[column]
                    namesString+="%s %s" %(separator,datamap[column])
                    valuesString+="%s %d" %(separator,int(tmpVal))
                elif (datatyp[column] == 'bool'):
                    if not prtDict[column]:
                        tmpVal=0
                    else:
                        tmpVal=prtDict[column]
                    namesString+="%s %s" %(separator,datamap[column])
                    valuesString+="%s %d" %(separator,int(tmpVal))
                elif (datatyp[column] =='float'):
                    if not prtDict[column]:
                        tmpVal=0.0
                    else:
                        tmpVal=prtDict[column]
                    namesString+="%s %s" %(separator,datamap[column])
                    valuesString+="%s %f" %(separator,float(tmpVal))
                elif (datatyp[column] == 'char'):
                    namesString+="%s %s" %(separator,datamap[column])
                    valuesString+="%s '%s'" %(separator,normalize(prtDict[column]).replace("False",''))
                if len(namesString)>0:
                    separator=","

            try:
                string1="insert into %s (%s) values (%s)" %(targetTable,namesString,valuesString)
                connection.execution_options(autocommit=False).execute(string1)
                checked[prtName]=prtDict
            except Exception,ex:
                checked[prtName]=False
        trans.commit()
    return checked

def saveBoms(ObjectOE, cr, uid, connection, checked, allIDs, dataTargetTable, datamap, datatyp, kindBomname, bomTargetTable, parentColName, childColName, bomdatamap, bomdatatyp):

    
    def checkChildren(ObjectOE, cr, uid, connection, components, datamap):
        for component in components:
            for bomid in component.bom_ids:
                if not (str(bomid.type).lower()==kindName):
                    continue
                for bom in bomid.bom_lines:
                    if not bom.product_id.name in childNames:
                        childNames.append(bom.product_id.name)
                        childIDs.append(bom.product_id.id)
                        
        tmpData=ObjectOE.export_data(cr, uid, childIDs, datamap.keys())
        return saveParts(ObjectOE, cr, uid, connection, tmpData.get('datas'), dataTargetTable, datamap, datatyp)

    def removeBoms(connection, bomTargetTable, parentColName, parentName):
        trans = connection.begin()
        try:
            string1="delete from %s where %s = '%s'" %(bomTargetTable,parentColName,parentName)
            connection.execution_options(autocommit=False).execute(string1)
        except Exception,ex:
            logging.error("[saveBoms::removeBoms] : Exception (%s) cleaning bom (%s)." %(str(ex),parentName))
        trans.commit()

    kindName=kindBomname.lower()
    relation=False
    childNames=checked.keys()
    childIDs=[]
    entityChecked=checked
    
    if connection:
        trans = connection.begin()
        components=ObjectOE.browse(cr, uid, allIDs)
        entityChecked.update(checkChildren(ObjectOE, cr, uid, connection, components, datamap))
                         
        for component in components:
            if not component.name in entityChecked.keys():
                logging.error("[saveBoms] : Product (%s) is not in current data package." %(component.name))
                continue
            entityFather=entityChecked[component.name]
            if not entityFather:
                logging.error("[saveBoms] : Product (%s), as father, seems it could be not saved." %(component.name))
                continue
            
            for bomid in component.bom_ids:
                if not (str(bomid.type).lower()==kindName):
                    continue
                
                removeBoms(connection, bomTargetTable, parentColName, component.name)

                for bom in bomid.bom_lines:
                    if not bom.product_id.name in entityChecked.keys():
                        logging.error("[saveBoms] : Product (%s) is not in current data package." %(bom.product_id.name))
                        continue

                    entityChild=entityChecked[bom.product_id.name]
                    if not entityChild:
                        logging.error("[saveBoms] : Product (%s), as child, seems it could be not saved." %(bom.product_id.name))
                        continue

                    separator=","
                    namesString="%s, %s" %(parentColName, childColName)
                    valuesString="'%s', '%s'" %(normalize(component.name),normalize(bom.product_id.name))
                    
                    expData=ObjectOE.pool.get('mrp.bom').export_data(cr, uid, [bom.id], bomdatamap.keys())
                    if expData.get('datas'):
                        bomDict=dict(zip(bomdatamap.keys(),expData.get('datas')[0]))                                       
                        for column in bomDict:
                            if (bomdatatyp[column] == 'datetime'):
                                if bomDict[column]:
                                    namesString+="%s %s" %(separator,bomdatamap[column])
                                    valuesString+="%s '%s'" %(separator,datetime.strptime(bomDict[column],"%Y-%m-%d %H:%M:%S"))
                            elif (bomdatatyp[column] == 'int'):
                                namesString+="%s %s" %(separator,bomdatamap[column])
                                valuesString+="%s %d" %(separator,int(bomDict[column]))
                            elif (bomdatatyp[column] == 'bool'):
                                namesString+="%s %s" %(separator,bomdatamap[column])
                                valuesString+="%s %d" %(separator,bomDict[column])
                            elif (bomdatatyp[column] =='float'):
                                namesString+="%s %s" %(separator,bomdatamap[column])
                                valuesString+="%s %f" %(separator,float(bomDict[column]))
                            elif (bomdatatyp[column] == 'char'):
                                namesString+="%s %s" %(separator,bomdatamap[column])
                                valuesString+="%s '%s'" %(separator,normalize(bomDict[column]).replace("False",''))

                        try:
                            string1="insert into %s (%s) values (%s)" %(bomTargetTable, namesString,valuesString)
                            connection.execution_options(autocommit=False).execute(string1)
                        except Exception:
                            logging.error("[saveBoms] : Parent (%s) Child (%s), relation not saved." %(component.name,bom.product_id.name))
        trans.commit()
        return True

    return False
