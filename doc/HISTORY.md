# 变更历史

> 每次任务完成后追加：日期 + 做了什么 + 为什么。

## 2026-07-31

### nginx 反代 subpath 修复（X-Script-Name 没生效 → reload）

- **背景**：浏览器点下载跳到 `http://host:8080/download/<file>`，期望 `http://host:8080/ftp/download/<file>`，否则 nginx 没有匹配 location 会 404。
- **根因**：`ftp.locations` 里加了 `proxy_set_header X-Script-Name /ftp;`，但**没 reload nginx**，所以 `ScriptNameMiddleware`（`app.py:16-31`）看到的 `HTTP_X_SCRIPT_NAME` 仍是空，`environ["SCRIPT_NAME"]` 没被设置，Flask `url_for('download', filename=f.name)` 自然不会拼 `/ftp` 前缀。
- **架构（满足「不硬编码 URL 路径」）**：
  1. nginx → `X-Script-Name: /ftp`
  2. `ScriptNameMiddleware` → `environ["SCRIPT_NAME"] = "/ftp"`，并把 `PATH_INFO` 剥掉 `/ftp`
  3. Flask `url_for(...)` 自动用 `SCRIPT_NAME` 拼前缀 → `/ftp/download/<file>`
  - 代码全文 grep 无 `/ftp` 字面量，纯靠 nginx header 驱动
- **变更**：
  - `sudo docker exec nginx1.30 nginx -s reload` 让新 header 配置生效
  - `app.py` 删掉 `index()` 里排查用的 DEBUG print
- **验证**：
  - 内网 `http://127.0.0.1:8080/ftp/` 与外网 `http://119.45.48.180:8080/ftp/` 渲染出的下载链接均为 `/ftp/download/...`
  - 带 cookie 实测 `/ftp/download/eb87e01b_RTX5090_SoulX_LiveAct__.md` → HTTP 200，51951 B，内容正确

### 目录重构（doc / src / docker + 根目录启动配置）

- **背景**：原结构为 `app/app.py` + `docker/`，与全局规则 8/9 不符——启动文件未在根目录、缺少 `doc/` 任务追踪、没有 `src/` 源代码目录。
- **变更**：
  - 将 `app/app.py` 上移到 `ftp_server/app.py`（启动文件必须位于根目录）
  - `pyproject.toml` / `uv.lock` 同步上移；`templates/` 迁入 `src/templates/`
  - `app.py` 设置 `template_folder="src/templates"`
  - `docker/web/Dockerfile` 改为 `build.context: ..`，多了一步 `COPY src ./src`
  - `docker-compose.yml` 中 web 服务的 `build.context` 改为 `..`、`dockerfile` 改为 `docker/web/Dockerfile`
  - `.dockerignore` 从 `docker/` 移到项目根（Docker 只看 build context 根目录的 `.dockerignore`）
  - 新建 `doc/TASK.md` 与 `doc/HISTORY.md`，记录任务与变更
- **验证**：`uv sync --frozen` 通过；Flask 测试客户端验证「未登录 302 → 解锁 200 → 错误密码 → 正确密码 302 → 已授权 download 404」流程全部 OK。

### 下载鉴权（默认密码 123456）

- **背景**：原 Web 下载完全开放，需要按用户要求加密码。
- **关键决策**：
  - 用 Flask session（不是 HTTP Basic Auth）—— 体验更顺，UI 已有原生的「解锁」页面
  - 一次解锁本次会话内所有下载免输入；提供 `/logout` 主动锁定
  - 密码走 `.env` 的 `DOWNLOAD_PASSWORD`，默认 `123456`（覆盖代码里的 `os.environ.get(..., "123456")`）
- **变更**：
  - `app.py` 新增 `download_auth_required` 装饰器、`/unlock` GET/POST、`/logout` POST
  - 路由 `/download/<path:filename>` 套上 `@download_auth_required`
  - 新模板 `src/templates/unlock.html`；`index.html` 顶部按 `download_authed` 渲染「🔓 已解锁 + 退出」条
  - 根目录新增 `.env` / `.env.example`，docker-compose 用 `env_file: ../.env`
