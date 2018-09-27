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
        logging.error("getFileStream : Exception (%s)reading  stream on file : %s." % (str(ex), objDoc.datas_fname))
    return content


class BookCollector(object):
    def __init__(self, jumpFirst=True, customTest=False, bottomHeight=20):
        """
            jumpFirst = (True/False)
                jump to add number at the first page
            customTest=(True/False,message) / False
                Add page number -> True/False, Custom Message)
        """
        self.jumpFirst = jumpFirst
        self.collector = PdfFileWriter()
        self.customTest = customTest
        self.pageCount = 1
        self.bottomHeight = bottomHeight

    def getNextPageNumber(self, mediaBox, docState):
        def computeFont(x1, y1):
            computedX1 = float(x1) / 2.834
            if y1 > x1:
                # vertical
                if computedX1 <= 298:
                    self.bottomHeight = 6
                    return 6
                return 10
            else:
                # horizontal
                if computedX1 <= 421:
                    self.bottomHeight = 6
                    return 6
                return 10

        pagetNumberBuffer = BytesIO()
        c = canvas.Canvas(pagetNumberBuffer)
        x, _y, x1, y1 = mediaBox
        fontSize = computeFont(x1, y1)
        c.setFont("Helvetica", fontSize)
        if isinstance(self.customTest, tuple):
            page, message = self.customTest
            message = message + '  State:%s' % (docState)
            if page:
                msg = "Page: %r%r" % (self.pageCount, message)
                cha = len(msg)
                c.drawRightString(float(x1) - cha, self.bottomHeight, " Page: %r" % self.pageCount)
                c.drawString(float(x) + 20, self.bottomHeight, message)
            else:
                cha = len(str(message))
                c.drawString(float(x) + 20, self.bottomHeight, message)
        else:
            c.drawRightString(float(x1) - 50, self.bottomHeight, "Page: %r" % self.pageCount)
        c.showPage()
        c.save()
        self.pageCount += 1
        return pagetNumberBuffer

    def addPage(self, pageRes):
        streamBuffer, docState = pageRes
        mainPage = PdfFileReader(streamBuffer)
        for i in range(0, mainPage.getNumPages()):
            if self.jumpFirst:
                self.collector.addPage(mainPage.getPage(i))
                self.jumpFirst = False
            else:
                numberPagerBuffer = self.getNextPageNumber(mainPage.getPage(i).mediaBox, docState)
                numberPageReader = PdfFileReader(numberPagerBuffer)
                pdfPage = mainPage.getPage(i)
                toMerge = numberPageReader.getPage(0)
                pdfPage.mergePage(toMerge)
                pageToAddInCollector = mainPage.getPage(i)
                self.collector.addPage(pageToAddInCollector)

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
        if document.type == 'binary':
            if document.id not in packed:
                appendPage = False
                if document.printout and document.printout != 'None':
                    byteIoStream = BytesIO(base64.b64decode(document.printout))
                    appendPage = True
                elif isPdf(document.datas_fname):
                    value = getDocumentStream(docRepository, document)
                    if value:
                        byteIoStream = BytesIO(value)
                        appendPage = True
                if appendPage:
                    page = PdfFileReader(byteIoStream)
                    _orientation, paper = paperFormat(page.getPage(0).mediaBox)
                    if(paper == 0):
                        output0.append((byteIoStream, document.state))
                    elif(paper == 1):
                        output1.append((byteIoStream, document.state))
                    elif(paper == 2):
                        output2.append((byteIoStream, document.state))
                    elif(paper == 3):
                        output3.append((byteIoStream, document.state))
                    elif(paper == 4):
                        output4.append((byteIoStream, document.state))
                    else:
                        output0.append((byteIoStream, document.state))
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
