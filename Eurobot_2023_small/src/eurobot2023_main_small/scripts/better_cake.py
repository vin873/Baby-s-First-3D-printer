#! /usr/bin/env python3

import rospy
from std_msgs.msg import Bool
from std_msgs.msg import Int16MultiArray
from std_msgs.msg import Int32MultiArray
from geometry_msgs.msg import Pose
from geometry_msgs.msg import Point
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseArray
from geometry_msgs.msg import Quaternion
import math
import numpy as np
from scipy.spatial.distance import euclidean
from itertools import permutations
from obstacle_detector.msg import Obstacles
from eurobot2023_main_small.srv import *

# subscribe each cake's position
browns = [[1125, 725], [1125, 1275], [1875, 725], [1875, 1275]]
yellows = [[775, 225], [775, 1775], [2225, 225], [2225, 1775]]
pinks = [[575, 225], [575, 1775], [2425, 225], [2425, 1775]]
allCakes = [list(browns), list(yellows), list(pinks)]

tempAllCakes = []
for i in range(3):
    tempAllCakes.append([[[-1, -1], [-1, -1], [-1, -1], [-1, -1]], [[-1, -1], [-1, -1], [-1, -1], [-1, -1]]])

# subscribe each enemy's pos
enemies = [[-1, -1], [-1, -1]]
# subscribe our robots pos
startPos = [[-1, -1], [-1, -1]]
absAng = [0, 0]

picked = [[[-1, -1],  [-1, -1],  [-1, -1]], [[-1, -1],  [-1, -1],  [-1, -1]]]
lastpicked = []
cakeNum = Int32MultiArray()
cakeCheckPos = [-1, -1]
used = []
adjustedNum = []
got = [[0, 0, 0], [0, 0, 0]]  # brown, yellow, pink
tempGot = [[0, 0, 0], [0, 0, 0]]
fullness = [[0, 0, 0, 0], [0, 0, 0, 0]]
tempFull = [[0, 0, 0, 0], [0, 0, 0, 0]]
used_changed = -1
currMin = [99999, 99999]
minAngle = 360
headAng = -45
camAng = 90
outAngle = [[0, 0, 0], [0, 0, 0]]
dockDis = 255
cakeDis = 95

robotNum = 0
side = 0
run_mode = ''
position = [-1, -1]
preposition = [-1, -1]
quaternion = Quaternion()
robotPose = PoseArray()

def handle_cake(req):
    global allCakes
    if (req.num):
        allCakes[math.floor(used_changed/4)][int(used_changed)%4] = [-1, -1]
    publisher()
    return cakeResponse(robotPose)

def startPos1_callback(msg):
    global startPos, absAng, headAng
    startPos[0][0] = msg.pose.pose.position.x * 1000
    startPos[0][1] = msg.pose.pose.position.y * 1000
    absAng[0] = quaternion2euler(msg.pose.pose.orientation.x, msg.pose.pose.orientation.y, msg.pose.pose.orientation.z, msg.pose.pose.orientation.w) - headAng

def startPos2_callback(msg):
    global startPos, absAng, headAng
    startPos[1][0] = msg.pose.pose.position.x * 1000
    startPos[1][1] = msg.pose.pose.position.y * 1000
    absAng[1] = quaternion2euler(msg.pose.pose.orientation.x, msg.pose.pose.orientation.y, msg.pose.pose.orientation.z, msg.pose.pose.orientation.w) - headAng

def enemiesPos1_callback(msg):
    global enemies
    enemies[0][0] = msg.pose.pose.position.x * 1000
    enemies[0][1] = msg.pose.pose.position.y * 1000

def enemiesPos2_callback(msg):
    global enemies
    enemies[1][0] = msg.pose.pose.position.x * 1000
    enemies[1][1] = msg.pose.pose.position.y * 1000

def enemies_callback(msg):
    global enemies
    if len(msg.circles) >= 1:
        enemies[0][0] = msg.circles[0].center.x * 1000
        enemies[0][1] = msg.circles[0].center.y * 1000
    else:
        enemies[0][0] = -1
        enemies[0][1] = -1
    if len(msg.circles) >= 2:
        enemies[1][0] = msg.circles[1].center.x * 1000
        enemies[1][1] = msg.circles[1].center.y * 1000
    else:
        enemies[1][0] = -1
        enemies[1][1] = -1

