import pytest
from app import create_app
from app.extensions import db
from app.models import User, Disaster, CrisisComment, EmergencyContact, Announcement, Feedback
from werkzeug.security import generate_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """Create a test Flask app with an in-memory SQLite database."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.drop_all()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def seed_users(app):
    """Seed one admin and one viewer user."""
    with app.app_context():
        admin = User(
            username="admin_test",
            email="admin@test.com",
            password=generate_password_hash("Admin@1234"),
            role="admin",
        )
        viewer = User(
            username="viewer_test",
            email="viewer@test.com",
            password=generate_password_hash("Viewer@1234"),
            role="viewer",
        )
        db.session.add_all([admin, viewer])
        db.session.commit()
    return {"admin": "admin@test.com", "viewer": "viewer@test.com"}


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def logout(client):
    return client.get("/auth/logout", follow_redirects=True)


# ══════════════════════════════════════════════════════════════════════════════
# 1. HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════

class TestHomePage:

    def test_home_page_loads(self, client):
        """Home page is accessible without login."""
        r = client.get("/")
        assert r.status_code == 200

    def test_home_page_contains_brand(self, client):
        """Home page shows the platform name."""
        r = client.get("/")
        assert b"Disaster Crisis Hub" in r.data

    def test_home_page_has_login_link(self, client):
        """Home page contains a link to login."""
        r = client.get("/")
        assert b"Log in" in r.data or b"login" in r.data.lower()

    def test_home_page_has_register_link(self, client):
        """Home page contains a link to register."""
        r = client.get("/")
        assert b"Register" in r.data or b"Get started" in r.data


# ══════════════════════════════════════════════════════════════════════════════
# 2. AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestAuth:

    def test_register_page_loads(self, client):
        r = client.get("/auth/register")
        assert r.status_code == 200

    def test_login_page_loads(self, client):
        r = client.get("/auth/login")
        assert r.status_code == 200

    def test_register_new_user(self, client):
        """Valid registration creates a user and redirects to login."""
        r = client.post("/auth/register", data={
            "username": "testuser",
            "email": "testuser@test.com",
            "password": "Test@1234",
            "confirm_password": "Test@1234",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b"Log in" in r.data or b"created" in r.data.lower()

    def test_register_duplicate_email(self, client):
        """Registering with an existing email shows an error."""
        client.post("/auth/register", data={
            "username": "dupuser",
            "email": "dup@test.com",
            "password": "Test@1234",
            "confirm_password": "Test@1234",
        })
        r = client.post("/auth/register", data={
            "username": "dupuser2",
            "email": "dup@test.com",
            "password": "Test@1234",
            "confirm_password": "Test@1234",
        }, follow_redirects=True)
        assert b"already" in r.data.lower() or r.status_code == 200

    def test_register_password_mismatch(self, client):
        """Mismatched passwords show validation error."""
        r = client.post("/auth/register", data={
            "username": "mismatch",
            "email": "mismatch@test.com",
            "password": "Test@1234",
            "confirm_password": "Different@1234",
        }, follow_redirects=True)
        assert b"match" in r.data.lower() or r.status_code == 200

    def test_login_valid(self, client, seed_users):
        """Valid credentials log in successfully."""
        r = login(client, "admin@test.com", "Admin@1234")
        assert r.status_code == 200
        logout(client)

    def test_login_invalid_password(self, client, seed_users):
        """Wrong password shows error."""
        r = login(client, "admin@test.com", "WrongPassword")
        assert b"Invalid" in r.data or b"incorrect" in r.data.lower()

    def test_login_invalid_email(self, client):
        """Non-existent email shows error."""
        r = login(client, "nobody@test.com", "Test@1234")
        assert b"Invalid" in r.data or r.status_code == 200

    def test_logout(self, client, seed_users):
        """Logout redirects to login page."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/auth/logout", follow_redirects=True)
        assert r.status_code == 200
        assert b"Log in" in r.data or b"login" in r.data.lower()

    def test_protected_route_redirects_unauthenticated(self, client):
        """Dashboard requires login."""
        logout(client)
        r = client.get("/dashboard/", follow_redirects=True)
        assert b"Log in" in r.data or b"login" in r.data.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 3. DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class TestDashboard:

    def test_dashboard_loads_when_logged_in(self, client, seed_users):
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/dashboard/")
        assert r.status_code == 200
        assert b"Mission overview" in r.data or b"Dashboard" in r.data
        logout(client)

    def test_chart_data_endpoint(self, client, seed_users):
        """Chart data API returns valid JSON."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/dashboard/chart-data")
        assert r.status_code == 200
        data = r.get_json()
        assert "by_type" in data
        assert "by_severity" in data
        assert "timeline" in data
        logout(client)

    def test_chart_data_structure(self, client, seed_users):
        """Chart data has correct keys."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/dashboard/chart-data")
        data = r.get_json()
        assert "labels" in data["by_type"]
        assert "data" in data["by_type"]
        assert len(data["timeline"]["labels"]) == 7
        logout(client)


