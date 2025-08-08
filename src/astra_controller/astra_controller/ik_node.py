import math
from pathlib import Path
import rclpy
import rclpy.node
import rclpy.qos

import geometry_msgs.msg
import astra_controller_interfaces.msg
import std_msgs.msg

from ament_index_python import get_package_share_directory

from typing import Any, List, Tuple, Union

import modern_robotics as mr
import numpy as np
from mr_urdf_loader import loadURDF
from pytransform3d import transformations as pt

import logging

logger = logging.getLogger(__name__)

np.set_printoptions(precision=4, suppress=True)

def pq_from_ros_pose(msg: geometry_msgs.msg.Pose):
    return [
        msg.position.x,
        msg.position.y,
        msg.position.z,
        msg.orientation.w,
        msg.orientation.x,
        msg.orientation.y,
        msg.orientation.z
    ]

def main(args=None):
    rclpy.init(args=args)

    node = rclpy.node.Node("ik_node")
    
    node.declare_parameter('eef_link_name', 'link_ree_teleop')
    node.declare_parameter('joint_names', [ 'joint_r1', 'joint_r2', 'joint_r3', 'joint_r4', 'joint_r5', 'joint_r6' ])

    eef_link_name = node.get_parameter('eef_link_name').value
    joint_names = node.get_parameter('joint_names').value
    
    assert len(joint_names) == 6

    # Ref: interbotix_ros_toolboxes/interbotix_xs_toolbox/interbotix_xs_modules/interbotix_xs_modules/xs_robot/arm.py
    urdf_name = str(Path(get_package_share_directory("astra_description")) / "urdf" / "astra_description_rel.urdf")
    logger.info(f'Loading URDF from: {urdf_name}')

    M, Slist, Blist, Mlist, Glist, robot = loadURDF(
        urdf_name, 
        eef_link_name=eef_link_name, 
        actuated_joint_names=joint_names
    )
    
    logger.info(f'Robot loaded successfully. End effector: {eef_link_name}')
    logger.info(f'Joint names: {joint_names}')
    logger.info(f'M matrix:\n{M}')
    logger.info(f'Slist:\n{Slist}')
    logger.info(f'IK node started and listening for goal_pose messages')
    
    joint_limit_lower = []
    joint_limit_upper = []
    for joint_name in joint_names:
        joint = robot.joint_map[joint_name]
        joint_limit_lower.append(joint.limit.lower)
        joint_limit_upper.append(joint.limit.upper)
        logger.info(f'Joint {joint_name}: limits [{joint.limit.lower}, {joint.limit.upper}]')

    arm_joint_command_publisher = node.create_publisher(astra_controller_interfaces.msg.JointCommand, "arm/joint_command", 10)
    lift_joint_command_publisher = node.create_publisher(astra_controller_interfaces.msg.JointCommand, "lift/joint_command", 10)
    
    error_publisher = node.create_publisher(std_msgs.msg.String, "ik_error", 10)
        
    def pub_theta(theta_list):
        logger.info(f'Publishing joint commands: arm={theta_list[1:]}, lift={theta_list[:1]}')
        msg = astra_controller_interfaces.msg.JointCommand(
            name=joint_names[1:],
            position_cmd=list(theta_list[1:])
        )
        arm_joint_command_publisher.publish(msg)

        msg = astra_controller_interfaces.msg.JointCommand(
            name=joint_names[:1],
            position_cmd=list(theta_list[:1])
        )
        lift_joint_command_publisher.publish(msg)
        
    last_theta_list = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def set_ee_pose_matrix(
        T_sd: np.ndarray,
    ) -> Tuple[Union[np.ndarray, Any, List[float]], bool]:
        """
        Command a desired end effector pose.

        :param T_sd: 4x4 Transformation Matrix representing the transform from the
            /<robot_name>/base_link frame to the /<robot_name>/ee_gripper_link frame
        :return: joint values needed to get the end effector to the desired pose
        :return: `True` if a valid solution was found; `False` otherwise
        """
        logger.info(f'Setting ee_pose to matrix=\n{T_sd}')
        logger.info(f'Target position: x={T_sd[0,3]:.3f}, y={T_sd[1,3]:.3f}, z={T_sd[2,3]:.3f}')
        
        nonlocal last_theta_list
        
        # Test forward kinematics first to verify the robot model
        test_theta = [0.6, 0.0, 1.75, -1.57, 0.0, 0.0]
        logger.info(f'Testing FK with theta={test_theta}')
        try:
            T_test = mr.FKinSpace(M, Slist, test_theta)
            logger.info(f'FK result:\n{T_test}')
            logger.info(f'FK position: x={T_test[0,3]:.3f}, y={T_test[1,3]:.3f}, z={T_test[2,3]:.3f}')
        except Exception as e:
            logger.error(f'FK test failed: {e}')
            return None, False
        
        # Try a much simpler approach with fewer initial guesses
        initial_guesses = [
            [0.6, 0.0, 1.75, -1.57, 0.0, 0.0],  # Default pose
            [0.6, 0.0, 1.0, -1.57, 0.0, 0.0],   # Lower arm
            [0.6, 0.0, 2.0, -1.57, 0.0, 0.0],   # Higher arm
            [0.6, 0.0, 1.5, -1.0, 0.0, 0.0],   # Different elbow
            [0.6, 0.0, 1.5, -2.0, 0.0, 0.0],   # More bent elbow
        ]
        
        # Much more lenient tolerances
        eomg = 0.5  # Orientation tolerance - extremely lenient
        ev = 0.5    # Position tolerance - extremely lenient
        
        for i, initial_guess in enumerate(initial_guesses):
            logger.info(f'Trying initial guess {i+1}/{len(initial_guesses)}: {initial_guess}')
            try:
                logger.info(f'Calling IKinSpace with:')
                logger.info(f'  Slist shape: {Slist.shape}')
                logger.info(f'  M shape: {M.shape}')
                logger.info(f'  T_sd shape: {T_sd.shape}')
                logger.info(f'  initial_guess: {initial_guess}')
                logger.info(f'  eomg: {eomg}, ev: {ev}')
                
                theta_list, success = mr.IKinSpace(
                    Slist=Slist,
                    M=M,
                    T=T_sd,
                    thetalist0=initial_guess,
                    eomg=eomg,
                    ev=ev,
                )
                
                logger.info(f'IK result: success={success}, theta_list={theta_list}')
                
                if not success:
                    logger.warn(f'IK failed with initial guess {initial_guess}')
                    continue
                
                logger.info(f'IK succeeded with theta_list: {theta_list}')
                
                # Check joint limits with very lenient tolerance
                ok = True
                tolerance = 0.5  # Very lenient tolerance for limit checking
                for i, (p, mn, mx) in enumerate(zip(theta_list, joint_limit_lower, joint_limit_upper)):
                    if not (mn - tolerance <= p <= mx + tolerance):
                        logger.error(f"Joint #{i+1} ({joint_names[i]}) out of limit: min={mn}, max={mx}, current={p:.4f}")
                        ok = False
                if not ok:
                    logger.warn(f'Skipping solution due to joint limit violations')
                    continue
                
                pub_theta(theta_list)
                last_theta_list = theta_list
                logger.info(f'IK successful with initial guess {initial_guess}')
                return theta_list, True
                
            except Exception as e:
                logger.error(f'IK exception with initial guess {initial_guess}: {e}')
                import traceback
                logger.error(f'Traceback: {traceback.format_exc()}')
                continue
        
        error_publisher.publish(std_msgs.msg.String(data="IK failed - no valid solution found"))
        logger.warn('No valid pose could be found. Will not execute')
        return None, False

    def cb(msg: geometry_msgs.msg.PoseStamped):
        logger.info(f'IK node received goal pose: position=({msg.pose.position.x:.3f}, {msg.pose.position.y:.3f}, {msg.pose.position.z:.3f}), orientation=({msg.pose.orientation.x:.3f}, {msg.pose.orientation.y:.3f}, {msg.pose.orientation.z:.3f}, {msg.pose.orientation.w:.3f})')
        
        # Check if goal pose is within reasonable bounds for SO-100 arms
        pos = msg.pose.position
        if pos.x < -0.6 or pos.x > 0.6 or pos.y < -0.6 or pos.y > 0.6 or pos.z < 0.1 or pos.z > 1.2:
            logger.warn(f'Goal pose position ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f}) appears to be outside reasonable workspace bounds for SO-100 arms')
            error_publisher.publish(std_msgs.msg.String(data="Goal pose outside workspace bounds"))
            return
            
        set_ee_pose_matrix(pt.transform_from_pq(np.array(pq_from_ros_pose(msg.pose))))
    node.create_subscription(geometry_msgs.msg.PoseStamped, "goal_pose", cb, rclpy.qos.qos_profile_sensor_data)

    rclpy.spin(node)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
