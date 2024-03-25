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
set(PROJECT_NAME "${PROJECT_NAME}")
set(PROJECT_BINARY "${PROJECT_NAME}")
project("\${PROJECT_NAME}" VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_VERBOSE_MAKEFILE ON)

include_directories("\${CMAKE_CURRENT_SOURCE_DIR}")


find_library(ARG_PRASE_LIB boost_program_options)
if (ARG_PRASE_LIB)
add_definitions(-DENABLE_ARG_PARSE)
message(STATUS "boost::program_options found: \${ARG_PRASE_LIB}")
else()
message(WARNING "not found, disable arg processing.")
endif()
configure_file(config.h.in config.h)
include_directories("\${CMAKE_BINARY_DIR}")

add_executable("\${PROJECT_BINARY}" main.cpp utils.cpp)

if (ARG_PRASE_LIB)
target_link_libraries("\${PROJECT_BINARY}" PRIVATE \${ARG_PRASE_LIB})
else()
endif()
EOF

cat<<EOF>config.h.in
#ifndef CONFIG_H
#define CONFIG_H

#define PROJECT_NAME "@PROJECT_NAME@"
#define PROJECT_BINARY "@PROJECT_BINARY@"
#define PROJECT_VERSION "@PROJECT_VERSION@"
#define PROJECT_VERSION_MAJOR "@PROJECT_VERSION_MAJOR@"
#define PROJECT_VERSION_MINOR "@PROJECT_VERSION_MINOR@"
#define PROJECT_VERSION_PATCH "@PROJECT_VERSION_PATCH@"

#endif

#ifdef ENABLE_ARG_PARSE
#else
#endif

EOF

cat<<EOF >"build_n_run.sh"
#!/usr/bin/bash
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "\${SCRIPT_DIR}";
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
if [[ \$? -ne 0 ]];
then 
echo "cmake fail";
exit;
else
clear;
fi

make;
if [[ \$? -ne 0 ]];
then 
echo "build fail";
exit;
else
clear;
fi
./"${PROJECT_NAME}"  "\$@";

EOF
chmod a+x "build_n_run.sh";

cat<<EOF >"main.cpp"
#include <iostream>
#include "main.h"

int main(int argc, char **argv, char **env)
{
  
    std::printf("project: %s version:%s\n", PROJECT_NAME, PROJECT_VERSION);
    print_args(argc, argv);
#ifdef ENABLE_ARG_PARSE
    auto vm = arg_praser(argc, argv);
    if (vm.count("string"))
    {
        std::cout << "string: " << vm["string"].as<std::string>() << std::endl;
    }

    if (vm.count("value"))
    {
        std::cout << "value: " << vm["value"].as<float>() << std::endl;
    }

    if (vm.count("enable"))
    {
        std::cout << "enable: " << vm["enable"].as<bool>() << std::endl;
    }

    if (vm.count("array"))
    {
        std::cout << "Output files:";
        for (const auto &output : vm["array"].as<std::vector<std::string>>())
        {
            std::cout << " " << output;
        }
        std::cout << std::endl;
    }
#else
    std::cout <<"boost_program_options no found." << std::endl;
#endif
}

EOF

cat<<EOF >"main.h"
#ifndef _MAIN_H_
#define _MAIN_H_
#include "utils.h"
#include "config.h"
#include <string>

#endif

EOF


cat<<EOF >"utils.h"
#ifndef _UTILS_H_
#define _UTILS_H_

void print_args(int argc, char **argv);
void print_env_vars(char **env);

#include "config.h"
#ifdef ENABLE_ARG_PARSE
#include <boost/program_options.hpp>
#include <cstdlib>
extern float value;
boost::program_options::variables_map arg_praser(int argc, char **argv);
#endif
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

#ifdef ENABLE_ARG_PARSE
float value;
boost::program_options::variables_map arg_praser(int argc, char **argv)
{
    namespace po = boost::program_options;
    po::options_description desc("Allowed options");
    desc.add_options()("help,h", "produce help message");
    desc.add_options()("string,s", po::value<std::string>(), "string option");
    desc.add_options()("value,v", po::value<float>(&value)->default_value(3.14), "float option");
    desc.add_options()("enable,e", po::bool_switch()->default_value(false), "enable option");
    desc.add_options()("array,a", po::value<std::vector<std::string>>()->multitoken(), "array of options");

    po::variables_map vm;
    po::store(po::parse_command_line(argc, argv, desc), vm);
    po::notify(vm);

    if (vm.count("help"))
    {
        std::cout << desc << std::endl;
        std::exit(EXIT_SUCCESS);
    }
    return vm;
}
#else
#endif

EOF

echo "project create ok.";