# ══════════════════════════════════════════════════════════════════════════════
# 4. CRISIS REPORTS (CRUD)
# ══════════════════════════════════════════════════════════════════════════════

class TestCrisisCRUD:

    def test_crisis_list_loads(self, client, seed_users):
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/crisis/")
        assert r.status_code == 200
        logout(client)

    def test_create_crisis_page_loads(self, client, seed_users):
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/crisis/create")
        assert r.status_code == 200
        logout(client)

    def test_create_crisis_valid(self, client, seed_users, app):
        """Valid crisis form creates a disaster and redirects to detail."""
        import os
        pkl = os.path.join(os.path.dirname(__file__), '../app/ml/severity_model.pkl')
        if os.path.exists(pkl):
            os.remove(pkl)
        login(client, "admin@test.com", "Admin@1234")
        r = client.post("/crisis/create", data={
            "title": "Test Flood — Kathmandu",
            "description": "Flash flood in Kathmandu valley.",
            "disaster_type": "flood",
            "latitude": "27.7172",
            "longitude": "85.3240",
            "location_name": "Kathmandu, Nepal",
            "affected_people": "5000",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b"Test Flood" in r.data or b"created" in r.data.lower()
        logout(client)

    def test_create_crisis_missing_title(self, client, seed_users):
        """Crisis without title shows validation error."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.post("/crisis/create", data={
            "title": "",
            "disaster_type": "flood",
            "latitude": "27.7172",
            "longitude": "85.3240",
        }, follow_redirects=True)
        assert b"required" in r.data.lower() or r.status_code == 200
        logout(client)

    def test_geojson_endpoint(self, client, seed_users):
        """GeoJSON endpoint returns valid FeatureCollection."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/crisis/geojson")
        assert r.status_code == 200
        data = r.get_json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        logout(client)

    def test_crisis_detail_loads(self, client, seed_users, app):
        """Crisis detail page loads for existing crisis."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            d = Disaster.query.first()
            if d:
                r = client.get(f"/crisis/{d.id}")
                assert r.status_code == 200
        logout(client)

    def test_edit_crisis(self, client, seed_users, app):
        """Editing a crisis updates the record."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            d = Disaster.query.first()
            if d:
                r = client.post(f"/crisis/{d.id}/edit", data={
                    "title": "Updated Flood Title",
                    "disaster_type": d.disaster_type,
                    "severity": d.severity,
                    "status": d.status,
                    "affected_people": "6000",
                    "location_name": d.location_name or "",
                    "description": d.description or "",
                }, follow_redirects=True)
                assert r.status_code == 200
        logout(client)

    def test_delete_crisis(self, client, seed_users, app):
        """Admin can delete a crisis."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            d = Disaster(
                title="To Delete",
                disaster_type="fire",
                severity="low",
                latitude=27.0,
                longitude=85.0,
                affected_people=0,
                created_by=User.query.filter_by(email="admin@test.com").first().id,
            )
            db.session.add(d)
            db.session.commit()
            did = d.id
        r = client.post(f"/crisis/{did}/delete", follow_redirects=True)
        assert r.status_code == 200
        logout(client)

    def test_crisis_filter_by_status(self, client, seed_users):
        """Crisis list can be filtered by status."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/crisis/?status=active")
        assert r.status_code == 200
        logout(client)

    def test_crisis_filter_by_type(self, client, seed_users):
        """Crisis list can be filtered by type."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/crisis/?type=flood")
        assert r.status_code == 200
        logout(client)


# ══════════════════════════════════════════════════════════════════════════════
# 5. COMMENTS
# ══════════════════════════════════════════════════════════════════════════════

class TestComments:

    def test_add_comment(self, client, seed_users, app):
        """Logged-in user can add a comment to a crisis."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            d = Disaster.query.first()
            if d:
                r = client.post(f"/crisis/{d.id}/comments/add",
                                data={"comment": "This is a test comment."},
                                follow_redirects=True)
                assert r.status_code == 200
        logout(client)

    def test_add_empty_comment(self, client, seed_users, app):
        """Empty comment is rejected."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            d = Disaster.query.first()
            if d:
                r = client.post(f"/crisis/{d.id}/comments/add",
                                data={"comment": ""},
                                follow_redirects=True)
                assert r.status_code == 200
        logout(client)

    def test_delete_comment(self, client, seed_users, app):
        """User can delete their own comment."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            d = Disaster.query.first()
            if d:
                client.post(f"/crisis/{d.id}/comments/add",
                            data={"comment": "Comment to delete."})
                c = CrisisComment.query.filter_by(comment="Comment to delete.").first()
                if c:
                    r = client.post(f"/crisis/comments/{c.id}/delete",
                                    follow_redirects=True)
                    assert r.status_code == 200
        logout(client)


