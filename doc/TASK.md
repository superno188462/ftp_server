# 任务清单

> 当前会话正在做的事情。按优先级排列，`in_progress` / `completed` / `cancelled`。
> 即使会话意外中断，下次也能从这里继续。

## 进行中

- [in_progress] （无）

## 待办（Backlog）

- [pending] （无）

## 已完成（最近）

- [completed] 2026-08-02 列表按 mtime 排序 + gunicorn 长连接配置：`index()` 改为按真实修改时间倒序（附 `mtime_str` 展示），gunicorn 加 `--timeout 600 --keep-alive 60` 与日志输出
- [completed] 2026-08-01 volume 改 bind mount：上传文件从 Docker 命名卷 `ftp_server_ftp_uploads` 改为宿主目录 `~/usr/database/ftp`，`docker-compose.yml` 去掉末尾的 named volume 声明
- [completed] 2026-07-31 nginx subpath 修复：reload nginx 后 `X-Script-Name: /ftp` 透传到 Flask，`url_for` 自动生成 `/ftp/download/...`；清理掉 index() 里临时的 DEBUG print；内网 + 外网验证下载链路 200
- [completed] 2026-07-31 目录重构：按全局规则 8/9 调整为 `doc/` + `src/` + `docker/` 三段式，启动文件与配置留在项目根
- [completed] 2026-07-31 下载鉴权：默认密码 `123456`，通过 `/unlock` + session 控制；`.env` 增 `DOWNLOAD_PASSWORD`