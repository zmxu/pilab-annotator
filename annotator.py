#! /usr/bin/python

# proje.py

import sys,os
from PyQt4 import QtGui, QtCore

extensions = (".png",".jpg")                    #image file extensions to filter
currentTool = ""                                #string to describe current tool
modes = {"dot":"click", "rectangle":"", "":""}  #modes for tools
currentIndex = 0                    #index of current image
points = []                                     #point coordinates for images

class Label(QtGui.QLabel):                    #label class to draw image and points
    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)
        
        self.paint = QtGui.QPainter()
        self.pen = QtGui.QPen(QtCore.Qt.red)

    def paintEvent(self, event):
        global points, currentIndex
        self.pen.setWidth(4)
        self.paint.begin(self)
        self.paint.setPen(self.pen)
        if self.pixmap():
            self.paint.drawImage(self.rect(), QtGui.QImage(self.pixmap()))
            if len(points[currentIndex]) > 0:
                for (i,j) in points[currentIndex]:
                    self.paint.drawPoint(i,j)
        self.paint.end()

    def mousePressEvent(self, event):
        global points, modes, currentTool, currentIndex
        if currentTool == "dot":
            if modes["dot"] == "click":
                points[currentIndex].append((event.pos().x(),event.pos().y()))
                self.repaint()
            elif modes["dot"] == "drag":
                self.dragIsActive = False
                for (i,j) in points[currentIndex]:
                    if abs(i-event.pos().x()) <= 3 and abs(j-event.pos().y()) <= 3:
                        self.pointToDrag = (i,j)
                        self.dragIsActive = True

    def mouseReleaseEvent(self, event):
        global points, modes, currentTool, currentIndex
        if currentTool == "dot":
            if modes["dot"] == "drag" and self.dragIsActive:
                points[currentIndex].remove(self.pointToDrag)
                points[currentIndex].append((event.pos().x(),event.pos().y()))
                self.repaint()
                self.dragIsActive = False


class ImageFrame(QtGui.QFrame):                    #the frame class, that the image will be displayed in
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setupUi()

    def setupUi(self):
        self.setFixedSize(600,534)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        
        self.image = Label(self)  #QtGui.QLabel(self)
        self.coordinates = QtGui.QLabel(self)
        self.scrollArea = QtGui.QScrollArea(self)
        self.scrollArea.setBackgroundRole(QtGui.QPalette.Dark)
        self.scrollArea.setWidget(self.image)
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.scrollArea)
        self.setLayout(layout)

        self.setMouseTracking(True)
        self.image.setMouseTracking(True)
        self.scrollArea.setMouseTracking(True)

    def loadImage(self, path):
        self.pixmap = QtGui.QPixmap(path)
        self.image.setPixmap(self.pixmap)
        self.image.setFixedSize(self.pixmap.size())
       
    def mouseMoveEvent(self, event):
        if 0 <= event.pos().x()-10 <= self.scrollArea.rect().width() and 0 <= event.pos().y()-10 <= self.scrollArea.rect().height():
            self.coordinates.setText("(%d, %d)" % (event.pos().x()-10, event.pos().y()-10))


class NavigationFrame(QtGui.QFrame):                    #frame class for navigation
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setupUi()

    def setupUi(self):
        self.setFixedSize(150, 150)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFont(QtGui.QFont("Serif", 8, QtGui.QFont.Light))

        self.nameLabel = QtGui.QLabel("Navigation", self)

        self.prevButton = QtGui.QPushButton("-1", self)
        self.nextButton = QtGui.QPushButton("+1", self)
        self.firstButton = QtGui.QPushButton("|<", self)
        self.minusTenButton = QtGui.QPushButton("-10", self)
        self.plusTenButton = QtGui.QPushButton("+10", self)
        self.lastButton = QtGui.QPushButton(">|", self)

        self.prevButton.setShortcut("Ctrl+P")
        self.nextButton.setShortcut("Ctrl+N")
        
        self.prevButton.setToolTip("Previous image (Ctrl-P)")
        self.nextButton.setToolTip("Next image (Ctrl-N)")
        self.firstButton.setToolTip("First image")
        self.lastButton.setToolTip("Last image")
        self.minusTenButton.setToolTip("10 images back")
        self.plusTenButton.setToolTip("10 images forward")

        self.imageComboBox = QtGui.QComboBox(self)

        topLayout = QtGui.QHBoxLayout()
        middleLayout = QtGui.QHBoxLayout()
        mainLayout = QtGui.QVBoxLayout()
        topLayout.addWidget(self.prevButton)
        topLayout.addWidget(self.nextButton)
        middleLayout.addWidget(self.firstButton)
        middleLayout.addWidget(self.minusTenButton)
        middleLayout.addWidget(self.plusTenButton)
        middleLayout.addWidget(self.lastButton)
        mainLayout.addWidget(self.nameLabel)
        mainLayout.addLayout(topLayout)
        mainLayout.addLayout(middleLayout)
        mainLayout.addWidget(self.imageComboBox)
        mainLayout.addStretch()

        self.setLayout(mainLayout)

        self.connect(self.prevButton, QtCore.SIGNAL("clicked()"), self.previousImage)
        self.connect(self.nextButton, QtCore.SIGNAL("clicked()"), self.nextImage)
        self.connect(self.plusTenButton, QtCore.SIGNAL("clicked()"), self.plusTenImage)
        self.connect(self.minusTenButton, QtCore.SIGNAL("clicked()"), self.minusTenImage)
        self.connect(self.firstButton, QtCore.SIGNAL("clicked()"), self.firstImage)
        self.connect(self.lastButton, QtCore.SIGNAL("clicked()"), self.lastImage)

    def previousImage(self):
        index = self.imageComboBox.currentIndex()-1
        if index<0:
            index=0
        self.imageComboBox.setCurrentIndex(index)
    def nextImage(self):
        index = self.imageComboBox.currentIndex()+1
        if index >= self.imageComboBox.count():
            index=self.imageComboBox.count()-1
        self.imageComboBox.setCurrentIndex(index)
    def plusTenImage(self):
        index = self.imageComboBox.currentIndex()+10
        if index >= self.imageComboBox.count():
            index=self.imageComboBox.count()-1
        self.imageComboBox.setCurrentIndex(index)
    def minusTenImage(self):
        index = self.imageComboBox.currentIndex()-10
        if index < 0:
            index=0
        self.imageComboBox.setCurrentIndex(index)
    def lastImage(self):
        self.imageComboBox.setCurrentIndex(self.imageComboBox.count()-1)
    def firstImage(self):
        self.imageComboBox.setCurrentIndex(0)


