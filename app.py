from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, session
from dotenv import load_dotenv
import os
import re
import unicodedata
import zipfile
import uuid
from datetime import datetime
from functools import wraps

load_dotenv()

app = Flask(__name__, template_folder="src/templates")
app.secret_key = os.environ.get("FLASK_SECRET", "change-me-in-production")


class ScriptNameMiddleware:
    def __init__(self, app):
        self.app = app
        self.default_subpath = os.environ.get("APP_SUBPATH", "")

    def __call__(self, environ, start_response):
        script_name = environ.get("HTTP_X_SCRIPT_NAME", "") or self.default_subpath
        if script_name:
            environ["SCRIPT_NAME"] = script_name
            path_info = environ.get("PATH_INFO", "")
            if path_info.startswith(script_name):
                environ["PATH_INFO"] = path_info[len(script_name):] or "/"
        return self.app(environ, start_response)


app.wsgi_app = ScriptNameMiddleware(app.wsgi_app)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/ftp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DOWNLOAD_PASSWORD = os.environ.get("DOWNLOAD_PASSWORD", "123456")

ALLOWED_TEXT_EXT = {".txt", ".md", ".log", ".csv", ".json", ".xml", ".yaml", ".yml", ".ini", ".conf"}
ALLOWED_ZIP_EXT = {".zip"}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def allowed_file(filename: str, allowed_exts: set) -> bool:
    if "." not in filename:
        return False
    ext = "." + filename.rsplit(".", 1)[1].lower()
    return ext in allowed_exts


def safe_unicode_filename(filename: str) -> str:
    if not filename:
        return ""
    filename = unicodedata.normalize("NFC", filename)
    filename = filename.replace("/", "").replace("\\", "").replace("\x00", "")
    filename = re.sub(r"[\x01-\x1f]", "", filename)
    filename = filename.replace("..", "")
    filename = filename.lstrip(".")
    return filename.strip()


def sanitize_filename(filename: str, fallback: str) -> str:
    name = safe_unicode_filename(filename)
    return name or fallback


def human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def _safe_next(nxt: str) -> str:
    """Resolve a `next` parameter to a safe full URL.

    - Internal path starting with single `/` → prepend script_root so the
      redirect lands back under the nginx sub-path (e.g. `/ftp`).
    - Empty / protocol-relative / external / non-path → fall back to index.
    """
    if nxt and nxt.startswith("/") and not nxt.startswith("//"):
        return request.script_root + nxt
    return url_for("index")


def download_auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("download_auth"):
            return redirect(url_for("unlock", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_auth_state():
    return {"download_authed": bool(session.get("download_auth"))}


@app.route("/unlock", methods=["GET", "POST"])
def unlock():
    nxt = request.args.get("next") or request.form.get("next") or ""
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw and pw == DOWNLOAD_PASSWORD:
            session["download_auth"] = True
            session.permanent = False
            return redirect(_safe_next(nxt))
        flash("密码错误", "error")
    return render_template("unlock.html", next=nxt)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("download_auth", None)
    flash("已退出下载授权", "success")
    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files.get("file")
        pasted_text = request.form.get("pasted_text", "").strip()
        filename_hint = request.form.get("text_filename", "").strip() or "pasted.txt"

        saved = []

        if pasted_text:
            if not allowed_file(filename_hint, ALLOWED_TEXT_EXT):
                filename_hint = filename_hint.rsplit(".", 1)[0] + ".txt"
            safe_name = sanitize_filename(filename_hint, "pasted.txt")
            unique = f"{uuid.uuid4().hex[:8]}_{safe_name}"
            full_path = os.path.join(UPLOAD_DIR, unique)
            with open(full_path, "w", encoding="utf-8") as fp:
                fp.write(pasted_text)
            saved.append(unique)

        if f and f.filename:
            if not (allowed_file(f.filename, ALLOWED_TEXT_EXT) or allowed_file(f.filename, ALLOWED_ZIP_EXT)):
                flash(f"不支持的文件类型: {f.filename}", "error")
                return redirect(url_for("index"))

            safe_name = sanitize_filename(f.filename, "upload.bin")
            unique = f"{uuid.uuid4().hex[:8]}_{safe_name}"
            full_path = os.path.join(UPLOAD_DIR, unique)
            f.save(full_path)

            if zipfile.is_zipfile(full_path):
                saved.append(unique)
            else:
                saved.append(unique)

        if saved:
            flash(f"上传成功: {', '.join(saved)}", "success")
        else:
            flash("请选择一个文件或输入文本", "error")

        return redirect(url_for("index"))

    files = []
    entries = [
        (name, os.path.join(UPLOAD_DIR, name))
        for name in os.listdir(UPLOAD_DIR)
        if os.path.isfile(os.path.join(UPLOAD_DIR, name))
    ]
    entries.sort(key=lambda e: os.path.getmtime(e[1]), reverse=True)
    for name, full in entries:
        files.append({
            "name": name,
            "size": human_size(os.path.getsize(full)),
            "mtime": os.path.getmtime(full),
            "mtime_str": datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return render_template("index.html", files=files)


@app.route("/download/<path:filename>")
@download_auth_required
def download(filename):
    safe = safe_unicode_filename(filename)
    if not safe or not os.path.isfile(os.path.join(UPLOAD_DIR, safe)):
        abort(404)
    return send_from_directory(UPLOAD_DIR, safe, as_attachment=True)


@app.route("/delete/<path:filename>", methods=["POST"])
def delete(filename):
    safe = safe_unicode_filename(filename)
    full = os.path.join(UPLOAD_DIR, safe)
    if safe and os.path.isfile(full):
        os.remove(full)
        flash(f"已删除: {safe}", "success")
    else:
        flash("文件不存在", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
