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

add_executable("${PROJECT_NAME}" main.cpp utils.cpp)
EOF

cat<<EOF >"build_n_run.sh"
#!/usr/bin/bash
if [ -d ".build" ]
then
#just cd to it.
:
else
rm -rv .build;
mkdir .build;
fi

cd .build;
cmake ..;
make;
./"${PROJECT_NAME}";

EOF
chmod a+x "build_n_run.sh";

cat<<EOF >"main.cpp"
#include <iostream>
#include "main.h"

const char* project_name = "${PROJECT_NAME}";
int main(int argc, char **argv, char **env)
{
    
    std::printf("project: %s \n",project_name);
    print_args(argc, argv);
    print_env_vars(env);
    return 0;
}

EOF

cat<<EOF >"main.h"
#ifndef _MAIN_H_
#define _MAIN_H_
#include "utils.h"

extern const char* project_name;

#endif

EOF


cat<<EOF >"utils.h"
#ifndef _UTILS_H_
#define _UTILS_H_
void print_args(int argc, char **argv);
void print_env_vars(char **env);
#endif

EOF

cat<<EOF >"utils.cpp"
#include <iostream>
#include "utils.h"

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

echo "project create ok.";