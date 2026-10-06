# How to run the demo

There are two versions of this demo. 
 - Part one uses the AWS Console and requires the user to manually configure and setup S3 and Lambda by themselves. 

 - Part two is a fully deployable version from the cli, and deploys the frontend UI to AWS as well

## Prerequisite software

 - `git`
 - Python 3 (check with `python3 --version`)
 - IDE (e.g. VS Code)
 - AWS CLI and AWS SAM CLI (only required for Part 2)

## Before you start

 - Clone this repo to an easy-to-find folder on your computer:
   ```
   git clone https://github.com/varunan-vara/aws-demo-quickdrop-app.git
   ```
 - Create a Root Account on AWS
 
   **NOTE**: It is highly recommended that you create an IAM User in your console (search for IAM / ...) and use that account to login. 


## Part One

### Access the AWS Console

1. Go to the [AWS Console login page](https://aws.amazon.com/console/)
2. Click 'Sign in to Console' and either create an account or login. 
    - If you are signing up for an account, you will need to verify your email before choosing a password.
    - After creating a password, select the 'Free' AWS Account Plan - this will get you enough credits to experiment with the main services offered by AWS.

3. Look at the top right of the console - this is your region (e.g. 'US East (Ohio)'). Pick one and **stay in it for everything below**. Your bucket and your Lambda must be in the same region.

### Create your S3 Bucket

This is where the uploaded files will live.

1. Search for 'S3' in the top search bar and open it
2. Click 'Create bucket'
3. Enter a bucket name: `<YOUR-BUCKET-NAME>`
    - Bucket names must be unique across all of AWS, so try something like `quickdrop-<YOUR-INITIALS>-<RANDOM-NUMBER>`
    - Lowercase letters, numbers and hyphens only
    - **Write it down**, you will need it three more times
4. Leave 'Block all public access' ticked - nobody should be able to read a file unless we give them a link
5. Leave everything else as the default and click 'Create bucket'

### Allow your website to talk to S3 (CORS)

Without this, your browser will refuse to upload straight to S3.

1. Open your bucket and go to the 'Permissions' tab
2. Scroll down to 'Cross-origin resource sharing (CORS)' and click 'Edit'
3. Paste in:
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST"],
       "AllowedOrigins": ["http://localhost:8000"],
       "ExposeHeaders": ["ETag"],
       "MaxAgeSeconds": 3000
     }
   ]
   ```
4. Click 'Save changes'

### Delete files after 1 day

So you never get charged for storage you forgot about.

1. In your bucket, go to the 'Management' tab and click 'Create lifecycle rule'
2. Rule name: `delete-after-1-day`
3. Rule scope: 'Apply to all objects in the bucket', and tick the box to acknowledge
4. Tick 'Expire current versions of objects'
5. Days after object creation: `1`
6. Click 'Create rule'

### Create your Lambda function

This is the code that creates the upload and download links.

1. Search for 'Lambda' in the top search bar and open it
2. Click 'Create function' and choose 'Author from scratch'
3. Function name: `quickdrop-presign`
4. Runtime: Python 3.13 (or the newest Python available)
5. Leave everything else as the default and click 'Create function'

### Add the code

The code is two files, both in the `backend` folder of the repo you cloned.

1. On your function page, open the 'Code' tab
2. In the file list on the left, right-click `lambda_function.py` and delete it
3. Click 'File' > 'New File', paste in everything from `backend/app.py`, then 'File' > 'Save As' and name it `app.py`
4. Do the same with `backend/utils.py`, saved as `utils.py`
5. Scroll down to 'Runtime settings', click 'Edit', and change the Handler to:
   ```
   app.lambda_handler
   ```
   then click 'Save'
6. Go back to the code editor and click 'Deploy'

**NOTE**: The default handler is `lambda_function.lambda_handler`, which no longer exists. If you skip step 5 you will get `No module named 'lambda_function'`.

**NOTE**: Any time you change the code you need to click 'Deploy' again.

### Tell the Lambda which bucket to use

1. Go to the 'Configuration' tab and click 'Environment variables' > 'Edit'
2. Click 'Add environment variable' twice and enter:

   | Key | Value |
   |---|---|
   | `BUCKET_NAME` | `<YOUR-BUCKET-NAME>` |
   | `EXPIRES_IN` | `3600` |

   `EXPIRES_IN` is how long a link lasts, in seconds (3600 = 1 hour)
3. Click 'Save'
4. Still in 'Configuration', open 'General configuration' > 'Edit', set the Timeout to `10 sec` and click 'Save'

### Give the Lambda permission to use your bucket

By default your Lambda is allowed to do nothing with S3. A signed link only works if whoever signed it was allowed to do that action, so we have to give it access to this one bucket.

1. In 'Configuration', open 'Permissions' and click the role name under 'Execution role' (it looks like `quickdrop-presign-role-xxxxxxxx`). This opens IAM
2. Click 'Add permissions' > 'Create inline policy' and switch to the 'JSON' tab
3. Delete what is there and paste in:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:PutObject", "s3:GetObject"],
         "Resource": "arn:aws:s3:::<YOUR-BUCKET-NAME>/*"
       }
     ]
   }
   ```
   Keep the `/*` on the end
