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
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import sys
import types
import logging
import copy
import stat
import openerp.addons.decimal_precision as dp
from openerp import models
from openerp import fields
from openerp import api
from openerp import SUPERUSER_ID
from openerp import _
from openerp import osv
from openerp.exceptions import UserError
_logger         =   logging.getLogger(__name__)

# To be adequated to plm.document class states
USED_STATES = [('draft', _('Draft')),
               ('confirmed', _('Confirmed')),
               ('released', _('Released')),
               ('undermodify', _('UnderModify')),
               ('obsoleted', _('Obsoleted'))]

def _moduleName():
    path = os.path.dirname(__file__)
    return os.path.basename(os.path.dirname(path))
openerpModule=_moduleName()


