#!/usr/bin/bash

find ~/backup/android_media/DCIM/Camera/ -type f -name "*jpg" -exec ./image2frequency.py \-\-debug \-\-RGB \-\-compare  \-i {} +
