#!/usr/bin/env python3
import rospy, cv2
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from cv_bridge import CvBridge
import argparse
import numpy as np

bridge = CvBridge()
latest_img = None
latest_wp = None
latest_samples = None

def img_cb(msg):
    global latest_img
    latest_img = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

def wp_cb(msg):
    global latest_wp
    latest_wp = msg.data

def samples_cb(msg):
    # msg: [meta, a0_x, a0_y, a1_x, a1_y, ...] 라고 가정
    global latest_samples
    latest_samples = np.array(msg.data, dtype=np.float32)

def main():
    rospy.init_node("overlay_viz", anonymous=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="/usb_cam/image_raw")
    parser.add_argument("--waypoint", default="/waypoint")
    parser.add_argument("--samples", default="/sampled_actions")
    parser.add_argument("--out", default="/viz/image")
    parser.add_argument("--scale", type=float, default=50.0, help="화살표 스케일")
    args = parser.parse_args(rospy.myargv()[1:])

    rospy.Subscriber(args.image, Image, img_cb, queue_size=1)
    rospy.Subscriber(args.waypoint, Float32MultiArray, wp_cb, queue_size=1)
    rospy.Subscriber(args.samples, Float32MultiArray, samples_cb, queue_size=1)
    pub = rospy.Publisher(args.out, Image, queue_size=1)

    rate = rospy.Rate(20)
    while not rospy.is_shutdown():
        if latest_img is None:
            rate.sleep(); continue
        frame = latest_img.copy()
        h, w = frame.shape[:2]
        origin = (int(0.1*w), int(0.9*h))  # 좌하단 근처 기준점

        # 샘플 경로들 (있으면 회색 점선/화살표)
        if latest_samples is not None and latest_samples.size >= 3:
            arr = latest_samples[1:]  # 첫 값은 메타라고 가정 ([0])
            pairs = arr.reshape(-1, 2)
            for (vx, vy) in pairs:
                tip = (int(origin[0] + args.scale*vx), int(origin[1] - args.scale*vy))
                cv2.arrowedLine(frame, origin, tip, (180,180,180), 1, tipLength=0.2)

        # 선택된 웨이포인트 (초록)
        if latest_wp is not None and len(latest_wp) >= 2:
            vx, vy = float(latest_wp[0]), float(latest_wp[1])
            tip = (int(origin[0] + args.scale*vx), int(origin[1] - args.scale*vy))
            cv2.arrowedLine(frame, origin, tip, (0,255,0), 2, tipLength=0.3)
            cv2.putText(frame, f"wp=({vx:.2f},{vy:.2f})", (origin[0], origin[1]-20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        pub.publish(bridge.cv2_to_imgmsg(frame, encoding='bgr8'))
        rate.sleep()

if __name__ == "__main__":
    main()

