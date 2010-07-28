#! /usr/bin/python

#annotator.py

import sys, os
from PyQt4 import QtGui, QtCore
from ui_mainwindow import Ui_mainWindow
import Image, ImageFilter, ImageMath, ImageChops

extensions = (".png",".jpg")                        # image file extensions to filter
currentTool = "point"                               # string to describe current tool
modes = {"point":"click", "rectangle":"", "":""}    # modes for tools
currentIndex = 0                                    # index of current image
points = []                                         # point coordinates for images
zoomPoints = []                                     # point coordinates for the zoomed image
zoomAmount = 3                                      # the image is zoomed "zoomAmount" times
pointWidth = 3                                      # width of the red points (is to be odd)
# penColor = QtCore.Qt.red                            # pen color for points/rectangles
penColor = QtGui.QColor(255,0,0)                            # pen color for points/rectangles
warningTimeout = 10000                              # time in miliseconds to show warning message
indicesVisible = True                               # visibility of indices of points/rectangles
useSmartColor = True                                # smart coloring of the points
currentImage = []                                   # current PIL image, filtered, and probabilities extracted

def getSmartColor(intensity):
    return min(15*intensity,255), 50, 100
    
    
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
        
        self.ui.saveAction.setEnabled(False)

        self.dragIsActive = False
        if indicesVisible:
            self.ui.indicesAction.setChecked(True)
            
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
                points[currentIndex].append((x,y))
                self.left, self.up = self.calculateZoomBorders(x,y)
                newX,newY = zoomAmount * x - self.left, zoomAmount * y - self.up
                zoomPoints.append((newX, newY))
                
                self.ui.image.repaint()
                self.ui.zoomImage.repaint()
            elif modes["point"] == "drag" or modes["point"] == "tempDrag":
                self.dragIsActive = False
                for (i,j) in points[currentIndex]:
                    if abs(i-x) <= pointWidth and abs(j-y) <= pointWidth:
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
            self.ui.zoomImage.paint.setPen(self.ui.image.pen)
            if len(zoomPoints) > 0:
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
            self.ui.image.pen.setWidth(pointWidth)
            self.ui.image.paint.begin(self.ui.image)
            self.ui.image.paint.setPen(self.ui.image.pen)
            self.ui.image.paint.drawImage(self.ui.image.rect(), QtGui.QImage(self.ui.image.pixmap()))
            if len(points[currentIndex]) > 0:
                for (i,j) in points[currentIndex]:
                    if useSmartColor:
                        r,g,b = getSmartColor(currentImage.getpixel((i,j)))
                        self.ui.image.paint.setPen(QtGui.QPen(QtGui.QColor(r,g,b), pointWidth))
                        
                    self.ui.image.paint.drawPoint(i,j)
                    # if indicesVisible:
                        # self.ui.image.paint.drawText(i+4,j-4, QtCore.QString.number(points[currentIndex].index((i,j))))
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
        self.connect(self.ui.dotUndoButton, QtCore.SIGNAL("clicked()"), self.handleDotUndoButton)

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
        global points
        if imagePath:
            path = imagePath
        else:  
            path = QtGui.QFileDialog.getExistingDirectory(self, "Open directory", ".")
        if path:
            try:
                allFiles = os.listdir(path)
                imageFiles = sorted([x for x in allFiles if os.path.splitext(x)[-1] in extensions])        
                self.ui.imageComboBox.clear()
                points = []
                self.ui.coord.setText("")
                if len(imageFiles) > 0:
                    for imageFile in imageFiles:
                        annotationFile = os.path.join(path, os.path.splitext(imageFile)[0] + ".pts") # @TODO: hardcoded extension!
                        try:
                            f = open(annotationFile, 'r')
                            fileContent = f.read().split()
                            start =  fileContent.index("{") + 1
                            end = fileContent.index("}")
                            pts = []
                            while start < end:
                                pts.append((float(fileContent[start]),float(fileContent[start+1])))
                                start += 2
                            f.close()
                            points.append(pts)
                        except:
                            points.append([])
                            
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
        "Currently supports only saving pts files"
        global points, path
        filename = os.path.splitext(str(self.ui.imageComboBox.currentText()))[0]
        filePath = os.path.join(str(path), str(filename) + ".pts")
        currentIndex = self.ui.imageComboBox.currentIndex()
        f = open(filePath, 'w')
        f.write('version: 1\nn_points: %d\n{\n' % len(points[currentIndex]))
        for p in points[currentIndex]:
            f.write("    %d %d\n" % (p[0], p[1]))
        f.write('}\n')
        f.close()

        self.ui.statusBar.showMessage("File saved to %s" % (filePath))
        
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
        global path, currentIndex

        self.loadImage("%s/%s" % (path, text))
        self.setWindowTitle("%s (%s) - pilab-annotator" % (self.ui.imageComboBox.currentText(), path))
        currentIndex = self.ui.imageComboBox.currentIndex()
        self.ui.indexLabel.setText("(%d / %d)" % (currentIndex+1, self.ui.imageComboBox.count()))
        self.ui.image.repaint()
        self.ui.zoomImage.repaint()

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
    main = MainWindow()
    main.show()

    if len(sys.argv) == 2:
        main.openImageDirectory(sys.argv[1]) 

    sys.exit(app.exec_())
