# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
#    Copyright (C) 2011-2023 https://OmniaSolutions.website
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
Created on 30 Mar 2023

@author: mboscolo
'''
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
L_CHARS =len(CHARS)
#
# this function are copyed from https://stackoverflow.com/a/56826099/1630672 thanks for sharing
#
def str2int(s):
    i = 0
    for c in s:
        i *= L_CHARS
        i += CHARS.index(c)
    return i

def int2str(i, digit=False):
    s = ""
    while i:
        s += CHARS[i % L_CHARS]
        i //= L_CHARS
    s = s[::-1]
    if digit:
        return s.zfill(digit)
    return s
