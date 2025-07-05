cmake_minimum_required(VERSION 3.22)
project(tickle_taesan_moveit)

find_package(ament_cmake REQUIRED)

# Install Python scripts - removed scripts not needed for current system
# All scripts were for testing purposes and are not used in tickle_moveit.launch.py

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/launch")
  install(
    DIRECTORY launch
    DESTINATION share/${PROJECT_NAME}
    PATTERN "setup_assistant.launch" EXCLUDE)
endif()

install(DIRECTORY config DESTINATION share/${PROJECT_NAME})
install(DIRECTORY urdf DESTINATION share/${PROJECT_NAME})
install(DIRECTORY meshes DESTINATION share/${PROJECT_NAME})
install(FILES .setup_assistant DESTINATION share/${PROJECT_NAME})

ament_package()
