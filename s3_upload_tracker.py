#!/usr/bin/env python3

import os
import hashlib
import boto3
import sqlite3
import concurrent.futures
import argparse
from datetime import datetime
from botocore.exceptions import NoCredentialsError

# AWS S3 Configuration
#BUCKET_NAME = "cloudnost"
S3_REGION = "us-east-1"  # Change as needed

# SQLite Configuration
DB_FILE = "uploads.db"

def initialize_db():
    """Initializes the database with required tables, ensuring 'allowed_users' exists."""
    debug = 1
    if debug > 0: print(f"initializing db")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            bucket_name TEXT, 
            s3_prefix TEXT,
            s3_key TEXT UNIQUE,
            file_hash TEXT,
            timestamp TEXT,
            allowed_users TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


# Initialize S3 Client
s3 = boto3.client("s3", region_name=S3_REGION)

def get_file_hash(file_path):
    """Compute MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def upload_to_s3(file_path, bucket_name, s3_prefix):
    """Uploads a file to S3 and updates SQLite database."""
    initialize_db()

    try:
        file_name = os.path.basename(file_path)
        s3_key = f"{s3_prefix}/{file_name}" if s3_prefix else file_name
        file_hash = get_file_hash(file_path)

        # Upload file with encryption and private ACL
        s3.upload_file(
            file_path, bucket_name, s3_key,
            ExtraArgs={
                "ServerSideEncryption": "AES256",
                "ACL": "private"
            }
        )

        # Record upload details
        store_metadata(file_name, bucket_name, s3_prefix, s3_key, file_hash)
        print(f"Uploaded {file_name} to s3://{bucket_name}/{s3_key}")

    except NoCredentialsError:
        print("AWS credentials not found.")
    except Exception as e:
        print(f"Error uploading {file_name}: {e}")

def store_metadata(file_name, bucket_name, s3_prefix, s3_key, file_hash):
    """Stores file metadata in SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            bucket_name TEXT,
            s3_prefix TEXT,
            s3_key TEXT UNIQUE,
            file_hash TEXT,
            timestamp TEXT,
            allowed_users TEXT DEFAULT ''
        )"""
    )
    conn.execute("PRAGMA journal_mode=WAL;")  # Improves reliability

    timestamp = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO uploads (file_name, bucket_name, s3_prefix, s3_key, file_hash, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(s3_key) DO UPDATE SET
        file_hash=excluded.file_hash,
        timestamp=excluded.timestamp
    """, (file_name, bucket_name, s3_prefix, s3_key, file_hash, timestamp))
    
    conn.commit()
    conn.close()

def upload_multiple_files(file_paths, bucket_name, s3_prefix):
    """Uploads multiple files in parallel."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(lambda f: upload_to_s3(f, bucket_name, s3_prefix), file_paths)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload files to S3 with a specified prefix.")
    parser.add_argument("--bucket_name", required=True, help="S3 prefix to organize files.")
    parser.add_argument("--prefix", required=True, help="S3 prefix to organize files.")
    parser.add_argument("files", nargs='+', help="List of files to upload.")
    args = parser.parse_args()
    
    upload_multiple_files(args.files, args.bucket_name, args.prefix)

