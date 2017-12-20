cmake_minimum_required(VERSION 2.8)
project(cplex)

add_executable(cplex_bnb branch_and_bound.cpp)
target_link_libraries(cplex_bnb PRIVATE
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

add_executable(cplex_bnc branch_and_cut.cpp)
target_link_libraries(cplex_bnc PRIVATE
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
