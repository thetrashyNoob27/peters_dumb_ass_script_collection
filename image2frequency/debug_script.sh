#!/usr/bin/bash

find testImages/ -type f \( -name "*jpg" -o -name "*png" \) -exec ./image2frequency.py \-\-debug \-\-RGB \-\-compare  \-i {} +