def adjust_callback(msg):
    global adjustedNum, allCakes
    if [msg.x, msg.y] == [-1, -1]:
        allCakes[math.floor(msg.z/4)][int(msg.z)%4] = [-1, -1]
    else:
        allCakes[math.floor(msg.z/4)][int(msg.z)%4] = [msg.x * 1000, msg.y * 1000]
    adjustedNum.append(msg.z)

def got_callback(msg):
    global got
    for i in range(3):
        got[robotNum][i] = msg.data[i]

def full_callback(msg):
    global fullness
    for i in range(4):
        if msg.data[i+1]:
            fullness[robotNum][i] = 999

def tPoint(mode, pos, target):
    # print(pos ,target)
    if target == [-1, -1]:
        return [-1, -1]
    else:
        if mode == 'd':
            dis = dockDis
        elif mode == 'c':
            dis = cakeDis
        point = [-1, -1]
        if target[0] == pos[0]:
            if target[1] > pos[1]:
                point = [target[0], target[1]-dis]
            elif target[1] < pos[1]:
                point = [target[0], target[1]+dis]
        elif target[1] == pos[1]:
            if target[0] > pos[0]:
                point = [target[0]-dis, target[1]]
            elif target[0] < pos[0]:
                point = [target[0]+dis, target[1]]
        else:
            if target[0] > pos[0]:
                x = target[0] - pos[0]
            else:
                x = pos[0] - target[0]
            if target[1] > pos[1]:
                y = target[1]-pos[1]
            else:
                y = pos[1]-target[1]
            if target[1] > pos[1]:
                point[1] = target[1] - dis*math.sin(math.atan(y/x))
            else:
                point[1] = target[1] + dis*math.sin(math.atan(y/x))
            if target[0] > pos[0]:
                point[0] = target[0] - dis*math.cos(math.atan(y/x))
            else:
                point[0] = target[0] + dis*math.cos(math.atan(y/x))
        return point

def robotPublish(num, color, count):
    global robotPose, tempFull, cakeNum

    c = '?'
    if color == 0:
        c = 'b'
    elif color == 1:
        c = 'y'
    elif color == 2:
        c = 'p'

    robotPose.header.frame_id += c
    for full in tempFull[num]:
        if full == count + 1:
            door = int(tempFull[num].index(full))
            if door == 4:
                door = 0
            robotPose.header.frame_id += str(door)
    robotPose.header.stamp = rospy.Time.now()

    for i in range(3):
        if cakeCheckPos in allCakes[i]:
            cakeNum.data.append(4*i+allCakes[i].index(cakeCheckPos))

    pose = Pose()
    pt = tPoint('d', preposition, position)
    # print(pt)
    pose.position.x = pt[0] * 0.001
    pose.position.y = pt[1] * 0.001
    pose.orientation.x = quaternion.x
    pose.orientation.y = quaternion.y
    pose.orientation.z = quaternion.z
    pose.orientation.w = quaternion.w
    robotPose.poses.append(pose)
    
    pose2 = Pose()
    pt = tPoint('c', preposition, position)
    pose2.position.x = pt[0] * 0.001
    pose2.position.y = pt[1] * 0.001
    pose2.orientation.x = quaternion.x
    pose2.orientation.y = quaternion.y
    pose2.orientation.z = quaternion.z
    pose2.orientation.w = quaternion.w
    robotPose.poses.append(pose2)

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

def howLong(pos):
    dis = 0
    for i in range(len(pos) - 1):
        if pos[i] != [-1, -1] and pos[i+1] != [-1, -1]:
            dis += euclidean(pos[i], pos[i+1])
    return dis

def closerEnemy(target):
    global enemies
    speed = 0.9  # enemy/our
    min = 99999
    for enemy in range(2):
        if enemies[enemy] != [-1, -1]:
            if min > euclidean(enemies[enemy], target) / speed:
                min = euclidean(enemies[enemy], target) / speed
    return min

def whatColorGet(pos, num):
    global tempGot
    for i in range(3):
        if pos in allCakes[i]:
            tempGot[num][i] = 1

def safest(pos, num):
    tempColorMin = 99999
    tempColorPicked =  [-1, -1]
    for i in range(3):
        if tempGot[num][i] != 1:
            for target in allCakes[i]:
                # print("ss", num, target)
                if target not in used and target != [-1, -1]:
                    if tempColorMin > euclidean(pos, target) - closerEnemy(target):
                        tempColorMin = euclidean(pos, target) - closerEnemy(target)
                        tempColorPicked = list(target)
    return tempColorPicked

