"""
CLI script to seed a demo workspace using the production service path.

Usage:
    python -m app.scripts.seed_demo --members 3 --files 2
"""

import argparse
import asyncio
import sys

from app.core.database import async_session_factory
from app.modules.demo.service import DemoService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo workspace using service layer")
    parser.add_argument("--members", type=int, default=2, help="Number of demo members to seed")
    parser.add_argument("--files", type=int, default=2, help="Number of demo files to seed")
    args = parser.parse_args()

    print(f"[*] Seeding demo workspace with {args.members} members and {args.files} files...")
    async with async_session_factory() as session:
        demo_service = DemoService(session)
        result = await demo_service.create_demo_session(
            ip_address="127.0.0.1",
            user_agent="CLI-SeedDemo/1.0",
            members_count=args.members,
            files_count=args.files,
        )
        print("[✓] Demo workspace created successfully!")
        print(f"    Organization ID: {result.organization_id}")
        print(f"    Session ID:      {result.session_id}")
        print(f"    Token Type:      {result.token_type}")
        print(f"    Access Token:    {result.access_token[:20]}...")
        print(f"    Refresh Token:   {result.refresh_token[:20]}...")


if __name__ == "__main__":
    asyncio.run(main())

