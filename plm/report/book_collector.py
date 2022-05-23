import os
import base64
from io import BytesIO
import logging
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileWriter, PdfFileReader
from datetime import datetime
from dateutil import tz


def isPdf(fileName):
    if not fileName:
        return False
    if (os.path.splitext(fileName)[1].lower() == '.pdf'):
        return True
    return False


def getBottomMessage(user, context):
    to_zone = tz.gettz(context.get('tz', 'Europe/Rome'))
    from_zone = tz.tzutc()
    dt = datetime.now()
    dt = dt.replace(tzinfo=from_zone)
    localDT = dt.astimezone(to_zone)
    localDT = localDT.replace(microsecond=0)
    return "Printed by %r : %r " % (user.name, localDT.ctime())


def getDocumentStream(docRepository, objDoc):
    """
        Gets the stream of a file
    """
    content = False
    try:
        if (not objDoc.store_fname) and (objDoc.db_datas):
            content = base64.b64decode(objDoc.db_datas)
        else:
            content = file(os.path.join(docRepository, objDoc.store_fname), 'rb').read()
    except Exception as ex:
        logging.error("getFileStream : Exception (%s)reading  stream on file : %s." % (str(ex), objDoc.name))
    return content


class BookCollector(object):
    def __init__(self, jumpFirst=True, customText=False, bottomHeight=20, poolObj=None):
        """
            jumpFirst = (True/False)
                jump to add number at the first page
            customText=(True/False,message) / False
                Add page number -> True/False, Custom Message)
        """
        self.jumpFirst = jumpFirst
        self.collector = PdfFileWriter()
        self.customText = customText
        self.pageCount = 1
        self.bottomHeight = bottomHeight
        self.poolObj = poolObj

    def evalDictVals(self, dict_vals, doc_obj, page_count, user_id):
        out = {}
        for key, val in dict_vals.items():
            try:
                if 'doc_obj' in val:
                    val = eval(val)
                elif 'page_count' in val:
                    val = eval(val)
                elif 'user_id' in val:
                    val = eval(val)
            except Exception as ex:
                logging.error('Cannot eval attribute %r for report due to error %r' % (val, ex))
            out[key] = val or ''
        return out
            
    def getNextPageNumber(self, mediaBox, docObject):

        def computeFont(x1, y1):
            computedX1 = float(x1)/2.834
            if y1 > x1:
                doc_orientation = 'vertical'
                #vertical
                if computedX1 <= 298:
                    self.bottomHeight = 6
                    return 6, doc_orientation
                return 10, doc_orientation
            else:
                doc_orientation = 'horizontal'
                #horizontal
                if computedX1 <= 421:
                    self.bottomHeight = 6
                    return 6, doc_orientation
                return 10, doc_orientation

        pagetNumberBuffer = BytesIO()
        c = canvas.Canvas(pagetNumberBuffer)
        x, _y, x1, y1 = mediaBox
        fontSize, doc_orientation = computeFont(x1, y1)
        c.setFont("Helvetica", fontSize)
        if isinstance(self.customText, tuple):
            msg, msg_vals = self.customText
            msg_vals = self.evalDictVals(msg_vals, docObject, self.pageCount, self.poolObj.user)
            end_msg = msg % msg_vals
            cha = len(end_msg)
            c.drawRightString(float(x1) - cha, self.bottomHeight, " Page: %r" % self.pageCount)
            c.drawString(float(x) + 20, self.bottomHeight, end_msg)
        else:
            c.drawRightString(float(x1) - 50, self.bottomHeight, "Page: %r" % self.pageCount)
        self.pageCount += 1
        return pagetNumberBuffer, c, doc_orientation

    def addPage(self, pageRes):
        streamBuffer, docObject = pageRes
        mainPage = PdfFileReader(streamBuffer,strict=False)
        for i in range(0, mainPage.getNumPages()):
            try:
                if self.jumpFirst:
                    self.collector.addPage(mainPage.getPage(i))
                    self.jumpFirst = False
                else:
                    page = mainPage.getPage(i)
                    numberPagerBuffer, canvas, doc_orientation = self.getNextPageNumber(page.mediaBox, docObject)
                    try:
                        _orientation, paper = paperFormat(page.mediaBox)
                        self.poolObj.get('ir.attachment').advancedPlmReportEngine(document=docObject,
                                                                                  canvas=canvas,
                                                                                  page_orientation=doc_orientation,
                                                                                  paper=paper,
                                                                                  page_obj=page)
                    except Exception as ex:
                        logging.warning(ex)
                        logging.warning('advancedPlmReportEngine function not implemented in plm.document object')
                    canvas.showPage()
                    canvas.save()
                    numberPageReader=PdfFileReader(numberPagerBuffer,strict=False)  
                    mainPage.getPage(i).mergePage(numberPageReader.getPage(0))
                    self.collector.addPage(mainPage.getPage(i))
            except Exception as ex:
                logging.error(ex)
                logging.error('Something went wrong during pdf generation')

    def printToFile(self, fileName):
        outputStream = open(fileName, "wb")
        self.collector.write(outputStream)
        outputStream.close()


