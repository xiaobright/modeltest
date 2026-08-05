#!/usr/bin/env python3
"""
上位机程序 - ESP32版本
从ESP32-S3通过USB CDC接口读取数据:
- CDC 0 (/dev/ttyACM0): MLX90640 红外传感器数据 (传感器1: 0x33, 传感器2: 0x34)
- CDC 1 (/dev/ttyACM1): ToF 传感器数据 (传感器1和2的透传数据)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import os
import serial
import serial.tools.list_ports
import struct
import sys

# ============ 常量定义 ============
# MLX90640 参数
MLX_SENSOR_W = 24
MLX_SENSOR_H = 32
MLX_NUM_PIXELS = MLX_SENSOR_W * MLX_SENSOR_H  # 768

# MaixSense 参数
MAIXSENSE_WIDTH = 100
MAIXSENSE_HEIGHT = 100

# 统一数据包格式常量
PACKET_SYNC1 = 0xAA
PACKET_SYNC2 = 0x55
SENSOR_TYPE_MLX = 0x01
SENSOR_TYPE_TOF = 0x02

# ============ JET 色彩映射 ============
def create_jet_colormap():
    """创建 JET 色彩映射表"""
    colors = np.zeros((256, 3), dtype=np.uint8)
    
    for i in range(256):
        # 简化的 JET 色彩映射
        if i < 32:
            colors[i] = [0, 0, 128 + i * 4]
        elif i < 96:
            colors[i] = [0, (i - 32) * 4, 255]
        elif i < 160:
            colors[i] = [(i - 96) * 4, 255, 255 - (i - 96) * 4]
        elif i < 224:
            colors[i] = [255, 255 - (i - 160) * 4, 0]
        else:
            colors[i] = [255 - (i - 224) * 4, 0, 0]
    
    return colors

JET_COLORS = create_jet_colormap()

# ============ CRC16校验函数 ============
def crc16_ccitt(data):
    """计算CRC16-CCITT校验值"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc

