#! /usr/bin/python

#annotator.py

import sys, os, copy, time
from PyQt4 import QtGui, QtCore
from ui_mainwindow import Ui_mainWindow
from xml.dom.minidom import Document, CDATASection
from xml.dom import minidom
import Image, ImageFilter, ImageMath, ImageChops

dashPattern = [2,2]                                 # Dash pattern for drawing rectangles in format [line length, space]
splashTime = 3                                      # splash screen duration in seconds
extensions = (".png",".jpg")                        # image file extensions to filter
currentTool = "point"                               # string to describe current tool
modes = {"point":"click", "rectangle":"draw", "":""}    # modes for tools
currentIndex = 0                                    # index of current image
points = []                                         # point coordinates for images
zoomPoints = []                                     # point coordinates for the zoomed image
rectangles = []										# rectangle coordinates
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

class CommandDragRect(QtGui.QUndoCommand):
	global rectangles, zoomAmount
	def __init__(self, index, before, after, description):
		super(CommandDragRect, self).__init__(description)
		self.rectList = rectangles[index]
		self.rectangle1 = before
		self.rectangle2 = after
		#self.zoomStack = []

	def redo(self):
		try:
			self.rectList[self.rectList.index(self.rectangle1)] = self.rectangle2
			#if len(self.zoomStack) > 0:
			#	zoomPoints.append(self.zoomStack.pop())
		except ValueError:
			pass
		
	def undo(self):
		try:
			self.rectList[self.rectList.index(self.rectangle2)] = self.rectangle1
			#if len(zoomPoints) > 0:
			#	self.zoomStack.append(zoomPoints.pop())
		except ValueError:
			pass
			
class CommandResizeRect(QtGui.QUndoCommand):
	global rectangles, zoomAmount
	def __init__(self, index, before, after, description):
		super(CommandResizeRect, self).__init__(description)
		self.rectList = rectangles[index]
		self.rectangle1 = before
		self.rectangle2 = after
		#self.zoomStack = []

	def redo(self):
		try:
			self.rectList[self.rectList.index(self.rectangle1)] = self.rectangle2
			#if len(self.zoomStack) > 0:
			#	zoomPoints.append(self.zoomStack.pop())
		except ValueError:
			pass
		
	def undo(self):
		try:
			self.rectList[self.rectList.index(self.rectangle2)] = self.rectangle1
			#if len(zoomPoints) > 0:
			#	self.zoomStack.append(zoomPoints.pop())
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

class CommandAddRect(QtGui.QUndoCommand):
	global rectangles, zoomAmount
	def __init__(self, index, rectangle, description):
		super(CommandAddRect, self).__init__(description)
		self.rectList = rectangles[index]
		self.rectangle = rectangle
		#self.zoomStack = []

	def redo(self):
		self.rectList.append(self.rectangle)
		#if len(self.zoomStack) > 0:
			#zoomPoints.append(self.zoomStack.pop())
		
	def undo(self):
		item = self.rectList.pop()
		#if len(zoomPoints) > 0:
			#self.zoomStack.append(zoomPoints.pop())
		#del item		
    