4. Click 'Next', name it `quickdrop-s3-presign`, and click 'Create policy'

**NOTE**: If you skip this step, uploads will fail with `AccessDenied`. That is the error telling you this step is missing.

### Give your Lambda a web address (Function URL)

1. Go back to your Lambda, open 'Configuration' > 'Function URL' and click 'Create function URL'
2. Auth type: `NONE` (anyone can call it, which is what our website needs)
3. Open 'Additional settings', tick 'Configure cross-origin resource sharing (CORS)', and fill in:

   | Box | Value |
   |---|---|
   | Allow origin | `http://localhost:8000` |
   | Allow headers | `content-type` |
   | Allow methods | `POST` |
   | Max age | `3000` |

   Leave 'Expose headers' empty and 'Allow credentials' unticked
4. Click 'Save'
5. Copy the Function URL. It looks like `https://<ID>.lambda-url.<REGION>.on.aws/`

**NOTE**: 'Allow headers' and 'Expose headers' are different boxes. Putting `content-type` in the wrong one is the most common mistake, and it makes the browser block your first request.

### Test your Lambda

1. Go to the 'Test' tab and create a new event named `presign-test`
2. Paste in:
   ```json
   {
     "body": "{\"filename\":\"hello.txt\",\"size\":11,\"contentType\":\"text/plain\"}"
   }
   ```
3. Click 'Save' then 'Test'
4. You should see `"statusCode": 200` and an `uploadUrl`, `downloadUrl` and `expiresIn`

### Run the website

1. In your IDE, open `frontend/config.js` and replace the placeholder with your Function URL:
   ```js
   window.APP_CONFIG = {
     FUNCTION_URL: "<YOUR-FUNCTION-URL>",
   };
   ```
2. Open a terminal in the folder you cloned and run:
   ```
   python3 scripts/serve.py
   ```
3. The website opens at `http://localhost:8000`. Drop in a small file
4. You should see 'Done!' and a link with a countdown. Click 'Copy', open a private window, and paste it in - your file should download
5. Go to your bucket in S3. Your file is in there, inside a folder with a random name

**NOTE**: Want to check everything without a browser? Run `python3 scripts/smoke_test.py`. Three 'ok' lines means it all works.

**Something not working?**

| What you see | What to check |
|---|---|
| CORS error in the browser console | 'Allow headers' and 'Allow origin' on your Function URL |
| 'Upload failed. Check bucket CORS' | The CORS section on your bucket |
| `AccessDenied` ... `no identity-based policy allows` | The IAM policy step |
| `No module named 'lambda_function'` | The Handler setting |
| `BUCKET_NAME is not set` | The environment variables |
| Test tab works, website doesn't | It's CORS - the Test tab doesn't use it |
| Anything else | Lambda > 'Monitor' > 'View CloudWatch logs' |

### (Optional) Watch a link expire

1. Go to your Lambda > 'Configuration' > 'Environment variables' and change `EXPIRES_IN` to `60`
2. Upload a file, wait a minute, and open the link. You should see `This link has expired.`
3. Change `EXPIRES_IN` back to `3600`

### Clean up

When you are done, delete what you made so nothing is left running:

1. S3: open your bucket, click 'Empty', then 'Delete'
2. Lambda: delete the function `quickdrop-presign`
3. IAM: go to 'Roles' and delete the `quickdrop-presign-role-...` role
4. CloudWatch: go to 'Log groups' and delete `/aws/lambda/quickdrop-presign`


## Part Two

This deploys everything - the Lambda, both buckets, and the website itself on CloudFront - from one command. The website runs on AWS instead of your laptop.

**NOTE**: You do not need Part One's resources for this, and it will not clash with them. Everything it creates has its own generated name.

### Set up the CLI

1. Install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
2. Run `aws configure` (or `aws configure sso`) and enter your credentials and region

**NOTE**: Do not create access keys for your root account. This is a good moment to use the IAM User from the 'Before you start' section.

### Deploy

1. In a terminal in the folder you cloned, run:
   ```
   scripts/deploy.sh
   ```
2. Wait - the first deploy takes several minutes because CloudFront is slow to create
3. When it finishes it prints two addresses. Open the first one (the website) and upload a file
4. To check the backend on its own, run the command it prints at the end (`python3 scripts/smoke_test.py <backend URL>`)

### Look at what it made

Open `infra/template.yaml`. It is everything you built by hand in Part One, written as code, plus the website hosting. The comments at the top match each block to the step you did in the console.

### Clean up

1. Run:
   ```
   scripts/teardown.sh
   ```
2. Type `yes` when asked. It empties both buckets and deletes everything. Removing CloudFront takes a few minutes