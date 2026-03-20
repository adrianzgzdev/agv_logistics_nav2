# 🤖 Autonomous AGV Logistics & Fleet Management (ROS 2 Jazzy)

![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-22314E?style=for-the-badge&logo=ros)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gazebo](https://img.shields.io/badge/Gazebo_Sim-FFB71B?style=for-the-badge&logo=gazebo&logoColor=black)

This repository contains a full-stack robotics project developing an autonomous Automated Guided Vehicle (AGV) for warehouse logistics. Built from the ground up using **ROS 2 Jazzy**, **Nav2**, and **Gazebo**, the project is evolving in phases, moving from basic simulation and mapping to production-grade fault-tolerant mission execution.

---

## 🎥 Project Demonstrations

### Phase 2: Localization Recovery & Industrial Docking
*Demonstrating the Fault-Tolerant System. The AGV recovers from a severe localization mismatch (Status 6 Abort) using a Watchdog timer and Retry Logic, while broadcasting its state to a simulated WMS.*

![Phase 2 Demo](demo_phase_2.gif)

### Phase 1: Dynamic Obstacle Avoidance
*Demonstrating baseline Nav2 integration, local costmap updates, and real-time path recalculation.*

![Phase 1 Demo](demo.gif)

---

## 🚀 Key Features & Milestones

### 🟢 Phase 2: Advanced Mission Executor & Fault-Tolerant Navigation
In this phase, the baseline script was upgraded into a robust, object-oriented **Mission Orchestrator Node**, bridging the gap between academic navigation and real-world industrial requirements.
* **Finite State Machine (FSM):** Strictly manages the AGV's mission lifecycle (`IDLE`, `APPROACHING_PICKUP`, `LOADING`, etc.).
* **WMS Integration Ready:** Continuously broadcasts the real-time FSM state to the `/agv_mission_state` topic.
* **Fault Tolerance & Recovery:** * **Retry Logic:** Intercepts Nav2 rejections or aborted goals and automatically retries after a 3-second safety cooldown.
  * **Watchdog Timer:** Prevents infinite loops by enforcing a strict timeout on all navigation tasks.
* **Safety First (E-Stop):** Explicitly cancels active `MapsToPose` goals upon mission abortion to prevent "zombie" hardware movements.
* **Industrial Docking:** Uses a 2-step approach logic (Alignment -> Straight insertion) to prevent sweeping turns into pallet racks.
* **Dynamic Configuration:** Uses **ROS 2 Parameters** for on-the-fly adjustment of timeouts and retries without recompiling.

### 🟡 Phase 1: Foundation & Basic Navigation
* **Physical Hardware Simulation:** Custom URDF and SDF modeling with fine-tuned kinematics and LiDAR sensor integration in modern Gazebo.
* **Topographic SLAM Mapping:** Precision mapping of the industrial warehouse environment to generate robust 2D occupancy grids.
* **Dynamic Autonomous Navigation:** Full Nav2 stack integration (Global planning, Behavior Trees, Local Costmaps).

---

## 💻 Tech Stack

* **Framework:** ROS 2 (Jazzy Jalisco)
* **Languages:** Python (WMS API, Mission Executor), C++ (Underlying ROS nodes), XML/YAML (Configuration)
* **Simulation & Visualization:** Gazebo (Ignition), RViz2
* **Navigation & Mapping:** Nav2, SLAM Toolbox, AMCL (Adaptive Monte Carlo Localization)

---

## 🛠️ How to Run

**1. Launch the Simulation & Navigation Stack:**
```bash
ros2 launch agv_nav2 navigation.launch.py
```
*This initializes Gazebo, loads the warehouse map, spawns the AGV, and brings up RViz with the Nav2 panel.*

**2. Execute the Logistic Shift:**

* **Option A (Phase 2 - Advanced Orchestrator):**
  ```bash
  ros2 run agv_mission_executor mission_node
  ```
  *(Optional) Run with custom parameters for max retries and timeout:*
  ```bash
  ros2 run agv_mission_executor mission_node --ros-args -p max_retries:=3 -p navigation_timeout_sec:=90.0
  ```
  *(Optional) Monitor the WMS State in a new terminal:*
  ```bash
  ros2 topic echo /agv_mission_state std_msgs/msg/String
  ```

* **Option B (Phase 1 - Legacy Script):**
  ```bash
  ros2 run agv_nav2 fleet_manager.py
  ```

---
👨‍💻 **Developed by Adrián** | 🔗 Let's connect on [LinkedIn](https://www.linkedin.com/in/adrianzgzdev/)