class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        global pointWidth
        QtGui.QMainWindow.__init__(self)

        # Set up the user interface from Designer.
        self.ui = Ui_mainWindow()
        self.ui.setupUi(self)
        self.setCentralWidget(self.ui.scrollArea)
		
        self.pModeButtonGroup = QtGui.QButtonGroup(self)
        self.pModeButtonGroup.addButton(self.ui.dotClickButton)
        self.pModeButtonGroup.addButton(self.ui.dotDragButton)
		
        self.rModeButtonGroup = QtGui.QButtonGroup(self)
        self.rModeButtonGroup.addButton(self.ui.rectClickButton)
        self.rModeButtonGroup.addButton(self.ui.rectDragButton)
		
        self.toolButtonGroup = QtGui.QButtonGroup(self)
        self.toolButtonGroup.addButton(self.ui.dotButton)
        self.toolButtonGroup.addButton(self.ui.rectangleButton)
		
        self.undoStacks = []
        self.connectSignals()

        if currentTool=="point":
			self.ui.rectClickButton.hide()
			self.ui.rectDragButton.hide()
        else:
			self.ui.dotClickButton.hide()
			self.ui.dotDragButton.hide()
        
        self.ui.saveAction.setEnabled(False)

        self.dragIsActive = False
        self.drawingRectangle = False
        self.resizeReady = False
        self.resizeIsActive = False
        self.resizeType = ""
		
        self.ui.indicesAction.setChecked(indicesVisible)
        self.ui.pointsAction.setChecked(pointsVisible)
        self.ui.rectanglesAction.setChecked(rectanglesVisible)

            
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
		
        self.rectPen = QtGui.QPen(penColor)
        self.rectPen.setDashPattern(dashPattern)
        #self.rectPen.setWidth(pointWidth-1)
        
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

    def mainKeyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift and modes[currentTool] != "drag":
            if currentTool == "point":
                self.ui.dotDragButton.setChecked(True)
            if currentTool == "rectangle":
                self.ui.rectDragButton.setChecked(True)
            modes[currentTool] = "tempDrag"
            self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))

    def mainKeyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift and modes[currentTool]=="tempDrag":
            if self.ui.image.pixmap() and (currentTool == "point" or currentTool == "rectangle"):
				if (modes[currentTool] == "drag" or modes[currentTool] == "tempDrag") and self.dragIsActive:
					annotationChanged[currentIndex] = True
					self.ui.image.repaint()
					self.dragIsActive = False
            if currentTool == "point":
                self.ui.dotClickButton.setChecked(True)
            if currentTool == "rectangle":
                self.ui.rectClickButton.setChecked(True)
            self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

    def imageMouseMoveEvent(self, event):
        global zoomPoints, points, rectangles, currentIndex
        x,y = event.pos().x(),event.pos().y()
        if self.dragIsActive:
            if currentTool == "point":
				if 0 <= x < self.ui.image.width() and 0 <= y < self.ui.image.height():
					points[currentIndex][self.pointToDrag] = (x,y)
					self.ui.image.repaint()
            elif currentTool == "rectangle":
				(i,j,k,m) = self.beforeRect
				deltaX,deltaY = x-self.rectDragPoint.x(),y-self.rectDragPoint.y()
				newX,newY = i+deltaX, j+deltaY
				if 0 <= x < self.ui.image.width() and 0 <= y < self.ui.image.height() \
					and 0 <= newX < self.ui.image.width()-k and 0 <= newY < self.ui.image.height()-m:
						rectangles[currentIndex][self.rectToDrag] = (newX,newY,k,m)
						self.ui.image.repaint()
						
        elif self.resizeIsActive:
			(i,j,w,h) = rectangles[currentIndex][self.rectToResize]
			if self.resizeType == "upleft":
				deltaX,deltaY = x-i, y-j
				newX, newY = x,y
				newWidth, newHeight = w-deltaX,h-deltaY
				#rectangles[currentIndex][self.rectToResize] = (x,y,w-deltaX,h-deltaY)
			elif self.resizeType == "downleft":
				deltaX,deltaY = x-i, y-j-h
				newX, newY = i+deltaX, j
				newWidth, newHeight = w-deltaX,h+deltaY
				#rectangles[currentIndex][self.rectToResize] = (i+deltaX,j,w-deltaX,h+deltaY)
			elif self.resizeType == "upright":
				deltaX,deltaY = x-i-w, y-j
				newX, newY = i,j+deltaY
				newWidth, newHeight = w+deltaX,h-deltaY
				#rectangles[currentIndex][self.rectToResize] = (i,j+deltaY,w+deltaX,h-deltaY)
			elif self.resizeType == "downright":
				deltaX,deltaY = x-i-w, y-j-h
				newX, newY = i,j
				newWidth, newHeight = w+deltaX,h+deltaY
				#rectangles[currentIndex][self.rectToResize] = (i,j,w+deltaX,h+deltaY)
			elif self.resizeType == "left":
				deltaX = x-i
				newX, newY = i+deltaX,j
				newWidth, newHeight = w-deltaX,h
				#rectangles[currentIndex][self.rectToResize] = (i+deltaX,j,w-deltaX,h)
			elif self.resizeType == "right":
				deltaX = x-i-w
				newX, newY = i,j
				newWidth, newHeight = w+deltaX,h
				#rectangles[currentIndex][self.rectToResize] = (i,j,w+deltaX,h)
			elif self.resizeType == "up":
				deltaY = y-j
				newX, newY = i,j+deltaY
				newWidth, newHeight = w,h-deltaY
				#rectangles[currentIndex][self.rectToResize] = (i,j+deltaY,w,h-deltaY)
			elif self.resizeType == "down":
				deltaY = y-j-h
				newX, newY = i,j
				newWidth, newHeight = w,h+deltaY
				#rectangles[currentIndex][self.rectToResize] = (i,j,w,h+deltaY)
			#if newWidth < 0:
			#	newX -= newWidth
			#	newWidth = abs(newWidth)
			#if newHeight < 0:
			#	newY += newHeight
			#	newHeight = abs(newHeight)
			rectangles[currentIndex][self.rectToResize] = (newX,newY,newWidth,newHeight)
			self.ui.image.repaint()
						
        elif currentTool == "rectangle" and modes[currentTool] != "drag" and modes[currentTool] != "tempDrag":
			self.resizeReady = False
			for (i,j,k,m) in rectangles[currentIndex]:
				if abs(x-i)<=2:
					if abs(y-j)<=2:   #upper-left corner of rectangle
						self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeFDiagCursor))
						self.resizeType = "upleft"
						self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
						self.resizeReady = True
						break
					elif abs(y-j-m)<=2:   #lower-left corner of rectangle
						self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeBDiagCursor))
						self.resizeType = "downleft"
						self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
						self.resizeReady = True
						break
					elif -2<=y-j<=m+2:   #left side of rectangle
						self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeHorCursor))
						self.resizeType = "left"
						self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
						self.resizeReady = True
						break
				elif abs(x-i-k)<=2:
					if abs(y-j)<=2:   #upper-right corner of rectangle
						self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeBDiagCursor))
						self.resizeType = "upright"
						self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
						self.resizeReady = True
						break
					elif abs(y-j-m)<=2:   #lower-right corner of rectangle
						self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeFDiagCursor))
						self.resizeType = "downright"
						self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
						self.resizeReady = True
						break
					elif -2<=y-j<=m+2:   #right side of rectangle
						self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeHorCursor))
						self.resizeType = "right"
						self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
						self.resizeReady = True
						break
				elif abs(y-j)<=2 and -2<=x-i<=k+2:   #upper side of rectangle
					self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeVerCursor))
					self.resizeType = "up"
					self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
					self.resizeReady = True
					break
				elif abs(y-j-m)<=2 and -2<=x-i<=k+2:   #lower side of the rectangle
					self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeVerCursor))
					self.resizeType = "down"
					self.rectToResize = rectangles[currentIndex].index((i,j,k,m))
					self.resizeReady = True
					break
			if not self.resizeReady:
				if self.ui.image.cursor().shape() != QtCore.Qt.CrossCursor:
					self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
				
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
						
            if self.drawingRectangle:
				(x,y) = self.rectCoord
				(self.tempWidth, self.tempHeight) = ((event.pos().x() - x), (event.pos().y() - y))
				self.ui.image.repaint()
				self.updateZoomedImage(event.pos().x(),event.pos().y())
				self.ui.zoomImage.repaint()
            else:
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
						
        elif self.ui.image.pixmap() and currentTool == "rectangle":
			if modes["rectangle"] == "draw":
				if self.resizeReady:
					self.resizeIsActive = True
					self.beforeRect = rectangles[currentIndex][self.rectToResize]
				else:
					self.drawingRectangle = True
				self.rectCoord = (x,y)
			elif modes["rectangle"] == "drag" or modes["rectangle"] == "tempDrag":
				self.dragIsActive = False
				for (i,j,k,m) in rectangles[currentIndex]:
					if ((abs(x-i)<=2 or abs(x-i-k)<=2) and -2<=y-j<=m+2) or ((abs(y-j)<=2 or abs(y-j-m)<=2) and -2<=x-i<=k+2):
						#print "x:%d y:%d i:%d j:%d w:%d h:%d" % (x,y,i,j,k+i,m+j)
						self.rectToDrag = rectangles[currentIndex].index((i,j,k,m))
						self.rectDragPoint = event.pos()
						self.dragIsActive = True
						self.beforeRect = (i,j,k,m)
						self.afterRect = (-1,-1,-1,-1)

    def imageMouseReleaseEvent(self, event):
        global points, modes, currentTool, currentIndex
        if self.ui.image.pixmap() and currentTool == "point":
            if (modes["point"] == "drag" or modes["point"] == "tempDrag") and self.dragIsActive:
                annotationChanged[currentIndex] = True
                self.ui.image.repaint()
                self.dragIsActive = False
                if self.afterPoint == (-1,-1):
					self.afterPoint = (event.pos().x(),event.pos().y())
                command = CommandDragPoint(currentIndex, self.beforePoint, self.afterPoint, "Drag Point")
                self.undoStacks[currentIndex].push(command)
				
        elif self.ui.image.pixmap() and currentTool == "rectangle":
			if modes["rectangle"] == "draw":
				if self.resizeIsActive:
					(i,j,w,h) = rectangles[currentIndex][self.rectToResize]
					if w < 0:
						i += w
						w = abs(w)
					if h < 0:
						j += h
						h = abs(h)
					rectangles[currentIndex][self.rectToResize] = self.afterRect = (i,j,w,h)
					command = CommandResizeRect(currentIndex, self.beforeRect, self.afterRect, "Drag Rectangle")
					self.undoStacks[currentIndex].push(command)
					self.resizeIsActive = False
					annotationChanged[currentIndex] = True
					self.ui.image.repaint()
				else:
					(x,y) = self.rectCoord
					width, height = (event.pos().x() - x), (event.pos().y() - y)
					if width != 0 and height != 0:	
						if width < 0:
							width = abs(width)
							x = event.pos().x()
						if height < 0:
							height = abs(height)
							y = event.pos().y()
						command = CommandAddRect(currentIndex, (x,y,width,height), "Add Rectangle @(%d-%d-%d-%d)" %(x,y,width,height))
						self.undoStacks[currentIndex].push(command)
						annotationChanged[currentIndex] = True
					if self.drawingRectangle:
						self.drawingRectangle = False
						self.ui.image.repaint()
			if (modes["rectangle"] == "drag" or modes["rectangle"] == "tempDrag") and self.dragIsActive:
				annotationChanged[currentIndex] = True
				self.ui.image.repaint()
				self.dragIsActive = False
				if self.afterRect == (-1,-1,-1,-1):
					(i,j,k,m) = self.beforeRect
					deltaX,deltaY = event.pos().x()-self.rectDragPoint.x(),event.pos().y()-self.rectDragPoint.y()
					self.afterRect = (i+deltaX,j+deltaY,k,m)
				command = CommandDragRect(currentIndex, self.beforeRect, self.afterRect, "Drag Rectangle")
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
            #print points
            if pointsVisible and len(points[currentIndex]) > 0:
                for (i,j) in points[currentIndex]:
                    if useSmartColor:
                        r,g,b = getSmartColor(currentImage.getpixel((i,j)))
                        self.ui.image.paint.setPen(QtGui.QPen(QtGui.QColor(r,g,b), pointWidth))
                        
                    self.ui.image.paint.drawPoint(i,j)
                    # if indicesVisible:
                        # self.ui.image.paint.drawText(i+4,j-4, QtCore.QString.number(points[currentIndex].index((i,j))))
            if self.drawingRectangle:
				self.ui.image.paint.setPen(self.rectPen)
				(x,y) = self.rectCoord
				self.ui.image.paint.drawRect(x,y,self.tempWidth,self.tempHeight)
            if rectanglesVisible and len(rectangles)>0:
				for index,(i,j,k,m) in enumerate(rectangles[currentIndex]):
					self.ui.image.paint.setPen(self.rectPen)
					self.ui.image.paint.drawRect(i,j,k,m)
					self.ui.image.paint.drawText(i+3,j+12, QtCore.QString.number(index))
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
        global points, rectangles, annotationChanged
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
                rectangles = []
                annotationChanged = []
                self.undoStacks = []
                self.ui.coord.setText("")
                if len(imageFiles) > 0:
                    for imageFile in imageFiles:
						objects = []
						try:
							annotationFile = os.path.join(path, os.path.splitext(imageFile)[0] + ".xml") # @TODO: hardcoded extension!
							xmldoc = minidom.parse(annotationFile)
							objects = xmldoc.getElementsByTagName("objects")			
						except:
							points.append([])
							rectangles.append([])
						else:
							pts = []
							rects = []
							pointsOK = True
							rectsOK = True

							for object in objects:
								lines = object.childNodes[1].data.splitlines()
								if object.attributes["type"].value == "points":
									try:
										for line in lines:
											(x,y) = line.split(' ')
											pts.append((int(x), int(y)))
									except:
										points.append([])
										pointsOK = False
								elif object.attributes["type"].value == "rectangles":
									try:
										for line in lines:
											(x,y,z,t) = line.split(' ')   # @TODO: uncomment when rectangle is implemented
											rects.append((int(x), int(y), int(z), int(t)))	
									except:
										rectangles.append([])
										rectsOK = False
							if pointsOK:
								points.append(pts)
							if rectsOK:
								rectangles.append(rects)

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
        if text == "":
			text = "\n"
        cDataSection = doc.createCDATASection(text)
        objects.appendChild(cDataSection)

        objects = doc.createElement("objects")
        objects.setAttribute("type", "rectangles")
        objects.setAttribute("count", "%.0f" % len(rectangles[currentIndex]))
        annotation.appendChild(objects)
		
        text = ""
        for (x,y,w,h) in rectangles[currentIndex]:
            text += "%.0f %.0f %.0f %.0f\n" % (x,y,w,h)
        if text == "":
			text = "\n"
        cDataSection = doc.createCDATASection(text)
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
            currentTool = "point"
            self.showDotOptions()
            
    def handleRectButton(self, check):
        global currentTool
        if check:
            currentTool = "rectangle"
            self.showRectOptions()

    def handleDotUndoButton(self):
		global points, currentIndex
		self.undoStack.undo()
		self.ui.image.repaint()

    def handleDotClickButton(self, check):
        if check:
            global modes
            modes["point"] = "click"
            self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
    def handleDotDragButton(self, check):
        if check:
            global modes
            modes["point"] = "drag"
            self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))
			
    def handleRectClickButton(self, check):
        if check:
            global modes
            modes["rectangle"] = "draw"
            self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
    def handleRectDragButton(self, check):
        if check:
            global modes
            modes["rectangle"] = "drag"
            self.ui.image.setCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))

    def showDotOptions(self):
        self.ui.dotClickButton.show()
        self.ui.dotDragButton.show()
        self.ui.rectClickButton.hide()
        self.ui.rectDragButton.hide()
        
    def showRectOptions(self):
        self.ui.rectClickButton.show()
        self.ui.rectDragButton.show()
        self.ui.dotClickButton.hide()
        self.ui.dotDragButton.hide()
	
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