class ToolFrame(QtGui.QFrame):                    #frame class for the toolbox
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setupUi()

    def setupUi(self):
        self.setFixedSize(150,120)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFont(QtGui.QFont("Serif", 8, QtGui.QFont.Light))

        self.nameLabel = QtGui.QLabel("Toolbox", self)
        self.dotButton = QtGui.QPushButton(".", self)
        self.dotButton.setFixedWidth(30)
        self.dotButton.setCheckable(True)
        self.rectangleButton = QtGui.QPushButton("|_|", self)
        self.rectangleButton.setFixedWidth(30)
        self.rectangleButton.setCheckable(True)
        
        topLayout = QtGui.QHBoxLayout()
        mainLayout = QtGui.QVBoxLayout()
        topLayout.addWidget(self.dotButton)
        topLayout.addWidget(self.rectangleButton)
        topLayout.addStretch()
        mainLayout.addWidget(self.nameLabel)
        mainLayout.addLayout(topLayout)
        mainLayout.addStretch()
        self.setLayout(mainLayout)

        self.connect(self.dotButton, QtCore.SIGNAL("toggled(bool)"), self.handleDotButton)
        self.connect(self.rectangleButton, QtCore.SIGNAL("toggled(bool)"), self.handleRectButton)

    def handleDotButton(self, check):
        global currentTool
        if check:
            self.dotButton.setEnabled(not check)
            self.rectangleButton.setEnabled(check)
            self.rectangleButton.setChecked(not check)
            currentTool = "dot"
            
    def handleRectButton(self, check):
        if check:
            self.rectangleButton.setEnabled(not check)
            self.dotButton.setEnabled(check)
            self.dotButton.setChecked(not check)


class OptionFrame(QtGui.QFrame):
    def __init__(self, style, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.style = style
        self.setupUi()

    def setupUi(self):
        self.setFixedSize(150, 120)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFont(QtGui.QFont("Serif", 8, QtGui.QFont.Light))

        if self.style == "dot":
            self.nameLabel = QtGui.QLabel("Dot Options", self)

            self.dotClickButton = QtGui.QPushButton("click")
            self.dotDragButton = QtGui.QPushButton("drag")
            self.dotUndoButton = QtGui.QPushButton("undo")

            self.dotClickButton.setCheckable(True)
            self.dotDragButton.setCheckable(True)

            topLayout = QtGui.QHBoxLayout()
            topLayout.addWidget(self.dotClickButton)
            topLayout.addWidget(self.dotDragButton)
            topLayout.addWidget(self.dotUndoButton)

            self.connect(self.dotClickButton, QtCore.SIGNAL("toggled(bool)"), self.handleDotClickButton)
            self.connect(self.dotDragButton, QtCore.SIGNAL("toggled(bool)"), self.handleDotDragButton)
            self.connect(self.dotUndoButton, QtCore.SIGNAL("clicked()"), self.handleDotUndoButton)
            
            self.dotClickButton.setChecked(True)                    #initially click mode is on

        elif self.style == "rectangle":
            self.nameLabel = QtGui.QLabel("rectangle", self)

            self.dotClickButton = QtGui.QPushButton("click")
            self.dotDragButton = QtGui.QPushButton("drag")

            topLayout = QtGui.QHBoxLayout()
            topLayout.addWidget(self.dotClickButton)
            topLayout.addWidget(self.dotDragButton)

        elif self.style == "empty":
            self.nameLabel = QtGui.QLabel("Options", self)
            topLayout = QtGui.QHBoxLayout()
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.nameLabel)
        mainLayout.addLayout(topLayout)
        mainLayout.addStretch()
        self.setLayout(mainLayout)

    def handleDotUndoButton(self):
        global points, currentIndex
        if len(points) > currentIndex and points[currentIndex]:
            points[currentIndex].pop()

    def handleDotClickButton(self, check):
        if check:
            global modes
            modes["dot"] = "click"
            self.dotClickButton.setEnabled(not check)
            self.dotDragButton.setEnabled(check)
            self.dotDragButton.setChecked(not check)
            
    def handleDotDragButton(self, check):
        if check:
            global modes
            modes["dot"] = "drag"
            self.dotDragButton.setEnabled(not check)
            self.dotClickButton.setEnabled(check)
            self.dotClickButton.setChecked(not check)
 

