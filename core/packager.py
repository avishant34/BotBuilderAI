"""
Create ZIP archives of generated bot projects + optional GitHub push.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from core.config import get_settings


def create_zip_from_files(files: Dict[str, str], bot_name: str = "telegram_bot") -> bytes:
    """Create an in-memory ZIP from a dict of {relative_path: content}."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in files.items():
            # Normalize path separators
            arcname = rel_path.replace("\\", "/")
            zf.writestr(arcname, content.encode("utf-8"))
        # Always add a simple .gitignore
        zf.writestr(
            ".gitignore",
            "__pycache__/\n*.py[cod]\n.env\n.venv/\nvenv/\n.idea/\n.vscode/\n*.log\ndata/\n",
        )
    buffer.seek(0)
    return buffer.getvalue()


async def push_to_github(
    files: Dict[str, str],
    repo_name: str,
    description: str = "Generated Telegram bot",
    private: bool = False,
) -> Optional[str]:
    """
    Create a new GitHub repository and push all files.
    Returns the repo HTML URL or None on failure.
    """
    settings = get_settings()
    if not settings.GITHUB_TOKEN or not settings.GITHUB_USERNAME:
        logger.warning("GitHub token/username not configured")
        return None

    try:
        from github import Github, Auth

        auth = Auth.Token(settings.GITHUB_TOKEN)
        g = Github(auth=auth)
        user = g.get_user()

        # Create repo
        repo = user.create_repo(
            name=repo_name,
            description=description,
            private=private,
            auto_init=False,
        )

        # Push files
        for path, content in files.items():
            repo.create_file(
                path=path,
                message=f"Add {path}",
                content=content,
                branch="main",
            )

        # Add .gitignore
        repo.create_file(
            path=".gitignore",
            message="Add .gitignore",
            content="__pycache__/\n*.py[cod]\n.env\n.venv/\nvenv/\n",
            branch="main",
        )

        logger.info(f"Pushed to GitHub: {repo.html_url}")
        return repo.html_url
    except Exception as e:
        logger.error(f"GitHub push failed: {e}")
        return None


def get_deploy_instructions(bot_name: str) -> str:
    """Return ready-to-use deploy help text."""
    return f"""
🚀 **Deploy Guide for `{bot_name}`**

### 1. Local Run
```bash
# Extract ZIP
cd {bot_name}
python -m venv venv
source venv/bin/activate   # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env → put your BOT_TOKEN from @BotFather
python main.py
```

### 2. Railway (Recommended)
1. Go to https://railway.app
2. New Project → Deploy from GitHub (or upload ZIP)
3. Add variable: `BOT_TOKEN=your_token`
4. Deploy → Done

### 3. Render
1. https://render.com → New → Web Service
2. Connect repo or upload
3. Build: `pip install -r requirements.txt`
4. Start: `python main.py`
5. Add env var BOT_TOKEN

### 4. Fly.io
```bash
fly launch
fly secrets set BOT_TOKEN=your_token
fly deploy
```

### 5. Docker
```bash
docker build -t {bot_name} .
docker run -e BOT_TOKEN=your_token {bot_name}
```

Need more help? Just ask me!
""".strip()