from __future__ import annotations

import rclpy
from rclpy.node import Node

from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped, Quaternion
from std_msgs.msg import Float32MultiArray

from tf_transformations import quaternion_from_euler


class PathVizNode(Node):
    def __init__(self) -> None:
        super().__init__('path_viz')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('waypoint_topic', '/waypoint')
        self.declare_parameter('path_topic', '/waypoint_path')

        self.frame_id: str = str(self.get_parameter('frame_id').value)
        self.waypoint_topic: str = str(self.get_parameter('waypoint_topic').value)
        self.path_topic: str = str(self.get_parameter('path_topic').value)

        self.path_pub = self.create_publisher(Path, self.path_topic, 10)
        self.create_subscription(Float32MultiArray, self.waypoint_topic, self._wp_cb, 10)

        self.path = Path()
        self.path.header.frame_id = self.frame_id
        self.get_logger().info(f'PathViz publishing to {self.path_topic}, listening {self.waypoint_topic}')

    def _wp_cb(self, msg: Float32MultiArray) -> None:
        if len(msg.data) < 2:
            return
        pose = PoseStamped()
        pose.header.frame_id = self.frame_id
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(msg.data[0])
        pose.pose.position.y = float(msg.data[1])
        qx, qy, qz, qw = quaternion_from_euler(0.0, 0.0, 0.0)
        pose.pose.orientation = Quaternion(x=qx, y=qy, z=qz, w=qw)

        self.path.poses.append(pose)
        self.path.header.stamp = self.get_clock().now().to_msg()
        self.path_pub.publish(self.path)


def main() -> None:
    rclpy.init()
    node = PathVizNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


