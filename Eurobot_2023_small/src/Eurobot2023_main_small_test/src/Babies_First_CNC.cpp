#include <ros/ros.h>
#include <std_msgs/Bool.h>
#include <std_msgs/String.h>
#include <std_msgs/Int32.h>
#include <std_msgs/Int32MultiArray.h>
#include <std_msgs/Float32.h>
#include <geometry_msgs/PoseStamped.h>
#include <nav_msgs/Odometry.h>
#include <geometry_msgs/PoseArray.h>
#include <tf/transform_datatypes.h>

#include <iostream>
#include <stdlib.h>
#include <math.h>

using namespace std;

enum MissionOrder
{
    CAKE = 0,
    CHERRY,
    BASKET,
    RELEASE,
    STEAL,
    HOME
};

enum Status
{
    SETUP = 0,
    RUN,
    FINISH
};

enum Mode
{
    EMERGENCY = 0,
    NORMAL
};

// Global Variables

int side = 1; // 0 for blue, 1 for green
int robot = 1; // 0 for big, 1 for small
int cakeNum = 0;
int gotCake = 0;
int cherryNum = 0;
int now_Mission = CAKE;
int now_Status = SETUP;
int now_Mode = NORMAL;

double myPos_x;
double myPos_y;
double myOri_z;
double myOri_w;
double enemiesPos_x;
double enemiesPos_y;
double enemiesOri_z;
double enemiesOri_w;
double mission_timeOut;
double startMissionTime;
double driving_timeOut;
double startDriveTime;
double go_home_time = 90.0;

bool start = false;
bool moving = false;
bool doing = false;
bool arrived = false;
bool route_failed = false;
bool mission_success = false;
bool got_cake_picked = false;
bool got_cherry_picked = false;
bool going_home = false;
bool fullness[4] = {0, 0, 0, 0}; // {0, 90, 180, 270}
bool plates[5] = {0, 0, 0, 0}; // x y
bool printOnce = false;

string id;
string id_frame;

std_msgs::Bool cake;
std_msgs::Bool cherry;
std_msgs::Bool release;
std_msgs::Bool finish_mission;
std_msgs::String missionStr;

geometry_msgs::PoseStamped cake_picked[3];
geometry_msgs::PoseStamped cherry_picked[2];
geometry_msgs::PoseStamped basket_point[2];
geometry_msgs::PoseStamped release_point[2];
geometry_msgs::PoseStamped home;

class mainProgram
{
public:

    void poseStamped_set(geometry_msgs::PoseStamped &pos, float x, float y, float z, float w)
    {
        pos.header.frame_id = id_frame;
        pos.header.stamp = ros::Time::now();
        pos.pose.position.x = x;
        pos.pose.position.y = y;
        pos.pose.orientation.x = 0.0;
        pos.pose.orientation.y = 0.0;
        pos.pose.orientation.z = z;
        pos.pose.orientation.w = w;
    }

    void pcake_callback(const geometry_msgs::PoseArray::ConstPtr &msg)
    {
        id = msg->header.frame_id;
        for (int i = 0;i < 3;i++)
        {
            poseStamped_set(cake_picked[i], msg->poses[i].position.x, msg->poses[i].position.y, msg->poses[i].orientation.z, msg->poses[i].orientation.w);
        }
        got_cake_picked = true;
        // ROS_INFO("cake_picked got!");
    }

    void pcherry_callback(const geometry_msgs::PoseArray::ConstPtr &msg)
    {
        for (int i = 0;i < 2;i++)
        {
            poseStamped_set(cherry_picked[i], msg->poses[i].position.x, msg->poses[i].position.y, msg->poses[i].orientation.z, msg->poses[i].orientation.w);
        }
        got_cherry_picked = true;
        // ROS_INFO("cherry_picked got!");
    }

    void finishall_callback(const std_msgs::Bool::ConstPtr &msg)
    {
        finish_mission.data = msg->data;
    }

    void nav_callback(const std_msgs::Bool::ConstPtr &msg)
    {
        moving = false;
        if (msg->data)
        {
            ROS_INFO("Arrived!");
            arrived = true;
        }
        else
        {
            route_failed = true;
            ROS_ERROR("Failed to reach goal!");
        }
    }

    void done_fullness_callback(const std_msgs::Int32MultiArray::ConstPtr &msg)
    {
        doing = false;
        if (msg->data.at(0))
        {
            mission_success = true;
            ROS_INFO("Mission finished!");
        }
        else
        {
            ROS_ERROR("Mission failed!");
        }
        for (int i = 1;i < 5;i++)
        {
            fullness[i-1] = msg->data.at(i);
        }
    }

