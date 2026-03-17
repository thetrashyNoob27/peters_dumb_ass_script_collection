#!/usr/bin/bash

openssl s_server -cert deadend-signby-CA.crt -key deadend.key -CAfile CA.crt  -accept 8443