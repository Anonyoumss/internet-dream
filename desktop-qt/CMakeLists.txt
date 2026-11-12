cmake_minimum_required(VERSION 3.21)
project(InternetDream LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets Network)

qt_add_executable(internet-dream
    src/main.cpp
    resources/resources.qrc
)

target_link_libraries(internet-dream PRIVATE Qt6::Widgets Qt6::Network)

install(TARGETS internet-dream RUNTIME DESTINATION bin)
