#! /usr/bin/python

#annotator.py

import sys, os
from PyQt4 import QtGui, QtCore
from ui_mainwindow import Ui_mainWindow

extensions = (".png",".jpg")                    #image file extensions to filter
currentTool = ""                                #string to describe current tool
modes = {"point":"click", "rectangle":"", "":""}  #modes for tools
currentIndex = 0                    #index of current image
points = []                                     #point coordinates for images
zoomPoints = []                            # point coordinates for the zoomed image
zoomAmount = 3                          # the image is zoomed "zoomAmount" times
pointWidth = 5                              # width of the red points
penColor = QtCore.Qt.red             # pen color for points/rectangles
warningTimeout = 10000             # time in miliseconds to show warning message
indicesVisible = False                  # visibility of indices of points/rectangles


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        global pointWidth
        QtGui.QMainWindow.__init__(self)

        # Set up the user interface from Designer.
        self.ui = Ui_mainWindow()
        self.ui.setupUi(self)
        self.setCentralWidget(self.ui.scrollArea)
        self.connectSignals()

        self.ui.dotClickButton.hide()
        self.ui.dotDragButton.hide()
        self.ui.dotUndoButton.hide()
        self.ui.rectClickButton.hide()
        self.ui.rectDragButton.hide()

        self.dragIsActive = False
        if indicesVisible:
            self.ui.indicesAction.setChecked(True)
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

    def mainKeyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift and modes[currentTool]!="drag":
            if currentTool == "point":
                self.ui.dotDragButton.setChecked(True)
            if currentTool == "rectangle":
                self.ui.rectDragButton.setChecked(True)
            modes[currentTool] = "tempDrag"

    def mainKeyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift and modes[currentTool]=="tempDrag":
            if currentTool == "point":
                self.ui.dotClickButton.setChecked(True)
            if currentTool == "rectangle":
                self.ui.rectClickButton.setChecked(True)

    def imageMouseMoveEvent(self, event):
        global zoomPoints, points, currentIndex
        if self.dragIsActive:
            points[currentIndex][self.pointToDrag] = (event.pos().x(),event.pos().y())
            self.ui.image.repaint()
        if self.ui.image.pixmap():
            width = self.ui.zoomImage.width()
            height = width = self.ui.zoomImage.height()

            self.left, self.up = self.calculateZoomBorders(event.pos().x(), event.pos().y())
  
            self.ui.coord.setText("(%d, %d)" % (event.pos().x(), event.pos().y()))
            if len(points[currentIndex]) > 0:
                del zoomPoints[:]
                for (i,j) in points[currentIndex]:
                    newX = zoomAmount * i - self.left
                    newY = zoomAmount * j - self.up
                    if 0 <= newX <= width and 0 <= newY <= height:
                        zoomPoints.append((newX, newY))

            self.updateZoomedImage(event.pos().x(), event.pos().y())

    def imageMousePressEvent(self, event):
        global points, modes, currentTool, currentIndex
        if self.ui.image.pixmap() and currentTool == "point":
            if modes["point"] == "click":
                points[currentIndex].append((event.pos().x(),event.pos().y()))
                self.ui.image.repaint()
                self.ui.zoomImage.repaint()
            elif modes["point"] == "drag" or modes["point"] == "tempDrag":
                self.dragIsActive = False
                for (i,j) in points[currentIndex]:
                    if abs(i-event.pos().x()) <= pointWidth and abs(j-event.pos().y()) <= pointWidth:
                        self.pointToDrag = points[currentIndex].index((i,j))
                        self.dragIsActive = True

    def imageMouseReleaseEvent(self, event):
        global points, modes, currentTool, currentIndex
        if self.ui.image.pixmap() and currentTool == "point":
            if (modes["point"] == "drag" or modes["point"] == "tempDrag") and self.dragIsActive:
                self.ui.image.repaint()
                self.dragIsActive = False

    def zoomImagePaintEvent(self, event):
        global zoomAmount, zoomPoints, pointWidth
        if self.ui.zoomImage.pixmap():
            self.ui.zoomImage.paint.begin(self.ui.zoomImage)
            self.ui.zoomImage.paint.setPen(self.ui.zoomImage.pen)
            self.ui.zoomImage.paint.drawImage(self.ui.zoomImage.rect(), QtGui.QImage(self.ui.zoomImage.pixmap()))
            if len(zoomPoints) > 0:
                for (i,j) in zoomPoints:
                    self.ui.zoomImage.paint.drawPoint(i,j)
                    if indicesVisible:
                        try:
                            index = points[currentIndex].index(((i+self.left)/zoomAmount,(j+self.up)/zoomAmount))
                            self.ui.zoomImage.paint.drawText(i+10,j-10, QtCore.QString.number(index))
                        except ValueError:
                            pass
            self.ui.zoomImage.paint.setPen(self.ui.zoomImage.crossPen)
            self.ui.zoomImage.paint.drawLine(0, self.ui.zoomImage.height()/2, self.ui.zoomImage.width(), self.ui.zoomImage.height()/2)
            self.ui.zoomImage.paint.drawLine(self.ui.zoomImage.width()/2, 0, self.ui.zoomImage.width()/2, self.ui.zoomImage.height())
            self.ui.zoomImage.paint.drawEllipse(self.ui.zoomImage.width()/2-15,self.ui.zoomImage.height()/2-15,30,30)
            self.ui.zoomImage.paint.end()
        
    def imagePaintEvent(self, event):
        global points, currentIndex
        if self.ui.image.pixmap():
            self.ui.image.pen.setWidth(pointWidth)
            self.ui.image.paint.begin(self.ui.image)
            self.ui.image.paint.setPen(self.ui.image.pen)
            self.ui.image.paint.drawImage(self.ui.image.rect(), QtGui.QImage(self.ui.image.pixmap()))
            if len(points[currentIndex]) > 0:
                for (i,j) in points[currentIndex]:
                    self.ui.image.paint.drawPoint(i,j)
                    if indicesVisible:
                        self.ui.image.paint.drawText(i+4,j-4, QtCore.QString.number(points[currentIndex].index((i,j))))
            self.ui.image.paint.end()

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
        self.connect(self.ui.exitAction, QtCore.SIGNAL("triggered()"), self, QtCore.SLOT("close()"))
        self.connect(self.ui.openAction, QtCore.SIGNAL("triggered()"), self.openImageDirectory)
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
        self.connect(self.ui.dotUndoButton, QtCore.SIGNAL("clicked()"), self.handleDotUndoButton)

    def previousImage(self):
        index = self.ui.imageComboBox.currentIndex()-1
        if index<0:
            index=0
        self.ui.imageComboBox.setCurrentIndex(index)
    def nextImage(self):
        index = self.ui.imageComboBox.currentIndex()+1
        if index >= self.ui.imageComboBox.count():
            index=self.ui.imageComboBox.count()-1
        self.ui.imageComboBox.setCurrentIndex(index)
    def plusTenImage(self):
        index = self.ui.imageComboBox.currentIndex()+10
        if index >= self.ui.imageComboBox.count():
            index=self.ui.imageComboBox.count()-1
        self.ui.imageComboBox.setCurrentIndex(index)
    def minusTenImage(self):
        index = self.ui.imageComboBox.currentIndex()-10
        if index < 0:
            index=0
        self.ui.imageComboBox.setCurrentIndex(index)
    def lastImage(self):
        self.ui.imageComboBox.setCurrentIndex(self.ui.imageComboBox.count()-1)
    def firstImage(self):
        self.ui.imageComboBox.setCurrentIndex(0)

    def openImageDirectory(self, imagePath=None):
        global path, points
        if imagePath:
            path = imagePath
        else:  
            path = unicode(QtGui.QFileDialog.getExistingDirectory(self, "Open directory", "/home"))
        if path:
            try:
                allFiles = os.listdir(path)
                imageFiles = sorted([x for x in allFiles if os.path.splitext(x)[-1] in extensions])        
                self.ui.imageComboBox.clear()
                points = []
                self.ui.coord.setText("")
                if len(imageFiles) > 0:
                    for i in imageFiles:
                        points.append([])
                    self.ui.imageComboBox.addItems(imageFiles)
                    self.loadImage("%s/%s" % (path, self.ui.imageComboBox.currentText()))
                    self.setWindowTitle("%s (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
                else:
                    self.ui.statusBar.showMessage("No image found in the directory.", warningTimeout)
                    self.setWindowTitle("pilab-annotator")
            except OSError as (errorNo, errorMessage):
                self.ui.statusBar.showMessage(errorMessage, warningTimeout)

    def updateZoomedImage(self, x, y):
        width = self.ui.zoomImage.width()
        height =  width = self.ui.zoomImage.height()
        x,y = self.calculateZoomBorders(x,y)
        myPixmap = self.zoomedPixmap.copy(x, y, width, height)
        self.ui.zoomImage.setPixmap(myPixmap)
        self.ui.zoomImage.setFixedSize(myPixmap.size())

    def loadImage(self, path):
        global zoomAmount
        pixmap = QtGui.QPixmap(path)
        self.ui.image.setPixmap(pixmap)
        self.ui.image.setFixedSize(pixmap.size())

        self.zoomedPixmap = pixmap.scaled (self.ui.image.width()*zoomAmount, self.ui.image.height()*zoomAmount, QtCore.Qt.KeepAspectRatio)
        myPixmap = self.zoomedPixmap.copy(0,0, self.ui.zoomImage.width(), self.ui.zoomImage.height())
        self.ui.zoomImage.setPixmap(myPixmap)
        self.ui.zoomImage.setFixedSize(myPixmap.size())

    def changeImage(self, text):
        global path, currentIndex
        self.loadImage("%s/%s" % (path, text))
        self.setWindowTitle("%s (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
        currentIndex = self.ui.imageComboBox.currentIndex()
        self.ui.indexLabel.setText("(%d / %d)" % (currentIndex+1, self.ui.imageComboBox.count()))

    def showIndices(self, check):
        global indicesVisible
        indicesVisible = check
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
        if len(points) > currentIndex and points[currentIndex]:
            points[currentIndex].pop()
            self.ui.image.repaint()

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

    def showDotOptions(self):
        self.ui.dotClickButton.show()
        self.ui.dotDragButton.show()
        self.ui.dotUndoButton.show()
        self.ui.rectClickButton.hide()
        self.ui.rectDragButton.hide()
    def showRectOptions(self):
        self.ui.rectClickButton.show()
        self.ui.rectDragButton.show()
        self.ui.dotClickButton.hide()
        self.ui.dotDragButton.hide()
        self.ui.dotUndoButton.hide()

    def calculateZoomBorders(self, mouseX, mouseY):
        left = mouseX * zoomAmount  - self.ui.zoomImage.width()/2
        up = mouseY * zoomAmount - self.ui.zoomImage.height()/2
        if left<0:
            left = 0
        elif left + self.ui.zoomImage.width() > self.zoomedPixmap.width():
            left = self.zoomedPixmap.width() - self.ui.zoomImage.width()
        if up<0:
            up = 0
        elif up + self.ui.zoomImage.height() > self.zoomedPixmap.height():
            up = self.zoomedPixmap.height() - self.ui.zoomImage.height()
        
        return (left, up)

    #def coordsNormalToZoom(self, x, y):
        


app = QtGui.QApplication(sys.argv)
main = MainWindow()
main.show()

if len(sys.argv) == 2:
    main.openImageDirectory(unicode(sys.argv[1])) 

sys.exit(app.exec_())
