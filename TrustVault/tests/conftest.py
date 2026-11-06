import pytest
from app import create_app
from extensions import db
from models import User

@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / "test.db"
    upload_path = tmp_path / "uploads"
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path.as_posix()}",
        "UPLOAD_FOLDER": str(upload_path),
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

def make_user(app, email, role="viewer", password="strong-test-password"):
    with app.app_context():
        user = User(name=email.split("@")[0], email=email,
                    password_hash=User.hash_password(password), role=role)
        db.session.add(user)
        db.session.commit()
        return user.id
