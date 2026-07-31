FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends vsftpd && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/ftp/uploads /etc/vsftpd_empty && \
    useradd -m -d /var/ftp -s /bin/bash ftpuser && \
    chown -R ftpuser:ftpuser /var/ftp && \
    chmod 755 /etc/vsftpd_empty

COPY vsftpd.conf /etc/vsftpd.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 21 21100-21110

ENTRYPOINT ["/entrypoint.sh"]