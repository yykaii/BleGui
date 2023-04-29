from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication,QFileDialog,QMessageBox

from PyQt5.QtCore import Qt,QObject, pyqtSignal,QThread,QTimer
import pyqtgraph as pg

from bleak.backends.device import BLEDevice
from bleak import BleakClient

import qasync
import asyncio
from dataclasses import dataclass
from functools import cached_property

import datetime
import time
import base64
import logging
import sys
import binascii
import numpy as np

import MainWindow
from FileHandle import FileHandleClass
from crc32_check import crc32_calculate
from set_sample_channel_dialog import SetSampleChannelDialog
from set_sample_params_dialog import  SetSampleParamsDialog

log_format = "[%(asctime)s][%(filename)s-%(lineno)s][%(levelname)s]-%(message)s"
log_level = logging.DEBUG
logging.basicConfig(level=logging.INFO, format=log_format)

# # apollo3设备
UART_SERVICE_UUID = "00002760-08c2-11e1-9073-0e8ac72e1011"
UART_TX_CHAR_UUID = "00002760-08c2-11e1-9073-0e8ac72e0012"
UART_RX_CHAR_UUID = "00002760-08c2-11e1-9073-0e8ac72e0011"

# # # 单车设备
# UART_SERVICE_UUID = "0000fee7-0000-1000-8000-00805f9b34fb"
# UART_TX_CHAR_UUID = "000036f6-0000-1000-8000-00805f9b34fb"
# UART_RX_CHAR_UUID = "000036f5-0000-1000-8000-00805f9b34fb"

@dataclass
class QBleakClient(QObject):
    device: BLEDevice

    # 设置信号量数据格式
    # 界面变化的信号量
    messageChanged = pyqtSignal(str)
    # 数据变化的信号量
    QtShowInfoChanged = pyqtSignal(str)

    def __post_init__(self):
        super().__init__()

    @cached_property
    def client(self) -> BleakClient:
        return BleakClient(self.device, disconnected_callback=self._handle_disconnect)

    async def start(self):
        await self.client.connect()
        await self.client.start_notify(UART_TX_CHAR_UUID, self._handle_read)

    async def ble_stop(self):
        await self.client.disconnect()

    async def write(self, data):
        # 发送蓝牙指令
        await self.client.write_gatt_char(UART_RX_CHAR_UUID, data)

    def _handle_disconnect(self, ble_client):
        logging.info("ble disconnected")
        self.QtShowInfoChanged.emit('disconnect')

        # for task in asyncio.all_tasks():
        #     task.cancel()

    def byte_to_str(self, data_byte):
        tmp_byte = binascii.b2a_hex(data_byte)
        data_str = tmp_byte.decode('utf-8')
        return data_str

    def str_to_byte(self, data_str):
        tmp_byte = bytes(data_str, 'utf-8')
        data_byte = base64.b16decode(tmp_byte.upper())
        return data_byte

    def _handle_read(self, _: int, data: bytearray) -> None:
        data_str = self.byte_to_str(data)
        logging.debug("接收到蓝牙数据:%s" % data_str)
        self.messageChanged.emit(data_str)

