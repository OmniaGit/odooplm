# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from . import controllers
from . import models
from . import wizards
from . import controllers


def post_init_hook(env):
    """Fill the last CAD upload date of the existing documents from their
    last CAD save, without touching their modification date."""
    env.cr.execute(
        """
        UPDATE ir_attachment a
           SET cad_upload_date = s.write_date
          FROM (SELECT DISTINCT ON (document_id) document_id, write_date
                  FROM plm_cad_open
                 WHERE operation_type = 'save'
                   AND document_id IS NOT NULL
              ORDER BY document_id, create_date DESC) s
         WHERE s.document_id = a.id
        """
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
