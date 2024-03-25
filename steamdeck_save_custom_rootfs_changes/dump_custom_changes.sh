#!/bin/bash


files=(
    "/usr/local/etc/frp"
    "/usr/local/etc/v2ray"
    "/etc/rc.local"
    "/etc/hosts"
    "/usr/local/bin/and_delete"
    "/usr/local/bin/fstab_formatter"
    "/usr/local/bin/do-until"
    "/usr/local/bin/cat_EOF_dir.py"
)


while IFS=  read -r -d $'\0'; do
    files+=("$REPLY");
done < <(find /usr/local/bin/  \( -name 'geo*' -o -name 'v2*' -o -name 'frp*' -o -name "ttyd" \) -print0)

while IFS=  read -r -d $'\0'; do
    files+=("$REPLY");
done < <(find /etc/systemd/system  \( -name 'v2*' -o -name 'frp*' -o -name "ttyd*" \) -print0)

for f in "${files[@]}";
do
echo "${f}";
done;


# Create a tar archive
backup_name="backup-$(date "+%F-%H-%M-%S").tar.gz";
tar -czvf "${backup_name}" "${files[@]}"
tar -tvf  "${backup_name}";