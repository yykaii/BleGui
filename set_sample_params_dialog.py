from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QComboBox

class SetSampleParamsDialog(object):
 def __init__(self):
  pass

 def SetSampleParamsDialogInit(self):
  self.set_color_frame = QDialog(self)
  self.set_color_frame.setWindowTitle("配置采集参数")
  self.set_color_frame.resize(320, 280)
  self.set_color_frame.setMaximumSize(QtCore.QSize(320, 280))
  self.set_color_frame.setMinimumSize(QtCore.QSize(320, 280))
  self.shu_len = 10
  self.lable_len = 30
  self.label_first_y = 10

  level_1_label = QLabel(self.set_color_frame)
  level_1_label.setText('湿度过采样:')
  # 距左侧距离，距上方距离，本身长度横方向，本身宽度竖方向
  self.label_first_y += 20
  level_1_label.setGeometry(QtCore.QRect(10, self.label_first_y, 80, 30))
  self.humidity_sample_combox = QComboBox(self.set_color_frame)
  self.humidity_sample_combox.setGeometry(QtCore.QRect(140, self.label_first_y, 120, 30))

  level_2_label = QLabel(self.set_color_frame)
  level_2_label.setText('压力过采样:')
  self.label_first_y += self.shu_len+self.lable_len
  level_2_label.setGeometry(QtCore.QRect(10, self.label_first_y, 80, 30))
  self.pressure_sample_combox = QComboBox(self.set_color_frame)
  self.pressure_sample_combox.setGeometry(QtCore.QRect(140, self.label_first_y, 120, 30))

  level_3_label = QLabel(self.set_color_frame)
  level_3_label.setText('温度过采样:')
  self.label_first_y += self.shu_len+self.lable_len
  level_3_label.setGeometry(QtCore.QRect(10, self.label_first_y, 80, 30))
  self.temp_sample_combox = QComboBox(self.set_color_frame)
  self.temp_sample_combox.setGeometry(QtCore.QRect(140, self.label_first_y, 120, 30))

  level_4_label = QLabel(self.set_color_frame)
  level_4_label.setText('滤波设置:')
  self.label_first_y += self.shu_len+self.lable_len
  level_4_label.setGeometry(QtCore.QRect(10, self.label_first_y, 80, 30))
  self.filter_sample_combox = QComboBox(self.set_color_frame)
  self.filter_sample_combox.setGeometry(QtCore.QRect(140, self.label_first_y, 120, 30))

  level_5_label = QLabel(self.set_color_frame)
  level_5_label.setText('StandBy时间:')
  self.label_first_y += self.shu_len+self.lable_len
  level_5_label.setGeometry(QtCore.QRect(10, self.label_first_y, 100, 30))
  self.StandBy_sample_combox = QComboBox(self.set_color_frame)
  self.StandBy_sample_combox.setGeometry(QtCore.QRect(140, self.label_first_y, 120, 30))


  # self.set_sample_params_ok_button = QPushButton(self.set_color_frame)
  # self.set_sample_params_ok_button.setGeometry(QtCore.QRect(60, self.label_first_y+50, 100, 30))
  # self.set_sample_params_ok_button.setText('设置并关闭')

  self.set_sample_params_cancel_button = QPushButton(self.set_color_frame)
  self.set_sample_params_cancel_button.setGeometry(QtCore.QRect(120, self.label_first_y+50, 80, 30))
  self.set_sample_params_cancel_button.setText('关闭')

 def SetSampleParamsDialogShow(self):
  self.set_color_frame.show()

 def SetSampleParamsDialogClose(self):
  self.set_color_frame.close()