#!/usr/bin/env python
# -*-coding: utf-8 -*-
# author: yang time:2022/4/26

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QLabel,QCheckBox, QPushButton
from PyQt5.QtGui import QFont

class SetSampleChannelDialog(object):
 def __init__(self):
  pass

 def SetSampleChannelDialogInit(self):
  self.setting_rx_frame = QDialog()
  self.setting_rx_frame.setWindowTitle("选择采集传感器")
  # 长和高
  self.setting_rx_frame.resize(450, 250)
  self.setting_rx_frame.setMaximumSize(QtCore.QSize(450, 250))
  self.setting_rx_frame.setMinimumSize(QtCore.QSize(450, 250))
  font = QFont()
  self.first_x = 20
  self.first_y = 10

  # 距左侧距离，距上方距离，本身长度横方向，本身宽度竖方向

  setting_rx_show_label = QLabel(self.setting_rx_frame)
  setting_rx_show_label_x = self.first_x
  setting_rx_show_label_y = self.first_y
  setting_rx_show_label.setGeometry(QtCore.QRect(setting_rx_show_label_x, setting_rx_show_label_y, 300, 30))
  font.setPointSize(12)
  setting_rx_show_label.setText('在此选择要采集的传感器')
  setting_rx_show_label.setFont(font)

  channel1_x = setting_rx_show_label_x
  channel1_y = setting_rx_show_label_y + 50
  self.Ch1_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch1_CheckBox.setGeometry(QtCore.QRect(channel1_x, channel1_y, 80, 20))
  self.Ch1_CheckBox.setText("ch-1")

  channel2_x = channel1_x + 80 + 20
  channel2_y = channel1_y
  self.Ch2_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch2_CheckBox.setGeometry(QtCore.QRect(channel2_x, channel2_y, 80, 20))
  self.Ch2_CheckBox.setText("ch-2")

  channel3_x = channel2_x + 80 + 20
  channel3_y = channel2_y
  self.Ch3_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch3_CheckBox.setGeometry(QtCore.QRect(channel3_x, channel3_y, 80, 20))
  self.Ch3_CheckBox.setText("ch-3")

  channel4_x = channel3_x + 80 + 20
  channel4_y = channel3_y
  self.Ch4_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch4_CheckBox.setGeometry(QtCore.QRect(channel4_x, channel4_y, 80, 20))
  self.Ch4_CheckBox.setText("ch-4")

  channel5_x = setting_rx_show_label_x
  channel5_y = channel4_y + 30
  self.Ch5_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch5_CheckBox.setGeometry(QtCore.QRect(channel5_x, channel5_y, 80, 20))
  self.Ch5_CheckBox.setText("ch-5")

  channel6_x = channel5_x + 80 + 20
  channel6_y = channel5_y
  self.Ch6_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch6_CheckBox.setGeometry(QtCore.QRect(channel6_x, channel6_y, 80, 20))
  self.Ch6_CheckBox.setText("ch-6")

  channel7_x = channel6_x + 80 + 20
  channel7_y = channel6_y
  self.Ch7_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch7_CheckBox.setGeometry(QtCore.QRect(channel7_x, channel7_y, 80, 20))
  self.Ch7_CheckBox.setText("ch-7")

  channel8_x = channel7_x + 80 + 20
  channel8_y = channel7_y
  self.Ch8_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch8_CheckBox.setGeometry(QtCore.QRect(channel8_x, channel8_y, 80, 20))
  self.Ch8_CheckBox.setText("ch-8")

  channel9_x = setting_rx_show_label_x
  channel9_y = channel8_y + 30
  self.Ch9_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch9_CheckBox.setGeometry(QtCore.QRect(channel9_x, channel9_y, 80, 20))
  self.Ch9_CheckBox.setText("ch-9")

  channel10_x = channel9_x + 80 + 20
  channel10_y = channel9_y
  self.Ch10_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch10_CheckBox.setGeometry(QtCore.QRect(channel10_x, channel10_y, 80, 20))
  self.Ch10_CheckBox.setText("ch-10")

  channel11_x = channel10_x + 80 + 20
  channel11_y = channel10_y
  self.Ch11_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch11_CheckBox.setGeometry(QtCore.QRect(channel11_x, channel11_y, 80, 20))
  self.Ch11_CheckBox.setText("ch-11")

  channel12_x = channel11_x + 80 + 20
  channel12_y = channel11_y
  self.Ch12_CheckBox = QCheckBox(self.setting_rx_frame)
  self.Ch12_CheckBox.setGeometry(QtCore.QRect(channel12_x, channel12_y, 80, 20))
  self.Ch12_CheckBox.setText("ch-12")

  # self.set_sample_channel_ok_button = QPushButton(self.setting_rx_frame)
  # self.set_sample_channel_ok_button.setGeometry(QtCore.QRect(60, channel12_y+50, 100, 30))
  # self.set_sample_channel_ok_button.setText('设置并关闭')

  self.set_sample_channel_cancel_button = QPushButton(self.setting_rx_frame)
  self.set_sample_channel_cancel_button.setGeometry(QtCore.QRect(180, channel12_y+50, 80, 30))
  self.set_sample_channel_cancel_button.setText('关闭')

 def SetSampleChannelDialogShow(self):
  self.setting_rx_frame.show()

 def SetSampleChannelDialogClose(self):
  self.setting_rx_frame.close()