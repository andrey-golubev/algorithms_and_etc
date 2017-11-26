cmake_minimum_required(VERSION 2.8)
project(cplex_bnb)

add_executable(${PROJECT_NAME} branch_and_bound.cpp)
target_link_libraries(${PROJECT_NAME} cplex1271)
