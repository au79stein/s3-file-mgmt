# s3-file-mgmt

## What

code to write local files to a named s3 bucket using a named prefix.
Written files are tracked in a local database that tracks filename, location, hash, and allowed users.

A list of files can be specified at once.  The code will attempt to parallelize the writes.

  ```
    with concurrent.futures.ThreadPoolExecutor() as executor:
      executor.map(lambda f: upload_to_s3(f, bucket_name, s3_prefix), file_paths)


## How

specify the bucket name using the --bucket_name argument.  
similarly, the prefix can be specified with the --prefix argument
The file, or files, is specified by a single, or multiple, list of filenames


## Current Features

- s3 bucket is private and not open to the public
- parallel file writes using concurrent.futures.ThreadPoolExecutor()
- tracking of written files in locally maintained sqlite database. File metadata is stored to manage duplication and to track user access and permissions.
- file hash tracks written files and will reduce/eliminate the same file from being written to the bucket more than once
- files written to the bucket can be updated and will be tracked by a datetime stamp.  Although not implemented, it could be used to insure that file writes are scheduled and only written and updated after some amount of time has passed.
- server-side encryption (AE256) and private ACLs are implemented


## Future Improvements

1. right now a single prefix can be specified - all files specified will be written to the s3 bucket under that prefix.
   by changing the input, there is not reason to limit this, and multiple files could be specified that would be written to 
   different prefixes in parallel.