class MainWindowWork(QtWidgets.QMainWindow, FileHandleClass, crc32_calculate,
                     SetSampleChannelDialog,SetSampleParamsDialog):
    close_signal = QtCore.pyqtSignal()

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        crc32_calculate.__init__(self)
        self.ui = MainWindow.Ui_mainWindow()
        self.ui.setupUi(self)

        self._client = None
        self.scan_timeout = 5
        self.ble_mac_addr = None
        self.bind_button_and_event()
        self.window_combox_init()
        self.dialog_init()


        self.ui.SetBleMacplainTextEdit.setPlainText("78:33:A4:EF:51:80")
        self.graph_init()
        self.set_tmp_graph_config()
        self.set_pressure_graph_config()
        self.set_humidity_graph_config()
        self.ble_sensor_data = []
        self.ble_conn_sta = 0
        self.log_file_handle = None  # 保存日志文件句柄
        self.ble_send_cnt = 0
        self.rx_sensor_data_cnt = 0
        self.graph_show_sensor_data_interval = 5 # 每采集5个点才输出到图像上.
        self.save_log_button_clicked_flag = False  # 保存日志按钮是否按下
        self.save_log_file_name = None  # 保存日志文件名称
        self.connect_button_push_flag = 0  #是否点击断开连接按钮.
        self.frame_flush_thread_handle = None
        self.reconnect_ble_timer_cnt = 0 #记录蓝牙重连次数
        self.frame_flush_timer_init() #刷新界面的定时器
        self.frame_flush_timer_start()
        self.mmHg_Pa = 133.322 #1毫米汞柱（mmHg）为133.322帕（Pa）
        self.pressure_ratio = 1 # 压力系数,压力输出值=实际传感器输出值×系数
        self.current_pressure = {} # 当前压力值
        self.pressure_offset = {} # 压强offset
        self.data_pack_header = [0, 0, 0, 16]
        # index与实际值间的关系.
        self.sample_val_list = [0,1,2,4,8,16]
        # 记录当前采集传感器,默认值表示全打开.
        self.sample_channel = 8190

        # 下行指令CMD
        self.get_device_info_cmd_id = 1
        self.get_device_ver_cmd_id= 2
        self.set_collect_config_cmd_id = 3
        self.get_collect_config_cmd_id = 4
        self.collect_control_cmd_id = 5
        self.transmit_control_cmd_id = 6
        # 上行指令CMD
        self.get_device_info_cmd_rsp = 129
        self.get_device_ver_cmd_rsp = 130
        self.set_collect_config_cmd_rsp = 131
        self.get_collect_config_cmd_rsp = 132
        self.collect_control_cmd_rsp = 133
        self.transmint_control_cmd_rsp = 134
        self.transmint_sensor_data_rsp = 255

    def bind_button_and_event(self):
        # 绑定按钮
        # 建立连接按钮
        self.ui.ConnectBleDevicepushButton.clicked.connect(self.connect_button_callback)
        # 断开连接按钮
        self.ui.DisconnectBleDevicepushButton.clicked.connect(self.disconnect_button_callback)
        # 查询设备信息按钮
        self.ui.GetDeviceInfopushButton.clicked.connect(self.get_device_info_cmd)
        # 查询版本信息按钮
        self.ui.GetVerInfopushButton.clicked.connect(self.get_device_ver_cmd)
        # 设置采样参数
        self.ui.SetCollectConfigpushButton.clicked.connect(self.set_collect_config_cmd)
        # 查询采样参数
        self.ui.GetCollectConfigpushButton.clicked.connect(self.get_collect_config_cmd)
        # 启动采集按钮
        self.ui.StartCollectpushButton.clicked.connect(self.start_collect_control_cmd)
        # 停止采集按钮
        self.ui.StopCollectpushButton.clicked.connect(self.stop_collect_control_cmd)
        # 保存数据按钮
        self.ui.SaveBleDatapushButton.clicked.connect(self.save_log_button_callback)
        # 启动上传按钮
        self.ui.StartTransmitpushButton.clicked.connect(self.start_transmit_control_cmd)
        # 停止上传按钮
        self.ui.StopTransmitpushButton.clicked.connect(self.stop_transmit_control_cmd)
        # 清空按钮
        self.ui.ClearBleDatapushButton.clicked.connect(self.clear_log_button_callback)
        # 设置压力系数
        self.ui.SetPressureRatiopushButton.clicked.connect(self.set_pressure_ratio_button_callback)
        # 设置压力清零
        self.ui.ClearPressurepushButton.clicked.connect(self.clear_pressure_button_callback)
        # 压力清零恢复
        self.ui.PressureDefaultpushButton.clicked.connect(self.clear_pressure_default_button_callback)
        # 设置图像显示时长
        self.ui.action2.triggered.connect(self.set_graph_show_time_2_min_triggered_callback)
        self.ui.action5.triggered.connect(self.set_graph_show_time_5_min_triggered_callback)
        self.ui.action10.triggered.connect(self.set_graph_show_time_10_min_triggered_callback)
        self.ui.action30.triggered.connect(self.set_graph_show_time_30_min_triggered_callback)

        # 设置采样通道对话框
        self.ui.set_sample_channel.triggered.connect(self.set_sample_channel_action_triggered_callback)
        self.ui.set_sample_params.triggered.connect(self.set_sample_params_action_triggered_callback)
    def graph_init(self):
        self.axis_x_min = 0
        self.axis_x_max = 200
        self.axis_y_min = 0
        self.axis_y_max = 300
        self.time_interval = 20 #表示数据为50ms一次,单位ms,默认值.
        self.graph_show_time = 5 # 表示画面显示持续时间.单位分钟
        self.showtime = 0
        self.rx_data_cnt = 0
        self.time = []
        self.ui.action5.setChecked(True)

    def window_combox_init(self):
        self.SensorChannelList = ["传感器1","传感器2","传感器3","传感器4","传感器5","传感器6",
                                  "传感器7","传感器8","传感器9","传感器10","传感器11","传感器12"]
        self.ui.ClearPressureValcomboBox.clear()
        for channel_val in self.SensorChannelList:
            self.ui.ClearPressureValcomboBox.addItem(str(channel_val))

    def dialog_init(self):
        self.SetSampleChannelDialogInit()
        self.SetSampleParamsDialogInit()

        self.set_sample_params()
        self.set_sample_channel()
        self.set_sample_params_cancel_button.clicked.connect(self.set_sample_params_cancel_button_callback)
        # self.set_sample_params_ok_button.clicked.connect(self.set_sample_params_ok_button_callback)
        self.set_sample_channel_cancel_button.clicked.connect(self.set_sample_channel_cancel_button_callback)
        # self.set_sample_channel_ok_button.clicked.connect(self.set_sample_channel_ok_button_callack)

    def set_tmp_graph_config(self):
        pg.setConfigOption('background', 'w') #设置显示图像区域部分颜色
        pg.setConfigOption('foreground', 'k')
        # 显示绘图区域
        self.pw = pg.PlotWidget()  # 实例化一个绘图部件
        self.pw.addLegend(size=(100, 50), offset=(0, 0))  # 设置图形的图例
        self.pw.showGrid(x=True, y=True, alpha=0.5)       # 设置图形网格的形式，我们设置显示横线和竖线，并且透明度惟0.5：
        self.pw.setLabel(axis='left', text=u'温度值/°C')
        self.pw.setLabel(axis='bottom', text=u'时间/s')
        self.pw.setXRange(min=0, max=1800, padding=0)
        self.pw.setYRange(min=10, max=30, padding=0) # 设置y轴范围
        self.curve_sensor_1_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(176,23,31)),    name='传感器1', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_2_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(34,139,34)),    name='传感器2', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_3_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(255,0,0)),    name='传感器3', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_4_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(0,0,0)),    name='传感器4', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_5_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(255,0,255)),    name='传感器5', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_6_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(255,215,0)),    name='传感器6', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_7_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(210,180,140)),    name='传感器7', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_8_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(0,255,255)),    name='传感器8', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_9_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(0,255,0)),    name='传感器9', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_10_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(64,224,208)),    name='传感器10', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_11_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(138,43,226)),    name='传感器11', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_12_tmp = self.pw.plot(pen=pg.mkPen(width=3, color=(221,160,221)),    name='传感器12', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.ui.temp_graph.addWidget(self.pw)  # 添加绘图部件到网格布局层

    def set_pressure_graph_config(self):
        pg.setConfigOption('background', 'w') #设置显示图像区域部分颜色
        pg.setConfigOption('foreground', 'k')
        # 显示绘图区域
        self.pw_pressure = pg.PlotWidget()  # 实例化一个绘图部件
        self.pw_pressure.addLegend(size=(100, 50), offset=(0, 0))  # 设置图形的图例
        self.pw_pressure.showGrid(x=True, y=True, alpha=0.5)       # 设置图形网格的形式，我们设置显示横线和竖线，并且透明度惟0.5：
        self.pw_pressure.setLabel(axis='left', text=u'压力值/mmHg')
        self.pw_pressure.setLabel(axis='bottom', text=u'时间/s')
        self.pw_pressure.setXRange(min=0, max=1800, padding=0)
        self.pw_pressure.setYRange(min=760, max=800, padding=0) # 设置y轴范围
        self.curve_sensor_1_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(176,23,31)),    name='传感器1', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_2_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(34,139,34)),    name='传感器2', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_3_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(255,0,0)),    name='传感器3', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_4_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(0,0,0)),    name='传感器4', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_5_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(255,0,255)),    name='传感器5', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_6_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(255,215,0)),    name='传感器6', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_7_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(210,180,140)),  name='传感器7', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_8_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(0,255,255)),    name='传感器8', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_9_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(0,255,0)),    name='传感器9', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_10_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(64,224,208)),    name='传感器10', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_11_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(138,43,226)),    name='传感器11', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_12_pressure = self.pw_pressure.plot(pen=pg.mkPen(width=3, color=(221,160,221)),    name='传感器12', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.ui.pressure_graph.addWidget(self.pw_pressure)  # 添加绘图部件到网格布局层

    def set_humidity_graph_config(self):
        pg.setConfigOption('background', 'w') #设置显示图像区域部分颜色
        pg.setConfigOption('foreground', 'k')
        # 显示绘图区域
        self.pw_humidity = pg.PlotWidget()  # 实例化一个绘图部件
        self.pw_humidity.addLegend(size=(100, 50), offset=(0, 0))  # 设置图形的图例
        self.pw_humidity.showGrid(x=True, y=True, alpha=0.5)       # 设置图形网格的形式，我们设置显示横线和竖线，并且透明度惟0.5：
        self.pw_humidity.setLabel(axis='left', text=u'湿度值/%RH')
        self.pw_humidity.setLabel(axis='bottom', text=u'时间/s')
        self.pw_humidity.setXRange(min=0, max=1800, padding=0)
        self.pw_humidity.setYRange(min=10, max=30, padding=0) # 设置y轴范围
        self.curve_sensor_1_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(176,23,31)),    name='传感器1', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_2_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(34,139,34)),    name='传感器2', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_3_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(255,0,0)),    name='传感器3', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_4_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(0,0,0)),    name='传感器4', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_5_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(255,0,255)),    name='传感器5', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_6_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(255,215,0)),    name='传感器6', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_7_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(210,180,140)),    name='传感器7', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_8_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(0,255,255)),    name='传感器8', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_9_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(0,255,0)),    name='传感器9', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_10_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(64,224,208)),    name='传感器10', symbol=None, symbolSize=5, symbolPen=(0, 0, 200),   symbolBrush=(0, 0, 200))
        self.curve_sensor_11_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(138,43,226)),    name='传感器11', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.curve_sensor_12_humidity = self.pw_humidity.plot(pen=pg.mkPen(width=3, color=(221,160,221)),    name='传感器12', symbol=None, symbolSize=4, symbolPen=(54,55,55), symbolBrush=(54,55,55))
        self.ui.humidity_graph.addWidget(self.pw_humidity)  # 添加绘图部件到网格布局层

    @staticmethod
    def dec_to_hex(data):
        # 十进制转16进制
        ret = format(int(data), "x")
        return ret

    @staticmethod
    def complement_data(data, num):
        # 原字符串右侧对齐,左侧补零
        ret = str(data).zfill(int(num))
        return ret

    @staticmethod
    def str_trans(str):
        tmp = ""
        for i in range(len(str), 0, -2):
            tmp += str[i - 2:i]
        ret = int(tmp, 16)
        return ret

    def save_log_to_file(self, text):
        # 判断是否需要保存日志到文件
        if self.save_log_file_name != None:
            tmp_data = self.add_timestamp(text)
            self.write_data_to_txt_file(self.save_log_file_name, tmp_data)

    @staticmethod
    def get_now_time():
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        return now

    @staticmethod
    def get_time_stamp():
        ct = time.time()
        local_time = time.localtime(ct)
        data_head = time.strftime("%m%d-%H:%M:%S", local_time)
        data_secs = (ct - int(ct)) * 1000
        time_stamp = "%s.%03d" % (data_head, data_secs)
        return time_stamp

    @staticmethod
    def str_to_byte(data_str):
        tmp_byte = bytes(data_str, 'utf-8')
        data_byte = base64.b16decode(tmp_byte.upper())
        return data_byte

    @staticmethod
    def byte_to_str(data_byte):
        tmp_byte = binascii.b2a_hex(data_byte)
        data_str = tmp_byte.decode('utf-8')
        return data_str

    def Dex2Hex(self, num:str):
        result = str(hex(eval(num)))
        ret_str = result[2:len(result)]
        result_hex_str = self.complement_data(ret_str, 2)
        return result_hex_str

    def add_timestamp(self, text):
        time_stamp = self.get_time_stamp()
        text_add_timestamp = '[' + time_stamp + ']' + ' ' + text
        return text_add_timestamp

    def add_data_to_frame(self, data):
        tmp_data = self.add_timestamp(data)
        self.ui.ShowBleDataplainTextEdit.appendPlainText(tmp_data)

    def update_ble_data_interval(self, hum_osr, pres_osr, temp_osr):
        '''
        通过设置的配置计算出蓝牙数据间隔,
        :param hum_osr: 湿度过采样index
        :param pres_osr: 压力过采样index
        :param temp_osr: 温度过采样index
        :return:
        '''
        hum_val = self.sample_val_list[hum_osr]
        pres_val = self.sample_val_list[pres_osr]
        temp_val = self.sample_val_list[temp_osr]

        self.time_interval = int(((1250+(2300*temp_val)+((2300*pres_val)+575)+((2300*hum_val)+575)/1000))/1000)
        self.time_interval += 80

    def is_number(self, s):
        '''
        判断参数是否为数字
        :param s:
        :return:
        '''
        try:
            float(s)
            return True
        except ValueError:
            pass
        try:
            import unicodedata
            unicodedata.numeric(s)
            return True
        except (TypeError, ValueError):
            pass
        return False

    def set_pressure_ratio_button_callback(self):
        ratio_val = self.ui.PressureRatioplainTextEdit.toPlainText()
        if ratio_val and self.is_number(ratio_val):
            self.pressure_ratio = float(ratio_val)
            logging.info(self.pressure_ratio)
            self.add_data_to_frame("设置压力系数为:%s" % self.pressure_ratio)
        else:
            QMessageBox.warning(self, "设置比例系数", "请输入比例系数", QMessageBox.Yes)

    def clear_pressure_button_callback(self):
        '''
        点击压力清零按钮
        :return:
        '''
        clear_pressure_index = self.ui.ClearPressureValcomboBox.currentIndex()
        clear_channel = clear_pressure_index + 1
        if (clear_channel-1)*3+1 in self.current_pressure:
            self.pressure_offset[clear_channel] = self.current_pressure[(clear_channel-1)*3+1]
            self.add_data_to_frame("设置传感器%s清零" % clear_channel)
        else:
            logging.info("dict null")

    def set_graph_show_time_2_min_triggered_callback(self):
        self.graph_show_time = 2
        if self.ui.action2.isChecked() == 1:
            self.ui.action5.setChecked(0)
            self.ui.action10.setChecked(0)
            self.ui.action30.setChecked(0)
        else:
            self.ui.action2.setChecked(1)

    def set_graph_show_time_5_min_triggered_callback(self):
        self.graph_show_time = 5
        if self.ui.action5.isChecked() == 1:
            self.ui.action2.setChecked(0)
            self.ui.action10.setChecked(0)
            self.ui.action30.setChecked(0)
        else:
            self.ui.action5.setChecked(1)

    def set_graph_show_time_10_min_triggered_callback(self):
        self.graph_show_time = 10
        if self.ui.action10.isChecked() == 1:
            self.ui.action5.setChecked(0)
            self.ui.action2.setChecked(0)
            self.ui.action30.setChecked(0)
        else:
            self.ui.action10.setChecked(1)

    def set_graph_show_time_30_min_triggered_callback(self):
        self.graph_show_time = 30
        if self.ui.action30.isChecked() == 1:
            self.ui.action5.setChecked(0)
            self.ui.action10.setChecked(0)
            self.ui.action2.setChecked(0)
        else:
            self.ui.action30.setChecked(1)

    def clear_pressure_default_button_callback(self):
        '''
        点击压力清零恢复按钮
        :return:
        '''
        clear_pressure_index = self.ui.ClearPressureValcomboBox.currentIndex()
        clear_channel = clear_pressure_index + 1
        if (clear_channel-1)*3+1 in self.current_pressure:
            self.pressure_offset[clear_channel] = 0
            self.add_data_to_frame("设置传感器%s清零恢复" % clear_channel)
        else:
            logging.info("dict null")

    def closeEvent(self, event):
        # 重写关闭窗口事件
        self.SetSampleParamsDialogClose()
        self.SetSampleChannelDialogClose()

    def set_sample_channel(self):
        '''
        设置采集通道初始化
        :return:
        '''
        self.Ch1_CheckBox.setChecked(True)
        self.Ch2_CheckBox.setChecked(True)
        self.Ch3_CheckBox.setChecked(True)
        self.Ch4_CheckBox.setChecked(True)
        self.Ch5_CheckBox.setChecked(True)
        self.Ch6_CheckBox.setChecked(True)
        self.Ch7_CheckBox.setChecked(True)
        self.Ch8_CheckBox.setChecked(True)
        self.Ch9_CheckBox.setChecked(True)
        self.Ch10_CheckBox.setChecked(True)
        self.Ch11_CheckBox.setChecked(True)
        self.Ch12_CheckBox.setChecked(True)

    def set_sample_params(self):
        '''
        设置采集参数对话框初始化
        :return:
        '''
        self.humidity_sample_combox.clear()
        for val in ['OFF','x1','x2','x4','x8','x16']:
            self.humidity_sample_combox.addItem(val)
            self.humidity_sample_combox.setCurrentIndex(1)

        self.pressure_sample_combox.clear()
        for val in ['OFF','x1','x2','x4','x8','x16']:
            self.pressure_sample_combox.addItem(val)
            self.pressure_sample_combox.setCurrentIndex(5)

        self.temp_sample_combox.clear()
        for val in ['OFF','x1','x2','x4','x8','x16']:
            self.temp_sample_combox.addItem(val)
            self.temp_sample_combox.setCurrentIndex(2)

        self.filter_sample_combox.clear()
        for val in ['Filter-OFF','Filter-2','Filter-4','Filter-8','Filter-16']:
            self.filter_sample_combox.addItem(val)
            self.filter_sample_combox.setCurrentIndex(4)

        self.StandBy_sample_combox.clear()
        for val in ['0','0.5ms','62.5ms','125ms','250ms','500ms', '1000ms', '10ms', '20ms']:
            self.StandBy_sample_combox.addItem(val)
            self.StandBy_sample_combox.setCurrentIndex(0)

    def set_sample_channel_action_triggered_callback(self):
        '''
        点击设置采样通道菜单栏事件,包括...
        :return:
        '''
        self.SetSampleChannelDialogClose()
        self.SetSampleChannelDialogShow()

    def set_sample_params_action_triggered_callback(self):
        '''
        点击设置采样参数菜单栏事件,包括...
        :return:
        '''
        self.SetSampleParamsDialogClose()
        self.SetSampleParamsDialogShow()

    def set_sample_params_cancel_button_callback(self):
        self.SetSampleParamsDialogClose()

    def set_sample_params_ok_button_callback(self):
        self.SetSampleParamsDialogClose()

    def set_sample_channel_cancel_button_callback(self):
        self.SetSampleChannelDialogClose()

    def set_sample_channel_ok_button_callack(self):
        self.SetSampleChannelDialogClose()

    def clear_log_button_callback(self):
        self.ui.ShowBleDataplainTextEdit.clear()

    def save_log_button_callback(self):
        if self.save_log_button_clicked_flag == False:
            now_time = self.get_now_time()
            fileName, fileType = QFileDialog.getSaveFileName(self, '保存日志到文件', now_time+'.csv', '.csv')
            logging.info("fileName:%s,fileType:%s" % (fileName, fileType))
            if len(fileName) != 0:
                self.save_log_button_clicked_flag = True
                self.log_file_handle = self.create_file(fileName)
                self.save_log_file_name = fileName
                self.ui.SaveBleDatapushButton.setText("保存数据中")
                self.write_title_to_file()
            else:
                self.save_log_file_name = None
        else:
            self.ui.SaveBleDatapushButton.setText("保存数据")
            if self.log_file_handle != None:
                self.close_file(self.log_file_handle)
                self.save_log_file_name = None
                self.save_log_button_clicked_flag = False

    def write_sensor_data_to_file(self, data):
        # 将传感器数据写入文件
        if self.save_log_file_name != None:
            # 如果设置了保存到文件,那么将数据保存至文件.
            tmp_data = []
            tmp_data.append(self.get_time_stamp())
            for i in range(len(data)):
                tmp_data.append(str(data[i]))
            if [] != tmp_data:
                self.write_data_to_csv_file(self.save_log_file_name, tmp_data)

    def write_title_to_file(self):
        # 写入文件头
        if self.save_log_file_name != None:
            # 如果设置了保存到文件,那么将数据保存至文件.
            write_data = ['时间',
                          'ch1-温度','ch1-压力','ch1-湿度','ch2-温度','ch2-压力','ch2-湿度',
                          'ch3-温度','ch3-压力','ch3-湿度','ch4-温度','ch4-压力','ch4-湿度',
                          'ch5-温度','ch5-压力','ch5-湿度','ch6-温度','ch6-压力','ch6-湿度',
                          'ch7-温度','ch7-压力','ch7-湿度','ch8-温度','ch8-压力','ch8-湿度',
                          'ch9-温度','ch9-压力','ch9-湿度','ch10-温度','ch10-压力','ch10-湿度',
                          'ch11-温度','ch11-压力','ch11-湿度','ch12-温度','ch12-压力','ch12-湿度']
            self.write_data_to_csv_file(self.save_log_file_name, write_data)

    @cached_property
    def devices(self):
        return list()

    @property
    def current_client(self):
        return self._client

    async def build_client(self, device):
        if self._client is not None:
            await self._client.ble_stop()
        self._client = QBleakClient(device)
        self._client.messageChanged.connect(self.handle_message_changed)
        self._client.QtShowInfoChanged.connect(self.handle_Qt_show_info_changed)
        await self._client.start()

    @qasync.asyncSlot()
    async def connect_button_callback(self):
        input_mac_addr_str = self.ui.SetBleMacplainTextEdit.toPlainText()

        if(len(input_mac_addr_str) != 17):
            self.add_data_to_frame("输入mac地址长度有误")
            return
        # 将小写转换为大写
        input_mac_addr = input_mac_addr_str.upper()

        self.statusBar().showMessage("开始连接至mac地址:%s" % input_mac_addr)
        logging.info("开始连接至mac地址:%s" % input_mac_addr)

        await self.build_client(input_mac_addr)
        logging.info("已连接至蓝牙设备,mac地址:%s" % input_mac_addr)
        self.statusBar().showMessage("已连接至蓝牙设备,mac地址:%s" % input_mac_addr)
        self.ui.ConnectBleDevicepushButton.setEnabled(False)
        self.ui.DisconnectBleDevicepushButton.setEnabled(True)
        self.ui.GetVerInfopushButton.setEnabled(True)
        self.ui.GetDeviceInfopushButton.setEnabled(True)
        self.ui.SetCollectConfigpushButton.setEnabled(True)
        self.ui.GetCollectConfigpushButton.setEnabled(True)
        self.ui.StartTransmitpushButton.setEnabled(True)
        self.ui.StopTransmitpushButton.setEnabled(True)
        self.ui.StartCollectpushButton.setEnabled(True)
        self.ui.StopCollectpushButton.setEnabled(True)
        self.ui.SaveBleDatapushButton.setEnabled(True)
        self.ui.ClearPressurepushButton.setEnabled(True)
        self.ui.PressureDefaultpushButton.setEnabled(True)
        self.ui.SetPressureRatiopushButton.setEnabled(True)

        self.ble_mac_addr = input_mac_addr
        self.ble_conn_sta = 1
        self.connect_button_push_flag = 0
        self.reconnect_ble_timer_cnt = 0
        # self.frame_flush_timer_stop()
        # 连接成功后，清空之前显示的数据
        self.time.clear()
        self.showtime = 0
        self.ble_sensor_data.clear()
        self.update_ble_data_interval(self.humidity_sample_combox.currentIndex(), self.pressure_sample_combox.currentIndex(),self.temp_sample_combox.currentIndex())

    def check_payload_crc(self, data_list):
        crc_list = []
        crc_ret = self.get_crc32(data_list)
        crc_str = self.complement_data(crc_ret, 8)
        for i in range(8, 0, -2):
            crc_list.append(crc_str[i-2:i])
        return crc_list

    @qasync.asyncSlot()
    async def disconnect_button_callback(self):
        logging.info("点击断开蓝牙连接按钮")
        if self.current_client is None:
            return
        self.connect_button_push_flag = 1
        await self._client.ble_stop()

    def list_to_str(self, data_list):
        data_str = ""
        for data in data_list:
            data_str += str(data).zfill(2)

        if(len(data_str)%2 != 0):
            ret_str = self.complement_data(data_str, len(data_str)+1)
        else:
            ret_str = data_str

        return ret_str


    @qasync.asyncSlot()
    async def get_device_info_cmd(self):
        '''
         点击获取设备信息按钮事件
         :return:
         '''
        crc_check_list = []  # 存放待进行crc校验的数据.
        crc_ret_list = []  # 存放crc校验结果

        crc_check_list.append(self.get_device_info_cmd_id)

        # 计算crc值
        crc_ret = self.check_payload_crc(crc_check_list)
        for crc in crc_ret:
            crc_ret_list.append(crc)

        all_data_list = []
        for data in self.data_pack_header:
            all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.get_device_info_cmd_id), 2))

        for data in crc_ret_list:
            all_data_list.append(data)
        all_data_list[0] = self.complement_data((len(all_data_list) - len(self.data_pack_header)), 2)

        ble_str = self.list_to_str(all_data_list)
        await self.send_ble_data(ble_str)


    @qasync.asyncSlot()
    async def get_device_ver_cmd(self):
        '''
        点击获取版本号事件
        :return:
        '''
        crc_check_list = [] # 存放待进行crc校验的数据.
        crc_ret_list = [] # 存放crc校验结果
        crc_check_list.append(self.get_device_ver_cmd_id)
        # 计算crc值
        crc_ret = self.check_payload_crc(crc_check_list)
        for crc in crc_ret:
            crc_ret_list.append(crc)

        all_data_list = []
        for data in self.data_pack_header:
            all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.get_device_ver_cmd_id), 2))

        for data in crc_ret_list:
            all_data_list.append(data)
        all_data_list[0] = self.complement_data((len(all_data_list)-len(self.data_pack_header)), 2)

        ble_str = self.list_to_str(all_data_list)
        await self.send_ble_data(ble_str)

    @qasync.asyncSlot()
    async def set_collect_config_cmd(self):
        '''
        配置采集参数
        :param osr: 过采样率
        :param odr: 采样率
        :return:
        '''
        crc_check_list = [] # 存放待进行crc校验的数据.
        crc_ret_list = [] # 存放crc校验结果

        crc_check_list.append(self.set_collect_config_cmd_id)
        osrs_h = self.humidity_sample_combox.currentIndex()
        osrs_p = self.pressure_sample_combox.currentIndex()
        osrs_t = self.temp_sample_combox.currentIndex()
        filter = self.filter_sample_combox.currentIndex()
        t_sb = self.StandBy_sample_combox.currentIndex()

        data_hex_str = self.complement_data(self.dec_to_hex(osrs_h), 2)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))
        data_hex_str = self.complement_data(self.dec_to_hex(osrs_p), 2)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))
        data_hex_str = self.complement_data(self.dec_to_hex(osrs_t), 2)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))
        data_hex_str = self.complement_data(self.dec_to_hex(filter), 2)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))
        data_hex_str = self.complement_data(self.dec_to_hex(t_sb), 2)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))
        # 计算crc值
        crc_ret = self.check_payload_crc(crc_check_list)
        for crc in crc_ret:
            crc_ret_list.append(crc)

        all_data_list = []
        for data in self.data_pack_header:
            all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.set_collect_config_cmd_id), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(osrs_h)), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(osrs_p)), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(osrs_t)), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(filter)), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(t_sb)), 2))

        for data in crc_ret_list:
            all_data_list.append(data)
        all_data_list[0] = self.complement_data(self.dec_to_hex((len(all_data_list)-len(self.data_pack_header))), 2)
        ble_str = self.list_to_str(all_data_list)
        await self.send_ble_data(ble_str)

    @qasync.asyncSlot()
    async def get_collect_config_cmd(self):
        '''
        查询采集参数
        :return:
        '''
        crc_check_list = [] # 存放待进行crc校验的数据.
        crc_ret_list = [] # 存放crc校验结果
        crc_check_list.append(self.get_collect_config_cmd_id)

        # 计算crc值
        crc_ret = self.check_payload_crc(crc_check_list)
        for crc in crc_ret:
            crc_ret_list.append(crc)

        all_data_list = []
        for data in self.data_pack_header:
            all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.get_collect_config_cmd_id), 2))

        for data in crc_ret_list:
            all_data_list.append(data)
        all_data_list[0] = self.complement_data((len(all_data_list)-len(self.data_pack_header)), 2)

        ble_str = self.list_to_str(all_data_list)
        await self.send_ble_data(ble_str)

    @qasync.asyncSlot()
    async def start_collect_control_cmd(self):
        '''
        启动采集
        :return:
        '''
        check_ret = (self.Ch1_CheckBox.isChecked() << 8) | (self.Ch2_CheckBox.isChecked() << 9) | \
                    (self.Ch3_CheckBox.isChecked() << 10) | (self.Ch4_CheckBox.isChecked() << 11) | \
                    (self.Ch5_CheckBox.isChecked() << 12) | (self.Ch6_CheckBox.isChecked() << 13) | \
                    (self.Ch7_CheckBox.isChecked() << 14) | (self.Ch8_CheckBox.isChecked() << 15) | \
                    (self.Ch9_CheckBox.isChecked() << 0) | (self.Ch10_CheckBox.isChecked() << 1) | \
                    (self.Ch11_CheckBox.isChecked() << 2) | (self.Ch12_CheckBox.isChecked() << 3) |\
                    (0 << 4) | (0 << 5) | \
                    (0 << 6) | (0 << 7)

        if(check_ret == 0):
            QMessageBox.warning(self, "启动采集操作", "请先勾选要采集的传感器", QMessageBox.Yes)
            return
        else:
            crc_check_list = []  # 存放待进行crc校验的数据.
            crc_ret_list = []  # 存放crc校验结果

            crc_check_list.append(self.collect_control_cmd_id)
            data_tmp = self.dec_to_hex(check_ret)
            logging.info(data_tmp)
            data_hex_tmp = self.complement_data(data_tmp, 4)
            # data_hex_str = data_hex_tmp[1:2] + '0' + data_hex_tmp[3:4] + data_hex_tmp[2:3]
            crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_tmp[0:2]))
            crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_tmp[2:4]))
            # 计算crc值
            crc_ret = self.check_payload_crc(crc_check_list)
            for crc in crc_ret:
                crc_ret_list.append(crc)

            all_data_list = []
            for data in self.data_pack_header:
                all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
            all_data_list.append(self.complement_data(self.dec_to_hex(self.collect_control_cmd_id), 2))

            all_data_list.append(self.complement_data(data_hex_tmp[0:2],2))
            all_data_list.append(self.complement_data(data_hex_tmp[2:4],2))

            for data in crc_ret_list:
                all_data_list.append(data)
            all_data_list[0] = self.complement_data((len(all_data_list) - len(self.data_pack_header)), 2)

            ble_str = self.list_to_str(all_data_list)

            await self.send_ble_data(ble_str)

    @qasync.asyncSlot()
    async def stop_collect_control_cmd(self):
        '''
        停止采集
        :return:
        '''
        crc_check_list = [] # 存放待进行crc校验的数据.
        crc_ret_list = [] # 存放crc校验结果
        crc_check_list.append(self.collect_control_cmd_id)
        control_cmd = 0
        data_hex_str = self.complement_data(self.dec_to_hex(control_cmd), 4)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))

        # 计算crc值
        crc_ret = self.check_payload_crc(crc_check_list)
        for crc in crc_ret:
            crc_ret_list.append(crc)
        all_data_list = []
        for data in self.data_pack_header:
            all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.collect_control_cmd_id), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(control_cmd)), 2))

        for data in crc_ret_list:
            all_data_list.append(data)
        all_data_list[0] = self.complement_data((len(all_data_list)-len(self.data_pack_header)), 2)

        ble_str = self.list_to_str(all_data_list)
        await self.send_ble_data(ble_str)

    @qasync.asyncSlot()
    async def stop_transmit_control_cmd(self):
        '''
        停止上传
        :return:
        '''
        crc_check_list = [] # 存放待进行crc校验的数据.
        crc_ret_list = [] # 存放crc校验结果

        crc_check_list.append(self.transmit_control_cmd_id)
        control_cmd = 0
        data_hex_str = self.complement_data(self.dec_to_hex(control_cmd), 2)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))

        # 计算crc值
        crc_ret = self.check_payload_crc(crc_check_list)
        for crc in crc_ret:
            crc_ret_list.append(crc)

        all_data_list = []
        for data in self.data_pack_header:
            all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.transmit_control_cmd_id), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(control_cmd)), 2))

        for data in crc_ret_list:
            all_data_list.append(data)
        all_data_list[0] = self.complement_data((len(all_data_list)-len(self.data_pack_header)), 2)

        ble_str = self.list_to_str(all_data_list)
        await self.send_ble_data(ble_str)

    @qasync.asyncSlot()
    async def start_transmit_control_cmd(self):
        '''
        启动上传
        :return:
        '''
        crc_check_list = [] # 存放待进行crc校验的数据.
        crc_ret_list = [] # 存放crc校验结果

        crc_check_list.append(self.transmit_control_cmd_id)
        control_cmd = 1
        data_hex_str = self.complement_data(self.dec_to_hex(control_cmd), 2)
        crc_check_list.append(self.hex_str_to_hex_int("0x" + data_hex_str[0:2]))

        # 计算crc值
        crc_ret = self.check_payload_crc(crc_check_list)
        for crc in crc_ret:
            crc_ret_list.append(crc)

        all_data_list = []
        for data in self.data_pack_header:
            all_data_list.append(self.complement_data(self.dec_to_hex(data), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.transmit_control_cmd_id), 2))
        all_data_list.append(self.complement_data(self.dec_to_hex(self.dec_to_hex(control_cmd)), 2))

        for data in crc_ret_list:
            all_data_list.append(data)
        all_data_list[0] = self.complement_data((len(all_data_list)-len(self.data_pack_header)), 2)

        ble_str = self.list_to_str(all_data_list)
        await self.send_ble_data(ble_str)

    def update_live_pressure(self,ch1,ch2,ch3,ch4,ch5,ch6,ch7,ch8,ch9,ch10,ch11,ch12):
        '''
        更新实时压力值。
        :return:
        '''
        self.ui.LivePressureLabel.setText('实时压力值(mmHg):1号:%s,2号:%s,3号:%s,4号:%s,5号:%s,6号:%s,7号:%s,8号:%s,9号:%s,10号:%s,11号:%s,12号:%s' %
                                            (ch1,ch2,ch3,ch4,ch5,ch6,ch7,ch8,ch9,ch10,ch11,ch12))

    def handle_Qt_show_info_changed(self, message):
        #处理页面需要显示的信息
        if(message == 'disconnect'):
            self.ble_conn_sta = 0
            logging.info("蓝牙断开连接")
            self.statusBar().showMessage("蓝牙断开连接")
            # 在此起一个定时器进行重连
            if self.connect_button_push_flag != 1:
                # 表示不是主动点击断开连接按钮进行的断开.
                self.frame_flush_timer_start()

    def handle_message_changed(self, message):
        # 处理接收到的蓝牙数据.可以在这里解码和显示到对话框里面或者是保存到文件
        # self.save_log_to_file(message)
        # logging.info("接收到蓝牙数据:%s" % message)

        ble_data_list = []
        for i in range(0, len(message), 2):
            tem = message[i:i + 2]
            ble_data_list.append(int(tem, 16))  # 将16进制字符串转成10进制整数
        # logging.info(ble_data_list)
        # 在这里应该计算下crc后再进行后续处理

        if ble_data_list[4] == self.get_device_info_cmd_rsp:
            #查询设备信息应答
            payload_len = ble_data_list[0] - 5
            # self.add_data_to_frame("rx_ble:%s" % message)
            self.add_data_to_frame("设备SN:%s" % message[5*2:(5+payload_len)*2])
        elif ble_data_list[4] == self.get_device_ver_cmd_rsp:
            # 查询设备版本号应答
            payload_len = ble_data_list[0] - 5
            # self.add_data_to_frame("rx_ble:%s" % message)
            self.add_data_to_frame("硬件版本:%d,软件版本:%d" % (self.str_trans(message[10:14]),self.str_trans(message[14:18])))
        elif ble_data_list[4] == self.set_collect_config_cmd_rsp:
            # 配置采集参数应答
            self.add_data_to_frame("rx_ble:%s" % message)
            if ble_data_list[5] == 1:
                self.add_data_to_frame("设置采样参数成功")
                self.update_ble_data_interval(self.humidity_sample_combox.currentIndex(),
                                          self.pressure_sample_combox.currentIndex(),
                                          self.temp_sample_combox.currentIndex())
            else:
                self.add_data_to_frame("设置采样参数失败")
        elif ble_data_list[4] == self.get_collect_config_cmd_rsp:
            # 获取采集参数应答
            payload_len = ble_data_list[0] - 5
            self.add_data_to_frame("rx_ble:%s" % message)
            self.add_data_to_frame("获取采样参数:%s" % message[5*2:(5+payload_len)*2])

        elif ble_data_list[4] == self.collect_control_cmd_rsp:
            # 采集控制结果应答
            # self.add_data_to_frame("rx_ble:%s" % message)
            if ble_data_list[5] == 1:
                self.add_data_to_frame("配置采集传感器成功")
            else:
                self.add_data_to_frame("配置采集传感器失败")

        elif ble_data_list[4] == self.transmint_control_cmd_rsp:
            # 上传控制结果应答
            self.add_data_to_frame("rx_ble:%s" % message)
            if ble_data_list[5] == 1:
                self.add_data_to_frame("设置上传成功")
            else:
                self.add_data_to_frame("设置上传失败")
        elif ble_data_list[4] == self.transmint_sensor_data_rsp:
            sensor_data = []
            # logging.info(message)
            # 共36路数据
            for i in range(0,36):
                if i in (1,4,7,10,13,16,19,22,25,28,31,34):
                    # cnt += 1
                    # 如果是压力值,转换为mmHg.
                    sensor_tmp = self.str_trans(message[10+8*i:10+8*(i+1)])*100/self.mmHg_Pa
                    # 查看是否需要设置比例系数.
                    sensor_tmp = int(sensor_tmp*self.pressure_ratio)
                    # 查看是否需要清零.
                    sensor_index = int((i-1)/3+1)
                    if sensor_index in self.pressure_offset:
                        logging.info("clear channel:%s" % sensor_index)
                        sensor_tmp = int(sensor_tmp-self.pressure_offset[sensor_index])
                    # 记录下当前值.
                    self.current_pressure[i] = sensor_tmp
                else:
                    sensor_tmp = int(self.str_trans(message[10+8*i:10+8*(i+1)]))
                sensor_data.append(sensor_tmp)
            # 更新实时压力显示
            self.update_live_pressure(sensor_data[1], sensor_data[4], sensor_data[7], sensor_data[10], sensor_data[13], sensor_data[16],
                                      sensor_data[19], sensor_data[22], sensor_data[25], sensor_data[28], sensor_data[31], sensor_data[34])
            # 将数据保存至文件
            self.write_sensor_data_to_file(sensor_data)

            self.rx_sensor_data_cnt += 1
            if self.graph_show_sensor_data_interval == self.rx_sensor_data_cnt:
                self.rx_sensor_data_cnt = 0
                self.time.append(self.showtime)
                self.showtime += (self.time_interval*self.graph_show_sensor_data_interval/1000)
                self.ble_sensor_data.append(sensor_data)
                tmp_data = np.array(self.ble_sensor_data)
                self.curve_sensor_1_tmp.setData(self.time, tmp_data[:,0])
                self.curve_sensor_1_pressure.setData(self.time, tmp_data[:,1])
                self.curve_sensor_1_humidity.setData(self.time, tmp_data[:,2])
                self.curve_sensor_2_tmp.setData(self.time, tmp_data[:,3])
                self.curve_sensor_2_pressure.setData(self.time, tmp_data[:,4])
                self.curve_sensor_2_humidity.setData(self.time, tmp_data[:,5])
                self.curve_sensor_3_tmp.setData(self.time, tmp_data[:,6])
                self.curve_sensor_3_pressure.setData(self.time, tmp_data[:,7])
                self.curve_sensor_3_humidity.setData(self.time, tmp_data[:,8])
                self.curve_sensor_4_tmp.setData(self.time, tmp_data[:,9])
                self.curve_sensor_4_pressure.setData(self.time, tmp_data[:,10])
                self.curve_sensor_4_humidity.setData(self.time, tmp_data[:,11])
                self.curve_sensor_5_tmp.setData(self.time, tmp_data[:,12])
                self.curve_sensor_5_pressure.setData(self.time, tmp_data[:,13])
                self.curve_sensor_5_humidity.setData(self.time, tmp_data[:,14])
                self.curve_sensor_6_tmp.setData(self.time, tmp_data[:,15])
                self.curve_sensor_6_pressure.setData(self.time, tmp_data[:,16])
                self.curve_sensor_6_humidity.setData(self.time, tmp_data[:,17])
                self.curve_sensor_7_tmp.setData(self.time, tmp_data[:,18])
                self.curve_sensor_7_pressure.setData(self.time, tmp_data[:,19])
                self.curve_sensor_7_humidity.setData(self.time, tmp_data[:,20])
                self.curve_sensor_8_tmp.setData(self.time, tmp_data[:,21])
                self.curve_sensor_8_pressure.setData(self.time, tmp_data[:,22])
                self.curve_sensor_8_humidity.setData(self.time, tmp_data[:,23])
                self.curve_sensor_9_tmp.setData(self.time, tmp_data[:,24])
                self.curve_sensor_9_pressure.setData(self.time, tmp_data[:,25])
                self.curve_sensor_9_humidity.setData(self.time, tmp_data[:,26])
                self.curve_sensor_10_tmp.setData(self.time, tmp_data[:,27])
                self.curve_sensor_10_pressure.setData(self.time, tmp_data[:,28])
                self.curve_sensor_10_humidity.setData(self.time, tmp_data[:,29])
                self.curve_sensor_11_tmp.setData(self.time, tmp_data[:,30])
                self.curve_sensor_11_pressure.setData(self.time, tmp_data[:,31])
                self.curve_sensor_11_humidity.setData(self.time, tmp_data[:,32])
                self.curve_sensor_12_tmp.setData(self.time, tmp_data[:,33])
                self.curve_sensor_12_pressure.setData(self.time, tmp_data[:,34])
                self.curve_sensor_12_humidity.setData(self.time, tmp_data[:,35])

            # 间隔一段时间清除图像
            self.rx_data_cnt += 1
            if(self.rx_data_cnt == int(self.graph_show_time*60*1000/(self.time_interval))):
                self.rx_data_cnt = 0
                self.ble_sensor_data.clear()
                self.time.clear()
        else:
            pass

    def clear_graph(self):
        self.pw.clear()

    @qasync.asyncSlot()
    async def send_ble_data(self, data_str):
        '''
        发送蓝牙数据
        :param data_str: 待发送的蓝牙数据
        :return:
        '''
        if self.current_client is None:
            return
        if self.ble_conn_sta == 0:
            logging.error("蓝牙已断开,请先连接蓝牙")
            self.statusBar().showMessage("蓝牙已断开,请先连接蓝牙")
            return

        if data_str == None:
            logging.error("send ble data error")
            return
        elif len(data_str) % 2 != 0:
            logging.error("send ble data len error")
            return
        data_byte = self.str_to_byte(data_str)
        await self.current_client.write(data_byte)

    @qasync.asyncSlot()
    async def frame_flush_timer_callback(self):
        QApplication.processEvents()

    def frame_flush_timer_init(self):
        self.frame_flush_thread_handle = CreateThread()
        self.frame_flush_thread_handle.timeout.connect(self.frame_flush_timer_callback)
        self.frame_flush_thread_handle.start()

    def frame_flush_timer_start(self):
        self.frame_flush_thread_handle.thread_start()

    def frame_flush_timer_stop(self):
        self.frame_flush_thread_handle.thread_stop()

class CreateThread(QThread):
    # 创建thread
    timeout = pyqtSignal()

    def __init__(self):
        super(CreateThread, self).__init__()
        self.timeout_s = 500
        self.thread_run_flag = False

    def thread_start(self):
        self.thread_run_flag = True

    def thread_stop(self):
        self.thread_run_flag = False

    def run(self):
        while True:
            if self.thread_run_flag == True:
                self.timeout.emit()
                self.msleep(self.timeout_s)

def main():
    # 适配高清屏
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindowWork()
    w.show()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()

