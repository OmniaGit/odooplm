# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2022 https://OmniaSolutions.website
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this prograIf not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
Created on 5 May 2022

@author: mboscolo
'''
import os
import logging
import datetime
import tempfile
import subprocess

FORMAT_FROM = ['.pdf','.3ds', '.3mf','.sat', '.sab','.CATPart', '.CATProduct','.3dxml','.dae','.dwg','.dxf','.fbx','.gltf', '.glb','.ifc','.igs', '.iges','.ipt', '.iam', '.jt','.obj','.brep','.x_t', '.x_b','.ply','.prc','.prt', '.asm','.3dm','.prt','.asm', '.par', '.psm','.sldprt', '.sldasm','.stp', '.step','.stl','.u3d','.wrl','.x3d']
FORMAT_TO = ['.pdf','.sat', '.sab','.dae','.dxf','.fbx','.gltf', '.glb','.ifc','.igs', '.iges', '.jt','.obj','.brep','.x_t', '.x_b','.3dm','.stp', '.step','.stl','.u3d','.usd', '.usda', '.usdc', '.usdz','.wrl','.x3d','.png', '.bmp', '.jpeg', '.jpg']

def create_xml_data():
    template="""<record id="update_%s_preview_%s" model="plm.convert.format">
                    <field name="server_id" ref="odoo_local_server"/>
                    <field name="available">Odoo</field>
                    <field name="cad_name">zedxf</field>
                    <field name="start_format">%s</field>
                    <field name="end_format">%s</field>
                </record>"""
    with open("/tmp/data.xml", 'wb') as f:
        for from_format in FORMAT_FROM:
            for to_format in FORMAT_TO:
                f.write(template % (from_format.replace(".",''),
                                    to_format.replace(".",''),
                                    from_format,
                                    to_format))
            
        
def convert(cad_excenge_installation_path, from_file, to_format):
    base_name = os.path.basename(from_file)
    name, exte = os.path.splitext(base_name) 
    if exte.lower() not in FORMAT_FROM:
        raise Exception("Unable to convert file from format %s" % exte)
    if to_format.lower() not in FORMAT_TO:
        raise Exception("Unable to convert file to format %s" % to_format)
    to_file = os.path.join(tempfile.gettempdir() ,base_name.replace(exte,to_format))
    err = subprocess.call([cad_excenge_installation_path, "-i", from_file, "-e", to_file])
    if err!=0:
        raise Exception("Unable to convert file %s to format %s"  %(from_file,to_format))
    return to_file
    #ExchangerConv -i test.jt -e test.png
    
    
    
    
