"""Entry point for the admin app server."""

from granian import Granian

if __name__ == "__main__":
    Granian("admin_app:app", address="0.0.0.0", port=8001, interface="asgi").serve()
