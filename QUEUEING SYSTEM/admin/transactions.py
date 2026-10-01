import psycopg2
from database.queries import add_user, delete_user, ensure_schema


# Gets a valid account operation from the user
def get_operation():
    operation = input("QUEUEUP ACCOUNT OPERATION (create/delete/quit): ").strip().lower()
    if operation in {"create", "delete", "quit"}:
        return operation

    print("Operation must be create, delete, or quit. Please try again!")
    return get_operation()


# Creates or deletes accounts until the user quits
def main():
    while True:
#Requests the next account operation
        operation = get_operation()
        if operation == "quit":
            print("Maraming Salamat!")
            return

# Collects the account credentials
        username = input("Create Username: ").strip()
        password = input("Create Password: ")

# Rejects incomplete account information
        if not username or not password:
            print("Username and password are required!")
            continue

        try:
# Makes sure the required database tables exist
            ensure_schema()
            if operation == "delete":
# Deletes the account after checking its password
                if not delete_user(username, password):
                    print("Invalid username or password!")
                    continue
                print("User deleted successfully!")
                continue

# Adds a new account to the users table
            add_user(username, password)
            print("User created successfully!")
        except psycopg2.errors.UniqueViolation:
            print("That username already exists in this database!")
        except psycopg2.Error as error:
            print(
                "Could not update the USER. Check PostgreSQL and the .env settings!\n"
                f"{error}"
            )


if __name__ == "__main__":
    main()