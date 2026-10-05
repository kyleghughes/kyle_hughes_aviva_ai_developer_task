def test_main_exports_application():
    from app.main import app, create_app
    assert app is not None
    assert callable(create_app)
