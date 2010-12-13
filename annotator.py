#! /usr/bin/python

#annotator.py

import sys, os, copy, time
from PyQt4 import QtGui, QtCore
from ui_mainwindow import Ui_mainWindow
from xml.dom.minidom import Document, CDATASection
from xml.dom import minidom
import Image, ImageFilter, ImageMath, ImageChops

splashTime = 3                                      #splash screen duration in seconds
extensions = (".png",".jpg")                        # image file extensions to filter
currentTool = "point"                               # string to describe current tool
modes = {"point":"click", "rectangle":"draw", "":""}    # modes for tools
currentIndex = 0                                    # index of current image
points = []                                         # point coordinates for images
zoomPoints = []                                     # point coordinates for the zoomed image
zoomAmount = 3                                      # the image is zoomed "zoomAmount" times
pointWidth = 3                                      # width of the red points (is to be odd)
# penColor = QtCore.Qt.red                            # pen color for points/rectangles
penColor = QtGui.QColor(255,0,0)                            # pen color for points/rectangles
warningTimeout = 10000                              # time in miliseconds to show warning message
indicesVisible = True                               # visibility of indices of points/rectangles
pointsVisible = True                                # visibility of points
rectanglesVisible = True                            # visibility of rectangles
useSmartColor = True                                # smart coloring of the points
currentImage = []                                   # current PIL image, filtered, and probabilities extracted
undoRedoStatus = []									# flags for undo/redo actions to enable/disable them
annotationChanged = []								# flags for images to determine changes in annotation
lastSavedState = 0									# QUndoStack index for the last state that is saved

def getSmartColor(intensity):
    return min(15*intensity,255), 50, 100

class CommandDragPoint(QtGui.QUndoCommand):
	global points, zoomPoints, zoomAmount
	def __init__(self, index, before, after, description):
		super(CommandDragPoint, self).__init__(description)
		self.pointList = points[index]
		self.point1 = before
		self.point2 = after
		self.zoomStack = []

	def redo(self):
		try:
			self.pointList[self.pointList.index(self.point1)] = self.point2
			if len(self.zoomStack) > 0:
				zoomPoints.append(self.zoomStack.pop())
		except ValueError:
			pass
		
	def undo(self):
		try:
			self.pointList[self.pointList.index(self.point2)] = self.point1
			if len(zoomPoints) > 0:
				self.zoomStack.append(zoomPoints.pop())
		except ValueError:
			pass

class CommandAddPoint(QtGui.QUndoCommand):
	global points, zoomPoints, zoomAmount
	def __init__(self, index, point, description):
		super(CommandAddPoint, self).__init__(description)
		self.pointList = points[index]
		self.point = point
		self.zoomStack = []

	def redo(self):
		self.pointList.append(self.point)
		if len(self.zoomStack) > 0:
			zoomPoints.append(self.zoomStack.pop())
		
	def undo(self):
		item = self.pointList.pop()
		if len(zoomPoints) > 0:
			self.zoomStack.append(zoomPoints.pop())
		#del item 		
    
