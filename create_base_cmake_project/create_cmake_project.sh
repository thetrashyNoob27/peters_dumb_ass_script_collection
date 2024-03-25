#!/usr/bin/bash



read -p "project name:" PROJECT_NAME;
echo "${PROJECT_NAME}";

if [[ -z "$PROJECT_NAME" ]]; then
    echo "project name empty.";
    exit;
fi

mkdir "${PROJECT_NAME}" && cd "${PROJECT_NAME}";
if [[ $? -ne 0 ]];
then
echo "mkdir && cd fail.";
exit;
else 
echo "folder create ok.";
fi

cat<<EOF >"CMakeLists.txt"
cmake_minimum_required(VERSION 3.10)
project("${PROJECT_NAME}" VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)


include_directories("\${CMAKE_CURRENT_SOURCE_DIR}")

add_executable("${PROJECT_NAME}" main.cpp prints.cpp)
EOF


cat<<EOF >"main.cpp"
#include <iostream>
#include "main.h"

int main(int argc, char **argv, char **env)
{
    std::printf("project: hello \n");
    print_args(argc, argv);
    print_env_vars(env);
    return 0;
}

EOF

cat<<EOF >"main.h"
#ifndef _MAIN_H_
#define _MAIN_H_
#include "prints.h"
#endif

EOF


cat<<EOF >"prints.h"
#ifndef _PRINTS_H_
#define _PRINTS_H_
void print_args(int argc, char **argv);
void print_env_vars(char **env);
#endif

EOF

cat<<EOF >"prints.cpp"
#include <iostream>
#include "prints.h"

void print_args(int argc, char **argv)
{
    std::printf("process args:\n");
    for (int i = 0; i < argc; i++)
    {
        std::printf("[%2d][%s]\n", i, argv[i]);
    }
    return;
}

void print_env_vars(char **env)
{
    std::printf("process env variables:\n");
    char **envstr = env;
    int env_counter = 0;
    while (*envstr != NULL)
    {
        std::printf("env[%02d] [%s]\n", env_counter++, *envstr);
        envstr++;
    }
    return;
}

EOF