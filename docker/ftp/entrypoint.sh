#!/bin/sh
set -e

FTP_USER="${FTP_USER:-ftpuser}"
FTP_PASS="${FTP_PASS:-ftppass123}"
PASV_ADDRESS="${PASV_ADDRESS:-127.0.0.1}"

sed -i "s|^pasv_address=.*|pasv_address=${PASV_ADDRESS}|" /etc/vsftpd.conf

if ! id "$FTP_USER" >/dev/null 2>&1; then
    useradd -m -d /var/ftp -s /bin/bash "$FTP_USER"
fi
chown -R "$FTP_USER:$FTP_USER" /var/ftp

echo "${FTP_USER}:${FTP_PASS}" | chpasswd

exec /usr/sbin/vsftpd /etc/vsftpd.conf