
#When the message "Permission denied: /dev/ttyx" appears, 
#change the permission settings on your serial_port
# eg. "sudo chmod 666 /dev/ttyUSB0"

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
import rclpy.time
from std_msgs.msg import String
from sensor_msgs.msg import Imu
import serial
import struct


class EbimuPublisher(Node):

	def __init__(self):
		super().__init__('ebimu_publisher')

		self.declare_parameter('device_name', '/dev/ttyUSB0')
		self.declare_parameter('baud_rate', 115200)
		self.declare_parameter('frame', 'map')

		device_name = self.get_parameter('device_name').get_parameter_value().string_value
		baud_rate = self.get_parameter('baud_rate').get_parameter_value().integer_value
		self.frame_id = self.get_parameter('frame').get_parameter_value().string_value

		self.get_logger().info(f'Serial device: {device_name}')
		self.get_logger().info(f'Baud rate: {baud_rate}')

		try:
			self.serial_port = serial.Serial(device_name, baud_rate)
			self.get_logger().info('Serial port opened successfully.')
		except serial.SerialException as e:
			self.get_logger().error(f'Failed to open serial port: {e}')
			rclpy.shutdown()
	
		qos_profile = QoSProfile(depth=10)

		self.publisher = self.create_publisher(Imu, 'ebimu_data', qos_profile)
		timer_period = 0.0005
		self.timer = self.create_timer(timer_period, self.timer_callback)
		self.count = 0

	def timer_callback(self):
		
		msg = Imu()
		if self.serial_port.read(2) == b'\x55\x55':  # SOP 확인

			data = self.serial_port.read(22)

			if len(data) == 22:
				self.parse_ahrs_data(data)
				msg.header.stamp = self.get_clock().now().to_msg()
				msg.header.frame_id = self.frame_id
				msg.orientation.x = self.qx
				msg.orientation.y = self.qy
				msg.orientation.z = self.qz
				msg.orientation.w = self.qw
				msg.linear_acceleration.x = self.accel_x
				msg.linear_acceleration.y = self.accel_y
				msg.linear_acceleration.z = self.accel_z
				msg.angular_velocity.x = self.gyro_x
				msg.angular_velocity.y = self.gyro_y
				msg.angular_velocity.z = self.gyro_z
				self.publisher.publish(msg)
			else:
				self.get_logger().error('data length error')
		# msg.data = ser_data.decode('utf-8')
		# 

	def validate_checksum(self,data):
		# SOP를 포함하여 체크섬 계산
		calculated_checksum = 0x55 + 0x55 + sum(data[:-2])  # SOP와 나머지 데이터의 합
		calculated_checksum &= 0xFFFF  # 16비트로 제한
		received_checksum = struct.unpack('<H', data[20:22])[0]  # 마지막 2바이트에서 체크섬 추출
		return calculated_checksum == received_checksum

	def parse_ahrs_data(self,data):
		# 쿼터니언 (4개, 각 2바이트)
		quaternion = struct.unpack('>hhhh', data[0:8])  # Little-endian으로 unpack
		self.qz, self.qy, self.qx, self.qw = [x / 32768.0 for x in quaternion]  # double형으로 변환

		# 자이로 (3개, 각 2바이트)
		gyro = struct.unpack('<hhh', data[8:14])  # Little-endian으로 unpack
		self.gyro_x, self.gyro_y, self.gyro_z = [x / 32768.0 for x in gyro]  # double형으로 변환

		# 가속도 (3개, 각 2바이트)
		accel = struct.unpack('<hhh', data[14:20])  # Little-endian으로 unpack
		self.accel_x, self.accel_y, self.accel_z = [x / 32768.0 for x in accel]  # double형으로 변환



def main(args=None):
	rclpy.init(args=args)

	print("Starting ebimu_publisher..")

	node = EbimuPublisher()
	
	try:
		rclpy.spin(node)

	finally:
		node.destroy_node()
		rclpy.shutdown()


if __name__ == '__main__':
	main()

