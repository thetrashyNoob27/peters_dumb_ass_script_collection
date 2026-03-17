#!/usr/bin/bash

openssl s_client -connect localhost:8443 \
    -cert deadclient-signby-CA.crt -key deadclient.key \
    -CAfile CA.crt