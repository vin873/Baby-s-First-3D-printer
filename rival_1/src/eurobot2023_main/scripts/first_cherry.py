#! /usr/bin/env python3

import rospy
from std_msgs.msg import Bool
from std_msgs.msg import Int32MultiArray
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Pose
from geometry_msgs.msg import PoseWithCovarianceStamped
from geometry_msgs.msg import PoseArray
import numpy as np
from scipy.spatial.distance import euclidean
from eurobot2023_main.srv import *

cherries = [[[200, 800], [400, 800]], [[1350, 1800], [1650, 1800]], [[2600, 800], [2800, 800]], [[1350, 200], [1650, 200]], [[200, 1200], [400, 1200]], [[2600, 1200], [2800, 1200]]]

# subscribe cherries’ existence
cherryE = [1, 1, 1, 1]

# subscribe each enemy's pos
enemies = [[-1, -1],[-1, -1]]
# subscribe our robots pos
startPos = [[-1, -1],[-1, -1]]

tempMin = [99999, 99999]
tempSide = [[[-1, -1], [-1, -1]], [[-1, -1], [-1, -1]]]
used = []

robotNum = 0
side = 0
run_mode = ''
robotPose = PoseArray()
pickedSide = [[[-1, -1], [-1, -1]], [[-1, -1], [-1, -1]]]

def handle_cherry(req):
    publisher()
    return rcherryResponse(robotPose)

def startPos1_callback(msg):
    global startPos, absAng
    startPos[0][0] = msg.pose.pose.position.x * 1000
    startPos[0][1] = msg.pose.pose.position.y * 1000

def startPos2_callback(msg):
    global startPos
    startPos[1][0] = msg.pose.pose.position.x * 1000
    startPos[1][1] = msg.pose.pose.position.y * 1000

def enemiesPos1_callback(msg):
    global enemies
    enemies[0][0] = msg.pose.pose.position.x * 1000
    enemies[0][1] = msg.pose.pose.position.y * 1000

def enemiesPos2_callback(msg):
    global enemies
    enemies[1][0] = msg.pose.pose.position.x * 1000
    enemies[1][1] = msg.pose.pose.position.y * 1000

def cherryPublish():
    global robotPose, pickedSide
    side = pickedSide[robotNum]
    # if side != [[-1, -1], [-1, -1]]:
    num = '-'
    for i in cherries:
        if side[0] in i:
            if cherries.index(i) < 4:
                num = str(cherries.index(i))
            elif cherries.index(i) == 4:
                num = '0'
            elif cherries.index(i) == 5:
                num = '2'
    robotPose.header.frame_id = num
    robotPose.header.stamp = rospy.Time.now()

    for i in side:
        pose = Pose()
        pose.position.x = i[0] * 0.001
        pose.position.y = i[1] * 0.001
        pose.orientation.x = 0
        pose.orientation.y = 0
        pose.orientation.z = 0
        pose.orientation.w = 1
        robotPose.poses.append(pose)

def cherry_callback(msg):
    if msg.data:
        publisher()

def cherryE_callback(msg):
    # print(cherry)
    for i in range(4):
        cherryE[i] = msg.data[i]

def closerEnemy(target):
    global enemies
    speed = 0.9  # enemy/our
    min = 99999
    side = [-1, -1]
    for enemy in enemies:
        if enemy != [-1, -1]:
            for i in target:
                if min > euclidean(enemy, i) / speed:
                    min = euclidean(enemy, i) / speed
                    side = list(i)
    return min

def where2suck(pos, num):
    global tempMin, tempSide, used, cherryE
    tempMin[num] = 99999
    tempChoice = [-1, -1]
    tempSide[num] = [[-1, -1], [-1, -1]]

    for sides in range(6):
        if (sides < 4 and cherryE[sides] != 0) or (sides == 4 and cherryE[0] != 0) or (sides == 5 and cherryE[2] != 0):
            # print(sides)
            for cherrySide in cherries[sides]:
                if sides == 0 or sides == 4:
                    temp = list(cherries[0]) + list(cherries[4])
                elif sides == 2 or sides == 5:
                    temp = list(cherries[2]) + list(cherries[5])
                else:
                    temp = list(cherries[sides])
                if (sides < 4 and cherrySide not in used) or (sides == 4 and cherries[0][0] not in used) or (sides == 5 and cherries[2][0] not in used):
                    dis2cherry = euclidean(pos, cherrySide) - closerEnemy(temp)
                    if dis2cherry > 0 and closerEnemy(temp) <= 300:
                        continue
                    if tempMin[num] > dis2cherry:
                        tempMin[num] = dis2cherry
                        tempSide[num] = list(cherries[sides])
                        tempChoice = list(cherrySide)
    for i in cherries:
        if tempChoice in i:
            if euclidean(pos, tempChoice) > euclidean(pos, i[int(not bool(i.index(tempChoice)))]):
                tempChoice = list(i[int(not bool(i.index(tempChoice)))])
            if tempChoice == tempSide[num][1]:
                tempSide[num][0], tempSide[num][1] = tempSide[num][1], tempSide[num][0]
            break

    return tempSide[num]

def listener():
    global side, robotNum, run_mode
    rospy.init_node("first_cherry")
    side = rospy.get_param('side')
    robotNum = rospy.get_param('robot')
    run_mode = rospy.get_param('run_mode')
    rospy.Service('rcherry'+str(robotNum), rcherry, handle_cherry)
    rospy.Subscriber("/cherryExistence", Int32MultiArray, cherryE_callback)
    if run_mode == 'run':
        rospy.Subscriber("/rival1/ekf_pose", PoseWithCovarianceStamped, startPos1_callback)
        rospy.Subscriber("/rival2/ekf_pose", PoseWithCovarianceStamped, startPos2_callback)
        rospy.Subscriber("/robot1/ekf_pose", PoseWithCovarianceStamped, enemiesPos1_callback)
        rospy.Subscriber("/robot2/ekf_pose", PoseWithCovarianceStamped, enemiesPos2_callback)
    elif run_mode == 'sim':
        rospy.Subscriber("/rival1/odom", Odometry, startPos1_callback)
        rospy.Subscriber("/rival2/odom", Odometry, startPos2_callback)
        rospy.Subscriber("/robot1/odom", Odometry, enemiesPos1_callback)
        rospy.Subscriber("/robot2/odom", Odometry, enemiesPos2_callback)
    rospy.spin()

def publisher():
    # print(cherryE)
    global robotPose, used, pickedSide
    for robot in startPos:
        if robot != [-1, -1]:
            pickedSide[startPos.index(robot)] = where2suck(robot, startPos.index(robot))

    if tempMin[0] < tempMin[1]:
        used = pickedSide[0]
        if startPos[1] != [-1, -1]:
            pickedSide[1] = [[-1, -1], [-1, -1]]
            tempMin[1] = 99999
            pickedSide[1] = where2suck(startPos[1], 1)
    else:
        used = pickedSide[1]
        if startPos[0] != [-1, -1]:
            pickedSide[0] = [[-1, -1], [-1, -1]]
            tempMin[0] = 99999
            pickedSide[0] = where2suck(startPos[0], 0)
    
    robotPose.poses = []
    # print(pickedSide)
    cherryPublish()

if __name__=="__main__":
    try:
        listener()

    except rospy.ROSInterruptException:
        pass
