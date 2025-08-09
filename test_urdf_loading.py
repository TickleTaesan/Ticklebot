#!/usr/bin/env python3

from pathlib import Path
from ament_index_python import get_package_share_directory
from mr_urdf_loader import loadURDF
import modern_robotics as mr
import numpy as np

# Test URDF loading for both arms
urdf_name = str(Path(get_package_share_directory("astra_description")) / "urdf" / "astra_description_rel.urdf")

print(f"Loading URDF: {urdf_name}")

# Test left arm
try:
    print("\n=== Testing Left Arm ===")
    joint_names_left = ["joint_l1", "joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6"]
    eef_link_left = "link_lee_teleop"
    
    M_left, Slist_left, Blist_left, Mlist_left, Glist_left, robot_left = loadURDF(
        urdf_name, 
        eef_link_name=eef_link_left, 
        actuated_joint_names=joint_names_left
    )
    
    print(f"Left arm M matrix:\n{M_left}")
    print(f"Left arm Slist shape: {Slist_left.shape}")
    print(f"Left arm joint limits:")
    for joint_name in joint_names_left:
        joint = robot_left.joint_map[joint_name]
        print(f"  {joint_name}: [{joint.limit.lower}, {joint.limit.upper}]")
    
    # Test forward kinematics
    theta_test = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    T_fk = mr.FKinSpace(M_left, Slist_left, theta_test)
    print(f"Forward kinematics at zero config:\n{T_fk}")
    
except Exception as e:
    print(f"Left arm error: {e}")

# Test right arm
try:
    print("\n=== Testing Right Arm ===")
    joint_names_right = ["joint_r1", "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6"]
    eef_link_right = "link_ree_teleop"
    
    M_right, Slist_right, Blist_right, Mlist_right, Glist_right, robot_right = loadURDF(
        urdf_name, 
        eef_link_name=eef_link_right, 
        actuated_joint_names=joint_names_right
    )
    
    print(f"Right arm M matrix:\n{M_right}")
    print(f"Right arm Slist shape: {Slist_right.shape}")
    print(f"Right arm joint limits:")
    for joint_name in joint_names_right:
        joint = robot_right.joint_map[joint_name]
        print(f"  {joint_name}: [{joint.limit.lower}, {joint.limit.upper}]")
    
    # Test forward kinematics
    theta_test = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    T_fk = mr.FKinSpace(M_right, Slist_right, theta_test)
    print(f"Forward kinematics at zero config:\n{T_fk}")
    
except Exception as e:
    print(f"Right arm error: {e}")

print("\nURDF loading test complete!") 