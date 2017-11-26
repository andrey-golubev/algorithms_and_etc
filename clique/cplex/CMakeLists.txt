cmake_minimum_required(VERSION 2.8)
project(cplex_bnb)

add_executable(${PROJECT_NAME} branch_and_bound.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE
    concert
    cplex1271
    cplex1271mpitransport
    cplex1271mpiworker
    cplex1271processtransport
    cplex1271processworker
    cplex1271remotejni
    cplex1271remote
    cplex1271tcpiptransport
    cplex1271tcpipworker

    ilocplex
    cplexdistmip

    pthread
    ${CMAKE_DL_LIBS}
)