class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        global pointWidth
        QtGui.QMainWindow.__init__(self)

        # Set up the user interface from Designer.
        self.ui = Ui_mainWindow()
        self.ui.setupUi(self)
        self.setCentralWidget(self.ui.scrollArea)
		
        self.undoStacks = []
        self.connectSignals()

        self.ui.dotClickButton.hide()
        self.ui.dotDragButton.hide()
        self.ui.rectClickButton.hide()
        self.ui.rectDragButton.hide()
        
        self.ui.saveAction.setEnabled(False)

        self.dragIsActive = False
        if indicesVisible:
            self.ui.indicesAction.setChecked(True)
        if pointsVisible:
            self.ui.pointsAction.setChecked(True)
        if rectanglesVisible:
            self.ui.rectanglesAction.setChecked(True)

            
        # Force pointwidth to be odd
        if pointWidth % 2 == 0:
            pointWidth += 1

        self.ui.zoomImage.paint = QtGui.QPainter()
        self.ui.zoomImage.pen = QtGui.QPen(penColor)
        self.ui.zoomImage.pen.setWidth(pointWidth*zoomAmount)
        self.ui.zoomImage.crossPen = QtGui.QPen(QtCore.Qt.black)
        self.ui.zoomImage.crossPen.setWidth(1)

        self.ui.image.paint = QtGui.QPainter()
        self.ui.image.pen = QtGui.QPen(penColor)
        
        self.ui.coo = QtGui.QLabel()
        self.ui.statusBar.addPermanentWidget(self.ui.coo)
        self.ui.coord = QtGui.QLabel()
        self.ui.statusBar.addPermanentWidget(self.ui.coord)
        
        self.keyPressEvent = self.mainKeyPressEvent
        self.keyReleaseEvent = self.mainKeyReleaseEvent
        self.ui.zoomImage.paintEvent = self.zoomImagePaintEvent
        self.ui.image.paintEvent = self.imagePaintEvent
        self.ui.image.mousePressEvent = self.imageMousePressEvent
        self.ui.image.mouseReleaseEvent = self.imageMouseReleaseEvent
        self.ui.image.mouseMoveEvent = self.imageMouseMoveEvent
        
        if currentTool == "point":
            self.handleDotButton(True)

    def mainKeyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift and modes[currentTool] != "drag":
            if currentTool == "point":
                self.ui.dotDragButton.setChecked(True)
            if currentTool == "rectangle":
                self.ui.rectDragButton.setChecked(True)
            modes[currentTool] = "tempDrag"

    def mainKeyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift and modes[currentTool]=="tempDrag":
            if self.ui.image.pixmap() and currentTool == "point":
				if (modes["point"] == "drag" or modes["point"] == "tempDrag") and self.dragIsActive:
					self.ui.image.repaint()
					self.dragIsActive = False
            if currentTool == "point":
                self.ui.dotClickButton.setChecked(True)
            if currentTool == "rectangle":
                self.ui.rectClickButton.setChecked(True)

    def imageMouseMoveEvent(self, event):
        global zoomPoints, points, currentIndex
        x,y = event.pos().x(),event.pos().y()
        if self.dragIsActive:
            if 0 <= x < self.ui.image.width() and 0 <= y < self.ui.image.height():
                points[currentIndex][self.pointToDrag] = (x,y)
                self.ui.image.repaint()
        if self.ui.image.pixmap():
            height, width = self.ui.zoomImage.width(), self.ui.zoomImage.height()

            self.left, self.up = self.calculateZoomBorders(x,y)
  
            self.ui.coord.setText("(%d, %d)" % (x,y))
            if len(points[currentIndex]) > 0:
                del zoomPoints[:]
                for (i,j) in points[currentIndex]:
                    newX = zoomAmount * i - self.left
                    newY = zoomAmount * j - self.up
                    if 0 <= newX <= width and 0 <= newY <= height:
                        zoomPoints.append((newX, newY))

            self.updateZoomedImage(x,y)

    def imageMousePressEvent(self, event):
        global zoomPoints, points, modes, currentTool, currentIndex
        x,y = event.pos().x(),event.pos().y()
        if self.ui.image.pixmap() and currentTool == "point":
            if modes["point"] == "click":
                #points[currentIndex].append((x,y))
                self.left, self.up = self.calculateZoomBorders(x,y)
                newX,newY = zoomAmount * x - self.left, zoomAmount * y - self.up
                zoomPoints.append((newX, newY))
				
                command = CommandAddPoint(currentIndex, (x,y), "Add Point @(%d-%d)" %(x,y))
                self.undoStacks[currentIndex].push(command)
                annotationChanged[currentIndex] = True
                
                self.ui.image.repaint()
                self.ui.zoomImage.repaint()
            elif modes["point"] == "drag" or modes["point"] == "tempDrag":
                self.dragIsActive = False
                for (i,j) in points[currentIndex]:
                    if abs(i-x) <= pointWidth and abs(j-y) <= pointWidth:
                        self.pointToDrag = points[currentIndex].index((i,j))
                        self.dragIsActive = True
                        self.beforePoint = (i,j)
                        self.afterPoint = (-1,-1)

    def imageMouseReleaseEvent(self, event):
        global points, modes, currentTool, currentIndex
        if self.ui.image.pixmap() and currentTool == "point":
            if (modes["point"] == "drag" or modes["point"] == "tempDrag") and self.dragIsActive:
                self.ui.image.repaint()
                self.dragIsActive = False
                if self.afterPoint == (-1,-1):
					self.afterPoint = (event.pos().x(),event.pos().y())
                command = CommandDragPoint(currentIndex, self.beforePoint, self.afterPoint, "Drag Point")
                self.undoStacks[currentIndex].push(command)

    def zoomImagePaintEvent(self, event):
        global zoomAmount, zoomPoints, pointWidth
        if self.ui.zoomImage.pixmap():
            self.ui.zoomImage.paint.begin(self.ui.zoomImage)
            self.ui.zoomImage.paint.setPen(self.ui.zoomImage.pen)
            self.ui.zoomImage.paint.drawImage(self.ui.zoomImage.rect(), QtGui.QImage(self.ui.zoomImage.pixmap()))
            self.ui.zoomImage.paint.setPen(self.ui.image.pen)
            if pointsVisible and len(zoomPoints) > 0:
                for (i,j) in zoomPoints:
                    if useSmartColor:
                        r,g,b = getSmartColor(currentImage.getpixel(((i+self.left)/zoomAmount,(j+self.up)/zoomAmount)))
                        self.ui.zoomImage.paint.setPen(QtGui.QPen(QtGui.QColor(r,g,b), pointWidth*3))

                    self.ui.zoomImage.paint.drawPoint(i,j)
                    if indicesVisible:
                        try:
                            index = -1
                            for k, p in enumerate(points[currentIndex]):
                                dx = p[0] - (i+self.left)/zoomAmount
                                dy = p[1] - (j+self.up)/zoomAmount 
                                if abs(dx) < 0.1 and abs(dy) < 0.1:
                                    index = k
                            if index > -1:
                                self.ui.zoomImage.paint.drawText(i+3,j-3, QtCore.QString.number(index))
                        except ValueError:
                            pass
                            
            self.ui.zoomImage.paint.setPen(self.ui.zoomImage.crossPen)
            self.ui.zoomImage.paint.drawLine(0, self.ui.zoomImage.height()/2, self.ui.zoomImage.width(), self.ui.zoomImage.height()/2)
            self.ui.zoomImage.paint.drawLine(self.ui.zoomImage.width()/2, 0, self.ui.zoomImage.width()/2, self.ui.zoomImage.height())
            self.ui.zoomImage.paint.drawEllipse(self.ui.zoomImage.width()/2-15,self.ui.zoomImage.height()/2-15,30,30)
            self.ui.zoomImage.paint.end()
        
    def imagePaintEvent(self, event):
        global points, currentIndex, currentImage
        if self.ui.image.pixmap():
            if len(annotationChanged) and annotationChanged[currentIndex]:
            	self.setWindowTitle("%s* (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
            elif len(annotationChanged) and not annotationChanged[currentIndex]:
            	self.setWindowTitle("%s (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
            self.ui.image.pen.setWidth(pointWidth)
            self.ui.image.paint.begin(self.ui.image)
            self.ui.image.paint.setPen(self.ui.image.pen)
            self.ui.image.paint.drawImage(self.ui.image.rect(), QtGui.QImage(self.ui.image.pixmap()))
            if pointsVisible and len(points[currentIndex]) > 0:
                for (i,j) in points[currentIndex]:
                    if useSmartColor:
                        r,g,b = getSmartColor(currentImage.getpixel((i,j)))
                        self.ui.image.paint.setPen(QtGui.QPen(QtGui.QColor(r,g,b), pointWidth))
                        
                    self.ui.image.paint.drawPoint(i,j)
                    # if indicesVisible:
                        # self.ui.image.paint.drawText(i+4,j-4, QtCore.QString.number(points[currentIndex].index((i,j))))
            self.ui.image.paint.end()
			
    def closeEvent(self, event):
		saveAll = False
		for i in range(self.ui.imageComboBox.count()):
			if annotationChanged[i]:
				self.ui.imageComboBox.setCurrentIndex(i)
				if saveAll:
					self.saveAnnotations()
					event.accept()
				else:					
					quit_msg = "Save changes to the annotation file of \"%s\"?" % self.ui.imageComboBox.itemText(i)
					reply = QtGui.QMessageBox.question(self, 'Quit', quit_msg, QtGui.QMessageBox.Save | 
														QtGui.QMessageBox.SaveAll | QtGui.QMessageBox.Discard |
														QtGui.QMessageBox.Cancel)
					if reply == QtGui.QMessageBox.Save:
						self.saveAnnotations()
						event.accept()
					elif reply == QtGui.QMessageBox.SaveAll:
						saveAll = True
						self.saveAnnotations()
						event.accept()
					elif reply == QtGui.QMessageBox.Cancel:
						event.ignore()
						break
				
		#quit_msg = "Are you sure you want to exit the program?"
		#reply = QtGui.QMessageBox.question(self, 'Message', quit_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

		#if reply == QtGui.QMessageBox.Yes:
		#	event.accept()
		#else:
		#	event.ignore()

    def connectSignals(self):
        self.connect(self.ui.toolboxAction, QtCore.SIGNAL("triggered(bool)"), 
                             self.ui.toolBox, QtCore.SLOT("setVisible(bool)"))
        self.connect(self.ui.toolBox, QtCore.SIGNAL("visibilityChanged(bool)"), 
                             self.ui.toolboxAction, QtCore.SLOT("setChecked(bool)"))
        self.connect(self.ui.optionsAction, QtCore.SIGNAL("triggered(bool)"), 
                             self.ui.optionBox, QtCore.SLOT("setVisible(bool)"))
        self.connect(self.ui.optionBox, QtCore.SIGNAL("visibilityChanged(bool)"), 
                             self.ui.optionsAction, QtCore.SLOT("setChecked(bool)"))
        self.connect(self.ui.zoomAction, QtCore.SIGNAL("triggered(bool)"),
                             self.ui.zoomBox, QtCore.SLOT("setVisible(bool)"))
        self.connect(self.ui.zoomBox, QtCore.SIGNAL("visibilityChanged(bool)"), 
                             self.ui.zoomAction, QtCore.SLOT("setChecked(bool)"))
        self.connect(self.ui.navigationAction, QtCore.SIGNAL("triggered(bool)"), 
                             self.ui.navigationBox, QtCore.SLOT("setVisible(bool)"))
        self.connect(self.ui.navigationBox, QtCore.SIGNAL("visibilityChanged(bool)"), 
                             self.ui.navigationAction, QtCore.SLOT("setChecked(bool)"))

        self.connect(self.ui.indicesAction, QtCore.SIGNAL("triggered(bool)"), self.showIndices)
        self.connect(self.ui.pointsAction, QtCore.SIGNAL("triggered(bool)"), self.showPoints)
        self.connect(self.ui.rectanglesAction, QtCore.SIGNAL("triggered(bool)"), self.showRectangles)
        self.connect(self.ui.openAction, QtCore.SIGNAL("triggered()"), self.openImageDirectory)
        self.connect(self.ui.saveAction, QtCore.SIGNAL("triggered()"), self.saveAnnotations)
        self.connect(self.ui.imageComboBox, QtCore.SIGNAL("currentIndexChanged(QString)"), self.changeImage)
        self.connect(self.ui.prevButton, QtCore.SIGNAL("clicked()"), self.previousImage)
        self.connect(self.ui.nextButton, QtCore.SIGNAL("clicked()"), self.nextImage)
        self.connect(self.ui.plusTenButton, QtCore.SIGNAL("clicked()"), self.plusTenImage)
        self.connect(self.ui.minusTenButton, QtCore.SIGNAL("clicked()"), self.minusTenImage)
        self.connect(self.ui.firstButton, QtCore.SIGNAL("clicked()"), self.firstImage)
        self.connect(self.ui.lastButton, QtCore.SIGNAL("clicked()"), self.lastImage)
        self.connect(self.ui.dotButton, QtCore.SIGNAL("toggled(bool)"), self.handleDotButton)
        self.connect(self.ui.rectangleButton, QtCore.SIGNAL("toggled(bool)"), self.handleRectButton)
        self.connect(self.ui.dotClickButton, QtCore.SIGNAL("toggled(bool)"), self.handleDotClickButton)
        self.connect(self.ui.dotDragButton, QtCore.SIGNAL("toggled(bool)"), self.handleDotDragButton)
        self.connect(self.ui.rectClickButton, QtCore.SIGNAL("toggled(bool)"), self.handleRectClickButton)
        self.connect(self.ui.rectDragButton, QtCore.SIGNAL("toggled(bool)"), self.handleRectDragButton)
        self.connect(self.ui.undoButton, QtCore.SIGNAL("clicked()"), self.undo)
        self.connect(self.ui.redoButton, QtCore.SIGNAL("clicked()"), self.redo)
        self.connect(self.ui.undoAction, QtCore.SIGNAL("triggered()"), self.undo)
        self.connect(self.ui.redoAction, QtCore.SIGNAL("triggered()"), self.redo)

    def previousImage(self):
        index = self.ui.imageComboBox.currentIndex() - 1
        if index < 0:
            index = 0
        self.ui.imageComboBox.setCurrentIndex(index)
    def nextImage(self):
        index = self.ui.imageComboBox.currentIndex() + 1
        if index >= self.ui.imageComboBox.count():
            index = self.ui.imageComboBox.count() - 1
        self.ui.imageComboBox.setCurrentIndex(index)
    def plusTenImage(self):
        index = self.ui.imageComboBox.currentIndex() + 10
        if index >= self.ui.imageComboBox.count():
            index = self.ui.imageComboBox.count() - 1
        self.ui.imageComboBox.setCurrentIndex(index)
    def minusTenImage(self):
        index = self.ui.imageComboBox.currentIndex() - 10
        if index < 0:
            index = 0
        self.ui.imageComboBox.setCurrentIndex(index)
    def lastImage(self):
        self.ui.imageComboBox.setCurrentIndex(self.ui.imageComboBox.count() - 1)
    def firstImage(self):
        self.ui.imageComboBox.setCurrentIndex(0)

    def openImageDirectory(self, imagePath=None):
        global path
        global points, annotationChanged
        if imagePath:
            path = imagePath
        else:  
            path = str(QtGui.QFileDialog.getExistingDirectory(self, "Open directory", "."))
        if path:
            try:
                allFiles = os.listdir(path)
                imageFiles = sorted([x for x in allFiles if os.path.splitext(x)[-1] in extensions])        
                self.ui.imageComboBox.clear()
                points = []
                annotationChanged = []
                self.undoStacks = []
                self.ui.coord.setText("")
                if len(imageFiles) > 0:
                    for imageFile in imageFiles:
                        annotationFile = os.path.join(path, os.path.splitext(imageFile)[0] + ".xml") # @TODO: hardcoded extension!
                        try:
                            xmldoc = minidom.parse(annotationFile)
                            objects = xmldoc.getElementsByTagName("objects")
	
                            pts = []
                            rects = []
	
                            for object in objects:
                                lines = object.childNodes[1].data.splitlines()
                            	if object.attributes["type"].value == "points":
                            		for line in lines:
                            		    (x,y) = line.split(' ')
                            		    pts.append((int(x), int(y)))
                            	elif object.attributes["type"].value == "rectangles":
                            		for line in lines:
                            			#(x,y,z,t) = line.split(' ')   # @TODO: uncomment when rectangle is implemented
                            			#rects.append((int(x), int(y), int(z), int(t)))
										rects.append(line.split(' '))
										
                            points.append(pts)
                        except:
							points.append([])
                        undoRedoStatus.append([False,False])
                        annotationChanged.append(False)
                        self.stack = QtGui.QUndoStack(self)
                        self.undoStacks.append(self.stack)

                        #self.connect(self.undoStacks[-1], QtCore.SIGNAL("indexChanged(int)"), self.ui.image, QtCore.SLOT("repaint()"))
                        self.connect(self.undoStacks[-1], QtCore.SIGNAL("indexChanged(int)"), self.ui.zoomImage, QtCore.SLOT("repaint()"))
                        self.connect(self.undoStacks[-1], QtCore.SIGNAL("canUndoChanged(bool)"), self.undoChange)
                        self.connect(self.undoStacks[-1], QtCore.SIGNAL("canRedoChanged(bool)"), self.redoChange)
                        #self.connect(self.undoStacks[-1], QtCore.SIGNAL("canUndoChanged(bool)"), self.ui.undoAction.setEnabled)
                        #self.connect(self.undoStacks[-1], QtCore.SIGNAL("canRedoChanged(bool)"), self.ui.redoAction.setEnabled)
                            
                    self.ui.imageComboBox.addItems(imageFiles)
                    # self.loadImage("%s/%s" % (path, self.ui.imageComboBox.currentText()))
                    self.setWindowTitle("%s (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
                    self.ui.saveAction.setEnabled(True)
                else:
                    self.ui.statusBar.showMessage("No image found in the directory.", warningTimeout)
                    self.setWindowTitle("pilab-annotator")
            except OSError:
                self.ui.statusBar.showMessage(OSError, warningTimeout)
        

    def saveAnnotations(self):
        "Currently supports only saving xml files"
        global points, path, lastSavedState, annotationChanged
        filename = os.path.splitext(str(self.ui.imageComboBox.currentText()))[0]
        filePath = os.path.join(str(path), str(filename) + ".xml")
        currentIndex = self.ui.imageComboBox.currentIndex()
        lastSavedState = self.undoStacks[currentIndex].index()
        annotationChanged[currentIndex] = False
       
        doc = Document()
        
        annotation = doc.createElement("annotation")
        doc.appendChild(annotation)
		
        objects = doc.createElement("objects")
        objects.setAttribute("type", "points")
        objects.setAttribute("count", "%.0f" % len(points[currentIndex]))
        annotation.appendChild(objects)
		
        text = ""
        for (x,y) in points[currentIndex]:
            text += "%.0f %.0f\n" % (x,y)
        cDataSection = doc.createCDATASection(text)
        objects.appendChild(cDataSection)

        objects = doc.createElement("objects")
        objects.setAttribute("type", "rectangles")
        objects.setAttribute("count", "int")
        annotation.appendChild(objects)
		
        cDataSection = doc.createCDATASection("\n")
        objects.appendChild(cDataSection)

        f = open(filePath, 'w')
        f.write(doc.toprettyxml(indent="  ", encoding="UTF-8"))
        f.close()
        
        self.ui.statusBar.showMessage("File saved to %s" % (filePath))
        self.setWindowTitle("%s (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
        
    def updateZoomedImage(self, x, y):
        width = self.ui.zoomImage.width()
        height =  width = self.ui.zoomImage.height()
        x,y = self.calculateZoomBorders(x,y)
        myPixmap = self.zoomedPixmap.copy(x, y, width, height)
        self.ui.zoomImage.setPixmap(myPixmap)
        self.ui.zoomImage.setFixedSize(myPixmap.size())

    def loadImage(self, path):
        global zoomAmount, currentImage
        pixmap = QtGui.QPixmap(path)
        self.ui.image.setPixmap(pixmap)
        self.ui.image.setFixedSize(pixmap.size())

        self.zoomedPixmap = pixmap.scaled (self.ui.image.width()*zoomAmount, self.ui.image.height()*zoomAmount, QtCore.Qt.KeepAspectRatio)
        myPixmap = self.zoomedPixmap.copy(0,0, self.ui.zoomImage.width(), self.ui.zoomImage.height())
        self.ui.zoomImage.setPixmap(myPixmap)
        self.ui.zoomImage.setFixedSize(myPixmap.size())

        currentImage = Image.open(path)
        # convert to grayscale
        if currentImage.mode != "L":
            currentImage= currentImage.convert("L")
            
        # Sobel operator
        # edge1 = currentImage.filter(ImageFilter.Kernel((3,3), [1, 0, -1, 2, 0, -2, 1, 0, -1], scale=4))
        # edge2 = currentImage.filter(ImageFilter.Kernel((3,3), [1, 2, 1, 0, 0, 0, -1, -2, -1], scale=4))
        # edge3 = currentImage.filter(ImageFilter.Kernel((3,3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4))
        # edge4 = currentImage.filter(ImageFilter.Kernel((3,3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4))
        
        # Scharr operator
        edge1 = currentImage.filter(ImageFilter.Kernel((3,3), [3, 0, -3, 10, 0, -10, 3, 0, -3], scale=16))
        edge2 = currentImage.filter(ImageFilter.Kernel((3,3), [3, 10, 3, 0, 0, 0, -3, -10, -3], scale=16))
        edge3 = currentImage.filter(ImageFilter.Kernel((3,3), [-3, 0, 3, -10, 0, 10, -3, 0, 3], scale=16))
        edge4 = currentImage.filter(ImageFilter.Kernel((3,3), [-3, -10, -3, 0, 0, 0, 3, 10, 3], scale=16))
        
        currentImage = ImageChops.add(ImageChops.add(ImageChops.add(edge1, edge2), edge3), edge4)

        # currentImage.save("tmp.png")

    def changeImage(self, text):
        global path, currentIndex, undoRedoStatus
        self.loadImage("%s/%s" % (path, text))
        self.setWindowTitle("%s (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
        currentIndex = self.ui.imageComboBox.currentIndex()
        self.ui.indexLabel.setText("(%d / %d)" % (currentIndex+1, self.ui.imageComboBox.count()))
        self.ui.image.repaint()
        self.ui.zoomImage.repaint()
		
        self.undoChange(undoRedoStatus[currentIndex][0])
        self.redoChange(undoRedoStatus[currentIndex][1])

    def showIndices(self, check):
        global indicesVisible
        indicesVisible = check
        self.ui.image.repaint()
        self.ui.zoomImage.repaint()
		
    def showPoints(self, check):
        global pointsVisible
        pointsVisible = check
        self.ui.image.repaint()
        self.ui.zoomImage.repaint()
		
    def showRectangles(self, check):
        global rectanglesVisible
        rectanglesVisible = check
        self.ui.image.repaint()
        self.ui.zoomImage.repaint()

    def handleDotButton(self, check):
        global currentTool
        if check:
            self.ui.dotButton.setEnabled(False)
            self.ui.rectangleButton.setEnabled(True)
            self.ui.rectangleButton.setChecked(False)
            currentTool = "point"
            self.showDotOptions()
            
    def handleRectButton(self, check):
        global currentTool
        if check:
            self.ui.rectangleButton.setEnabled(False)
            self.ui.dotButton.setEnabled(True)
            self.ui.dotButton.setChecked(False)
            currentTool = "rectangle"
            self.showRectOptions()

    def handleDotUndoButton(self):
		global points, currentIndex
		self.undoStack.undo()
		self.ui.image.repaint()
        #if len(points) > currentIndex and points[currentIndex]:
        #    points[currentIndex].pop()
		#	 self.ui.image.repaint()

    def handleDotClickButton(self, check):
        if check:
            global modes
            modes["point"] = "click"
            self.ui.dotClickButton.setEnabled(False)
            self.ui.dotDragButton.setEnabled(True)
            self.ui.dotDragButton.setChecked(False)
            
    def handleDotDragButton(self, check):
        if check:
            global modes
            modes["point"] = "drag"
            self.ui.dotDragButton.setEnabled(False)
            self.ui.dotClickButton.setEnabled(True)
            self.ui.dotClickButton.setChecked(False)
			
    def handleRectClickButton(self, check):
        if check:
            global modes
            modes["rectangle"] = "draw"
            self.ui.rectClickButton.setEnabled(False)
            self.ui.rectDragButton.setEnabled(True)
            self.ui.rectDragButton.setChecked(False)
            
    def handleRectDragButton(self, check):
        if check:
            global modes
            modes["rectangle"] = "drag"
            self.ui.rectDragButton.setEnabled(False)
            self.ui.rectClickButton.setEnabled(True)
            self.ui.rectClickButton.setChecked(False)

    def showDotOptions(self):
        self.ui.dotClickButton.show()
        self.ui.dotDragButton.show()
        #self.ui.dotUndoButton.show()
        self.ui.rectClickButton.hide()
        self.ui.rectDragButton.hide()
        
    def showRectOptions(self):
        self.ui.rectClickButton.show()
        self.ui.rectDragButton.show()
        self.ui.dotClickButton.hide()
        self.ui.dotDragButton.hide()
        #self.ui.dotUndoButton.hide()
	
    def undo(self):
		global currentIndex, lastSavedState
		self.undoStacks[currentIndex].undo()
		if self.undoStacks[currentIndex].index() == lastSavedState:
			annotationChanged[currentIndex] = False
		else:
			annotationChanged[currentIndex] = True
		self.ui.zoomImage.repaint()
		self.ui.image.repaint()
		
    def redo(self):
		global currentIndex, lastSavedState
		self.undoStacks[currentIndex].redo()
		if self.undoStacks[currentIndex].index() == lastSavedState:
			annotationChanged[currentIndex] = False
		else:
			annotationChanged[currentIndex] = True
		self.ui.zoomImage.repaint()
		self.ui.image.repaint()
	
    def undoChange(self, b):
		global undoRedoStatus,currentIndex
		self.ui.undoAction.setEnabled(b)
		self.ui.undoButton.setEnabled(b)
		undoRedoStatus[currentIndex][0] = b
		
    def redoChange(self, b):
		global undoRedoStatus,currentIndex
		self.ui.redoAction.setEnabled(b)
		self.ui.redoButton.setEnabled(b)
		undoRedoStatus[currentIndex][1] = b

    def calculateZoomBorders(self, mouseX, mouseY):
        left = mouseX * zoomAmount  - self.ui.zoomImage.width()/2
        up = mouseY * zoomAmount - self.ui.zoomImage.height()/2
        if left < 0:
            left = 0
        elif left + self.ui.zoomImage.width() > self.zoomedPixmap.width():
            left = self.zoomedPixmap.width() - self.ui.zoomImage.width()
        if up < 0:
            up = 0
        elif up + self.ui.zoomImage.height() > self.zoomedPixmap.height():
            up = self.zoomedPixmap.height() - self.ui.zoomImage.height()
        
        return (left, up)
        


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    pixmap = QtGui.QPixmap("graphics/annotator.png")
    splash = QtGui.QSplashScreen(pixmap)
    splash.show()
    main = MainWindow()
    time.sleep(splashTime)
    splash.finish(main)
    main.show()

    if len(sys.argv) == 2:
        main.openImageDirectory(sys.argv[1]) 

    sys.exit(app.exec_())
