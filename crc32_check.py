# -*- coding: utf-8 -*-
import logging


logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] - %(message)s')
class crc32_calculate(object):
    def __init__(self):
        # 定义一个256个元素的全0数组
        self.custom_crc32_table = [0 for x in range(0, 256)]
        # 定义一个256个元素的全0数组
        self.reversal_crc32_table = [0 for x in range(0, 256)]

    # 一个8位数据加到16位累加器中去，只有累加器的高8位或低8位与数据相作用，
    # 其结果仅有256种可能的组合值。
    def generate_crc32_table(self):
        for i in range(256):
            c = i << 24
            for j in range(8):
                if (c & 0x80000000):
                    c = (c << 1) ^ 0x04C11DB7
                else:
                    c = c << 1
            self.custom_crc32_table[i] = c & 0xffffffff

    def get_crc32_val(self, bytes_arr):
        length = len(bytes_arr)
        if bytes_arr != None:
            crc = 0xffffffff
            for i in range(0, length):
                crc = (crc << 8) ^ self.custom_crc32_table[(self.getReverse(bytes_arr[i], 8) ^ (crc >> 24)) & 0xff]
        else:
            crc = 0xffffffff
        # - 返回计算的CRC值
        crc = self.getReverse(crc ^ 0xffffffff, 32)
        return crc

    # 反转
    def getReverse(self, tempData, byte_length):
        reverseData = 0
        for i in range(0, byte_length):
            reverseData += ((tempData >> i) & 1) << (byte_length - 1 - i)
        return reverseData

    def reversal_init_crc32_table(self):
        for i in range(256):
            c = i
            for j in range(8):
                if (c & 0x00000001):
                    c = (c >> 1) ^ 0xEDB88320
                else:
                    c = c >> 1
            self.reversal_crc32_table[i] = c & 0xffffffff

    def reversal_getCrc32(self,bytes_arr):
        length = len(bytes_arr)
        if bytes_arr != None:
            crc = 0xffffffff
            for i in range(0, length):
                crc = (crc >> 8) ^ self.reversal_crc32_table[(bytes_arr[i] ^ crc) & 0xff]
        else:
            crc = 0xffffffff
        crc = crc ^ 0xffffffff
        return crc

    def get_crc32(self, data_list):
        self.generate_crc32_table()
        crc_stm = self.get_crc32_val(bytearray(data_list)) & 0xffffffff
        crc_str = "{:0>8s}".format(str('%x' % crc_stm))
        return crc_str


    def dec_to_hex(self, data):
        # 十进制转16进制
        ret = format(int(data), "x")
        return ret


    def complement_data(self, data, num):
        # 原字符串右侧对齐,左侧补零
        ret = str(data).zfill(int(num))
        return ret


    def hex_str_to_hex_int(self, hex_str):
        tmp = eval(hex_str)
        return tmp


if __name__ == '__main__':
    crc_ = crc32_calculate()


    # 十进制
    buf = [11]
    data = 65500
    data_tmp = crc_.dec_to_hex(data)
    data_hex_str = crc_.complement_data(data_tmp, 4)
    buf.append(crc_.hex_str_to_hex_int("0x" + data_hex_str[0:2]))
    buf.append(crc_.hex_str_to_hex_int("0x" + data_hex_str[2:4]))


    logging.info(buf)
    crc_ret = crc_.get_crc32(buf)
    logging.info("crc_ret:%s" % crc_ret)