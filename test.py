import pyqtgraph as pg

import sys
import numpy as np
from PyQt5 import QtCore, QtWidgets

x = np.random.random(10)
pg.plot(x,title = "坚持")    #该行代码只是绘制了图形，但是没有执行的GUI窗口，所以直会一闪而过

x = [2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50]
y = [10,12,15,16,20,25,26,28,30,25,36,38,39,55,42,41,20,12,10,23,2,35,36,37,56,]


# 主窗口类
class MainWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("学习使我快乐") # 设置窗口标题
        main_widget = QtWidgets.QWidget() # 实例化一个widget部件
        main_widget.resize(1000,600)
        main_layout = QtWidgets.QGridLayout() # 实例化一个网格布局层
        main_widget.setLayout(main_layout) # 设置主widget部件的布局为网格布局
        p3 = pg.PlotWidget(title="Drawing with points")
        p4 = pg.PlotWidget(title = "Second")
        p3.plot(x=x, y=y, pen=(0, 255, 0), symbolBrush=(0, 0, 255), symbolPen='b')
        p4.plot(y,pen=(0, 255, 0), symbolBrush=(0, 0, 255), symbolPen='b')
        main_layout.addWidget(p3)
        main_layout.addWidget(p4)
        self.setCentralWidget(main_widget) # 设置窗口默认部件为主widget

# 运行函数
def main():
    app = QtWidgets.QApplication(sys.argv)
    gui = MainWidget()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
