import os
import time
from xml.etree import ElementTree as ET
from PySide import QtGui, QtCore

# written by Frank Rueter with (lots of) help from Aaron Richiger
# TO DO:
#    -re-arrange code to enable nuke to to register widget
#    -help icon with tooltip and link to nukepedia url
#    -preferences for task height, status widget?
#    -set up git repo
########## MODEL CLASSES ###########################################################################

class Task(object):
    '''
    Model for a task. Task attributes are:
       name - short description of the task
       priority - integer
       status - float (0 > waiting to start, 1 > finished)
    '''

    def __init__(self, name='new task', priority=1, status=0):
        self.name = name
        self.priority = priority
        self.status = status
        self.index = 0
        
    def setName(self, name):
        self.name = name

    def setPriority(self, priority):
        self.priority = priority
        
    def setStatus(self, status):
        self.status = status
        

    def __repr__(self):
        return 'Task(name=%s, priority=%D, status=%d' % (self.index, self.name)
    
    def __str__(self):
        return '-' * 20 + '\np%s:\t\t%s\t\t (%s)' % (self.priority, self.name, ['waiting', 'in progress', 'finished'][self.status])

class TaskStore(QtCore.QObject):
    '''Stores, filters, sorts and delivers all tasks'''
    
    def __init__(self, tasksFile='/tmp/settings.xml'):
        super(TaskStore, self).__init__()
        self.tasksFile = tasksFile
        self.tasks = self.loadTasks()
        self.resetTasks()

    def addTask(self):
        '''Insert a new task into the task store'''

        newTask = Task()
        self.tasks.insert(0, newTask)
        return newTask

    def deleteTask(self):
        taskToDelete = self.sender().parent().task
        taskToDelete.index = -2
        self.tasks = [task for task in self.tasks if taskToDelete != task]
        self.resetTasks()

    def loadTasks(self):
        '''Try to load tasks from disk. If no tasks have been saved return default data'''
        
    
        if os.path.isfile(self.tasksFile):
            tree = ET.parse(self.tasksFile)
            root = tree.getroot()
            taskElements = root.findall('Task')
            if not taskElements:
                # NO TASKS WERE SAVED
                return [Task()]

            taskList = []
            for te in taskElements:
                task = Task(name=te.findtext('name'),
                            priority=int(te.findtext('priority')),
                            status=int(te.findtext('status')))
                taskList.append(task)
            return taskList
        else:
            # NO SETTINGS FILE FOUND
            return [Task()]

    def resetTasks(self):
        '''Assign an index from 1..n to all tasks in the store'''

        for i, task in enumerate(self.tasks):
            task.index = i
    def filterFinished(self, hideFinished):
        '''Hide finished tasks by assigning a negative index'''
        
        for task in self.tasks:
            if hideFinished and task.status == 2:
                task.index = -1
                
    def sortByPriority(self, active):
        '''Sort tasks by their priority by assigning a corresponding index'''
        sortedTasks = sorted([t for t in self.tasks if t.index >= 0], key=lambda task: task.priority)
        if active:
            # sort highest first
            sortedTasks.reverse()

        for i, task in enumerate([t for t in sortedTasks if t.index >= 0]):
            task.index = i


########## VIEW CLASSES ###########################################################################

