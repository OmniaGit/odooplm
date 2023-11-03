##############################################################################
#
#    OmniaSolutions, Your own solutions
#    Copyright (C) 2020-2021 OmniaSolutions (<https://omniasolutions.website>).
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
# Leonardo Cazziolati
# leonardo.cazziolati@omniasolutions.eu
# 23-06-2020
{
    "name": "PLM Breakages Helpdesk",
    "version": "17.0.0.1",
    "author": "OmniaSolutions",
    "website": "https://www.omniasolutions.website",
    "category": "Helpdesk",
    "license": "AGPL-3",
    "summary": "PLM Breakages",
    "depends": ["plm_breakages","helpdesk"],
    "data": [
        # Security
        # Views
        "views/breakages.xml",
        "views/helpdesk_ticket.xml",
    ],
    "installable": True,
}