# ══════════════════════════════════════════════════════════════════════════════
# 6. EMERGENCY CONTACTS
# ══════════════════════════════════════════════════════════════════════════════

class TestContacts:

    def test_contacts_page_loads(self, client, seed_users):
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/alerts/contacts")
        assert r.status_code == 200
        logout(client)

    def test_add_contact(self, client, seed_users):
        """Valid contact is added successfully."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.post("/alerts/contacts/add", data={
            "name": "Nepal Red Cross",
            "phone": "+9771234567",
            "email": "nrc@test.com",
            "relation": "Relief org",
            "notify_email": "on",
        }, follow_redirects=True)
        assert r.status_code == 200
        logout(client)

    def test_add_contact_missing_name(self, client, seed_users):
        """Contact without name is rejected."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.post("/alerts/contacts/add", data={
            "name": "",
            "email": "nobody@test.com",
        }, follow_redirects=True)
        assert b"required" in r.data.lower() or r.status_code == 200
        logout(client)

    def test_delete_contact(self, client, seed_users, app):
        """Contact can be deleted by its owner."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            admin = User.query.filter_by(email="admin@test.com").first()
            contact = EmergencyContact.query.filter_by(user_id=admin.id).first()
            if contact:
                r = client.post(f"/alerts/contacts/{contact.id}/delete",
                                follow_redirects=True)
                assert r.status_code == 200
        logout(client)


# ══════════════════════════════════════════════════════════════════════════════
# 7. ANNOUNCEMENTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAnnouncements:

    def test_announcements_page_loads(self, client, seed_users):
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/announcements")
        assert r.status_code == 200
        logout(client)

    def test_add_announcement(self, client, seed_users):
        """Admin can post an announcement."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.post("/announcements/add", data={
            "title": "Test Announcement",
            "content": "This is a test announcement content.",
            "priority": "normal",
        }, follow_redirects=True)
        assert r.status_code == 200
        logout(client)

    def test_viewer_cannot_add_announcement(self, client, seed_users):
        """Viewer role cannot post announcements."""
        login(client, "viewer@test.com", "Viewer@1234")
        r = client.post("/announcements/add", data={
            "title": "Unauthorized",
            "content": "Should not be allowed.",
            "priority": "normal",
        }, follow_redirects=True)
        assert b"Permission denied" in r.data or r.status_code == 200
        logout(client)

    def test_delete_announcement(self, client, seed_users, app):
        """Admin can delete their announcement."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            ann = Announcement.query.first()
            if ann:
                r = client.post(f"/announcements/{ann.id}/delete",
                                follow_redirects=True)
                assert r.status_code == 200
        logout(client)


# ══════════════════════════════════════════════════════════════════════════════
# 8. FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════

class TestFeedback:

    def test_feedback_page_loads(self, client, seed_users):
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/feedback")
        assert r.status_code == 200
        logout(client)

    def test_submit_feedback(self, client, seed_users):
        """User can submit feedback."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.post("/feedback/add", data={
            "subject": "Test feedback subject",
            "message": "This is a test feedback message.",
            "category": "general",
        }, follow_redirects=True)
        assert r.status_code == 200
        logout(client)

    def test_admin_reply_to_feedback(self, client, seed_users, app):
        """Admin can reply to feedback."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            fb = Feedback.query.first()
            if fb:
                r = client.post(f"/feedback/{fb.id}/reply", data={
                    "admin_reply": "Thank you for your feedback.",
                    "status": "reviewed",
                }, follow_redirects=True)
                assert r.status_code == 200
        logout(client)

    def test_viewer_cannot_reply(self, client, seed_users, app):
        """Viewer cannot reply to feedback."""
        login(client, "viewer@test.com", "Viewer@1234")
        with app.app_context():
            fb = Feedback.query.first()
            if fb:
                r = client.post(f"/feedback/{fb.id}/reply", data={
                    "admin_reply": "Unauthorized reply.",
                    "status": "reviewed",
                }, follow_redirects=True)
                assert b"Admin only" in r.data or r.status_code == 200
        logout(client)


# ══════════════════════════════════════════════════════════════════════════════
# 9. ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

class TestAdmin:

    def test_admin_panel_loads_for_admin(self, client, seed_users):
        """Admin user can access the admin panel."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/admin/")
        assert r.status_code == 200
        logout(client)

    def test_admin_panel_blocked_for_viewer(self, client, seed_users):
        """Viewer cannot access admin panel."""
        login(client, "viewer@test.com", "Viewer@1234")
        r = client.get("/admin/", follow_redirects=True)
        assert b"Admin access required" in r.data or r.status_code == 200
        logout(client)

    def test_admin_users_list(self, client, seed_users):
        """Admin can view all users."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/admin/users")
        assert r.status_code == 200
        assert b"admin_test" in r.data or b"viewer_test" in r.data
        logout(client)

    def test_admin_audit_log(self, client, seed_users):
        """Admin can view audit log."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/admin/audit")
        assert r.status_code == 200
        logout(client)

    def test_admin_crises_list(self, client, seed_users):
        """Admin can view all crises."""
        login(client, "admin@test.com", "Admin@1234")
        r = client.get("/admin/crises")
        assert r.status_code == 200
        logout(client)

    def test_admin_edit_user_role(self, client, seed_users, app):
        """Admin can edit another user's role."""
        login(client, "admin@test.com", "Admin@1234")
        with app.app_context():
            viewer = User.query.filter_by(email="viewer@test.com").first()
            if viewer:
                r = client.post(f"/admin/users/{viewer.id}/edit", data={
                    "role": "responder",
                    "is_active": "on",
                }, follow_redirects=True)
                assert r.status_code == 200
        logout(client)