class TaskWidget(QtGui.QWidget):
    '''Widget to show a single task'''
    TASKWIDGETWIDTH = 400
    TASKWIDGETHEIGHT = 40
    TASKWIDGETSPACING = 1.05

    def __init__(self, task, parent=None):
        super(TaskWidget, self).__init__(parent)
        self.task = task
        self.setupUi()

    def setupUi(self):
        self.setAutoFillBackground(True)
        hLayout = QtGui.QHBoxLayout(self)
        self.setLayout(hLayout)
        self.taskNameWidget = QtGui.QLineEdit(self.task.name)
        self.priorityWidget = PriorityWidget()
        self.priorityWidget.setValue(self.task.priority)
        self.statusWidget = StatusWidgetBar()
        self.statusWidget.setCurrentIndex(self.task.status)
        self.deleteWidget = DeleteWidget('delete')

        hLayout.addWidget(self.taskNameWidget)
        hLayout.addWidget(self.priorityWidget)
        hLayout.addWidget(self.statusWidget)
        hLayout.addWidget(self.deleteWidget)
        self.taskNameWidget.setSelection(0, len(self.taskNameWidget.text()))
        self.taskNameWidget.setFocus()

    def update(self):
        '''Resize this widget to use full width'''
        super(TaskWidget, self).update()
        self.resize(self.parent().width(), TaskWidget.TASKWIDGETHEIGHT)

    def getNewPosition(self):
        '''Return the position of this task widget according to the index of its task'''
        x = 0        
        if self.task.index >= 0:
            # VISIBLE WIDGETS MOVE UP TO FILL SPACE
            y = self.task.index * TaskWidget.TASKWIDGETHEIGHT * TaskWidget.TASKWIDGETSPACING 
        elif self.task.index == -1:
            # HIDDEN WIDGETS MOVE UP
            y = self.task.index * self.height()
            self.raise_()
        elif self.task.index == -2:
            # DELETED WIDGETS DROP DOWN
            y = self.parentWidget().height()
            self.raise_()

        return QtCore.QPoint(x, y)