# ============ ToF数据解析器 ============
class ToFDataParser:
    """解析ESP32回传的ToF传感器数据 (新格式带CRC)"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.state = 'WAIT_HEADER'
        self.current_sensor_type = 0
        self.current_sensor_id = 0
        self.current_payload_len = 0
        self.current_payload = bytearray()
        
    def parse_data(self, data):
        """解析数据并返回完整的帧
        返回: (sensor_id, payload) 或 None
        """
        self.buffer.extend(data)
        
        while len(self.buffer) > 0:
            if self.state == 'WAIT_HEADER':
                # 查找包头 [0xAA, 0x55]
                if len(self.buffer) < 2:
                    return None
                
                if self.buffer[0] == PACKET_SYNC1 and self.buffer[1] == PACKET_SYNC2:
                    if len(self.buffer) >= 6:
                        # 解析包头: [0xAA, 0x55, sensor_type, sensor_id, len_low, len_high]
                        self.current_sensor_type = self.buffer[2]
                        self.current_sensor_id = self.buffer[3]
                        self.current_payload_len = self.buffer[4] | (self.buffer[5] << 8)
                        self.buffer = self.buffer[6:]
                        self.current_payload = bytearray()
                        self.state = 'READ_PAYLOAD'
                    else:
                        return None
                else:
                    # 丢弃无效字节
                    self.buffer.pop(0)
            
            elif self.state == 'READ_PAYLOAD':
                # 读取负载数据 + CRC (2字节)
                total_needed = self.current_payload_len + 2  # payload + CRC
                if len(self.buffer) >= total_needed:
                    self.current_payload.extend(self.buffer[:self.current_payload_len])
                    payload_data = bytes(self.current_payload)
                    
                    # 读取CRC
                    crc_received = self.buffer[self.current_payload_len] | \
                                   (self.buffer[self.current_payload_len + 1] << 8)
                    
                    # 验证CRC
                    crc_calculated = crc16_ccitt(payload_data)
                    
                    self.buffer = self.buffer[total_needed:]
                    
                    if crc_received == crc_calculated:
                        # CRC校验通过,仅处理ToF类型数据
                        if self.current_sensor_type == SENSOR_TYPE_TOF:
                            result = (self.current_sensor_id, payload_data)
                            self.state = 'WAIT_HEADER'
                            return result
                    else:
                        # CRC校验失败
                        print(f"警告: ToF数据CRC校验失败! 期望={crc_calculated:04X}, 收到={crc_received:04X}")
                    
                    self.state = 'WAIT_HEADER'
                else:
                    return None
        
        return None

class MaixSenseFrameParser:
    """解析MaixSense的帧数据 (ESP32已经发送完整帧)"""
    
    META_LEN = 16  # MaixSense元数据长度
    
    def __init__(self):
        self.buffer = bytearray()
        
    def parse_frame(self, data):
        """解析MaixSense帧数据
        ESP32端已经解析完整帧，payload应该直接是完整帧
        MaixSense帧格式: [00 FF] [LEN_L LEN_H] [META(16)] [IMG_DATA...] [CHECKSUM] [DD]
        返回: numpy array (100x100) 或 None
        """
        # 如果payload以 00 FF 开头且以 DD 结尾，直接解析
        if len(data) >= 6 and data[0] == 0x00 and data[1] == 0xFF:
            # 读取数据长度
            data_len = data[2] | (data[3] << 8)
            expected_frame_len = 2 + 2 + data_len + 1 + 1
            
            if len(data) == expected_frame_len and data[-1] == 0xDD:
                # 提取payload（跳过帧头4字节和尾部2字节）
                payload = data[4:-2]
                
                if len(payload) < self.META_LEN:
                    return None
                
                # 跳过前16字节元数据，提取图像数据
                img_data = payload[self.META_LEN:]
                
                # 检查是否是100x100图像
                if len(img_data) == MAIXSENSE_WIDTH * MAIXSENSE_HEIGHT:
                    depth_array = np.frombuffer(img_data, dtype=np.uint8).reshape((MAIXSENSE_HEIGHT, MAIXSENSE_WIDTH))
                    return depth_array
                else:
                    return None
        
        # 如果不是完整帧，使用原来的缓冲区累积方式
        self.buffer.extend(data)
        
        # 查找 00 FF 帧头
        while len(self.buffer) >= 6:
            header_pos = self.buffer.find(b'\x00\xFF')
            
            if header_pos == -1:
                # 没找到帧头，保留最后1个字节（可能是0x00的开头）
                if len(self.buffer) > 1:
                    self.buffer = self.buffer[-1:]
                return None
            
            # 找到了帧头
            if header_pos > 0:
                # 丢弃帧头之前的无效数据
                self.buffer = self.buffer[header_pos:]
            
            # 检查是否有足够数据读取长度字段
            if len(self.buffer) < 4:
                return None
            
            # 读取数据长度
            data_len = self.buffer[2] | (self.buffer[3] << 8)
            frame_len = 2 + 2 + data_len + 1 + 1
            
            # 检查是否有完整帧
            if len(self.buffer) >= frame_len:
                # 检查帧尾
                if self.buffer[frame_len - 1] != 0xDD:
                    # 帧尾不对，跳过这个假的帧头
                    self.buffer = self.buffer[1:]
                    continue
                
                # 提取payload
                payload = self.buffer[4:frame_len-2]
                
                if len(payload) >= self.META_LEN:
                    # 跳过元数据，提取图像
                    img_data = payload[self.META_LEN:]
                    
                    if len(img_data) == MAIXSENSE_WIDTH * MAIXSENSE_HEIGHT:
                        depth_array = np.frombuffer(img_data, dtype=np.uint8).reshape((MAIXSENSE_HEIGHT, MAIXSENSE_WIDTH))
                        # 移除已处理的帧
                        self.buffer = self.buffer[frame_len:]
                        return depth_array
                
                # 数据长度不对，跳过
                self.buffer = self.buffer[1:]
                continue
            else:
                # 找到帧头但数据不完整，等待更多数据
                return None
        
        # 缓冲区数据不足一个完整帧
        # 如果缓冲区太大但没有帧头，清理一下避免内存溢出
        if len(self.buffer) > 20000:
            header_pos = self.buffer.find(b'\x00\xFF')
            if header_pos == -1:
                # 没有帧头，只保留最后1000字节
                self.buffer = self.buffer[-1000:]
            elif header_pos > 10000:
                # 帧头位置太靠后，丢弃前面的数据
                self.buffer = self.buffer[header_pos:]
        
        return None

# ============ 主应用程序 ============
class DataCollectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 四通道数据采集工具 v3.0 (USB CDC)")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 串口设备
        self.cdc0_port = None  # MLX90640数据
        self.cdc1_port = None  # ToF数据
        
        # 数据解析器
        self.tof_parser = ToFDataParser()
        self.cam1_parser = MaixSenseFrameParser()
        self.cam2_parser = MaixSenseFrameParser()
        
        # 调试统计
        self.tof_bytes_received = 0
        self.tof_packets_received = 0
        self.mlx_packets_received = 0
        
        # 最新数据
        self.latest_frame_cam1 = None  # 深度摄像头1
        self.latest_frame_cam2 = None  # 深度摄像头2
        self.latest_temps_mlx1 = None  # MLX传感器1 (0x33 - long)
        self.latest_temps_mlx2 = None  # MLX传感器2 (0x34 - wide)
        
        # 数据更新标志
        self.new_data_flags = {
            'cam1': False,
            'cam2': False,
            'mlx1': False,
            'mlx2': False
        }
        
        # 保存相关
        self.save_path = "collected_data"
        self.scene_name = ""
        self.frame_counter = 0
        self.scene_initialized = False
        
        # 线程控制
        self.running = False
        self.read_threads = []
        
        # 创建UI
        self.create_widgets()
        self.update_preview()
    
    def log(self, message):
        """添加日志"""
        def append_log():
            if self.log_text.winfo_exists():
                timestamp = time.strftime("%H:%M:%S")
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
                self.log_text.see(tk.END)
        self.root.after(0, append_log)
        print(message)
    
    def create_widgets(self):
        """创建GUI组件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # --- 控制面板 ---
        control_panel = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_panel.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        control_panel.columnconfigure((0, 1, 2, 3), weight=1)
        
        # 自动检测可用的串口
        available_ports = self.get_available_cdc_ports()
        
        ttk.Label(control_panel, text="CDC 0 (MLX):").grid(row=0, column=0, sticky="w", padx=5)
        self.port_combo_cdc0 = ttk.Combobox(control_panel, values=available_ports, width=15)
        self.port_combo_cdc0.grid(row=0, column=1, sticky="ew", padx=5)
        if len(available_ports) > 0:
            self.port_combo_cdc0.set(available_ports[0])
        
        ttk.Label(control_panel, text="CDC 1 (ToF):").grid(row=1, column=0, sticky="w", padx=5)
        self.port_combo_cdc1 = ttk.Combobox(control_panel, values=available_ports, width=15)
        self.port_combo_cdc1.grid(row=1, column=1, sticky="ew", padx=5)
        if len(available_ports) > 1:
            self.port_combo_cdc1.set(available_ports[1])
        
        self.connect_button = ttk.Button(control_panel, text="连接并开始", 
                                         command=self.connect_and_start)
        self.connect_button.grid(row=0, column=2, rowspan=2, ipady=10, padx=10)
        
        self.record_button = ttk.Button(control_panel, text="保存当前帧", 
                                       command=self.save_current_frames, state=tk.DISABLED)
        self.record_button.grid(row=0, column=3, rowspan=2, ipady=10, padx=10)
        
        self.disconnect_button = ttk.Button(control_panel, text="断开连接", 
                                           command=self.disconnect_all, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=4, rowspan=2, ipady=10, padx=10)
        
        # --- 预览面板 (2x2布局) ---
        preview_panel = ttk.Frame(main_frame)
        preview_panel.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        preview_panel.columnconfigure(0, weight=1)
        preview_panel.columnconfigure(1, weight=1)
        preview_panel.rowconfigure(0, weight=1)
        preview_panel.rowconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 创建占位图像
        placeholder = Image.new('RGB', (300, 200), 'black')
        
        # 左上: 深度摄像头1
        self.photo1 = ImageTk.PhotoImage(image=placeholder)
        self.preview_label1 = ttk.Label(preview_panel, image=self.photo1, 
                                        text="深度摄像头1", compound="top")
        self.preview_label1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 右上: 深度摄像头2
        self.photo2 = ImageTk.PhotoImage(image=placeholder)
        self.preview_label2 = ttk.Label(preview_panel, image=self.photo2, 
                                        text="深度摄像头2", compound="top")
        self.preview_label2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # 左下: 红外传感器1 (0x33 - long)
        self.thermal_photo1 = ImageTk.PhotoImage(image=placeholder)
        self.thermal_label1 = ttk.Label(preview_panel, image=self.thermal_photo1, 
                                        text="红外传感器 (long - 0x33)", compound="top")
        self.thermal_label1.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # 右下: 红外传感器2 (0x34 - wide)
        self.thermal_photo2 = ImageTk.PhotoImage(image=placeholder)
        self.thermal_label2 = ttk.Label(preview_panel, image=self.thermal_photo2, 
                                        text="红外传感器 (wide - 0x34)", compound="top")
        self.thermal_label2.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        # --- 日志窗口 ---
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=80, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="ew")
    
    def get_available_cdc_ports(self):
        """获取可用的CDC串口列表 (跨平台)"""
        ports = []
        
        # 使用pyserial的list_ports自动检测
        available_ports = serial.tools.list_ports.comports()
        for port in available_ports:
            # Windows: COM1, COM2, ...
            # Linux: /dev/ttyACM0, /dev/ttyUSB0, ...
            # macOS: /dev/cu.usbmodem...
            ports.append(port.device)
            self.log(f"检测到串口: {port.device} - {port.description}")
        
        if len(ports) == 0:
            self.log("警告: 未检测到任何串口设备！")
        
        return ports
    
    def connect_and_start(self):
        """连接串口并开始读取"""
        cdc0_path = self.port_combo_cdc0.get()
        cdc1_path = self.port_combo_cdc1.get()
        
        if not cdc0_path or not cdc1_path:
            messagebox.showerror("错误", "请选择两个CDC串口。")
            return
        
        if cdc0_path == cdc1_path:
            messagebox.showerror("错误", "两个CDC串口不能相同。")
            return
        
        self.connect_button.config(state=tk.DISABLED)
        threading.Thread(target=self._connect_task, args=(cdc0_path, cdc1_path), daemon=True).start()
    
    def _connect_task(self, cdc0_path, cdc1_path):
        """连接任务"""
        try:
            # 打开CDC 0 (MLX90640)
            self.log(f"正在连接 CDC 0: {cdc0_path}...")
            self.cdc0_port = serial.Serial(cdc0_path, baudrate=115200, timeout=0.1)
            
            # 打开CDC 1 (ToF)
            self.log(f"正在连接 CDC 1: {cdc1_path}...")
            self.cdc1_port = serial.Serial(cdc1_path, baudrate=115200, timeout=0.1)
            
            self.log("连接成功!")
            self.running = True
            
            # 启动读取线程
            thread_cdc0 = threading.Thread(target=self._read_cdc0_thread, daemon=True)
            thread_cdc1 = threading.Thread(target=self._read_cdc1_thread, daemon=True)
            
            thread_cdc0.start()
            thread_cdc1.start()
            
            self.read_threads = [thread_cdc0, thread_cdc1]
            
            # 更新UI
            def update_ui():
                self.record_button.config(state=tk.NORMAL)
                self.disconnect_button.config(state=tk.NORMAL)
            self.root.after(0, update_ui)
            
        except Exception as e:
            self.log(f"连接失败: {e}")
            self.root.after(0, self.connect_button.config, {'state': tk.NORMAL})
    
    def _read_cdc0_thread(self):
        """读取CDC 0 (MLX90640数据)"""
        buffer = bytearray()
        
        while self.running:
            try:
                if self.cdc0_port and self.cdc0_port.in_waiting > 0:
                    data = self.cdc0_port.read(self.cdc0_port.in_waiting)
                    buffer.extend(data)
                    
                    # 解析MLX数据包
                    self._parse_mlx_data(buffer)
                
                time.sleep(0.01)
                
            except Exception as e:
                self.log(f"CDC0 读取错误: {e}")
                break
    
    def _parse_mlx_data(self, buffer):
        """解析MLX90640数据包 (新格式带CRC)
        格式: [0xAA, 0x55, SENSOR_TYPE, SENSOR_ID, LEN_LOW, LEN_HIGH] + 3072字节浮点数据 + [CRC_LOW, CRC_HIGH]
        """
        HEADER_SIZE = 6
        DATA_SIZE = MLX_NUM_PIXELS * 4  # 768 * 4 = 3072 bytes
        CRC_SIZE = 2
        PACKET_SIZE = HEADER_SIZE + DATA_SIZE + CRC_SIZE
        
        while len(buffer) >= PACKET_SIZE:
            # 查找包头
            if buffer[0] == PACKET_SYNC1 and buffer[1] == PACKET_SYNC2:
                sensor_type = buffer[2]
                sensor_id = buffer[3]
                data_len = buffer[4] | (buffer[5] << 8)
                
                if sensor_type == SENSOR_TYPE_MLX and data_len == DATA_SIZE:
                    # 提取温度数据 (3072字节)
                    temp_bytes = bytes(buffer[HEADER_SIZE:HEADER_SIZE + DATA_SIZE])
                    
                    # 提取CRC
                    crc_received = buffer[HEADER_SIZE + DATA_SIZE] | \
                                   (buffer[HEADER_SIZE + DATA_SIZE + 1] << 8)
                    
                    # 验证CRC
                    crc_calculated = crc16_ccitt(temp_bytes)
                    
                    if crc_received == crc_calculated:
                        # CRC校验通过
                        temps = np.frombuffer(temp_bytes, dtype=np.float32)
                        
                        if len(temps) == MLX_NUM_PIXELS:
                            self.mlx_packets_received += 1
                            if sensor_id == 0x01:  # MLX传感器1 (0x33)
                                self.latest_temps_mlx1 = temps.copy()
                                self.new_data_flags['mlx1'] = True
                            elif sensor_id == 0x02:  # MLX传感器2 (0x34)
                                self.latest_temps_mlx2 = temps.copy()
                                self.new_data_flags['mlx2'] = True
                    else:
                        print(f"警告: MLX传感器{sensor_id} CRC校验失败! 期望={crc_calculated:04X}, 收到={crc_received:04X}")
                    
                    # 移除已处理的数据包
                    buffer[:] = buffer[PACKET_SIZE:]
                else:
                    # 未知传感器类型或长度不匹配,丢弃包头
                    buffer.pop(0)
            else:
                # 包头不匹配,丢弃一个字节
                buffer.pop(0)
    
    def _read_cdc1_thread(self):
        """读取CDC 1 (ToF数据)"""
        last_log_time = time.time()
        no_data_logged = False
        
        while self.running:
            try:
                if self.cdc1_port and self.cdc1_port.in_waiting > 0:
                    data = self.cdc1_port.read(self.cdc1_port.in_waiting)
                    self.tof_bytes_received += len(data)
                    no_data_logged = False
                    
                    # 解析ToF数据
                    result = self.tof_parser.parse_data(data)
                    if result:
                        src_id, payload = result
                        self.tof_packets_received += 1
                        self._process_tof_payload(src_id, payload)
                else:
                    # CDC1没有数据，每30秒警告一次
                    if time.time() - last_log_time > 30.0 and not no_data_logged:
                        self.log(f"⚠ 警告: ToF传感器无数据")
                        no_data_logged = True
                        last_log_time = time.time()
                
                time.sleep(0.01)
                
            except Exception as e:
                self.log(f"CDC1 读取错误: {e}")
                break
    
    def _process_tof_payload(self, src_id, payload):
        """处理ToF传感器的负载数据"""
        # 根据源ID选择对应的解析器
        if src_id == 1:
            frame = self.cam1_parser.parse_frame(payload)
            if frame is not None:
                self.latest_frame_cam1 = frame
                self.new_data_flags['cam1'] = True
                
        elif src_id == 2:
            frame = self.cam2_parser.parse_frame(payload)
            if frame is not None:
                self.latest_frame_cam2 = frame
                self.new_data_flags['cam2'] = True
    
    def disconnect_all(self):
        """断开所有连接"""
        self.log("正在断开连接...")
        self.running = False
        
        # 等待线程结束
        for thread in self.read_threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        
        # 关闭串口
        if self.cdc0_port:
            self.cdc0_port.close()
            self.cdc0_port = None
        
        if self.cdc1_port:
            self.cdc1_port.close()
            self.cdc1_port = None
        
        # 更新UI
        self.connect_button.config(state=tk.NORMAL)
        self.record_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.DISABLED)
        self.scene_initialized = False
        
        self.log("已断开连接")
    
    def save_current_frames(self):
        """保存当前帧"""
        # 初始化场景
        if not self.scene_initialized:
            scene_name = simpledialog.askstring("场景名称", 
                                               "请输入本次采集的场景名称 (例如: desktop_test):", 
                                               parent=self.root)
            if not scene_name:
                return
            
            self.scene_name = scene_name
            self.frame_counter = 0
            
            # 创建目录
            os.makedirs(os.path.join(self.save_path, self.scene_name, "cam1"), exist_ok=True)
            os.makedirs(os.path.join(self.save_path, self.scene_name, "cam2"), exist_ok=True)
            os.makedirs(os.path.join(self.save_path, self.scene_name, "long"), exist_ok=True)
            os.makedirs(os.path.join(self.save_path, self.scene_name, "wide"), exist_ok=True)
            os.makedirs(os.path.join(self.save_path, self.scene_name, "preview"), exist_ok=True)
            
            self.scene_initialized = True
            self.log(f"场景 '{self.scene_name}' 已初始化")
        
        # 检查数据
        if (self.latest_frame_cam1 is None or self.latest_frame_cam2 is None or
            self.latest_temps_mlx1 is None or self.latest_temps_mlx2 is None):
            messagebox.showwarning("警告", "部分传感器数据未就绪,请等待数据更新。")
            return
        
        try:
            filename = f"{self.frame_counter:05d}"
            
            # 保存深度数据
            path_cam1 = os.path.join(self.save_path, self.scene_name, "cam1", filename + ".bin")
            with open(path_cam1, "wb") as f:
                f.write(self.latest_frame_cam1.tobytes())
            
            path_cam2 = os.path.join(self.save_path, self.scene_name, "cam2", filename + ".bin")
            with open(path_cam2, "wb") as f:
                f.write(self.latest_frame_cam2.tobytes())
            
            # 保存红外数据
            temp_array_long = self.latest_temps_mlx1.reshape(MLX_SENSOR_H, MLX_SENSOR_W)
            path_long = os.path.join(self.save_path, self.scene_name, "long", filename + ".bin")
            temp_array_long.astype(np.float32).tofile(path_long)
            
            temp_array_wide = self.latest_temps_mlx2.reshape(MLX_SENSOR_H, MLX_SENSOR_W)
            path_wide = os.path.join(self.save_path, self.scene_name, "wide", filename + ".bin")
            temp_array_wide.astype(np.float32).tofile(path_wide)
            
            # 保存预览图像
            preview_path = os.path.join(self.save_path, self.scene_name, "preview", filename + ".png")
            self.save_preview_image(preview_path)
            
            self.log(f"✓ 已保存帧 #{self.frame_counter}")
            self.frame_counter += 1
            
        except Exception as e:
            self.log(f"✗ 保存帧时出错: {e}")
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def save_preview_image(self, filepath):
        """保存预览图像"""
        try:
            images = []
            
            # 深度图像1
            if self.latest_frame_cam1 is not None:
                color_img1 = JET_COLORS[self.latest_frame_cam1]
                h, w, _ = color_img1.shape
                img1 = Image.fromarray(color_img1, 'RGB').resize((w * 2, h * 2), Image.NEAREST)
                images.append(img1)
            
            # 深度图像2
            if self.latest_frame_cam2 is not None:
                color_img2 = JET_COLORS[self.latest_frame_cam2]
                h, w, _ = color_img2.shape
                img2 = Image.fromarray(color_img2, 'RGB').resize((w * 2, h * 2), Image.NEAREST)
                images.append(img2)
            
            # 热成像图像1
            if self.latest_temps_mlx1 is not None:
                thermal_img1 = self.temp_to_thermal_image(self.latest_temps_mlx1)
                thermal_img1 = thermal_img1.resize((thermal_img1.width * 8, 
                                                   thermal_img1.height * 8), Image.NEAREST)
                images.append(thermal_img1)
            
            # 热成像图像2
            if self.latest_temps_mlx2 is not None:
                thermal_img2 = self.temp_to_thermal_image(self.latest_temps_mlx2)
                thermal_img2 = thermal_img2.resize((thermal_img2.width * 8, 
                                                   thermal_img2.height * 8), Image.NEAREST)
                images.append(thermal_img2)
            
            if len(images) == 4:
                # 创建2x2网格
                width = max(img.width for img in images)
                height = max(img.height for img in images)
                
                # 调整尺寸
                resized_images = []
                for img in images:
                    resized_img = Image.new('RGB', (width, height), 'black')
                    resized_img.paste(img, ((width - img.width) // 2, (height - img.height) // 2))
                    resized_images.append(resized_img)
                
                # 组合图像
                combined = Image.new('RGB', (width * 2, height * 2))
                combined.paste(resized_images[0], (0, 0))
                combined.paste(resized_images[1], (width, 0))
                combined.paste(resized_images[2], (0, height))
                combined.paste(resized_images[3], (width, height))
                
                combined.save(filepath)
                
        except Exception as e:
            self.log(f"保存预览图像时出错: {e}")
    
    def temp_to_color(self, v, vmin=5.0, vmax=50.0):
        """温度值转颜色"""
        COLORS = [[0, 0, 0], [0, 0, 1], [0, 1, 0], [1, 1, 0], [1, 0, 0], [1, 0, 1], [1, 1, 1]]
        NUM_COLORS = len(COLORS)
        
        v = (v - vmin) / (vmax - vmin)
        if v <= 0:
            idx1 = idx2 = 0
        elif v >= 1:
            idx1 = idx2 = NUM_COLORS - 1
        else:
            v *= (NUM_COLORS - 1)
            idx1 = int(v)
            idx2 = idx1 + 1
        
        fract_between = v - float(idx1)
        r = ((COLORS[idx2][0] - COLORS[idx1][0]) * fract_between + COLORS[idx1][0]) * 255.0
        g = ((COLORS[idx2][1] - COLORS[idx1][1]) * fract_between + COLORS[idx1][1]) * 255.0
        b = ((COLORS[idx2][2] - COLORS[idx1][2]) * fract_between + COLORS[idx1][2]) * 255.0
        
        return int(r), int(g), int(b)
    
    def temp_to_thermal_image(self, temps):
        """将温度数组转换为热成像图像（顺时针旋转90度）"""
        # 先按原始方向生成图像
        img_array = np.zeros((MLX_SENSOR_H, MLX_SENSOR_W, 3), dtype=np.uint8)
        
        for y in range(MLX_SENSOR_H):
            for x in range(MLX_SENSOR_W):
                # 注意索引顺序
                idx = (MLX_SENSOR_W - 1 - x) * MLX_SENSOR_H + y
                val = temps[idx]
                img_array[y, x] = self.temp_to_color(val)
        
        # 顺时针旋转90度：transpose后水平翻转
        # 或者直接使用numpy的rot90(-1)表示顺时针旋转90度
        img_array = np.rot90(img_array, k=-1)  # k=-1表示顺时针旋转90度
        
        return Image.fromarray(img_array, 'RGB')
    
    def update_preview(self):
        """更新预览"""
        try:
            # 更新深度图像
            if self.new_data_flags['cam1'] and self.latest_frame_cam1 is not None:
                color_img = JET_COLORS[self.latest_frame_cam1]
                h, w, _ = color_img.shape
                img = Image.fromarray(color_img, 'RGB').resize((w * 2, h * 2), Image.NEAREST)
                self.photo1 = ImageTk.PhotoImage(image=img)
                self.preview_label1.config(image=self.photo1)
                self.new_data_flags['cam1'] = False
            
            if self.new_data_flags['cam2'] and self.latest_frame_cam2 is not None:
                color_img = JET_COLORS[self.latest_frame_cam2]
                h, w, _ = color_img.shape
                img = Image.fromarray(color_img, 'RGB').resize((w * 2, h * 2), Image.NEAREST)
                self.photo2 = ImageTk.PhotoImage(image=img)
                self.preview_label2.config(image=self.photo2)
                self.new_data_flags['cam2'] = False
            
            # 更新热成像图像
            if self.new_data_flags['mlx1'] and self.latest_temps_mlx1 is not None:
                img_thermal1 = self.temp_to_thermal_image(self.latest_temps_mlx1)
                img_thermal1 = img_thermal1.resize((img_thermal1.width * 8, 
                                                   img_thermal1.height * 8), Image.NEAREST)
                self.thermal_photo1 = ImageTk.PhotoImage(image=img_thermal1)
                self.thermal_label1.config(image=self.thermal_photo1)
                self.new_data_flags['mlx1'] = False
            
            if self.new_data_flags['mlx2'] and self.latest_temps_mlx2 is not None:
                img_thermal2 = self.temp_to_thermal_image(self.latest_temps_mlx2)
                img_thermal2 = img_thermal2.resize((img_thermal2.width * 8, 
                                                   img_thermal2.height * 8), Image.NEAREST)
                self.thermal_photo2 = ImageTk.PhotoImage(image=img_thermal2)
                self.thermal_label2.config(image=self.thermal_photo2)
                self.new_data_flags['mlx2'] = False
            
        except Exception as e:
            pass  # 忽略预览错误
        
        # 定时更新 (约30fps)
        self.root.after(33, self.update_preview)
    
    def on_closing(self):
        """关闭程序"""
        self.log("正在关闭程序...")
        self.disconnect_all()
        time.sleep(0.2)
        self.root.destroy()

# ============ 主程序 ============
if __name__ == "__main__":
    root = tk.Tk()
    app = DataCollectorApp(root)
    root.mainloop()
