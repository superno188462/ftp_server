# FTP 上传服务 (Flask + vsftpd)

一个由 Docker 编排的 FTP 上传服务：用户通过浏览器上传文本或 zip 压缩包，文件落到共享目录，FTP 客户端可同时通过 FTP 协议访问下载。

## 结构

```
ftp_server/
├── .env                       # 真实环境变量（不入库；模板见 .env.example）
├── .env.example
├── .gitignore
├── .dockerignore
├── app.py                     # Flask 入口（启动脚本位于项目根目录）
├── pyproject.toml             # uv 依赖声明
├── uv.lock
├── doc/                       # 任务清单与历史
│   ├── TASK.md
│   └── HISTORY.md
├── src/                       # 源代码
│   └── templates/
│       ├── index.html
│       └── unlock.html
└── docker/                    # 所有 Docker 资产
    ├── docker-compose.yml
    ├── web/Dockerfile         # 构建 Flask 镜像（基于本地 python:3.11-alpine）
    └── ftp/
        ├── Dockerfile         # 构建 vsftpd 镜像（基于本地 ubuntu:22.04）
        ├── entrypoint.sh
        └── vsftpd.conf
```

> 根目录放启动文件 + 配置（`.env` / `.gitignore` / `pyproject.toml` 等），`src/` 放源代码，`docker/` 放 Docker 资产，`doc/` 放任务与历史。`doc/` 要纳入版本控制。

`docker-compose.yml` 通过 `build.context` / `dockerfile` 显式声明，源码与构建资产解耦，全部 Docker 资产集中在 `docker/`。

两个容器共享宿主目录 `~/usr/database/ftp`（bind mount 到容器内的 `/var/ftp/uploads`）。宿主目录需提前创建并设置好权限（`chown 1001:1001 && chmod 777`），1001 是 ftp 容器内 `ftpuser` 的 UID（Ubuntu 22.04 基础镜像中 `ubuntu=1000`，`ftpuser` 顺延为 1001）。

## 启动

```bash
cd ~/usr/docker/ftp_server/docker
docker compose up -d --build
```

启动后：

| 服务     | 地址                      | 凭据            |
|----------|---------------------------|-----------------|
| Web 上传 | http://localhost:5000     | 无              |
| FTP      | ftp://localhost:21        | `ftpuser` / `ftppass123` |

## Web 端使用

打开 http://localhost:5000

- **上传文件**：支持 `.txt` `.md` `.log` `.csv` `.json` `.xml` `.yaml` `.yml` `.ini` `.conf` `.zip`，单文件最大 500 MB
- **粘贴文本保存**：填文件名（如 `note.txt`）+ 内容 → 提交
- **列表**：显示已上传文件，可下载或删除
- 上传后文件名会加上 8 位前缀以避免冲突
- **下载需密码**：点击「下载」会先跳转到 `/unlock` 输入下载密码（默认 `123456`），通过后本次会话内的所有下载免输入；顶部有「退出」按钮主动锁定

## FTP 客户端使用

```bash
ftp ftp://ftpuser:ftppass123@localhost
```

> 注意：`PASV_ADDRESS` 在 `entrypoint.sh` 里硬编码 `127.0.0.1`，仅供本机或反代访问。远程客户端需改为宿主机对外 IP，并在安全组/防火墙放行 `21` 端口和 `21100-21110` 端口段。

## 关于基础镜像

构建优先复用本地已有镜像（通过 `docker images` 查看），避免不必要的网络下载。本项目使用：

- `python:3.11-alpine` — 本地已有，作为 Flask 镜像基底
- `ubuntu:22.04` — 本地已有，作为 vsftpd 镜像基底
- `ghcr.io/astral-sh/uv:0.10.4` — 本地没有，唯一会触发的拉取；版本已锁定避免后续再拉

如本机版本不同，先 `docker images` 看一眼再调整 `docker/web/Dockerfile` 和 `docker/ftp/Dockerfile` 里的 `FROM`。

## 自定义

所有环境变量集中在项目根目录的 `.env` 文件（模板见 `.env.example`）：

| 变量               | 默认值        | 用途                       |
|--------------------|---------------|----------------------------|
| `UPLOAD_DIR`       | `/var/ftp/uploads` | 共享上传目录          |
| `FLASK_SECRET`     | `change-me-in-production` | Flask session 密钥 |
| `DOWNLOAD_PASSWORD`| `123456`      | Web 端下载密码             |
| `FTP_PASS`         | `change-me`   | FTP 登录密码               |
| `PASV_ADDRESS`     | `127.0.0.1`   | vsftpd 被动模式对外地址    |

修改后重建并重启：

```bash
cd ~/usr/docker/ftp_server/docker
sudo docker compose up -d --build
```

修改 Python 依赖：

```bash
cd ~/usr/docker/ftp_server
uv add <pkg>
uv lock
```

## 停止

```bash
docker compose down              # 停止容器，保留数据
docker compose down -v           # 停止并清除 volume（数据会丢）
```