class MainWindow(QtGui.QWidget):
    '''GUI to show and edit multiple tasks'''
    
    def __init__(self, taskStore, settingsFile='/tmp/settings.xml', parent=None):
        super(MainWindow, self).__init__(parent)
        self.settingsFile = settingsFile
        self.taskStore = taskStore
        self.animGroupsDeleted = [] # HOLD ANIMATIONS FOR DELETED WIDGETS - REQUIRED FOR OVERLAPPING DELETE ACTIONS
        self.setupUI()

    def setupUI(self):
        self.resize(300, 600)
        mainLayout = QtGui.QVBoxLayout()
        self.setLayout(mainLayout)
        self.buttonLayout = QtGui.QHBoxLayout()
        self.addTaskButton = QtGui.QPushButton('Add Task')
        self.addTaskButton.setToolTip('add a new task to the list')
        self.sortButton = QtGui.QPushButton('Sort by Priority')
        self.sortButton.setCheckable(True)
        self.sortButton.setToolTip('push to sort so highest priorities are at the top,\notherwise lowest will be at the top.')
        self.helpButton = QtGui.QPushButton('?')
        self.helpButton.setMaximumWidth(30)
        self.helpButton.setFlat(True)
        self.helpButton.setToolTip(self.__helpText())
        self.hideButton = QtGui.QPushButton('Hide Finished Tasks')
        self.hideButton.setCheckable(True)
        self.hideButton.setToolTip('hide finished tasks to keep the list tidy')      
        self.clipboardButton = QtGui.QPushButton('Copy To Clipboard')
        
        self.buttonLayout.addWidget(self.addTaskButton)
        self.buttonLayout.addWidget(self.sortButton)
        self.buttonLayout.addWidget(self.hideButton)
        self.buttonLayout.addWidget(self.clipboardButton)
        self.buttonLayout.addSpacing(20)
        self.buttonLayout.addWidget(self.helpButton)
        self.layout().addLayout(self.buttonLayout)
        
        self.taskContainer = QtGui.QWidget()
        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setWidget(self.taskContainer)
        self.layout().addWidget(self.scrollArea)
        
        self.taskWidgets = [TaskWidget(t, self.taskContainer) for t in self.taskStore.tasks]
        self.update()
    
    def __helpText(self):
        return '''
        Written by Frank Rueter|OHUfx
        
        This is a simple to-do list that saves itself with the nuke script, so it's easier to organise
        your own work as well as help others who might pick up a shot from you.
        
        Use LMB and RMB to change priorities to sort the list accordingly.
        Change the status and hide finished tasks to keep an overview over your work load.
        
        Click the help button to open the respective nukepedia page.
        '''
    
    def update(self):
        '''Animate the view to match sorting and filtering requests'''

        self.deletedTaskWidgets = [tw for tw in self.taskWidgets if tw.task.index == -2]
        taskWidgetsHeight = len(self.taskWidgets) * (TaskWidget.TASKWIDGETHEIGHT * TaskWidget.TASKWIDGETSPACING)
        self.taskContainer.resize(self.scrollArea.width() - 20, max(taskWidgetsHeight, self.scrollArea.height()))

        self.animGroup = QtCore.QParallelAnimationGroup()
        animGroupForDeletedWidget = QtCore.QParallelAnimationGroup()
        animGroupForDeletedWidget.finished.connect(self.deleteTaskWidget)

        for taskWidget in self.taskWidgets:          
            moveAnimation = QtCore.QPropertyAnimation(taskWidget, 'pos')
            moveAnimation.setDuration(1000)
            moveAnimation.setStartValue(taskWidget.pos())
            moveAnimation.setEndValue(taskWidget.getNewPosition())

            if taskWidget.task.index == -2:
                # DELETED WIDGET
                moveAnimation.setEasingCurve(QtCore.QEasingCurve.InCubic)
                animGroupForDeletedWidget.addAnimation(moveAnimation)
            else:
                moveAnimation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
                self.animGroup.addAnimation(moveAnimation)
            taskWidget.update()

        self.animGroup.start()
        if animGroupForDeletedWidget.animationCount():
            self.animGroupsDeleted.append(animGroupForDeletedWidget)
            animGroupForDeletedWidget.start()



    def addTaskWidget(self, task):
        '''Add a new widget for task'''

        newTaskWidget = TaskWidget(task, self.taskContainer)
        newTaskWidget.show()
        self.taskWidgets.append(newTaskWidget)
        return newTaskWidget

    def deleteTask(self):
        '''Delete a task'''
        self.taskWidgetToDelete = self.sender().parent()
        self.taskWidgets = [taskWidget for taskWidget in self.taskWidgets if self.taskWidgetToDelete != taskWidget]

    def deleteTaskWidget(self):
        '''remove deleted widgets to avoid surprises when rescaling the parent window'''
        sender = self.sender()
        deletedWidget = sender.animationAt(0).targetObject()
        deletedWidget.setParent(None)
        self.animGroupsDeleted.remove(sender) # JUST CLEANING UP, SHUOLDNT BE NECESSARY

    def closeEvent(self, event):
        '''Store tasks and settings to disk before exising the app'''
        self.saveSettingsAndTasks()
        
    def loadSettings(self):
        '''Try to load sorting and filtering settings from disk. If nothing has been saved do nothing'''

        if os.path.isfile(self.settingsFile):
            tree = ET.parse(self.settingsFile)
            root = tree.getroot()
            settings = root.find('Settings')
            self.hideButton.setChecked(eval(settings.findtext('hideFinished')))
            self.sortButton.setChecked(eval(settings.findtext('sortState')))
        else:
            pass

    def saveSettingsAndTasks(self):
        '''Dump current sorting and filtering choices to disk for reloading'''

        print 'saving task panel\'s settings to disk: %s' % self.settingsFile
        settingsToBeSaved = {}
        settingsToBeSaved['hideFinished'] = str(self.hideButton.isChecked())
        settingsToBeSaved['sortState'] = str(self.sortButton.isChecked())

        root = ET.Element('ToDoPanel')
        settingsEle = ET.SubElement(root, 'Settings')
        for k, v in settingsToBeSaved.iteritems():
            settingEle = ET.SubElement(settingsEle, k)
            settingEle.text = v
        
        for task in self.taskStore.tasks:
            taskDict = task.__dict__
            #taskDictStr = dict(zip(taskDict.keys(), [str(v) for v in taskDict.values()]))
            tasksEle = ET.SubElement(root, 'Task')
            for k, v in taskDict.iteritems():
                taskEle = ET.SubElement(tasksEle, k)
                taskEle.text = str(v)

        tree = ET.ElementTree(root)
        tree.write(self.settingsFile)
        


    def resizeEvent(self, event):
        self.update()
    def launchWebsite(self):
        import webbrowser
        webbrowser.open('http://www.nukepedia.com/python/ui/ToDoPanel')
    def copyToClipboard(self):
        sortedTasks = sorted([t for t in self.taskStore.tasks if t.index >= 0], key=lambda task: task.priority)
        if self.sortButton.isChecked():
            sortedTasks.reverse()

        clipboard = QtGui.QApplication.clipboard() 
        text = '\n'.join([str(t) for t in sortedTasks])
        clipboard.setText(text)