    void start_callback(const std_msgs::Bool::ConstPtr &msg)
    {
        if (msg->data)
        {
            start = true;
        }
    }

    void cake_callback(const geometry_msgs::PoseArray::ConstPtr &msg)
    {
        ROS_INFO("Cake!");
    }

    void cherry_callback(const std_msgs::Int32MultiArray::ConstPtr &msg)
    {
        ROS_INFO("Cherry!");
    }

    void myPos_callback(const nav_msgs::Odometry::ConstPtr &msg)
    {
        myPos_x = msg->pose.pose.position.x;
        myPos_y = msg->pose.pose.position.y;
        myOri_z = msg->pose.pose.orientation.z;
        myOri_w = msg->pose.pose.orientation.w;
    }

    void enemiesPos_callback(const geometry_msgs::PoseStamped::ConstPtr &msg)
    {
        enemiesPos_x = msg->pose.position.x;
        enemiesPos_y = msg->pose.position.y;
        enemiesOri_z = msg->pose.orientation.z;
        enemiesOri_w = msg->pose.orientation.w;
    }
    
    ros::NodeHandle nh;

    // main
    ros::Publisher _better_cake = nh.advertise<std_msgs::Bool>("cake"+to_string(robot), 1000);
    ros::Publisher _first_cherry = nh.advertise<std_msgs::Bool>("cherry"+to_string(robot), 1000);
    ros::Publisher _release = nh.advertise<std_msgs::Bool>("release"+to_string(robot), 1000);
    ros::Publisher _ifinish = nh.advertise<std_msgs::Bool>("finishall", 1000);
    ros::Subscriber _cake_picked = nh.subscribe<geometry_msgs::PoseArray>("cake_picked"+to_string(robot), 1000, &mainProgram::pcake_callback, this);
    ros::Subscriber _cherry_picked = nh.subscribe<geometry_msgs::PoseArray>("cherry_picked"+to_string(robot), 1000, &mainProgram::pcherry_callback, this);
    ros::Subscriber _finishall = nh.subscribe<std_msgs::Bool>("finishall", 1000, &mainProgram::finishall_callback, this);

    // chassis
    ros::Publisher _where2go = nh.advertise<geometry_msgs::PoseStamped>("/robot"+to_string(robot+1)+"/nav_goal", 1000);
    ros::Subscriber _finishornot = nh.subscribe<std_msgs::Bool>("/robot"+to_string(robot+1)+"/finishornot", 1000, &mainProgram::nav_callback, this);

    // mission
    ros::Publisher _mission = nh.advertise<std_msgs::String>("mission"+to_string(robot), 1000);
    ros::Subscriber _donefullness = nh.subscribe<std_msgs::Int32MultiArray>("donefullness"+to_string(robot), 1000, &mainProgram::done_fullness_callback, this);
    ros::Subscriber _startornot = nh.subscribe<std_msgs::Bool>("startornot", 1000, &mainProgram::start_callback, this);

    // basket
    ros::Publisher _point_home = nh.advertise<std_msgs::Int32>("point_home", 1000);

    // camera
    ros::Publisher _turnonornot = nh.advertise<std_msgs::Bool>("turnonornot", 1000);
    ros::Subscriber _allCakes = nh.subscribe<geometry_msgs::PoseArray>("allCakes", 1000, &mainProgram::cake_callback, this);
    ros::Subscriber _cherryExistence = nh.subscribe<std_msgs::Int32MultiArray>("cherryExistence", 1000, &mainProgram::cherry_callback, this);

    // locate
    ros::Publisher _obstacles = nh.advertise<geometry_msgs::PoseArray>("obstacles", 1000);
    ros::Subscriber _myPos = nh.subscribe<nav_msgs::Odometry>("/robot"+to_string(robot+1)+"/odom", 1000, &mainProgram::myPos_callback, this);
    ros::Subscriber _enemiesPos = nh.subscribe<geometry_msgs::PoseStamped>("enemiesPos", 1000, &mainProgram::enemiesPos_callback, this);
};