def where2go(pos, num):
    global picked, enemies, currMin, fullness, absAng, minAngle, used, outAngle, tempAllCakes, allCakes, tempGot, headAng, tempFull
    
    # print(allCakes)
    # print(got)
    tempGot[num] = list(got[num])
    tempAllCakes = []
    for i in range(3):
        tempAllCakes.append([[[-1, -1], [-1, -1], [-1, -1], [-1, -1]], [[-1, -1], [-1, -1], [-1, -1], [-1, -1]]])

    # tempGot = list(got)

    if got[num] == [1, 1, 1]:
        return []
    tempMin = 99999
    for enemy in range(2):
        if enemies[enemy] != [-1, -1]:
            for i in range(3):
                if got[num][i] != 1:
                    for target in range(4):
                        if euclidean(pos, allCakes[i][target]) < euclidean(enemies[enemy], allCakes[i][target]) and allCakes[i][target] != [-1, -1]:
                            tempAllCakes[i][num][target] = list(allCakes[i][target])

    for i in used:
        for j in range(3):
            if i in tempAllCakes[j][num]:
                tempAllCakes[j][num][tempAllCakes[j][num].index(i)] = [-1, -1]

    for i in range(3):
        if got[num][i] == 1:
            tempAllCakes[i][num] = [[99999, 99999], [99999, 99999], [99999, 99999], [99999, 99999]]

    orders = list(permutations([tempAllCakes[0][num], tempAllCakes[1][num], tempAllCakes[2][num]]))
    # print(tempAllCakes, num, picked[num])

    for order in orders:
        for i in order[0]:
            for j in order[1]:
                for k in order[2]:
                    if order[0] == [[99999, 99999], [99999, 99999], [99999, 99999], [99999, 99999]]:
                        i = pos
                    if order[1] == [[99999, 99999], [99999, 99999], [99999, 99999], [99999, 99999]]:
                        j = i
                    if order[2] == [[99999, 99999], [99999, 99999], [99999, 99999], [99999, 99999]]:
                        k = j
                    tempDis = 0
                    enemyDis = 0
                    if i != [-1, -1] and j != [-1, -1] and k != [-1, -1]:
                        tempDis = euclidean(pos, i) + euclidean(i, j)
                        enemyDis = closerEnemy(j)
                        if tempDis < enemyDis and tempDis < tempMin:
                            tempDis += euclidean(j, k)
                            enemyDis = closerEnemy(k)
                            if tempDis < enemyDis and tempDis < tempMin:
                                tempMin = tempDis
                                picked[num] = [i, j, k]
                                for a in picked[num]:
                                    if a == pos:
                                        picked[num][picked[num].index(a)] = [-1, -1]
                                # print(num, picked[num])
                                for o in order:
                                    if o == [[99999, 99999], [99999, 99999], [99999, 99999], [99999, 99999]]:
                                        picked[num][order.index(o)] =  [-1, -1]

    # print("pp", num, picked[num])

    if picked[num] == [[-1, -1], [-1, -1], [-1, -1]]:
        # print("so safe", num)
        picked[num][0] = safest(pos, num)
        whatColorGet(picked[num][0], num)
        picked[num][1] = safest(picked[num][0], num)
        whatColorGet(picked[num][1], num)
        picked[num][2] = safest(picked[num][1], num)
        whatColorGet(picked[num][2], num)
        if [-1, -1] in picked[num]:
            picked[num].remove([-1, -1])
        minDis = 99999
        safeOrders = list(permutations(picked[num]))
        for order in safeOrders:
            order = list(order)
            order.insert(0, pos)
            if minDis > howLong(order):
                minDis = howLong(order)
                order.remove(pos)
                picked[num] = list(order)
        for i in range(3):
            if len(picked[num]) < 3:
                picked[num].append([-1, -1])

    for b in range(3):
        for c in range(2-b):
            if picked[num][b] == picked[num][b+1+c]:
                picked[num][b+1+c] = [-1, -1]

    for b in range(2):
        if picked[num][b] == [-1, -1]:
            picked[num][b], picked[num][b+1] = picked[num][b+1], picked[num][b]
    if picked[num][0] == [-1, -1]:
        picked[num][0], picked[num][1] = picked[num][1], picked[num][0]

    if picked[num]:
        anglePos = list(pos)
        tempAng = list(absAng)
        tempFull[num] = list(fullness[num])
        wherePrePos = list(pos)
        for j in range(3):
            minAngle = 360
            minAngleNum = -1
            wherePrePos = list(tPoint('c', wherePrePos, picked[num][j]))
            tAngle = (np.rad2deg(np.arctan2(picked[num][j][1] - wherePrePos[1], picked[num][j][0] - wherePrePos[0])) - tempAng[num] + 360) % 360
            tAngles = [999, 999, 999, 999]
            for i in range(4):
                if tempFull[num][i] == 0:
                    tAngles[i] = (tAngle - i * 90 + 360 - headAng) % 360
            for i in tAngles:
                if abs(i) < abs(minAngle):
                    minAngle = i
                    minAngleNum = tAngles.index(i)
            outAngle[num][j] = minAngle + tempAng[num] + 2*headAng
            # print(outAngle[num], tempAng[num], tAngles, minAngle, tAngle)
            tempAng[num] = outAngle[num][j] - headAng
            tempFull[num][minAngleNum] = j+1
            anglePos = picked[num][j]
        # print("tF", num, tempFull[num])
    # print(outAngle[robotNum][0], absAng[robotNum])

    currMin[num] = tempMin