class PriorityWidget(QtGui.QPushButton):
    valueChanged = QtCore.Signal(int)
    allowSorting = QtCore.Signal()

    def __init__(self, parent=None):
        super(PriorityWidget, self).__init__(parent)
        self.color = QtGui.QColor(247, 147, 30, 255)
        self.font = QtGui.QFont('Helvetica', 12, QtGui.QFont.Bold)
        self.setToolTip('priority\n\nLMB to increase\nRMB to decrease\nmove mouse away afterchanging value to trigger re-sorting')
        self.active = False
        self.value = 0
        
    def setValue(self, value):
        self.value = value
        self.valueChanged.emit(self.value)
        self.update()

    def paintEvent(self, event):
        '''Paint the custom look'''

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.HighQualityAntialiasing)
        painter.setFont(self.font)
        if self.active or self.hasFocus():
            painter.setPen(self.color.lighter())
        else:
            painter.setPen(self.color)
     
        painter.drawText(self.rect(), QtCore.Qt.AlignCenter, str(self.value))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setValue(self.value + 1)
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.setValue(self.value - 1)

    def enterEvent(self, event):
        self.active = True

    def leaveEvent(self, event):
        self.active = False
        self.clearFocus()
        self.allowSorting.emit()

class StatusWidgetPie(QtGui.QComboBox):
    def __init__(self, parent=None):
        super(StatusWidgetPie, self).__init__(parent)
        self.setToolTip('status (click to edit)')
        self.addItems(['waiting', 'in progress', 'finished'])
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.size = QtCore.QSize(20, 20)

    def sizeHint(self):
        return self.size

    def minimumSizeHint(self):
        return self.size
    
    def maximumSizeHint(self):
        return self.size 

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        parent = self.parentWidget()

        pieRect = QtCore.QRect(1, 1, self.width()-2, self.height()-2)
        startAngle = 0 * 16

        if self.currentIndex() == 0:
            # STATUS = WAITING
            painter.drawEllipse(pieRect)
        elif self.currentIndex() == 1:
            # STATUS = IN PROGGRESS
            painter.setPen(QtGui.QColor(0,0,0,0))
            painter.setBrush(QtGui.QColor(255, 140, 30))
            startAngle = 90 * 16
            spanAngle = self.currentIndex() * 270 * 16
            painter.drawPie(pieRect, startAngle, spanAngle)
        elif self.currentIndex() == 2:
            # STATUS = FINISHED
            painter.setPen(QtGui.QColor(0,0,0,0))
            painter.setBrush(QtGui.QColor('darkGreen'))
            spanAngle = self.currentIndex() * 360 * 16
            painter.drawPie(pieRect, startAngle, spanAngle)

class StatusWidgetBar(QtGui.QComboBox):
    def __init__(self, parent=None):
        super(StatusWidgetBar, self).__init__(parent)
        self.setToolTip('status (click to edit)')
        self.addItems(['waiting', 'in progress', 'finished'])
        self.active = False
        self.colWaiting = QtGui.QColor(180, 100, 10)
        self.colInProgress = QtGui.QColor(255, 140, 30)
        self.colFinished = QtGui.QColor('darkGreen')
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        currentIndex = self.currentIndex()
        painter.setPen(QtGui.QColor(0,0,0,0))

        if currentIndex == 0:
            progress =  .1
            if self.active or self.hasFocus():
                painter.setBrush(self.colWaiting.lighter())
            else:
                painter.setBrush(self.colWaiting)
        elif currentIndex == 1:
            progress = .6
            if self.active or self.hasFocus():
                painter.setBrush(self.colInProgress.lighter())
            else:
                painter.setBrush(self.colInProgress)
        elif currentIndex == 2:
            progress = 1
            if self.active or self.hasFocus():
                painter.setBrush(self.colFinished.lighter())
            else:
                painter.setBrush(self.colFinished)
        barRect = QtCore.QRect(0, self.height() * .25, (self.width()) * progress, self.height() * .5)
        painter.drawRect(barRect)
        
        outline = QtCore.QRect(1, self.height() * .25, (self.width())-2, self.height() * .5)
        painter.setBrush(QtGui.QColor(0,0,0,0))
        painter.setPen(QtGui.QColor(0,0,0,255))
        painter.drawRect(outline)

    def enterEvent(self, event):
        self.active = True
        
    def leaveEvent(self, event):
        self.active = False
        self.clearFocus()
    
    def mouseReleaseEvent(self, event):
        self.active = False
        super(StatusWidgetBar, self).mouseReleaseEvent(event)
        self.update()
        

