#!/bin/sh
set -e

FTP_PASS="${FTP_PASS:-ftppass123}"
PASV_ADDRESS="${PASV_ADDRESS:-127.0.0.1}"

sed -i "s|^pasv_address=.*|pasv_address=${PASV_ADDRESS}|" /etc/vsftpd.conf

if ! id ftpuser >/dev/null 2>&1; then
    useradd -m -d /var/ftp -s /bin/bash ftpuser
    chown -R ftpuser:ftpuser /var/ftp
fi

echo "ftpuser:${FTP_PASS}" | chpasswd

exec /usr/sbin/vsftpd /etc/vsftpd.conf