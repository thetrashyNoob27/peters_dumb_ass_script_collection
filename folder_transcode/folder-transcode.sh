#!/bin/bash


get_relative_path() {
    local source_path="$1"
    local target_path="$2"
    echo "$(realpath --relative-to="$source_path" "$target_path")"
}

# Default values
SEARCH_PATH="${PWD}"
OUTPUT_PATH=""
PROFILE=""

# Function to display usage
usage() {
    echo "Usage: $0 -i <input_path> -o <output_path> -p <profile>"
    echo "Options:"
    echo "  -i <input_path>    Specify the input path."
    echo "  -o <output_path>   Specify the output path."
    echo "  -p <profile>       Specify the profile."
    exit 1
}

# Parse arguments
while getopts ":i:o:p:" opt; do
    case ${opt} in
        i )
            SEARCH_PATH="$OPTARG"
        ;;
        o )
            OUTPUT_PATH="$OPTARG"
        ;;
        p )
            PROFILE="$OPTARG"
        ;;
        \? )
            echo "Invalid option: $OPTARG" 1>&2
            usage
        ;;
        : )
            echo "Invalid option: $OPTARG requires an argument" 1>&2
            usage
        ;;
    esac
done
shift $((OPTIND -1))

if [[ -z "${OUTPUT_PATH}" ]];
then
    
    echo "output path not set!";
    exit;
fi

if [[ -z "${PROFILE}" ]];
then
    
    echo "ffmpeg profile not set!";
    exit;
fi

PROFILE_DIRNAME=${HOME}"/.local/share/folder-transcode-profile";
PROFILE_PATH="${PROFILE_DIRNAME}"/"${PROFILE}";
if [[ ! -d "${PROFILE_DIRNAME}" ]];
then
    mkdir -p "${PROFILE_DIRNAME}";
cat<<'EOF'>> "${PROFILE_DIRNAME}"/psp;
FFMPEG_CONFIG='-vcodec libx264 -vf 'scale=480:-2' -vf format=yuv420p -crf 18 -profile:v main -level:v 2.1 -x264-params ref=3:bframes=1 -acodec aac -b:a 128k -ac 2 -movflags +faststart';
VIDEO_SUFFIX="mp4"
VIDEO_CONTAINER="mp4"
EOF
cat<<'EOF'>> "${PROFILE_DIRNAME}"/mipad1-1080;
FFMPEG_CONFIG='-c:v h264 -vf 'scale=-2:1080' -crf 18';
EOF
cat<<'EOF'>> "${PROFILE_DIRNAME}"/mipad1-720;
FFMPEG_CONFIG='-c:v h264 -vf 'scale=-2:720' -crf 18';
EOF
fi

source <(grep -E '^(FFMPEG_CONFIG|VIDEO_SUFFIX|VIDEO_CONTAINER)=' ${PROFILE_PATH})
if [[ 0 -ne $? ]];
then
    echo "load profile fail!(${PROFILE_PATH})";
    exit;
fi

if [[ -z "${FFMPEG_CONFIG}" ]]
then
    
    echo "ffmpeg args missing config!";
    exit;
fi

if [[ -z "${VIDEO_SUFFIX}" ]]||[[ -z "${VIDEO_CONTAINER}" ]];
then
    echo "video container format setting missing,default set to mkv";
    VIDEO_SUFFIX="mkv";
    VIDEO_CONTAINER="matroska";
fi

VIDEO_IN_PATH=()
while IFS=  read -r -d $'\0'; do
    VIDEO_IN_PATH+=("$REPLY");
done < <(find "${SEARCH_PATH}" -type f \( -iname  "*.mkv" -o -iname  "*.avi" -o -iname  "*.mp4" -o -iname  "*.rm" -o -iname  "*.rmvb" \) -print0)


NEW_PATH_BASE=$(dirname "${SEARCH_PATH}");
if [[ -f "${SEARCH_PATH}" ]];
then
    NEW_PATH_BASE=$(dirname "${NEW_PATH_BASE}");
fi


for v in "${VIDEO_IN_PATH[@]}";
do
    video_r_path=$(get_relative_path "${NEW_PATH_BASE}" "$(realpath "${v}")");
    video_folder=$(dirname "${video_r_path}" );
    output_folder="${OUTPUT_PATH}"/"${video_folder}"
    mkdir -p "${output_folder}";
    
    video_name="$(basename "${v}")";
    video_name="${video_name%.*}";
    output_name="${output_folder}"/"${video_name}";
    
    if [[ -f "${output_name}"."${VIDEO_SUFFIX}" ]];
    then
        echo "video: ${output_name} finished. skip.";
        continue;
    fi;
    (ffmpeg -y -i "${v}"  ${FFMPEG_CONFIG}  -f ${VIDEO_CONTAINER}  "${output_name}".tmp);
    if [[ 0 -eq $? ]];
    then
        mv "${output_name}".tmp "${output_name}"."${VIDEO_SUFFIX}";
    else
        rm "${output_name}".tmp;
    fi
done
