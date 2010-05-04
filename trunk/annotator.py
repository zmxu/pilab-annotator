#! /usr/bin/python

#annotator.py

import sys, os
from PyQt4 import QtGui, QtCore
from ui_mainwindow import Ui_mainWindow

extensions = (".png",".jpg")                    #image file extensions to filter
currentTool = ""                                #string to describe current tool
modes = {"dot":"click", "rectangle":"", "":""}  #modes for tools
currentIndex = 0                    #index of current image
points = []                                     #point coordinates for images
zoomAmount = 3


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
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

        self.ui.zoomImage.paint = QtGui.QPainter()
        self.ui.image.paint = QtGui.QPainter()
        self.ui.image.pen = QtGui.QPen(QtCore.Qt.red)
        self.ui.coord = QtGui.QLabel()
        self.ui.statusBar.addPermanentWidget(self.ui.coord)
        
        self.ui.zoomImage.paintEvent = self.zoomImagePaintEvent
        self.ui.image.paintEvent = self.imagePaintEvent
        self.ui.image.mousePressEvent = self.imageMousePressEvent
        self.ui.image.mouseReleaseEvent = self.imageMouseReleaseEvent
        self.ui.image.mouseMoveEvent = self.imageMouseMoveEvent

    def imageMouseMoveEvent(self, event):
        if self.ui.image.pixmap():
            self.ui.coord.setText("(%d, %d)" % (event.pos().x(), event.pos().y()))
            self.updateZoomedImage(event.pos().x(), event.pos().y())

    def zoomImagePaintEvent(self, event):
        if self.ui.zoomImage.pixmap():
            self.ui.zoomImage.paint.begin(self.ui.zoomImage)
            self.ui.zoomImage.paint.drawImage(self.ui.zoomImage.rect(), QtGui.QImage(self.ui.zoomImage.pixmap()))
            self.ui.zoomImage.paint.end()
        
    def imagePaintEvent(self, event):
        global points, currentIndex
        if self.ui.image.pixmap():
            self.ui.image.pen.setWidth(4)
            self.ui.image.paint.begin(self.ui.image)
            self.ui.image.paint.setPen(self.ui.image.pen)
            self.ui.image.paint.drawImage(self.ui.image.rect(), QtGui.QImage(self.ui.image.pixmap()))
            if len(points[currentIndex]) > 0:
                for (i,j) in points[currentIndex]:
                    self.ui.image.paint.drawPoint(i,j)
            self.ui.image.paint.end()

    def imageMousePressEvent(self, event):
        global points, modes, currentTool, currentIndex
        if self.ui.image.pixmap() and currentTool == "dot":
            if modes["dot"] == "click":
                points[currentIndex].append((event.pos().x(),event.pos().y()))
                self.ui.image.repaint()
            elif modes["dot"] == "drag":
                self.dragIsActive = False
                for (i,j) in points[currentIndex]:
                    if abs(i-event.pos().x()) <= 3 and abs(j-event.pos().y()) <= 3:
                        self.pointToDrag = (i,j)
                        self.dragIsActive = True

    def imageMouseReleaseEvent(self, event):
        global points, modes, currentTool, currentIndex
        if self.ui.image.pixmap() and currentTool == "dot":
            if modes["dot"] == "drag" and self.dragIsActive:
                points[currentIndex].remove(self.pointToDrag)
                points[currentIndex].append((event.pos().x(),event.pos().y()))
                self.ui.image.repaint()
                self.dragIsActive = False

    def connectSignals(self):
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

    def openImageDirectory(self):
        global path, points
        path = unicode(QtGui.QFileDialog.getExistingDirectory(self, "Open directory", "/home"))
        if path:
            self.setWindowTitle("Annotator - " + path)
            allFiles = os.listdir(path)
            imageFiles = sorted([x for x in allFiles if os.path.splitext(x)[-1] in extensions])        
            self.ui.imageComboBox.clear()
            points = []
            if len(imageFiles) > 0:
                for i in imageFiles:
                    points.append([])
                self.ui.imageComboBox.addItems(imageFiles)
                self.loadImage("%s/%s" % (path, self.ui.imageComboBox.currentText()))

    def updateZoomedImage(self, x, y):
        width = self.ui.zoomImage.width()
        height = width = self.ui.zoomImage.height()
        x = zoomAmount*x - width / 2
        y = zoomAmount*y - height / 2
        if x < 0:
            x=0
        elif x+width > self.zoomedPixmap.width():
            x = self.zoomedPixmap.width() - width
        if y < 0:
            y=0
        elif y+height > self.zoomedPixmap.height():
            y = self.zoomedPixmap.height() - height
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
        currentIndex = self.ui.imageComboBox.currentIndex()
        self.ui.indexLabel.setText("(%d / %d)" % (currentIndex+1, self.ui.imageComboBox.count()))

    def handleDotButton(self, check):
        global currentTool
        if check:
            self.ui.dotButton.setEnabled(False)
            self.ui.rectangleButton.setEnabled(True)
            self.ui.rectangleButton.setChecked(False)
            currentTool = "dot"
            self.showDotOptions()
            
    def handleRectButton(self, check):
        global currentTool
        if check:
            self.ui.rectangleButton.setEnabled(False)
            self.ui.dotButton.setEnabled(True)
            self.ui.dotButton.setChecked(False)
            currentTool = "rect"
            self.showRectOptions()

    def handleDotUndoButton(self):
        global points, currentIndex
        if len(points) > currentIndex and points[currentIndex]:
            points[currentIndex].pop()
            self.ui.image.repaint()

    def handleDotClickButton(self, check):
        if check:
            global modes
            modes["dot"] = "click"
            self.ui.dotClickButton.setEnabled(False)
            self.ui.dotDragButton.setEnabled(True)
            self.ui.dotDragButton.setChecked(False)
            
    def handleDotDragButton(self, check):
        if check:
            global modes
            modes["dot"] = "drag"
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


app = QtGui.QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec_())
