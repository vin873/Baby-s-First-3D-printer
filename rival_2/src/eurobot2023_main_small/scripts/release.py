#! /usr/bin/env python3

import rospy
from std_msgs.msg import Bool
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Pose
from geometry_msgs.msg import PoseStamped
from geometry_msgs.msg import Quaternion
from std_msgs.msg import Int32
from std_msgs.msg import Int32MultiArray
from geometry_msgs.msg import PoseArray
import numpy as np
from scipy.spatial.distance import euclidean
from geometry_msgs.msg import Quaternion
import math
from eurobot2023_main_small.srv import *

point = [[[[2.825, 1.825, 135], [2.725, 1.725, 135], [2.825, 1.825, 270], [2.725, 1.725, 270]] # B4
        , [[0.175, 0.175, 315], [0.275, 0.275, 315], [0.175, 0.175, 90], [0.275, 0.275, 90]]]  # B0
        ,[[[2.825, 0.175, 225], [2.725, 0.275, 225], [2.825, 0.175, 90], [2.725, 0.275, 90]]   # G3
        , [[0.175, 1.825, 45], [0.275, 1.725, 45], [0.175, 1.825, 270], [0.275, 1.725, 270]]]] # G0

robotNum = 0
side = 0
absAng = [0, 0]
fullness = [0, 0, 0, 0]
headAng = -45

ang = 0
robotAng = Quaternion()
robotPose = PoseArray()

def handle_release(req):
    publisher(req.num)
    return rreleaseResponse(robotPose)

def mission_callback(msg):
    for i in range(4):
        fullness[i] = msg.data[i+1]

def euler2quaternion(roll, pitch, yaw):
    """
    Convert an Euler angle to a quaternion.

    Input
    :param roll: The roll (rotation around x-axis) angle in radians.
    :param pitch: The pitch (rotation around y-axis) angle in radians.
    :param yaw: The yaw (rotation around z-axis) angle in radians.

    Output
    :return qx, qy, qz, qw: The orientation in quaternion [x,y,z,w] format
    """
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)

    return Quaternion(qx, qy, qz, qw)

def quaternion2euler(x, y, z, w):
        """
        Convert a quaternion into euler angles (roll, pitch, yaw)
        roll is rotation around x in radians (counterclockwise)
        pitch is rotation around y in radians (counterclockwise)
        yaw is rotation around z in radians (counterclockwise)
        """
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + y * y)
        roll_x = math.atan2(t0, t1)
     
        t2 = +2.0 * (w * y - z * x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch_y = math.asin(t2)
     
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        yaw_z = math.atan2(t3, t4)
     
        return yaw_z / math.pi * 180 # in radians

def listener():
    global side, robotNum
    rospy.init_node("release")
    side = rospy.get_param('side')
    robotNum = rospy.get_param('robot')
    rospy.Service('rrelease'+str(robotNum), rrelease, handle_release)
    rospy.Subscriber("/rdonefullness"+str(robotNum), Int32MultiArray, mission_callback)
    rospy.spin()

def publisher(num):
    global robotPose

    for i in range(4):
            if fullness[i] == 0:
                 empty = i
                 break
    # print(empty)
    if empty < 2:
        robotPose.header.frame_id = str(empty+1) + str(empty+2)
    elif empty == 2:
         robotPose.header.frame_id = '30'
    elif empty == 3:
         robotPose.header.frame_id = '01'
    robotPose.header.stamp = rospy.Time.now()

    for i in range(4):
        
        ang = (point[side][num][i][2] - empty*90) * math.pi / 180
        robotAng = euler2quaternion(0, 0, ang+headAng)
    
        pose = Pose()
        pose.position.x = point[side][num][i][0]
        pose.position.y = point[side][num][i][1]
        pose.orientation.x = robotAng.x
        pose.orientation.y = robotAng.y
        pose.orientation.z = robotAng.z
        pose.orientation.w = robotAng.w
        robotPose.poses.append(pose)

if __name__=="__main__":
    try:
        listener()

    except rospy.ROSInterruptException:
        pass
