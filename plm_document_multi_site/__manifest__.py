##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solution
#    Copyright (C) 2011-2021 https://OmniaSolutions.website
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
{
    "name": "PLM Document Syncronization",
    "version": "15.0.3",
    "author": "OmniaSolutions",
    "website": "https://github.com/OmniaGit/odooplm",
    "category": "Product Lifecycle Management",
    "sequence": 15,
    "license": "AGPL-3",
    "summary": "PLM document server syncronization",
    "images": [],
    "depends": ["plm"],
    "data": [
        "views/ir_attachment.xml",
        "views/plm_remote_server.xml",
        "views/plm_document_action_syncronize.xml",
        "data/server_action.xml",
        "security/base_plm_web_rev_security.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