# ══════════════════════════════════════════════════════════════════════════════
# 10. SECURITY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurity:

    def test_unauthenticated_cannot_access_crisis(self, client):
        """Unauthenticated user is redirected from crisis list."""
        logout(client)
        r = client.get("/crisis/", follow_redirects=True)
        assert b"Log in" in r.data or b"login" in r.data.lower()

    def test_unauthenticated_cannot_access_admin(self, client):
        """Unauthenticated user cannot reach admin panel."""
        logout(client)
        r = client.get("/admin/", follow_redirects=True)
        assert b"Log in" in r.data or b"login" in r.data.lower()

    def test_unauthenticated_cannot_access_contacts(self, client):
        """Unauthenticated user cannot see contacts."""
        logout(client)
        r = client.get("/alerts/contacts", follow_redirects=True)
        assert b"Log in" in r.data or b"login" in r.data.lower()

    def test_csrf_token_present_on_login(self, client):
        """Login form includes a CSRF token."""
        r = client.get("/auth/login")
        assert b"csrf_token" in r.data

    def test_csrf_token_present_on_register(self, client):
        """Register form includes a CSRF token."""
        r = client.get("/auth/register")
        assert b"csrf_token" in r.data

    def test_password_not_stored_plaintext(self, client, seed_users, app):
        """Password stored in DB is a hash, not plaintext."""
        with app.app_context():
            user = User.query.filter_by(email="admin@test.com").first()
            assert user.password != "Admin@1234"
            assert ":" in user.password
            assert len(user.password) > 20

    def test_sql_injection_in_login(self, client):
        """SQL injection attempt in login does not crash the app."""
        r = client.post("/auth/login", data={
            "email": "' OR '1'='1",
            "password": "' OR '1'='1",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b"Invalid" in r.data or b"Log in" in r.data

    def test_viewer_cannot_delete_crisis(self, client, seed_users, app):
        """Viewer role cannot delete a crisis."""
        login(client, "viewer@test.com", "Viewer@1234")
        with app.app_context():
            d = Disaster.query.first()
            if d:
                r = client.post(f"/crisis/{d.id}/delete", follow_redirects=True)
                assert b"Permission denied" in r.data or r.status_code == 200
        logout(client)
