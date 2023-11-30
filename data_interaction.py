import socket
import threading
import json
import time
import struct
import argparse
import os
import copy
import signal

import tacview_parse


def exit_handler(signum, frame):
    exit(0)

signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGTERM, exit_handler)

class DataTCPClient:
    def __init__(self, addr, port):
        self.addr = (addr, port)
        self.sock = socket.socket()
        self.ev = threading.Event()

    def start(self):
        print("start client")
        self.ev.clear()
        self.sock.connect(self.addr)
        thread = threading.Thread(target=self.recv_data, name="recv_data", daemon=True)
        thread.start()

    def heart_beat(self):
        while not self.ev.is_set():
            self.send_data("MsgHeart", b'')
            time.sleep(1)

    def heart_beat_start(self):
        thread = threading.Thread(target=self.heart_beat, name="heart_beat", daemon=True)
        thread.start()

    def receive(self, length):
        receive_buf = b''
        receive_length = 0
        while receive_length < length:
            once_buf = self.sock.recv(length - receive_length)
            if not once_buf:
                print('receive once buf is null')
                return None
            receive_buf += once_buf
            receive_length = len(receive_buf)
        return receive_buf

    def recv_data(self):
        while not self.ev.is_set():
            try:
                # 1,接收2个字节，计算消息字节总长度
                msg_len_byteNum = 2;# 消息字节总长度占用的字节数
                msg_len_buf = self.sock.recv(msg_len_byteNum)
                if not msg_len_buf:
                    continue
                msg_len = msg_len_buf[0]  + msg_len_buf[1] * 256

                # 2,再接收2个字节，计算消息类型的字节长度
                msg_type_byteNum = 2 # 消息类型的字节长度占用的字节数
                msg_type_buf = self.sock.recv(msg_type_byteNum)
                if not msg_type_buf:
                    continue
                msg_type_len = msg_type_buf[0]  + msg_type_buf[1] * 256

                # 3,根据消息类型的字节长度，接收消息类型的字节数据
                msg_type_buf = self.receive(msg_type_len)
                if not msg_type_buf:
                    print('recevice msg_type buffer failed!')
                    break

                # 4,计算消息数据的字节长度
                msg_data_len = msg_len - msg_type_byteNum - msg_type_len
                
                # 5，根据消息数据的字节长度, 接收消息数据的字节数据
                msg_data_buf = self.receive(msg_data_len)
                if not msg_data_buf:
                    print('recevice msg_data buffer failed!')
                    break

                print("--------------------")
                print("receive data:")
                print("proto_name", msg_type_buf.decode())
                print("json_data", json.loads(msg_data_buf))
                print("--------------------")
                
            except ConnectionError as e:
                print("ERROR:{}".format(e))
                self.sock.close()
                break

    def send_data(self, proto_name, data):
        print("send_data " + proto_name)
        try:
            proto_name_len = len(proto_name.encode())
            data_len = len(data) + proto_name_len + 2 # 此处应该+2，不是+4，对接文档中的消息格式图有误，在对接文档的更新版本中会更正错误。
            data_length_num = data_len % 256
            data_length_mul = data_len // 256
            msg_type_length_num = proto_name_len % 256
            msg_type_length_mul = proto_name_len // 256
            byte_number_header = bytes([data_length_num,data_length_mul,msg_type_length_num,msg_type_length_mul])

            data = byte_number_header + proto_name.encode() + data
            self.sock.send(data)
        except OSError as e:
            self.stop()
            print("ERROR:{}".format(e))
            raise e

    def stop(self):
        if self.ev.is_set(): return
        self.sock.close()
        self.ev.wait(1)
        self.ev.set()


def define_myArgs():
    argparser = argparse.ArgumentParser(description="读取文件并进行解析")
    argparser.add_argument('--filein', '-f', help='读取的源文件目录')
    args=argparser.parse_args()
    return args

def set_airinfo(tmp_air_info, dist_dict):
    tmp_air_info["id"] = dist_dict.intid
    tmp_air_info["longitude"] = dist_dict.Longitude
    tmp_air_info["latitude"] = dist_dict.Latitude   
    tmp_air_info["altitude"] = dist_dict.Altitude
    tmp_air_info["roll"] = dist_dict.Roll
    tmp_air_info["pitch"] = dist_dict.Pitch
    tmp_air_info["yaw"] = dist_dict.Yaw
    tmp_air_info["name"] = dist_dict.name
    tmp_air_info["camp"] = dist_dict.camp
    tmp_air_info["type"] = dist_dict.type
    tmp_air_info["state"] = dist_dict.state


if __name__ == '__main__':
    print("启动")
    
    args=define_myArgs()
    result_path = os.path.abspath(args.filein)
    print('filein:', result_path)

    my_client = DataTCPClient('192.168.1.130', 8888)
    my_client.start()
    MsgSocket = {"protoName": "MsgSocket", "id": 2}
    my_client.send_data("MsgSocket", json.dumps(MsgSocket).encode())

    MsgTaskInit = {"protoName": "MsgTaskInit", "redNum": 0, "blueNum": 0, "longitude": 0.0, "latitude": 0.0}

    GameInfo = {"time": 0.0, "airs": []}
    AirInfo = {"id": 0, "longitude": 0.0, "latitude":0.0, "altitude": 0.0, "roll": 0.0,
                "pitch":0.0, "yaw":0.0, "name": "", "camp": 0, "type": 0, "state": 0}
    MsgGameInfo = {"protoName": "MsgGameInfo", "gameInfo": GameInfo}


    my_client.heart_beat_start()
    filepath = result_path    # Fill in the file path
    lines = tacview_parse.safe_read(filepath)
    tacview_parser = tacview_parse.Parser(lines)
    last_deltatime = 0.0
    for deltatime in tacview_parser.next():
        time.sleep(deltatime-last_deltatime)
        last_deltatime = deltatime

        try:
            GameInfo["time"] = deltatime
            GameInfo["airs"] = []
            for strid,dist_dict in tacview_parser.agent.items():
                tmp_air_info = copy.deepcopy(AirInfo)
                set_airinfo(tmp_air_info, dist_dict)
                GameInfo["airs"].append(tmp_air_info)
            # print("MsgGameInfo", MsgGameInfo)
            bytearray_str = json.dumps(MsgGameInfo).encode()
            my_client.send_data("MsgGameInfo", bytearray_str)
        except OSError as e:
            print("ERROR:{}".format(e))
            break
    my_client.stop()
    
    
