# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2019 https://OmniaSolutions.website
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
Created on Sep 11, 2019

@author: mboscolo
'''
import py2exe
from setuptools import setup, find_packages

NAME = "OdooPLMSyncServer"
VERSION = "1.0"

setup(
    name=NAME,
    version=VERSION,
    description="Provide syncronization for file in odoo",
    long_description="",
    classifiers=[],
    author="Matteo Boscolo OmniaSolutions",
    author_email='',
    url='',
    license='Free',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask >= 0.10.1'
    ],
    console=['main.py']
)
