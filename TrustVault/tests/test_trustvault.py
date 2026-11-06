import io
from tests.conftest import make_user
from extensions import db
from models import Document, Permission, AuditLog
from audit import verify_audit_chain

PASSWORD = "strong-test-password"

def login(client, email):
    return client.post("/login", data={"email": email, "password": PASSWORD}, follow_redirects=True)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

def test_registration_creates_viewer(app, client):
    response = client.post("/register", data={
        "name": "Test Person", "email": "new@example.com",
        "password": "a-long-test-password", "confirm_password": "a-long-test-password"
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        from models import User
        user = db.session.query(User).filter_by(email="new@example.com").one()
        assert user.role == "viewer"

def test_owner_can_upload_and_download(app, client):
    make_user(app, "owner@example.com", "owner")
    login(client, "owner@example.com")
    response = client.post("/upload", data={"file": (io.BytesIO(b"sample file"), "notes.txt")},
                           content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        doc = db.session.query(Document).one()
        doc_id = doc.id
    download = client.get(f"/documents/{doc_id}/download")
    assert download.status_code == 200
    assert download.data == b"sample file"

def test_viewer_cannot_download_without_permission(app, client):
    make_user(app, "owner@example.com", "owner")
    make_user(app, "viewer@example.com", "viewer")
    with app.app_context():
        owner_id = db.session.query(__import__("models").User).filter_by(email="owner@example.com").one().id
        doc = Document(owner_id=owner_id, original_name="secret.txt", stored_name="storedsecret",
                       mime_type="text/plain", size_bytes=6)
        db.session.add(doc)
        db.session.commit()
        (app.config["UPLOAD_FOLDER"] and __import__("pathlib").Path(app.config["UPLOAD_FOLDER"]) /
         "storedsecret").write_bytes(b"secret")
        doc_id = doc.id
    login(client, "viewer@example.com")
    assert client.get(f"/documents/{doc_id}/download").status_code == 403

def test_revocation_blocks_future_downloads(app, client):
    make_user(app, "owner@example.com", "owner")
    make_user(app, "viewer@example.com", "viewer")
    with app.app_context():
        from models import User
        owner = db.session.query(User).filter_by(email="owner@example.com").one()
        viewer = db.session.query(User).filter_by(email="viewer@example.com").one()
        doc = Document(owner_id=owner.id, original_name="file.txt", stored_name="storedfile",
                       mime_type="text/plain", size_bytes=4)
        db.session.add(doc)
        db.session.commit()
        permission = Permission(document_id=doc.id, user_id=viewer.id, granted_by_id=owner.id,
                                can_view=True, can_download=True, active=True)
        db.session.add(permission)
        db.session.commit()
        doc_id, permission_id = doc.id, permission.id
        from pathlib import Path
        (Path(app.config["UPLOAD_FOLDER"]) / "storedfile").write_bytes(b"data")
    login(client, "owner@example.com")
    revoke_response = client.post(f"/permissions/{permission_id}/revoke", follow_redirects=True)
    assert revoke_response.status_code == 200
    client.post("/logout")
    login(client, "viewer@example.com")
    assert client.get(f"/documents/{doc_id}/download").status_code == 403

def test_audit_chain_detects_tampering(app):
    with app.app_context():
        from audit import write_audit
        write_audit("test.event", detail="first")
        assert verify_audit_chain() is True
        entry = db.session.query(AuditLog).first()
        entry.detail = "changed"
        db.session.commit()
        assert verify_audit_chain() is False
