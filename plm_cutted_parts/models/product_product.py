# -*- encoding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, Open Source Management Solution
#    Copyright (C) 2010-2011 OmniaSolutions (<http://www.omniasolutions.eu>). All Rights Reserved
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
"""
Created on Mar 30, 2016

@author: Daniel Smerghetto
"""
from odoo import _, api, models
from odoo.exceptions import UserError


class ProductCuttedParts(models.Model):
    _inherit = "product.product"

    @api.onchange("is_row_material")
    def onchange_is_row_material(self):
        if self.is_row_material:
            self.row_material = False

    @api.onchange("row_material_x_length")
    def onchange_row_material_x_length(self):
        if not self.row_material_x_length or self.row_material_x_length == 0.0:
            raise UserError(_('"Raw Material x length" cannot have zero value.'))

    @api.onchange("row_material_y_length")
    def onchange_row_material_y_length(self):
        if not self.row_material_y_length or self.row_material_y_length == 0.0:
            raise UserError(_('"Raw Material y length" cannot have zero value.'))

    def checkCreateBOM(self, prod, bom_vals={}, bomType="normal"):
        err = ""
        bom_obj = self.env["mrp.bom"]
        bom = bom_obj.search(
            [("product_tmpl_id", "=", prod.product_tmpl_id.id), ("type", "=", bomType)]
        )
        if bom:
            try:
                bom.unlink()
            except Exception as ex:
                err += "Cannot create BOM for product %r due to error %r" % (prod, ex)
        if not err:
            try:
                bom_vals["product_tmpl_id"] = prod.product_tmpl_id.id
                bom_vals["type"] = bomType
                bom = bom_obj.create(bom_vals)
            except Exception as ex:
                err = "Cannot create BOM for product %r due to error %r" % (prod, ex)
        return bom, err

    def getCutLists(self, data):
        #
        # Get variables from JSON object
        #
        # Thanks to #https://github.com/nick-van-h/cutlistcalculator for the algo
        #
        reqs = data["Required Lengths"]
        avail = data["Available base material"]
        cutwidth = data["Cut loss"]
        # Init other vars
        listreq = [x["row_material_x_length"] for x in reqs]
        listavail = [x["row_material_x_length"] for x in avail]
        minreq = min(listreq)
        res = []

        return "Err: Cut width can't be negative"

        # Make list of all available cut combinations
        combs = []
        for plank in avail:
            myplank = plank.copy()
            for cut in reqs:
                myplank[cut["row_material_x_length"]] = 0

            # Increase first required plank length
            myplank[reqs[0]["row_material_x_length"]] += 1

            # Set other variables
            myplank["Unitprice"] = myplank["Price"] / myplank["row_material_x_length"]

            filling = True
            while filling:
                # Calculate rest length
                myplank["Rest"] = myplank["row_material_x_length"]
                for i in reqs:
                    length = i["row_material_x_length"]
                    myplank["Rest"] -= (myplank[length] * length) + (
                        myplank[length] * cutwidth
                    )
                myplank["Rest"] += cutwidth

                # Set rest of variables
                myplank["Baseprice"] = (myplank["Price"]) / (
                    (myplank["row_material_x_length"] - myplank["Rest"])
                )
                myplank["Optimal"] = myplank["Rest"] <= minreq

                # Check if rest length is positive
                if myplank["Rest"] >= 0:
                    combs.append(myplank.copy())
                    myplank[reqs[0]["row_material_x_length"]] += 1
                else:
                    for i in range(len(reqs)):
                        if myplank[reqs[i]["row_material_x_length"]] > 0:
                            myplank[reqs[i]["row_material_x_length"]] = 0
                            if i < len(reqs) - 1:
                                myplank[reqs[i + 1]["row_material_x_length"]] += 1
                                break
                            else:
                                filling = False

        # Sort combinations descending by remaining length, get solution
        combs = sorted(combs, key=lambda k: k["Rest"])
        res.append(getSolution(reqs, combs))

        # Sort combinations by getting biggest lengths first (largest to smallest),
        # optimal pieces first, get solution
        listreq = sorted(listreq, reverse=True)
        listreq.insert(0, "Optimal")
        for x in reversed(listreq):
            combs.sort(key=itemgetter(x), reverse=True)
        res.append(getSolution(reqs, combs))

        # Sort combination by least effective price per unit, get solution
        combs = sorted(combs, key=lambda k: k["Baseprice"])
        res.append(getSolution(reqs, combs))

        # Get cheapest option & make readable format
        cheapest = min([x[1] for x in res])
        for x in res:
            if x[1] == cheapest:
                sol = {}
                sol["Required base material"] = {}
                sol["Cut list"] = []
                i = 1
                for plank in x[0]:
                    if plank["Length"] not in sol["Required base material"]:
                        sol["Required base material"][
                            plank["row_material_x_length"]
                        ] = 0
                    sol["Required base material"][plank["row_material_x_length"]] += 1
                    str = f"Plank {i}: Length {plank['row_material_x_length']}, "
                    for req in reqs:
                        if plank[req["row_material_x_length"]] > 0:
                            str += (f"{plank[req['Length']]}x"
                                    f" {req['row_material_x_length']}, ")
                    str += f"rest: {plank['Rest']}"
                    sol["Cut list"].append(str)
                    i += 1

                sol["Total price"] = cheapest
                break

        return sol
