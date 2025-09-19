# -*- coding: utf-8 -*-
##############################################################################
#
#    OmniaSolutions, ERP-PLM-CAD Open Source Solutions
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
"""
Created on 1 Dec 2021

@author: mboscolo
"""
from odoo import models, fields, api

# SaveStructure
# GetExploseSum
# GetExplose
# GetWhereUsedSum
# GetWhereUsed
# ConvertToPlmProduct
# createOrUpdate
# getLastTime
# SaveOrUpdate
# Clone
# NewRevision
# GetUpdated
# GetLatestIds
# SaveStructure
# getLastTime
# GetNextDocumentName
# Clone
# NewRevision
# GetUpdated
# GetLatestIds
# GetRelatedDocs
# GetLastNamesFromID
# CheckIn
# RegMessage
# CheckSaveUpdate
# SaveOrUpdate
# CheckedIn
# UpdateDocuments
# CleanUp
# getCheckedOut
# SaveStructure
# checkout
# search_read
# getServerTime
# getServerTime
# getRelatedLyTree
# action_confirm
# action_release
# wf_message_post_client
# saveRelationNew
# CheckAllFiles
# getPartOfFile
# isDownloadableFromServer
# GetSomeFiles
# CheckIn2
# CheckInRecursive2
# isLatestRevision
# getUserSign
# QueryLast
# GetSomeFiles
# getNewThreadTransaction
# getErrorMissingDocument
# GetProductDocumentId
# getRelated3DFiles
#
#
# CallCustomFunction
# cleanZipArchives
# checkNewer
# checkUnlinkCadOpen
#
# callCustomMethodNoDisplay
#
# getCustomProcedure
# getMacros
# getMacroUserInfos
# create_server_syncronize
# clientCanIUpload
# notifieDoneToDbThread
# freezeDbThread
# saveSingleLevel
# preCheckInRecursive
# preCheckOutRecursive
#


class PLMAccessObject(models.Model):
    _name = "plm.access"
    _description = "PLM Access"

    name = fields.Char("Name")


class PlmClient(models.TransientModel):
    _name = "plm.client"
    _description = "PLM Client Support object"

    def getFileStructure(self, ir_attachemnt_id, hostname, pws_path, latest=False):
        """
        get all the relation of the passed attachment and their status
        :ir_attachment_id int id of object ir_attachment
        :hostname client host name
        :pws_path client pws path
        :return: list of [{<ir_attachment_attrivutes>}]
        """
        out = []
        ir_attachemnt = self.env["ir.attachment"]
        for ir_attachment_id in ir_attachemnt.search([("id", "=", ir_attachemnt_id)]):
            #
            if latest:
                ir_attachment_id = ir_attachment_id.get_latest_version()[0]
            out.extend(ir_attachment_id.computeDownloadStatus(hostname, pws_path))
            #
            if ir_attachment_id.is2D():
                for related_attachment_id in ir_attachment_id.getRelatedLyTreeNew(
                    latest=latest
                ):
                    out.extend(
                        related_attachment_id.computeDownloadStatus(hostname, pws_path)
                    )
            #
            for children_attachment_id in ir_attachment_id.getRelatedHiTreeNew(
                recursion=True, getRftree=True, latest=latest
            ):
                #
                out.extend(
                    children_attachment_id.computeDownloadStatus(hostname, pws_path)
                )
            #
        return out

    def getAttachmentFromProp(self, document_attributes):
        """
        Get The attachment from a dictionary
        check before from id and the from minimun property
        """
        attach_object = self.env["ir.attachment"]
        attach_id = document_attributes.get("id")
        if attach_id:
            ir_browse = attach_object.browse(attach_id)
        else:
            ir_browse = attach_object.search(
                [
                    (
                        "engineering_code",
                        "=",
                        document_attributes.get("engineering_code", ""),
                    ),
                    (
                        "engineering_revision",
                        "=",
                        document_attributes.get("engineering_revision", -1),
                    ),
                ]
            )
        return ir_browse

    @api.model
    def attachmentCanBeSaved(
        self,
        document_attributes,
        raiseError=False,
        returnCode=False,
        skipCheckOutControl=False,
    ):
        """
        Check if the document can be saved !!
        """
        for brwItem in self.getAttachmentFromProp(document_attributes):
            return brwItem.canBeSaved(
                raiseError=raiseError,
                returnCode=returnCode,
                skipCheckOutControl=skipCheckOutControl,
            )
        return True, ""

    @api.model
    def attachmentCheckOut(
        self, document_attributes, hostName, hostPws, showError=True
    ):
        """
        perform the check out operation from document attributes
        """
        for brwItem in self.getAttachmentFromProp(document_attributes):
            return brwItem.checkout(
                hostName=hostName, hostPws=hostPws, showError=showError
            )
        return True, ""

    @api.model
    def getNotCopiableFields(self, model_name):
        """
        return a non copiable fields name
        """
        return (
            self.env["ir.model.fields"]
            .sudo()
            .search([("model", "in", model_name), ("copied", "=", False)])
            .mapped("name")
        )

    @api.model
    def check_pre_download_data(self, args):
        """
        function used for prefetch easely the data fro the download function
        :attachemnt id to downalod
        :last_revision get latest version of the file
        :out list of result
        """
        attachment_ids, last_revision = args
        out = []
        for attachment_id in self.env["ir.attachment"].search(
            [("id", "in", attachment_ids)]
        ):
            if last_revision:
                attachment_id = attachment_id.get_latest_version()[0]
            out.append(attachment_id.get_open_attachment_data_out())
        return out

    def CheckAllFiles(self, request, default=None):
        """
        Evaluate documents to return
        """
        forceFlag = False
        outIds = []
        doc_id, listedFiles, selection, hostname, hostpws = request
        docBrws = self.browse(doc_id)
        outIds.append(doc_id)
        if selection is False:
            selection = 1  # Case of selected
        if selection < 0:  # Case of force refresh PWS
            forceFlag = True
            selection = selection * (-1)
        if docBrws.is2D():
            outIds.extend(self.getRelatedLyTree(doc_id))
        outIds.extend(self.getRelatedHiTree(doc_id, recursion=True, getRftree=True))
        outIds = list(set(outIds))
        if selection == 2:  # Case of latest
            outIds = self._getlastrev(outIds)
        return self._data_check_files(
            outIds, listedFiles, forceFlag, False, hostname, hostpws
        )

    def getCopyField(self, src_model):
        return (
            self.env["ir.model.fields"]
            .sudo()
            .search([("model", "=", src_model), ("copied", "=", True)])
            .mapped("name")
        )
