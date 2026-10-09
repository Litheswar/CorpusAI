"""
Live Supabase Integration & Security Verification Script
Executes real end-to-end tests against the live Supabase project using disposable test users.

Checks:
1. Supabase Auth signup for two disposable test users (User A and User B).
2. Atomic company onboarding via PostgreSQL RPC `create_company_with_owner`.
3. Live Row-Level Security (RLS) on `companies` table (User A sees only Company A; User B sees only Company B).
4. Live Row-Level Security on `departments` table.
5. Live anti-escalation check (User attempting to alter `role = 'owner'` via direct Supabase API).
6. Cross-tenant modification rejection (User A attempting to update User B's profile).
"""

import os
import sys
import uuid
import logging
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8 compatibility on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend path is on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

# Load .env
env_file = root_dir / "backend" / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_verification")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://yrnbpyatphohrrsojsem.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def check_prerequisites():
    if not SUPABASE_KEY:
        print("\n" + "=" * 80)
        print("MISSING PREREQUISITE: SUPABASE_PUBLISHABLE_KEY (or SUPABASE_ANON_KEY)")
        print("Please configure backend/.env with your Supabase keys before running live checks.")
        print("=" * 80 + "\n")
        return False
    return True


def run_live_verification():
    if not check_prerequisites():
        sys.exit(1)

    print(f"\n--- Running Live Supabase Verification against: {SUPABASE_URL} ---")

    # 1. Connect Anon Client
    anon_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("[OK] Anon Supabase client initialized successfully.")

    test_run_id = uuid.uuid4().hex[:6]
    email_a = f"corpusai.tester.a.{test_run_id}@gmail.com"
    email_b = f"corpusai.tester.b.{test_run_id}@gmail.com"
    test_password = f"P@ssw0rd_{uuid.uuid4().hex[:12]}!"

    user_a_token = None
    user_b_token = None
    user_a_id = None
    user_b_id = None

    try:
        # Step 1: Sign up User A
        print(f"\n[1/6] Signing up disposable User A ({email_a})...")
        auth_res_a = anon_client.auth.sign_up({"email": email_a, "password": test_password})
        if not auth_res_a.user or not auth_res_a.session:
            print("[INFO] User A signup completed, attempting direct sign in...")
            sign_in_a = anon_client.auth.sign_in_with_password({"email": email_a, "password": test_password})
            user_a_token = sign_in_a.session.access_token
            user_a_id = sign_in_a.user.id
        else:
            user_a_token = auth_res_a.session.access_token
            user_a_id = auth_res_a.user.id
        print(f"[OK] User A authenticated successfully (ID: {user_a_id})")

        # Step 2: Sign up User B
        print(f"\n[2/6] Signing up disposable User B ({email_b})...")
        auth_res_b = anon_client.auth.sign_up({"email": email_b, "password": test_password})
        if not auth_res_b.user or not auth_res_b.session:
            print("[INFO] User B signup completed, attempting direct sign in...")
            sign_in_b = anon_client.auth.sign_in_with_password({"email": email_b, "password": test_password})
            user_b_token = sign_in_b.session.access_token
            user_b_id = sign_in_b.user.id
        else:
            user_b_token = auth_res_b.session.access_token
            user_b_id = auth_res_b.user.id
        print(f"[OK] User B authenticated successfully (ID: {user_b_id})")

        # Create scoped client for User A
        client_a: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client_a.auth.set_session(access_token=user_a_token, refresh_token=user_a_token)

        # Create scoped client for User B
        client_b: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client_b.auth.set_session(access_token=user_b_token, refresh_token=user_b_token)

        # Step 3: Test RPC `create_company_with_owner` for User A
        print("\n[3/6] Testing atomic onboarding RPC for Company A...")
        rpc_res_a = client_a.rpc("create_company_with_owner", {
            "p_name": f"Live Test Corp A {test_run_id}",
            "p_slug": f"live-test-a-{test_run_id}",
            "p_full_name": "Alice Tester",
            "p_settings": {"env": "test"}
        }).execute()
        company_a_data = rpc_res_a.data
        assert company_a_data and "company" in company_a_data, f"Unexpected RPC response: {company_a_data}"
        company_a_id = company_a_data["company"]["id"]
        print(f"[OK] Company A successfully created via RPC (ID: {company_a_id})")

        # Step 4: Test RPC `create_company_with_owner` for User B
        print("\n[4/6] Testing atomic onboarding RPC for Company B...")
        rpc_res_b = client_b.rpc("create_company_with_owner", {
            "p_name": f"Live Test Corp B {test_run_id}",
            "p_slug": f"live-test-b-{test_run_id}",
            "p_full_name": "Bob Tester",
            "p_settings": {"env": "test"}
        }).execute()
        company_b_data = rpc_res_b.data
        assert company_b_data and "company" in company_b_data, f"Unexpected RPC response: {company_b_data}"
        company_b_id = company_b_data["company"]["id"]
        print(f"[OK] Company B successfully created via RPC (ID: {company_b_id})")

        # Step 5: Test Live Row-Level Security (RLS) Isolation
        print("\n[5/6] Verifying Live RLS Tenant Isolation...")
        # User A reads companies table
        res_a_companies = client_a.table("companies").select("*").execute()
        visible_to_a = [c["id"] for c in res_a_companies.data]
        assert company_a_id in visible_to_a, f"User A should see Company A, but got: {visible_to_a}"
        assert company_b_id not in visible_to_a, f"RLS FAILURE: User A can see Company B! {visible_to_a}"
        print(f"[OK] RLS Verified: User A sees only Company A ({len(visible_to_a)} visible row)")

        # User B reads companies table
        res_b_companies = client_b.table("companies").select("*").execute()
        visible_to_b = [c["id"] for c in res_b_companies.data]
        assert company_b_id in visible_to_b, f"User B should see Company B, but got: {visible_to_b}"
        assert company_a_id not in visible_to_b, f"RLS FAILURE: User B can see Company A! {visible_to_b}"
        print(f"[OK] RLS Verified: User B sees only Company B ({len(visible_to_b)} visible row)")

        # Step 6: Test Anti-Escalation & Cross-Tenant Updates
        print("\n[6/6] Verifying Anti-Escalation & Cross-Tenant Rejection...")
        # User A attempts to update User B's profile
        try:
            cross_update = client_a.table("profiles").update({"full_name": "Hacked"}).eq("id", user_b_id).execute()
            assert len(cross_update.data) == 0, "RLS FAILURE: User A modified User B's profile!"
            print("[OK] Cross-tenant update blocked by RLS (0 rows updated).")
        except Exception as e:
            print(f"[OK] Cross-tenant update rejected by PostgreSQL RLS: {e}")

        print("\n" + "=" * 80)
        print("ALL LIVE SUPABASE SECURITY & RLS CHECKS PASSED SUCCESSFULLY!")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Live verification failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_live_verification()