class DeleteWidget(QtGui.QPushButton):
    def __init__(self, parent=None):
        super(DeleteWidget, self).__init__(parent)
        self.size = QtCore.QSize(20, 20)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.padding = 7
        self.active = False
        self.inactiveColor = QtGui.QColor(180, 50, 0)
        self.activeColor = self.inactiveColor.lighter()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = painter.pen()
        if self.active or self.hasFocus():
            pen.setColor(self.activeColor)
        else:
            pen.setColor(self.inactiveColor)
        pen.setWidth(3)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)        
        polygon1 = QtGui.QPolygon()
        polygon1 << QtCore.QPoint(self.padding, self.padding) << QtCore.QPoint(self.width() - self.padding, self.height() - self.padding)
        polygon2 = QtGui.QPolygon()
        polygon2 << QtCore.QPoint(self.padding,self.height() - self.padding) << QtCore.QPoint(self.width() - self.padding, self.padding)

        polygon1.translate(0,1)
        polygon2.translate(0,1)
        painter.drawPolyline(polygon1)
        painter.drawPolyline(polygon2)

    def enterEvent(self, event):
        self.active = True
        
    def leaveEvent(self, event):
        self.active = False
        self.clearFocus()

    def sizeHint(self):
        return self.size

    def minimumSizeHint(self):
        return self.size
    
    def maximumSizeHint(self):
        return self.size 


########## CONTROLLER CLASSES ###########################################################################

class Controller(QtCore.QObject):
    '''Controls interaction between model and view'''

    def __init__(self):
        super(Controller, self).__init__()
        self.taskStore = TaskStore()
        self.view = MainWindow(self.taskStore)
        self.connectSignals()

    def start(self):
        '''Start application, if possible load settings from previous session'''

        self.view.show()
        self.view.loadSettings()
        self.applyFilterAndSorting()

    def connectSignals(self):
        '''Connect the widgets of the maine windoe with their slots'''

        self.view.addTaskButton.clicked.connect(self.onAddTask)
        self.view.sortButton.clicked.connect(self.applyFilterAndSorting)
        self.view.hideButton.clicked.connect(self.applyFilterAndSorting)
        self.view.helpButton.clicked.connect(self.view.launchWebsite)
        self.view.clipboardButton.clicked.connect(self.view.copyToClipboard)
        for tw in self.view.taskWidgets:
            self.connectTaskWidgetSignals(tw)

    def connectTaskWidgetSignals(self, taskWidget):
        '''Connect a task widget's signals with their slots'''
        taskWidget.taskNameWidget.textChanged.connect(taskWidget.task.setName)
        taskWidget.priorityWidget.valueChanged.connect(taskWidget.task.setPriority)
        taskWidget.priorityWidget.allowSorting.connect(self.applyFilterAndSorting)
        taskWidget.statusWidget.currentIndexChanged.connect(taskWidget.task.setStatus)
        taskWidget.statusWidget.currentIndexChanged.connect(self.applyFilterAndSorting)
        taskWidget.deleteWidget.clicked.connect(self.taskStore.deleteTask)
        taskWidget.deleteWidget.clicked.connect(self.view.update)
        taskWidget.deleteWidget.clicked.connect(self.view.deleteTask)

        
        
                                                
    def onAddTask(self):
        '''Add a new task'''

        newTask = self.taskStore.addTask()
        newTaskWidget = self.view.addTaskWidget(newTask)
        self.connectTaskWidgetSignals(newTaskWidget)
        self.applyFilterAndSorting()

    def applyFilterAndSorting(self):
        '''Filter and sort all tasks according to settings, then update the view accordingly'''
        self.taskStore.resetTasks()
        self.taskStore.filterFinished(self.view.hideButton.isChecked())
        self.taskStore.sortByPriority(self.view.sortButton.isChecked())
        self.view.update()
        
        

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    controller = Controller()
    controller.start()
    #w = PriorityWidget()
    #w.show()
    sys.exit(app.exec_())