def packDocuments(docRepository, documents, bookCollector):
    """
        pack the documenta for paper size
    """
    packed = []
    output0 = []
    output1 = []
    output2 = []
    output3 = []
    output4 = []
    if not bookCollector:
        bookCollector = BookCollector()
    for document in documents:
        if document.id not in packed:
            appendPage = False
            if document.printout and document.printout != 'None':
                byteIoStream = BytesIO(base64.b64decode(document.printout))
                appendPage = True
            elif isPdf(document.name):
                value = getDocumentStream(docRepository, document)
                if value:
                    byteIoStream = BytesIO(value)
                    appendPage = True
            if appendPage:
                page = PdfFileReader(byteIoStream,strict=False)
                _orientation, paper = paperFormat(page.getPage(0).mediaBox)
                if(paper == 0):
                    output0.append((byteIoStream, document))
                elif(paper == 1):
                    output1.append((byteIoStream, document))
                elif(paper == 2):
                    output2.append((byteIoStream, document))
                elif(paper == 3):
                    output3.append((byteIoStream, document))
                elif(paper == 4):
                    output4.append((byteIoStream, document))
                else:
                    output0.append((byteIoStream, document))
                packed.append(document.id)
    for pag in output0 + output1 + output2 + output3 + output4:
        bookCollector.addPage(pag)
    if bookCollector is not None:
        pdf_string = BytesIO()
        bookCollector.collector.write(pdf_string)
        out = pdf_string.getvalue()
        pdf_string.close()
        return (out, 'pdf')
    return (False, '')


def paperFormat(_boundingBox):
        """
            Get Paper dimensions from drawing
        """
        orientation = 1                                 # 0 - Portrait, 1 - LandScape
        paper = 4
        clearance = 5
        defaultUSpace = 25.4 / 72.0
        minX, minY = _boundingBox.lowerLeft
        maxX, maxY = _boundingBox.upperRight
        deltaX = maxX - minX
        deltaY = maxY - minY
        if deltaX > deltaY:
            measureX = float(deltaX)
            measureY = float(deltaY)
            orientation = 1                             # Landscape
        else:
            measureX = float(deltaY)
            measureY = float(deltaX)
            orientation = 0                             # Portrait

        minX = (measureX * defaultUSpace) - clearance
        maxX = (measureX * defaultUSpace) + clearance
        minY = (measureY * defaultUSpace) - clearance
        maxY = (measureY * defaultUSpace) + clearance

        if minX >= 1180 and minX <= 1196:
            paper = 0                                     # Format A0
            return (orientation, paper)
        elif minX >= 834 and minX <= 848:
            paper = 1                                     # Format A1
            return (orientation, paper)
        elif minX >= 587 and minX <= 601:
            paper = 2                                     # Format A2
            return (orientation, paper)
        elif minX >= 413 and minX <= 427:
            paper = 3                                     # Format A3
            return (orientation, paper)
        elif minX >= 290 and minX <= 304:
            paper = 4                                     # Format A4
            return (orientation, paper)
        return (orientation, paper)
