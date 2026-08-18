#!/usr/bin/env python3
"""Project Priory — Web GUI Runner.

Usage:
    python3 run_web.py
"""

import os
from web.app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    print(f"🏛️ Starting Project Priory Web GUI on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
