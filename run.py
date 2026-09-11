"""
Application Entry Point for the Hiver AI Customer Support Agent.
Launches the FastAPI server with Uvicorn.
"""

import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print(" Starting Hiver AI Customer Support Agent Server...")
    print(" Dashboard URL: http://127.0.0.1:8000")
    print(" OpenAPI Docs:  http://127.0.0.1:8000/docs")
    print("=" * 70)
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
