#!/usr/bin/bash


HOSTNAME="CA";
if [[ -f "${HOSTNAME}.key" ]];
then 
echo "private key ${HOSTNAME}.key already exist skip generate.";
else
echo "generate private key ${HOSTNAME}.key"
openssl genrsa -out "${HOSTNAME}.key" 4096;
fi



cat <<EOF  > "${HOSTNAME}.cnf" 
[ req ]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = req_ext

[ dn ]
C  = CN
ST = Xi'an
L  = Shannxi
O  = NONE
OU = NONE
# CN = device-a ; hostname 
emailAddress = 896010555@qq.com

[ req_ext ]
#subjectAltName = @alt_names

[ alt_names ]
#DNS.1 = localhost
#IP.1  = 127.0.0.1
EOF

if [[ ! -f "${HOSTNAME}.crt" ]];
then
openssl req -x509 -new -nodes   -key "${HOSTNAME}.key"   -sha256   -days 36500   -out "${HOSTNAME}.crt"  -config "${HOSTNAME}.cnf";
else
OLD_VALID_RANGE=$(openssl x509 -in "${HOSTNAME}.crt"  -noout -dates);
echo "public key "${HOSTNAME}.crt" exist, renew (old public key valid range:${OLD_VALID_RANGE})";


openssl x509 -in "${HOSTNAME}.crt" -out "${HOSTNAME}.crt" -days 36500 -signkey "${HOSTNAME}.key";


NEW_VALID_RANGE=$(openssl x509 -in "${HOSTNAME}.crt"  -noout -dates);

echo "new public key valid range:${NEW_VALID_RANGE}";
fi