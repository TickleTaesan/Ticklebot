import numpy as np
import yaml
import serial
import time
from typing import Tuple

# ROS
import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, Bool

from topic_names import (WAYPOINT_TOPIC, 
			 			REACHED_GOAL_TOPIC)
from ros_data import ROSData
from utils import clip_angle

# CONSTS
CONFIG_PATH = "../config/robot.yaml"
with open(CONFIG_PATH, "r") as f:
	robot_config = yaml.safe_load(f)
MAX_V = robot_config["max_v"]
MAX_W = robot_config["max_w"]
VEL_TOPIC = robot_config["vel_navi_topic"]
DT = 1/robot_config["frame_rate"]
RATE = 9
EPS = 1e-8
WAYPOINT_TIMEOUT = 1 # seconds # TODO: tune this
FLIP_ANG_VEL = np.pi/4

# ODESC 3.6 v0.5.1 설정
ODESC_SERIAL_PORT = rospy.get_param('~serial_port', '/dev/ttyUSB0')
ODESC_BAUDRATE = 115200
WHEEL_SEPARATION = rospy.get_param('~wheel_separation', 0.26)  # 휠 간격 (m)
WHEEL_RADIUS = rospy.get_param('~wheel_radius', 0.069)         # 휠 반지름 (m)

# GLOBALS
vel_msg = Twist()
waypoint = ROSData(WAYPOINT_TIMEOUT, name="waypoint")
reached_goal = False
reverse_mode = False
current_yaw = None
odesc_serial = None  # ODESC 시리얼 연결

def clip_angle(theta) -> float:
	"""Clip angle to [-pi, pi]"""
	theta %= 2 * np.pi
	if -np.pi < theta < np.pi:
		return theta
	return theta - 2 * np.pi

def init_odesc():
	"""ODESC 3.6 v0.5.1 초기화"""
	global odesc_serial
	try:
		odesc_serial = serial.Serial(ODESC_SERIAL_PORT, ODESC_BAUDRATE, timeout=1)
		time.sleep(2)  # 연결 대기
		
		# ODESC v0.5.1 초기화 명령어
		odesc_serial.write(b"odrv0.axis0.requested_state = 3\n")  # CLOSED_LOOP_CONTROL
		odesc_serial.write(b"odrv0.axis1.requested_state = 3\n")  # CLOSED_LOOP_CONTROL
		time.sleep(1)
		
		rospy.loginfo(f"ODESC 3.6 v0.5.1 연결 성공: {ODESC_SERIAL_PORT}")
		return True
	except Exception as e:
		rospy.logerr(f"ODESC 연결 실패: {e}")
		return False

def differential_drive_kinematics(linear_vel, angular_vel):
	"""차동 구동 역기구학 계산"""
	# v = (v_left + v_right) / 2
	# ω = (v_right - v_left) / L
	# 따라서:
	# v_left = v - (ω * L) / 2
	# v_right = v + (ω * L) / 2
	
	left_vel = linear_vel - (angular_vel * WHEEL_SEPARATION) / 2
	right_vel = linear_vel + (angular_vel * WHEEL_SEPARATION) / 2
	
	return left_vel, right_vel

def send_odesc_commands(left_vel, right_vel):
	"""ODESC 3.6 v0.5.1로 모터 명령 전송"""
	global odesc_serial
	if odesc_serial is None:
		return False
	
	try:
		# ODESC v0.5.1 속도 제어 명령어
		# 속도를 RPM으로 변환 (휠 반지름 고려)
		left_rpm = int(left_vel * 60 / (2 * np.pi * WHEEL_RADIUS))
		right_rpm = int(right_vel * 60 / (2 * np.pi * WHEEL_RADIUS))
		
		# ODESC v0.5.1 명령어 형식
		left_cmd = f"odrv0.axis0.controller.vel_setpoint = {left_rpm}\n"
		right_cmd = f"odrv0.axis1.controller.vel_setpoint = {right_rpm}\n"
		
		odesc_serial.write(left_cmd.encode())
		odesc_serial.write(right_cmd.encode())
		
		return True
	except Exception as e:
		rospy.logerr(f"ODESC 명령 전송 실패: {e}")
		return False
      

def pd_controller(waypoint: np.ndarray) -> Tuple[float]:
	"""PD controller for the robot"""
	assert len(waypoint) == 2 or len(waypoint) == 4, "waypoint must be a 2D or 4D vector"
	if len(waypoint) == 2:
		dx, dy = waypoint
	else:
		dx, dy, hx, hy = waypoint
	# this controller only uses the predicted heading if dx and dy near zero
	if len(waypoint) == 4 and np.abs(dx) < EPS and np.abs(dy) < EPS:
		v = 0
		w = clip_angle(np.arctan2(hy, hx))/DT		
	elif np.abs(dx) < EPS:
		v =  0
		w = np.sign(dy) * np.pi/(2*DT)
	else:
		v = dx / DT
		w = np.arctan(dy/dx) / DT
	v = np.clip(v, 0, MAX_V)
	w = np.clip(w, -MAX_W, MAX_W)
	return v, w


def callback_drive(waypoint_msg: Float32MultiArray):
	"""Callback function for the waypoint subscriber"""
	global vel_msg
	print("seting waypoint")
	waypoint.set(waypoint_msg.data)
	
	
def callback_reached_goal(reached_goal_msg: Bool):
	"""Callback function for the reached goal subscriber"""
	global reached_goal
	reached_goal = reached_goal_msg.data


def main():
	global vel_msg, reverse_mode
	rospy.init_node("PD_CONTROLLER", anonymous=False)
	
	# ODESC 3.6 v0.5.1 초기화
	if not init_odesc():
		rospy.logerr("ODESC 초기화 실패. 프로그램을 종료합니다.")
		return
	
	waypoint_sub = rospy.Subscriber(WAYPOINT_TOPIC, Float32MultiArray, callback_drive, queue_size=1)
	reached_goal_sub = rospy.Subscriber(REACHED_GOAL_TOPIC, Bool, callback_reached_goal, queue_size=1)
	vel_out = rospy.Publisher(VEL_TOPIC, Twist, queue_size=1)
	rate = rospy.Rate(RATE)
	print("Registered with master node. Waiting for waypoints...")
	
	while not rospy.is_shutdown():
		vel_msg = Twist()
		if reached_goal:
			# 목표 도달 시 모터 정지
			send_odesc_commands(0, 0)
			vel_out.publish(vel_msg)
			print("Reached goal! Stopping...")
			return
		elif waypoint.is_valid(verbose=True):
			v, w = pd_controller(waypoint.get())
			if reverse_mode:
				v *= -1
			
			# 차동 구동 역기구학으로 좌우 휠 속도 계산
			left_vel, right_vel = differential_drive_kinematics(v, w)
			
			# ODESC로 모터 제어
			if send_odesc_commands(left_vel, right_vel):
				vel_msg.linear.x = v
				vel_msg.angular.z = w
				print(f"ODESC 제어: v={v:.3f}, w={w:.3f}, left={left_vel:.3f}, right={right_vel:.3f}")
			else:
				print("ODESC 명령 전송 실패")
		
		vel_out.publish(vel_msg)
		rate.sleep()
	
	# 종료 시 모터 정지
	send_odesc_commands(0, 0)
	

if __name__ == '__main__':
	main()
