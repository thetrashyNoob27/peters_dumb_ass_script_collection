#!/usr/bin/bash


INSTALL_PATH="";
if [ "$(id -u)" -eq 0 ]; then
    INSTALL_PATH="/usr/local/bin/";

else
    INSTALL_PATH="${HOME}/.local/bin/";
    mkdir -p "${INSTALL_PATH}";
fi

echo "install to ${INSTALL_PATH}";


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"


cp -v "create_cmake_project.sh" "${INSTALL_PATH}";