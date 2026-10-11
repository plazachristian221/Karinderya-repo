
import os
import psycopg2

# Read the Railway database URL from an environment variable.
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    print("ERROR: DATABASE_URL is not configured.")
    print("Set it in PowerShell before running this script.")
    raise SystemExit(1)

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )

try:
    with psycopg2.connect(
        database_url,
        connect_timeout=10,
        sslmode="require"
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, role FROM users WHERE username = %s",
                ("admin",)
            )
            user = cur.fetchone()

            if user is None:
                print("Admin account not found.")
            else:
                print("Admin account:", user)

                if user[2] != "admin":
                    cur.execute(
                        "UPDATE users SET role = 'admin' WHERE username = %s",
                        ("admin",)
                    )
                    print("Admin role updated successfully.")
                else:
                    print("This account already has the admin role.")

except Exception as error:
    print("Database error:", error)