class ZoomFrame(QtGui.QFrame):
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setupUi()

    def setupUi(self):
        self.setFixedSize(150, 120)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFont(QtGui.QFont("Serif", 8, QtGui.QFont.Light))

        self.nameLabel = QtGui.QLabel("Zoom", self)

        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.nameLabel)
        mainLayout.addStretch()
        self.setLayout(mainLayout)


class MainWindow(QtGui.QMainWindow):                    #main window class for the application
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        path = ""
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle("Proje")
        self.setFixedSize(1000, 600)
        self.move(50,50)

        self.centralWidget = QtGui.QWidget()
        self.setCentralWidget(self.centralWidget)

        self.openAction = QtGui.QAction(QtGui.QIcon("icons/open.png"), "Open", self)
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.setStatusTip("Open a directory containing images")
        self.exitAction = QtGui.QAction(QtGui.QIcon("icons/exit.png"), "Exit", self)
        self.exitAction.setShortcut("Ctrl+Q")
        self.exitAction.setStatusTip("Exit application")

        self.imageBox = ImageFrame(self)
        self.toolBox = ToolFrame(self)
        self.emptyBox = OptionFrame("empty", self)
        self.dotOptionBox = OptionFrame("dot", self)
        self.rectOptionBox = OptionFrame("rectangle", self)
        self.zoomBox = ZoomFrame(self)
        self.navigationBox = NavigationFrame(self)

        self.dotOptionBox.hide()
        self.rectOptionBox.hide()

        self.statusBar = self.statusBar()
        self.statusBar.addPermanentWidget(self.imageBox.coordinates)
        self.menuBar = self.menuBar()
        self.fileMenu = self.menuBar.addMenu("&File")
        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAction)

        leftLayout = QtGui.QVBoxLayout()                    #layout management
        rightLayout = QtGui.QVBoxLayout()
        mainLayout = QtGui.QHBoxLayout()
        leftLayout.addWidget(self.toolBox)
        leftLayout.addWidget(self.emptyBox)
        leftLayout.addWidget(self.dotOptionBox)
        leftLayout.addWidget(self.rectOptionBox)
        leftLayout.addWidget(self.zoomBox)
        leftLayout.addStretch()
        rightLayout.addWidget(self.navigationBox)
        rightLayout.addStretch()
        mainLayout.addLayout(leftLayout)
        mainLayout.addWidget(self.imageBox)
        mainLayout.addLayout(rightLayout)
        self.centralWidget.setLayout(mainLayout)

        self.connect(self.openAction, QtCore.SIGNAL("triggered()"), self.openImageDirectory)
        self.connect(self.exitAction, QtCore.SIGNAL("triggered()"), QtCore.SLOT("close()"))
        self.connect(self.navigationBox.imageComboBox, QtCore.SIGNAL("currentIndexChanged(QString)"), self.changeImage)
        self.connect(self.toolBox.dotButton, QtCore.SIGNAL("toggled(bool)"), self.showDotOptions)
        self.connect(self.toolBox.rectangleButton, QtCore.SIGNAL("toggled(bool)"), self.showRectOptions)
        self.connect(self.dotOptionBox.dotUndoButton, QtCore.SIGNAL("clicked()"), self.imageBox.image.repaint)

    def openImageDirectory(self):
        global path, points
        path = unicode(QtGui.QFileDialog.getExistingDirectory(self, "Open directory", "/home"))
        if path:
            self.setWindowTitle("Annotator - " + path)
            allFiles = os.listdir(path)
            imageFiles = sorted([x for x in allFiles if os.path.splitext(x)[-1] in extensions])        
            self.navigationBox.imageComboBox.clear()
            points = []
            if len(imageFiles) > 0:
                for i in imageFiles:
                    points.append([])
                self.navigationBox.imageComboBox.addItems(imageFiles)
                self.imageBox.loadImage("%s/%s" % (path, self.navigationBox.imageComboBox.currentText()))

    def changeImage(self, text):
        global path, currentIndex
        self.imageBox.loadImage("%s/%s" % (path, text))
        currentIndex = self.navigationBox.imageComboBox.currentIndex()

    def showDotOptions(self):
        self.emptyBox.close()
        self.rectOptionBox.close()
        self.dotOptionBox.show()
    def showRectOptions(self):
        self.emptyBox.close()
        self.dotOptionBox.close()
        self.rectOptionBox.show()


app = QtGui.QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec_())
