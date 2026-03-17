#!/usr/bin/bash

OPTIONS=$(getopt -o "" --long ca:,hostname: -- "$@")
eval set -- "$OPTIONS"

WITH_CA=0;
unset CA_PREFIX;
unset HOSTNAME;

while true; do
    case "$1" in
        --ca) CA_PREFIX="$2"; shift 2 ;;
        --hostname) HOSTNAME="$2"; shift 2 ;;
        --) shift; break ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -n "${CA_PREFIX}" && -z "${HOSTNAME}" ]];
then 
HOSTNAME=$(hostname)
fi

if [[ -z "${HOSTNAME}" ]];
then
    echo "subject name not set, using default name CA";
    HOSTNAME="CA";
fi
if [[ -f "${HOSTNAME}.key" ]];
then
    echo "private key ${HOSTNAME}.key already exist skip generate.";
else
    echo "generate private key ${HOSTNAME}.key"
    openssl genrsa -out "${HOSTNAME}.key" 4096;
fi

if [[ -z "${CA_PREFIX}" && ! -f  "${HOSTNAME}-selfsign.cnf" ]];
then
    echo  "${HOSTNAME}-selfsign.cnf not exist, gen default"
cat <<EOF  > "${HOSTNAME}-selfsign.cnf"
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
fi

if [[ -z "${CA_PREFIX}" ]];
then
    OTHER_SIGN_CNF="${HOSTNAME}-signby-NONE.cnf"
else
    CA_NAME=$(basename ${CA_PREFIX})
    OTHER_SIGN_CNF="${HOSTNAME}-signby-${CA_NAME}.cnf"
fi

if [[ -n "${CA_PREFIX}" &&  ! -f  "${OTHER_SIGN_CNF}" ]];
then
    echo "CA_PREFIX=${CA_PREFIX}";
    echo  "${OTHER_SIGN_CNF} not exist, gen default"
cat <<EOF  > "${OTHER_SIGN_CNF}"
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
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth  # Adjust based on use case


[alt_names]
#DNS.1 = your-hostname.example.com
# Add more SANs as needed
EOF
fi



if [[ -z "${CA_PREFIX}" ]];
then
    echo "not given CA prefix, go self-sign route";
    if [[ ! -f "${HOSTNAME}.crt" ]];
    then
        openssl req -x509 -new -nodes -key "${HOSTNAME}.key"   -sha256   -days 36500   -out "${HOSTNAME}.crt"  -config "${HOSTNAME}-selfsign.cnf" ;
    else
        echo "cert exist, auto renew..."
        OLD_VALID_RANGE=$(openssl x509 -in "${HOSTNAME}.crt"  -noout -dates);
        echo "public key ${HOSTNAME}.crt exist, renew (old public key valid range:${OLD_VALID_RANGE})";
        openssl x509 -in "${HOSTNAME}.crt" -out "${HOSTNAME}.crt" -days 36500 -signkey "${HOSTNAME}.key";
        NEW_VALID_RANGE=$(openssl x509 -in "${HOSTNAME}.crt"  -noout -dates)
        echo "new public key valid range:${NEW_VALID_RANGE}";
    fi
else
    echo "CA prefix given, try sign with CA";
    if [[ ! -f "${HOSTNAME}.crt" ]];
    then
        openssl req -new -key "${HOSTNAME}.key" -out "${HOSTNAME}-signby-${CA_NAME}.csr" -config "${OTHER_SIGN_CNF}"
        openssl x509 -req -in "${HOSTNAME}-signby-${CA_NAME}.csr" \
        -CA "${CA_PREFIX}.crt" -CAkey "${CA_PREFIX}.key" -CAcreateserial \
        -out "${HOSTNAME}-signby-${CA_NAME}.crt" -days 3650 -sha256 \
        -extfile "${OTHER_SIGN_CNF}" -extensions req_ext
    else
        echo "cert exist, not do anything."
    fi
    openssl verify -CAfile "${CA_PREFIX}.crt"  "${HOSTNAME}-signby-${CA_NAME}.crt"
fi

