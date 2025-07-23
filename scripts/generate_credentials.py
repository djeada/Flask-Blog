import os
import json
import argparse


parser = argparse.ArgumentParser(description="Generate credentials files.")
parser.add_argument('--example', action='store_true', help='Generate credentials.json.example')
parser.add_argument('--output', type=str, default=None, help='Output file path')
parser.add_argument('--clean', action='store_true', help='Remove credentials artifacts')
args = parser.parse_args()

credentials = {
    "host": os.environ.get("BLOG_DB_HOST", "localhost"),
    "user": os.environ.get("BLOG_DB_USER", "root"),
    "password": os.environ["BLOG_DB_PASSWORD"] if "BLOG_DB_PASSWORD" in os.environ else (lambda: (_ for _ in ()).throw(ValueError("Environment variable BLOG_DB_PASSWORD must be set for database connection.")))(),
    "database": os.environ.get("BLOG_DB_NAME", "flask_db"),
    "cursor_class": os.environ.get("BLOG_DB_CURSOR", "DictCursor")
}

if args.clean:
    removed = []
    for path in ["credentials.json", "src/credentials.json.example"]:
        try:
            os.remove(path)
            removed.append(path)
        except FileNotFoundError:
            pass
    if removed:
        print(f"Removed: {', '.join(removed)}")
    else:
        print("No credentials artifacts found to remove.")
    exit(0)

if args.example:
    # Example values for credentials.json.example
    example_credentials = {
        "host": "192.168.56.1",
        "user": "root",
        "password": "root",
        "database": "flask_db",
        "cursor_class": "DictCursor"
    }
    output_path = args.output or "src/credentials.json.example"
    with open(output_path, "w") as f:
        json.dump(example_credentials, f, indent=4)
    print(f"Generated {output_path} with example values.")
else:
    output_path = args.output or "credentials.json"
    with open(output_path, "w") as f:
        json.dump(credentials, f, indent=4)
    print(f"Generated {output_path} with environment variables.")
