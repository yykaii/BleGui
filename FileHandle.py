import csv
import logging

log_format = "[%(asctime)s][%(filename)s-%(lineno)s][%(levelname)s]-%(message)s"
log_level = logging.DEBUG
logging.basicConfig(level=logging.INFO,format=log_format)

class FileHandleClass(object):
    def __init__(self):
        pass

    def create_file(self, file_name):
        """
        descripion:创建文件
        para:1.file_name,创建的文件所保存的路径
        return:返回创建好的文件
        """
        file = open(file_name, 'w', encoding='utf-8')
        return file

    def close_file(self, file_name):
        file_name.close()

    def write_data_to_txt_file(self, file_name, file_data):
        with open(file_name, "a", encoding="utf-8") as f:
            f.write(file_data + "\n")

    def write_data_to_csv_file(self, file_name, file_data):
        with open(file_name, "a+", newline="") as f:
            csv_write = csv.writer(f)
            csv_write.writerow(file_data)