"""Entry point for the admin app server."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("admin_app:app", host="0.0.0.0", port=8001)
