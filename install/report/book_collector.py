import StringIO
from reportlab.pdfgen import canvas

# NOTE : TO BE ADDED TO FINAL CONFIGURATION. NOT IN STANDARD PYTHON
from pyPdf import PdfFileWriter, PdfFileReader
# NOTE : TO BE ADDED TO FINAL CONFIGURATION. NOT IN STANDARD PYTHON

from report.render import render
import base64
class BookCollector(object):
    def __init__(self,jumpFirst=True,customTest=False,bottomHeight=20):
        """
            jumpFirst = (True/False)
                jump to add number at the first page
            customTest=(True/False,message) / False
                Add page number -> True/Fale, Custom Message)
        """
        self.jumpFirst=jumpFirst
        self.collector=PdfFileWriter()
        self.customTest=customTest
        self.pageCount=1
        self.bottomHeight=bottomHeight
        
    def getNextPageNumber(self,mediaBox):
        pagetNumberBuffer = StringIO.StringIO()
        c = canvas.Canvas(pagetNumberBuffer)
        x,y,x1,y1 = mediaBox
        if isinstance(self.customTest,tuple):
            page,message=self.customTest
            if page:
                msg="Page: "+str(self.pageCount) +str(message)
                cha=len(msg)
                c.drawRightString(float(x1)-cha,self.bottomHeight," Page: "+str(self.pageCount))
                c.drawString(float(x)+20,self.bottomHeight,str(message))
            else:
                cha=len(str(message))
                c.drawString(float(x)+20,self.bottomHeight,str(message))
        else:
            c.drawRightString(float(x1)-50,self.bottomHeight,"Page: "+str(self.pageCount))
        c.showPage()
        c.save()
        self.pageCount+=1
        return pagetNumberBuffer
    
    def addPage(self,streamBuffer):
        if streamBuffer.len<1:
            return False
        mainPage=PdfFileReader(streamBuffer)
        for i in range(0,mainPage.getNumPages()):
            if self.jumpFirst:
                self.collector.addPage(mainPage.getPage(i))
                self.jumpFirst=False
            else:
                numberPagerBuffer=self.getNextPageNumber(mainPage.getPage(i).mediaBox)
                numberPageReader=PdfFileReader(numberPagerBuffer)  
                mainPage.getPage(i).mergePage(numberPageReader.getPage(0))
                self.collector.addPage(mainPage.getPage(i))
    
    def printToFile(self,fileName):  
        outputStream = file(fileName, "wb")
        self.collector.write(outputStream)
        outputStream.close()

class external_pdf(render):

    """ Generate External PDF """

    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type = 'pdf'

    def _render(self):
        return self.pdf
            
def packDocuments(documents,bookCollector):
    """
        pack the documenta for paper size
    """
    packed=[]
    output0 = [] 
    output1 = [] 
    output2 = []
    output3 = [] 
    output4 = []
    for document in documents:
        if document.printout:
            if not document.id in packed:   
                input1 = StringIO.StringIO(base64.decodestring(document.printout))
                page=PdfFileReader(input1)
                orientation,paper=paperFormat(page.getPage(0).mediaBox)
                if(paper==0)  :
                    output0.append(input1)
                elif(paper==1):
                    output1.append(input1)
                elif(paper==2):
                    output2.append(input1)
                elif(paper==3):
                    output3.append(input1)
                elif(paper==4):
                    output4.append(input1)
                else: 
                    output0.append(input1)
                packed.append(document.id)
    for pag in output0+output1+output2+output3+output4:
        bookCollector.addPage(pag)
    if bookCollector != None:
        pdf_string = StringIO.StringIO()
        bookCollector.collector.write(pdf_string)
        obj = external_pdf(pdf_string.getvalue())
        obj.render()
        pdf_string.close()
        return (obj.pdf, 'pdf')
    return (False, '')

def paperFormat(_boundingBox):
        """
            Get Paper dimensions from drawing
        """
        orientation = 1                                 # 0 - Portrait, 1 - LandScape
        paper=4
        clearance = 5
        defaultUSpace=25.4/72.0
        minX,minY=_boundingBox.lowerLeft
        maxX,maxY=_boundingBox.upperRight
        deltaX=maxX-minX
        deltaY=maxY-minY
        if deltaX > deltaY:
            measureX = float(deltaX)
            measureY = float(deltaY)
            orientation = 1                             # Landscape
        else:
            measureX = float(deltaY)
            measureY = float(deltaX)
            orientation = 0                             # Portrait
            
        minX = (measureX*defaultUSpace) - clearance
        maxX = (measureX*defaultUSpace) + clearance
        minY = (measureY*defaultUSpace) - clearance
        maxY = (measureY*defaultUSpace) + clearance
        
        if minX>=1180 and minX<=1196:
            paper=0                                     # Format A0
            return (orientation, paper)
        elif minX>=834 and minX<=848:
            paper=1                                     # Format A1
            return (orientation, paper)
        elif minX>=587 and minX<=601:
            paper=2                                     # Format A2
            return (orientation, paper)
        elif minX>=413 and minX<=427:
            paper=3                                     # Format A3
            return (orientation, paper)
        elif minX>=290 and minX<=304:
            paper=4                                     # Format A4
            return (orientation, paper)
        return (orientation, paper)