
#!/usr/bin/env python3
import rospy
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32MultiArray  # waypoint 메시지 타입에 맞춰 변경 필요
import tf

class PathVisualizer:
    def __init__(self):
        self.path_pub = rospy.Publisher("/waypoint_path", Path, queue_size=10)
        self.path_msg = Path()
        self.path_msg.header.frame_id = "map"  # 프레임 이름 맞춰 변경
        rospy.Subscriber(rospy.get_param("~waypoint_topic", "/waypoint"),
                         Float32MultiArray, self.waypoint_callback)

    def waypoint_callback(self, msg):
        # msg.data = [x, y] 또는 [x1, y1, x2, y2, ...] 구조라고 가정
        if len(msg.data) >= 2:
            pose = PoseStamped()
            pose.header.frame_id = "map"
            pose.header.stamp = rospy.Time.now()
            pose.pose.position.x = msg.data[0]
            pose.pose.position.y = msg.data[1]
            pose.pose.orientation = tf.transformations.quaternion_from_euler(0, 0, 0)
            self.path_msg.poses.append(pose)

            self.path_msg.header.stamp = rospy.Time.now()
            self.path_pub.publish(self.path_msg)

if __name__ == "__main__":
    rospy.init_node("path_viz")
    PathVisualizer()
    rospy.spin()
