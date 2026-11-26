"""Find out why a login fails, and optionally set a new password.

Run from the project folder:  python check_login.py
"""
from getpass import getpass
from sqlalchemy import func
from database import SessionLocal
from models import Employee


def main():
    email = input("Email you type on the login page: ").strip()
    db = SessionLocal()
    try:
        exact = db.query(Employee).filter(Employee.email == email).first()
        emp = exact or db.query(Employee).filter(func.lower(Employee.email) == email.lower()).first()
        if not emp:
            total = db.query(Employee).count()
            print(f"\nPROBLEM: no employee has that email. The table has {total} employee(s).")
            for e in db.query(Employee).order_by(Employee.id).limit(10).all():
                print(f"   id={e.id}  email={e.email!r}  role={e.role}")
            return

        print(f"\nFound: id={emp.id}, email={emp.email!r}, role={emp.role}, is_active={emp.is_active}")
        if exact is None:
            print(f"NOTE: the stored email is {emp.email!r}; it only matches when letter case is ignored.")
        if not emp.is_active:
            print("PROBLEM: this account is inactive (is_active = false). Login is refused for inactive accounts.")

        h = emp.password_hash or ""
        print(f"Stored hash: {len(h)} characters, starts with {h[:7]!r}")
        if not (h.startswith(("$2a$", "$2b$", "$2y$")) and len(h) == 60):
            print("PROBLEM: this is not a bcrypt hash (bcrypt hashes are 60 characters and start with $2b$).")
            print("         The app can only verify bcrypt hashes, so this password can never match.")
            print("         Set a new password below.")

        pw = getpass("Password to test (hidden): ")
        try:
            from routers.auth import verify_password
            ok = verify_password(pw, h)
        except Exception as e:
            if type(e).__name__ == "UnknownHashError":
                print("PROBLEM: the stored value is not a valid password hash, so it cannot be checked.")
            else:
                print(f"PROBLEM: the password library failed: {type(e).__name__}: {e}")
                print('         Fix: pip install "bcrypt==4.0.1" "passlib[bcrypt]"')
        else:
            print("RESULT: the password matches. Login should work." if ok
                  else "PROBLEM: that password does NOT match the stored hash.")

        if input("\nSet a new password for this account now? (y/n): ").strip().lower() == "y":
            from routers.auth import get_password_hash
            new = getpass("New password (8+ characters): ")
            if getpass("Confirm new password: ") != new:
                print("Passwords do not match. Nothing changed.")
                return
            if not 8 <= len(new.encode("utf-8")) <= 72:
                print("Password must be 8 to 72 bytes. Nothing changed.")
                return
            emp.password_hash = get_password_hash(new)
            if not emp.is_active and input("Account is inactive. Activate it too? (y/n): ").strip().lower() == "y":
                emp.is_active = True
            db.commit()
            print("Done. Try logging in with the new password.")
    finally:
        db.close()


if __name__ == "__main__":
    main()