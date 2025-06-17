#!/usr/bin/bash

VERSION_MAJOR=0;
VERSION_MINOR=8;
VERSION_PATCH=0;

script="create_base_python_script.sh";
if [[ -f "$script" ]]; then
    rm -v "${script}";
fi

cat<<'__EOF__'>>"${script}"
#!/usr/bin/bash
read -p "project name:" PROJECT_NAME;
echo "${PROJECT_NAME}";

if [[ -z "$PROJECT_NAME" ]]; then
    echo "project name empty.";
    exit;
fi
if [[ -f "$PROJECT_NAME.py" ]]; then
    echo "file exist.";
    exit;
fi

cat<<EOF >"${PROJECT_NAME}.py"
__EOF__

#begin of python code
cat test_script.py >>"${script}";
echo "#create by base python script creator ${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}" >>"${script}";

#end of python code


cat<<'__EOF__'>>"${script}"
EOF

echo "# create on $(date "+ [%z]%F %H:%M:%S")">>"${PROJECT_NAME}.py";
chmod a+x "${PROJECT_NAME}.py";
__EOF__
chmod a+x "${script}";