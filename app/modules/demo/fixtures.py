"""
DEMO MODULE — fixtures.py

Plain data inputs for generating live demo workspaces.
No ORM objects or canned responses live here.
"""

DEMO_DEFAULT_PASSWORD = "DemoPassword123!"

DEMO_ORG_NAMES = [
    "Nexus AI Technologies",
    "Apex Cloud Analytics",
    "Horizon Data Systems",
    "Vanguard Autonomous Lab",
]

DEMO_MEMBERS_FIXTURES = [
    {"role": "admin", "name_prefix": "sarah.admin"},
    {"role": "member", "name_prefix": "alex.dev"},
    {"role": "member", "name_prefix": "elena.research"},
]

DEMO_INVITES_FIXTURES = [
    "jordan.product@partner-demo.io",
    "marcus.security@audit-preview.org",
]

DEMO_SAMPLE_FILES = [
    {
        "filename": "q3_financial_model.csv",
        "content": (
            "Quarter,Revenue_USD,COGS_USD,Operating_Expenses,EBITDA\n"
            "Q1,1250000,320000,450000,480000\n"
            "Q2,1480000,360000,490000,630000\n"
            "Q3,1820000,410000,530000,880000\n"
        ).encode("utf-8"),
    },
    {
        "filename": "workspace_guidelines.txt",
        "content": (
            "Welcome to the multi-tenant SaaS workspace demonstration!\n\n"
            "This tenant operates under real PostgreSQL data isolation, RBAC policies,\n"
            "quota tracking, and streaming audit logging.\n"
        ).encode("utf-8"),
    },
]