def listener():
    global side, robotNum, run_mode
    rospy.init_node("better_cake")
    side = rospy.get_param('side')
    robotNum = rospy.get_param('robot')
    run_mode = rospy.get_param('run_mode')
    rospy.Subscriber('adjustCake', Point, adjust_callback)
    rospy.Subscriber('gotcake'+str(robotNum), Int32MultiArray, got_callback)
    rospy.Subscriber('donefullness'+str(robotNum), Int16MultiArray, full_callback)
    rospy.Service('cake'+str(robotNum), cake, handle_cake)
    if run_mode == 'run':
        rospy.Subscriber("/robot1/ekf_pose", PoseWithCovarianceStamped, startPos1_callback)
        rospy.Subscriber("/robot2/ekf_pose", PoseWithCovarianceStamped, startPos2_callback)
        rospy.Subscriber("/RivalObstacle", Obstacles, enemies_callback)
    elif run_mode == 'sim':
        rospy.Subscriber("/robot1/odom", Odometry, startPos1_callback)
        rospy.Subscriber("/robot2/odom", Odometry, startPos2_callback)
        rospy.Subscriber("/rival1/odom", Odometry, enemiesPos1_callback)
        rospy.Subscriber("/rival2/odom", Odometry, enemiesPos2_callback)
    rospy.spin()

