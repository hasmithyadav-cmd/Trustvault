import os
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort, send_file, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import select
from extensions import db
from models import User, Document, Permission, AuditLog
from audit import write_audit, verify_audit_chain
from forms import RegisterForm, LoginForm, UploadForm, ShareForm
from config import Config

login_manager = LoginManager()
csrf = CSRFProtect()

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def can_view_document(user, document):
    if user.role == "admin" or document.owner_id == user.id:
        return True
    permission = db.session.scalar(
        select(Permission).where(
            Permission.document_id == document.id,
            Permission.user_id == user.id,
            Permission.active.is_(True),
            Permission.can_view.is_(True),
        )
    )
    return permission is not None


def can_download_document(user, document):
    if user.role == "admin" or document.owner_id == user.id:
        return True
    permission = db.session.scalar(
        select(Permission).where(
            Permission.document_id == document.id,
            Permission.user_id == user.id,
            Permission.active.is_(True),
            Permission.can_download.is_(True),
        )
    )
    return permission is not None


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:; "
            "form-action 'self'; frame-ancestors 'none'"
        )
        return response

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = RegisterForm()
        if form.validate_on_submit():
            email = form.email.data.strip().lower()
            if db.session.scalar(select(User).where(User.email == email)):
                flash("An account with that email already exists.", "error")
            else:
                user = User(
                    name=form.name.data.strip(),
                    email=email,
                    password_hash=User.hash_password(form.password.data),
                    role="viewer",
                )
                db.session.add(user)
                db.session.commit()
                write_audit("user.register", actor_id=user.id, detail=f"New account: {email}")
                login_user(user)
                flash("Account created. Your role is Viewer until an Owner shares a document with you.", "success")
                return redirect(url_for("dashboard"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = LoginForm()
        if form.validate_on_submit():
            email = form.email.data.strip().lower()
            user = db.session.scalar(select(User).where(User.email == email))
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                write_audit("user.login", actor_id=user.id, detail="Successful login")
                return redirect(url_for("dashboard"))
            write_audit("user.login_failed", detail=f"Failed login for {email}")
            flash("Email or password is incorrect.", "error")
        return render_template("login.html", form=form)

    @app.post("/logout")
    @login_required
    def logout():
        write_audit("user.logout", actor_id=current_user.id, detail="User logged out")
        logout_user()
        return redirect(url_for("index"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        if current_user.role == "admin":
            documents = db.session.scalars(select(Document).order_by(Document.created_at.desc())).all()
        else:
            owned = db.session.scalars(
                select(Document).where(Document.owner_id == current_user.id)
                .order_by(Document.created_at.desc())
            ).all()
            shared_ids = db.session.scalars(
                select(Permission.document_id).where(
                    Permission.user_id == current_user.id,
                    Permission.active.is_(True),
                    Permission.can_view.is_(True),
                )
            ).all()
            shared = db.session.scalars(
                select(Document).where(Document.id.in_(shared_ids))
                .order_by(Document.created_at.desc())
            ).all() if shared_ids else []
            documents = list({doc.id: doc for doc in owned + shared}.values())
        return render_template("dashboard.html", documents=documents)

    @app.route("/upload", methods=["GET", "POST"])
    @login_required
    def upload():
        form = UploadForm()
        if form.validate_on_submit():
            file = form.file.data
            original_name = secure_filename(file.filename or "")
            if not original_name or not allowed_file(original_name):
                flash("File type not allowed. Accepted: PDF, PNG, JPG, TXT and DOCX.", "error")
                return render_template("upload.html", form=form)
            file.stream.seek(0, os.SEEK_END)
            size = file.stream.tell()
            file.stream.seek(0)
            if size == 0 or size > MAX_FILE_BYTES:
                flash("Choose a non-empty file no larger than 10 MB.", "error")
                return render_template("upload.html", form=form)
            stored_name = os.urandom(24).hex()
            destination = Path(current_app.config["UPLOAD_FOLDER"]) / stored_name
            file.save(destination)
            document = Document(
                owner_id=current_user.id,
                original_name=original_name,
                stored_name=stored_name,
                mime_type=file.mimetype or "application/octet-stream",
                size_bytes=size,
            )
            db.session.add(document)
            db.session.commit()
            write_audit("document.upload", actor_id=current_user.id, document_id=document.id,
                        detail=f"Uploaded {original_name} ({size} bytes)")
            flash("Document uploaded successfully.", "success")
            return redirect(url_for("document_detail", document_id=document.id))
        return render_template("upload.html", form=form)

    @app.get("/documents/<int:document_id>")
    @login_required
    def document_detail(document_id):
        document = db.session.get(Document, document_id)
        if not document:
            abort(404)
        if not can_view_document(current_user, document):
            write_audit("document.view_denied", actor_id=current_user.id, document_id=document.id,
                        detail="View permission missing")
            db.session.commit()
            abort(403)
        write_audit("document.view", actor_id=current_user.id, document_id=document.id,
                    detail="Viewed document details")
        permissions = db.session.scalars(
            select(Permission).where(Permission.document_id == document.id, Permission.active.is_(True))
        ).all() if document.owner_id == current_user.id or current_user.role == "admin" else []
        users = db.session.scalars(select(User).where(User.id != document.owner_id).order_by(User.email)).all()
        share_form = ShareForm()
        return render_template("document_detail.html", document=document, permissions=permissions,
                               users=users, share_form=share_form,
                               can_download=can_download_document(current_user, document),
                               is_owner=(document.owner_id == current_user.id or current_user.role == "admin"))

    @app.get("/documents/<int:document_id>/download")
    @login_required
    def download_document(document_id):
        document = db.session.get(Document, document_id)
        if not document:
            abort(404)
        if not can_download_document(current_user, document):
            write_audit("document.download_denied", actor_id=current_user.id, document_id=document.id,
                        detail="Download permission missing")
            db.session.commit()
            abort(403)
        path = Path(current_app.config["UPLOAD_FOLDER"]) / document.stored_name
        if not path.is_file():
            abort(404)
        write_audit("document.download", actor_id=current_user.id, document_id=document.id,
                    detail="Downloaded document")
        return send_file(path, as_attachment=True, download_name=document.original_name,
                         mimetype="application/octet-stream")

    @app.post("/documents/<int:document_id>/share")
    @login_required
    def share_document(document_id):
        document = db.session.get(Document, document_id)
        if not document:
            abort(404)
        if document.owner_id != current_user.id and current_user.role != "admin":
            write_audit("permission.grant_denied", actor_id=current_user.id, document_id=document.id,
                        detail="Only owner or admin may share")
            db.session.commit()
            abort(403)
        form = ShareForm()
        if not form.validate_on_submit():
            flash("Please check the sharing form.", "error")
            return redirect(url_for("document_detail", document_id=document.id))
        target = db.session.get(User, form.user_id.data)
        if not target or target.id == document.owner_id:
            flash("Select a valid recipient.", "error")
            return redirect(url_for("document_detail", document_id=document.id))
        permission = db.session.scalar(
            select(Permission).where(Permission.document_id == document.id,
                                     Permission.user_id == target.id)
        )
        if permission:
            permission.active = True
            permission.can_view = True
            permission.can_download = form.can_download.data
            permission.granted_by_id = current_user.id
            permission.updated_at = datetime.now(timezone.utc)
        else:
            permission = Permission(
                document_id=document.id, user_id=target.id, granted_by_id=current_user.id,
                can_view=True, can_download=form.can_download.data, active=True
            )
            db.session.add(permission)
        db.session.commit()
        write_audit("permission.granted", actor_id=current_user.id, document_id=document.id,
                    detail=f"Granted access to user_id={target.id}; download={form.can_download.data}")
        flash(f"Access granted to {target.email}.", "success")
        return redirect(url_for("document_detail", document_id=document.id))

    @app.post("/permissions/<int:permission_id>/revoke")
    @login_required
    def revoke_permission(permission_id):
        permission = db.session.get(Permission, permission_id)
        if not permission:
            abort(404)
        document = db.session.get(Document, permission.document_id)
        if document.owner_id != current_user.id and current_user.role != "admin":
            write_audit("permission.revoke_denied", actor_id=current_user.id,
                        document_id=document.id, detail="Only owner or admin may revoke")
            db.session.commit()
            abort(403)
        permission.active = False
        permission.can_view = False
        permission.can_download = False
        permission.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        write_audit("permission.revoked", actor_id=current_user.id, document_id=document.id,
                    detail=f"Revoked permission_id={permission.id}")
        flash("Access revoked immediately for future requests.", "success")
        return redirect(url_for("document_detail", document_id=document.id))

    @app.get("/admin")
    @login_required
    def admin_dashboard():
        if current_user.role != "admin":
            abort(403)
        users = db.session.scalars(select(User).order_by(User.created_at.desc())).all()
        logs = db.session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)).all()
        chain_ok = verify_audit_chain()
        return render_template("admin.html", users=users, logs=logs, chain_ok=chain_ok)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, message="You do not have permission to do that."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="The requested page or document was not found."), 404

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        print("Database tables created.")

    @app.cli.command("bootstrap-admin")
    def bootstrap_admin_command():
        """Create the first admin from deployment environment variables.

        Safe to run on every startup: if an admin already exists, it does nothing.
        """
        email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
        name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "").strip()
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")

        if not email or not name or len(password) < 12:
            raise SystemExit(
                "Set BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_NAME, and "
                "BOOTSTRAP_ADMIN_PASSWORD (at least 12 characters)."
            )

        existing_admin = db.session.scalar(
            select(User).where(User.role == "admin")
        )
        if existing_admin:
            print("An administrator already exists; bootstrap skipped.")
            return

        user = db.session.scalar(select(User).where(User.email == email))
        if user:
            user.name = name
            user.password_hash = User.hash_password(password)
            user.role = "admin"
        else:
            user = User(
                name=name,
                email=email,
                password_hash=User.hash_password(password),
                role="admin",
            )
            db.session.add(user)

        db.session.commit()
        print("Initial administrator account created.")

    @app.cli.command("create-admin")
    def create_admin_command():
        import getpass
        email = input("Admin email: ").strip().lower()
        name = input("Admin name: ").strip()
        password = getpass.getpass("Admin password (12+ characters): ")
        if len(password) < 12:
            raise SystemExit("Password must be at least 12 characters.")
        if db.session.scalar(select(User).where(User.email == email)):
            raise SystemExit("That email already exists.")
        admin = User(name=name, email=email, password_hash=User.hash_password(password), role="admin")
        db.session.add(admin)
        db.session.commit()
        print("Admin account created.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