int main(int argc, char **argv)
{
    // ROS initial
    ros::init(argc, argv, "Babies_First_CNC");

    mainProgram mainClass;

    mainClass.nh.getParam("robot", robot);
    mainClass.nh.getParam("side", side);

    ros::Time initialTime = ros::Time::now();
    ros::Time cakeTime = ros::Time::now();
    
    // Main Node Update Frequency
    ros::Rate rate(20);

    while (ros::ok())
    {
        switch (now_Mode)
        {
        case NORMAL:
            switch (now_Status)
            {
            case SETUP:

                if (!printOnce)
                {
                    ROS_WARN("SETUP");
                    cake.data = true;
                    cakeTime = ros::Time::now();
                    cherry.data = false;
                    release.data = false;
                    finish_mission.data = false;
                    mainClass.poseStamped_set(basket_point[0], 0.225, 0.225, 0, 1);
                    mainClass.poseStamped_set(basket_point[1], 0.420, 1.775, 0, 1);
                    mainClass.poseStamped_set(home, 1.125, 0.420, 0, 1);

                    mainClass.poseStamped_set(release_point[0], 0.225, 1.775, 0, 1);
                    mainClass.poseStamped_set(release_point[1], 3.775, 0.225, 0, 1);

                    
                }
                printOnce = true;

                if (start)
                {
                    now_Status = RUN;
                    printOnce = false; 
                }
                if (ros::Time::now().toSec() - cakeTime.toSec() >= 0.4)
                {
                    mainClass._better_cake.publish(cake);
                    cakeTime = ros::Time::now();
                }
                break;

            case RUN:
                if (!printOnce)
                {
                    initialTime = ros::Time::now();
                    ROS_WARN("RUN");
                    ROS_INFO("%s",id.c_str());
                }
                printOnce = true;

                switch (now_Mission)
                {
                case CAKE:

                    mission_timeOut = 5;
                    driving_timeOut = 20;
                    
                    if (ros::Time::now().toSec() - initialTime.toSec() >= go_home_time && !going_home)
                    {
                        moving = false;
                        doing = false;
                        arrived = false;
                        mission_success = false;
                        now_Mission = HOME;
                        ROS_INFO("===== Time to Go Home !!! =====");
                    }
                    else if (got_cake_picked)
                    {
                        if (!moving && !doing)
                        {
                            if (route_failed)
                            {
                                route_failed = false;
                                if (cakeNum < 2)
                                {
                                    cakeNum++;
                                }
                                else
                                {
                                    now_Mission = CHERRY;
                                }
                            }
                            else if (!arrived && !mission_success)
                            {
                                missionStr.data = id[2*cakeNum];
                                missionStr.data += id[2*cakeNum+1];
                                mainClass._mission.publish(missionStr);
                                ROS_INFO("Mission [%s] published!", missionStr.data.c_str());

                                mainClass._where2go.publish(cake_picked[cakeNum]);
                                ROS_INFO("Heading over to x:[%.3f] y:[%.3f]", cake_picked[cakeNum].pose.position.x, cake_picked[cakeNum].pose.position.y);
                                moving = true;
                                startDriveTime = ros::Time::now().toSec();
                            }
                            else if (arrived)
                            {
                                arrived = false;
                                missionStr.data.at(0) = 'c';
                                mainClass._mission.publish(missionStr);
                                ROS_INFO("Mission [%s] published!", missionStr.data.c_str());
                                doing = true;
                                startMissionTime = ros::Time::now().toSec();
                            }
                            else if (mission_success)
                            {
                                mission_success = false;
                                gotCake++;
                                if (cakeNum < 2)
                                {
                                    cakeNum++;
                                }
                                else
                                {
                                    now_Mission = CHERRY;
                                }
                            }
                        }
                        else if (moving && ros::Time::now().toSec() - startDriveTime >= driving_timeOut)
                        {
                            moving = false;
                            doing = false;
                            arrived = false;
                            mission_success = false;
                            ROS_WARN("===== Can't reach x:[%.3f] y:[%.3f]! =====", cake_picked[cakeNum].pose.position.x, cake_picked[cakeNum].pose.position.y);
                            if (cakeNum < 2)
                            {
                                cakeNum++;
                            }
                            else
                            {
                                now_Mission = CHERRY;
                            }
                        }
                        else if (doing && ros::Time::now().toSec() - startMissionTime >= mission_timeOut)
                        {
                            moving = false;
                            doing = false;
                            arrived = false;
                            mission_success = false;
                            ROS_WARN("===== Mission [%s] overtime! =====", missionStr.data.c_str());
                            if (cakeNum < 2)
                            {
                                cakeNum++;
                            }
                            else
                            {
                                now_Mission = CHERRY;
                            }
                        }
                    }
                    break;
                
                case CHERRY:
                    
                    mission_timeOut = 10;
                    driving_timeOut = 20;
                    if (ros::Time::now().toSec() - initialTime.toSec() >= go_home_time && !going_home)
                    {
                        moving = false;
                        doing = false;
                        arrived = false;
                        mission_success = false;
                        now_Mission = HOME;
                        ROS_INFO("===== Time to Go Home !!! =====");
                    }
                    else if (!cherry.data)
                    {
                        cherry.data = true;
                        mainClass._first_cherry.publish(cherry);
                    }
                    else if (got_cherry_picked)
                    {
                        if (!moving && !doing)
                        {
                            if (route_failed)
                            {
                                route_failed = false;
                                now_Mission = BASKET;
                            }
                            else if (!arrived && !mission_success)
                            {
                                mainClass._where2go.publish(cherry_picked[cherryNum]);
                                ROS_INFO("Heading over to x:[%.3f] y:[%.3f]", cherry_picked[cherryNum].pose.position.x, cherry_picked[cherryNum].pose.position.y);
                                moving = true;
                                startDriveTime = ros::Time::now().toSec();
                            }
                            else if (arrived)
                            {
                                arrived = false;
                                if (cherryNum == 0)
                                {
                                    missionStr.data = "s0";
                                }
                                else
                                {
                                    missionStr.data = "v0";
                                }
                                mainClass._mission.publish(missionStr);
                                ROS_INFO("Mission [%s] published!", missionStr.data.c_str());
                                doing = true;
                                startMissionTime = ros::Time::now().toSec();
                            }
                            else if (mission_success)
                            {
                                mission_success = false;
                                if (cherryNum < 1)
                                {
                                    cherryNum++;
                                }
                                else
                                {
                                    now_Mission = BASKET;
                                }
                            }
                        }
                        else if (moving && ros::Time::now().toSec() - startDriveTime >= driving_timeOut)
                        {
                            moving = false;
                            doing = false;
                            arrived = false;
                            mission_success = false;
                            ROS_WARN("===== Can't reach x:[%.3f] y:[%.3f]! =====",  cherry_picked[cherryNum].pose.position.x, cherry_picked[cherryNum].pose.position.y);
                            now_Mission = BASKET;
                        }
                        else if (doing && ros::Time::now().toSec() - startMissionTime >= mission_timeOut)
                        {
                            moving = false;
                            doing = false;
                            arrived = false;
                            mission_success = false;
                            ROS_WARN("===== Mission [%s] overtime! =====", missionStr.data.c_str());
                            now_Mission = BASKET;
                        }
                    }
                    break;

                case BASKET:
                    
                    mission_timeOut = 10;
                    driving_timeOut = 20;
                    if (ros::Time::now().toSec() - initialTime.toSec() >= go_home_time && !going_home)
                    {
                        now_Mission = HOME;
                        ROS_INFO("===== Time to Go Home !!! =====");
                    }
                    else if (!moving && !doing)
                    {
                        if (route_failed)
                        {
                            route_failed = false;
                            now_Mission = RELEASE;
                        }
                        else if (!arrived && !mission_success)
                        {
                            mainClass._where2go.publish(basket_point[side]);
                            ROS_INFO("Heading over to x:[%.3f] y:[%.3f]", basket_point[side].pose.position.x, basket_point[side].pose.position.y);
                            moving = true;
                            startDriveTime = ros::Time::now().toSec();
                        }
                        else if (arrived)
                        {
                            arrived = false;
                            missionStr.data = "u0";
                            mainClass._mission.publish(missionStr);
                            ROS_INFO("Mission [%s] published!", missionStr.data.c_str());
                            doing = true;
                            startMissionTime = ros::Time::now().toSec();
                        }
                        else if (mission_success)
                        {
                            mission_success = false;
                            now_Mission = RELEASE;
                        }
                    }
                    else if (moving && ros::Time::now().toSec() - startDriveTime >= driving_timeOut)
                    {
                        moving = false;
                        doing = false;
                        arrived = false;
                        mission_success = false;
                        ROS_WARN("===== Can't reach x:[%.3f] y:[%.3f]! =====", basket_point[side].pose.position.x, basket_point[side].pose.position.y);
                        now_Mission = RELEASE;
                    }
                    else if (doing && ros::Time::now().toSec() - startMissionTime >= mission_timeOut)
                    {
                        moving = false;
                        doing = false;
                        arrived = false;
                        mission_success = false;
                        ROS_WARN("===== Mission [%s] overtime! =====", missionStr.data.c_str());
                        now_Mission = RELEASE;
                    }
                    break;

                case RELEASE:

                    mission_timeOut = 10;
                    driving_timeOut = 20;
                    ROS_INFO("fullness : %d %d %d %d", fullness[0], fullness[1], fullness[2], fullness[3]);
                    now_Mission = STEAL;
                    // if (gotCake == 3)
                    // {
                    //     release.data = true;
                    //     mainClass._release.publish(release);
                    // }

                    // if (ros::Time::now().toSec() - initialTime.toSec() >= go_home_time && !going_home)
                    // {
                    //     now_Mission = HOME;
                    //     ROS_INFO("===== Time to Go Home !!! =====");
                    // }
                    // else if (!moving && !doing)
                    // {
                    //     if (route_failed)
                    //     {
                    //         route_failed = false;
                    //         now_Mission = STEAL;
                    //     }
                    //     else if (!arrived && !mission_success)
                    //     {
                    //         mainClass._where2go.publish(release_point[robot]);
                    //         ROS_INFO("Heading over to x:[%.3f] y:[%.3f]", release_point[robot].pose.position.x, release_point[robot].pose.position.y);
                    //         moving = true;
                    //         startDriveTime = ros::Time::now().toSec();
                    //     }
                    //     else if (arrived)
                    //     {
                    //         arrived = false;
                    //         missionStr.data = "o0";
                    //         mainClass._mission.publish(missionStr);
                    //         ROS_INFO("Mission [%s] published!", missionStr.data.c_str());
                    //         doing = true;
                    //         startMissionTime = ros::Time::now().toSec();
                    //     }
                    //     else if (mission_success)
                    //     {
                    //         mission_success = false;
                    //         if (gotCake > 0)
                    //         {
                    //             gotCake--;
                    //         }
                    //         else
                    //         {
                    //             now_Mission = STEAL;
                    //         }
                    //     }
                    // }
                    // else if (moving && ros::Time::now().toSec() - startDriveTime >= driving_timeOut)
                    // {
                    //     moving = false;
                    //     doing = false;
                    //     arrived = false;
                    //     mission_success = false;
                    //     ROS_WARN("===== Can't reach x:[%.3f] y:[%.3f]! =====", release_point[robot].pose.position.x, release_point[robot].pose.position.y);
                    //     now_Mission = STEAL;
                    // }
                    // else if (doing && ros::Time::now().toSec() - startMissionTime >= mission_timeOut)
                    // {
                    //     moving = false;
                    //     doing = false;
                    //     arrived = false;
                    //     mission_success = false;
                    //     ROS_WARN("===== Mission [%s] overtime! =====", missionStr.data.c_str());
                    //     now_Mission = STEAL;
                    // } 
                    break;

                case STEAL:
                    now_Mission = HOME;
                    break;
                
                case HOME:
                    going_home = true;
                    if (route_failed)
                    {
                        route_failed = false;
                        mainClass._where2go.publish(home);
                        ROS_INFO("Trying to reach x:[%.3f] y:[%.3f] again!", home.pose.position.x, home.pose.position.y);
                        moving = true;
                    }
                    else if (!moving)
                    {
                        if (!arrived)
                        {
                            mainClass._where2go.publish(home);
                            ROS_INFO("Heading over to x:[%.3f] y:[%.3f]", home.pose.position.x, home.pose.position.y);
                            moving = true;
                        }
                        else
                        {
                            missionStr.data = "d0";
                            mainClass._mission.publish(missionStr);
                            now_Status = FINISH;
                            printOnce = false;
                        }
                    }
                    break;
                }
                break;

            case FINISH:
                if (!printOnce)
                {
                    missionStr.data = "f0";
                    mainClass._mission.publish(missionStr);
                    ROS_INFO("Finish all missions!");
                    ROS_INFO("Robot%d finish time : %.1f", robot+1, ros::Time::now().toSec() - initialTime.toSec());
                    if (!finish_mission.data)
                    {
                        finish_mission.data = true;
                        mainClass._ifinish.publish(finish_mission);
                    }
                    else
                    {
                        ROS_INFO("Total time : %.1f", ros::Time::now().toSec() - initialTime.toSec());
                    }
                    printOnce = true;
                }
                break;
            }
            break;
        
        case EMERGENCY:
            ROS_INFO("Emergency State");
            break;
        }
        ros::spinOnce();
        rate.sleep();
    }
    return 0;
}