def publisher():
    global quaternion, enemies, startPos, currMin, picked, used, robotNum, robotPose, tempFull, minAngle, tempAllCakes, outAngle, position, quaternion, tempGot, preposition, used_changed, cakeNum, cakeCheckPos, lastpicked
    color = -1

    picked = [[[-1, -1],  [-1, -1],  [-1, -1]], [[-1, -1],  [-1, -1],  [-1, -1]]]
    
    cakeNum.data = []
    used = []
    tempGot[robotNum] = list(got[robotNum])
    tempFull = [[0, 0, 0, 0], [0, 0, 0, 0]]
    currMin = [99999, 99999]
    minAngle = 360
    outAngle = [[0, 0, 0], [0, 0, 0]]
    position = [-1, -1]
    quaternion = Quaternion()
    robotPose = PoseArray()
    tempAllCakes = []
    for i in range(3):
        tempAllCakes.append([[[-1, -1], [-1, -1], [-1, -1], [-1, -1]], [[-1, -1], [-1, -1], [-1, -1], [-1, -1]]])

    if enemies[0] ==  [-1, -1] and enemies[1] ==  [-1, -1]:
        enemies[0] = [99999, 99999]

    for robot in range(2):
        if robot != [-1, -1]:
            where2go(startPos[robot], robot)

    if currMin[0] < currMin[1]:
        used = picked[0]
        if startPos[1] != [-1, -1]:
            picked[1] = [[-1, -1], [-1, -1], [-1, -1]]
            currMin[1] = 99999
            where2go(startPos[1], 1)
    else:
        used = picked[1]
        if startPos[0] != [-1, -1]:
            picked[0] = [[-1, -1], [-1, -1], [-1, -1]]
            currMin[0] = 99999
            where2go(startPos[0], 0)

    # print("ppp", picked[robotNum])

    if startPos[robotNum] != [-1, -1]:
        robotPose.poses=[]
        robotPose.header.frame_id = ''
        flag = 0
        count = 0
        for pos in range(3):
            if picked[robotNum][pos] != [-1, -1]:
                if flag:
                    position = [-1, -1]
                    color = -1
                    robotPublish(robotNum, color, pos)
                else:
                    if count == 0:
                        preposition[0] = startPos[robotNum][0]
                        preposition[1] = startPos[robotNum][1]
                    else:
                        preposition = list(tPoint('c', preposition, position))
                    for axis in range(2):                    
                        for i in range(3):
                            if picked[robotNum][pos] in allCakes[i]:
                                color = i
                        cakeCheckPos = list(picked[robotNum][pos])
                        position[axis] = picked[robotNum][pos][axis]
                    quaternion = euler2quaternion(0, 0, outAngle[robotNum][pos] * math.pi / 180)
                    robotPublish(robotNum, color, pos)
                    count += 1
                    for i in range(3):
                        if picked[robotNum][pos] in allCakes[i] and 4*i+allCakes[i].index(picked[robotNum][pos]) in adjustedNum:
                            used_changed = 4 * i + allCakes[i].index(picked[robotNum][pos])
                            robotPose.poses[2*(count-1)+1].position.x = -777
                            camtAng = (np.rad2deg(np.arctan2(picked[robotNum][pos][1] - preposition[1]*1000, picked[robotNum][pos][0] - preposition[0]*1000)) + 360 - camAng) % 360
                            quat = euler2quaternion(0, 0, camtAng*math.pi/180)
                            robotPose.header.frame_id = robotPose.header.frame_id[:-1]
                            robotPose.header.frame_id += '!'
                            robotPose.poses[2*(count-1)].orientation.x = quat.x
                            robotPose.poses[2*(count-1)].orientation.y = quat.y
                            robotPose.poses[2*(count-1)].orientation.z = quat.z
                            robotPose.poses[2*(count-1)].orientation.w = quat.w
                            flag = 1
                            break
        for i in range(3-count):
            position = [-1, -1]
            color = -1
            robotPublish(robotNum, color, pos)

        for i in range(3):
            if len(cakeNum.data) < 3:
                cakeNum.data.append(-1)

        while len(cakeNum.data) > 3:
            cakeNum.data.pop()
        
        pub = rospy.Publisher('cakeNum'+str(robotNum), Int32MultiArray, queue_size=1000)
        rospy.sleep(0.3)
        pub.publish(cakeNum)

        if lastpicked != picked[robotNum]:
            print("picked", picked[robotNum], robotPose.header.frame_id, cakeNum.data)
            lastpicked = picked[robotNum]
        
        # pub_obs = rospy.Publisher('cake_camera', PoseArray, queue_size=1000)
        # obs_PA = PoseArray()
        # obs_PA.header.frame_id = 'sample'
        # obs_PA.header.stamp = rospy.Time.now()
        # not_obs_num = []
        # for cc in range(3):
        #     for rp in range(2):
        #         for pc in range(3):
        #             if picked[rp][pc] in allCakes[cc]:
        #                 not_obs_num.append(4*cc+allCakes[cc].index(picked[rp][pc]))
        # # print(not_obs_num)
        # for i in range(3):
        #     for j in range(4):
        #         if 4*i+j not in not_obs_num:
        #             obs_pose = Pose()
        #             obs_pose.position.x = allCakes[i][j][0] / 1000
        #             obs_pose.position.y = allCakes[i][j][1] / 1000
        #             obs_PA.poses.append(obs_pose)
        # rospy.sleep(0.3)
        # pub_obs.publish(obs_PA)

        # print(robotPose.header.frame_id)
        # print(fullness[robotNum])
        # print(outAngle[robotNum])
        # for i in range(6): 
        #     print(i, " : [", robotPose.poses[i].position.x, robotPose.poses[i].position.y, quaternion2euler(robotPose.poses[i].orientation.x, robotPose.poses[i].orientation.y, robotPose.poses[i].orientation.z, robotPose.poses[i].orientation.w), "]")

if __name__=="__main__":
    try:
        listener()

    except rospy.ROSInterruptException:
        pass