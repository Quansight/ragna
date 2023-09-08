# import io
#
# import boto3
#
#
# # def generate_presigned_url():
# #     # Create a Boto3 client for S3
# #     s3_client = boto3.client("s3")
# #
# #     # Generate a presigned URL for uploading an object
# #     bucket_name = "pmeier-presigned-urls-test"
# #     object_key = f"foo.txt"
# #
# #     presigned_url = s3_client.generate_presigned_url(
# #         ClientMethod="put_object",
# #         Params={"Bucket": bucket_name, "Key": object_key},
# #         ExpiresIn=300,  # URL expiration time in seconds
# #     )
# #
# #     return presigned_url
# #
# #
# # url = generate_presigned_url()
# #
# # import requests
# #
# #
# # requests.put(url, b"This is a test")
#
# from botocore.exceptions import ClientError
# import logging
# import boto3
#
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)
#
#
# class BucketWrapper:
#     """Encapsulates S3 bucket actions."""
#
#     def __init__(self, bucket):
#         """
#         :param bucket: A Boto3 Bucket resource. This is a high-level resource in Boto3
#                        that wraps bucket actions in a class-like structure.
#         """
#         self.bucket = bucket
#         self.name = bucket.name
#
#     def generate_presigned_post(self, object_key, expires_in):
#         """
#         Generate a presigned Amazon S3 POST request to upload a file.
#         A presigned POST can be used for a limited time to let someone without an AWS
#         account upload a file to a bucket.
#
#         :param object_key: The object key to identify the uploaded object.
#         :param expires_in: The number of seconds the presigned POST is valid.
#         :return: A dictionary that contains the URL and form fields that contain
#                  required access data.
#         """
#         try:
#             response = self.bucket.meta.client.generate_presigned_post(
#                 Bucket=self.bucket.name, Key=object_key, ExpiresIn=expires_in
#             )
#             logger.info("Got presigned POST URL: %s", response["url"])
#         except ClientError:
#             logger.exception(
#                 "Couldn't get a presigned POST URL for bucket '%s' and object '%s'",
#                 self.bucket.name,
#                 object_key,
#             )
#             raise
#         return response

import boto3

session = boto3.Session(
    aws_access_key_id="AKIA37YRZN3V5LNM3BE2",
    aws_secret_access_key="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",
    region_name="eu-central-1",
)
s3 = session.client("s3")

# bucket = s3.Bucket("pmeier-presigned-urls-test")

# for obj in bucket.objects.all():
#     print(obj.key)
#
# bucket_wrapper = BucketWrapper(bucket)

response = s3.generate_presigned_post(
    Bucket="pmeier-presigned-urls-test", Key="bar.txt", ExpiresIn=300
)
print(response)

# url = s3.generate_presigned_url(
#     ClientMethod="put_object",
#     Params={"Bucket": "pmeier-presigned-urls-test", "Key": "foo.txt"},
#     ExpiresIn=300,  # URL expiration time in seconds
# )

import requests


response = requests.post(
    response["url"], data=response["fields"], files={"file": b"This is a test!"}
)

print(response.status_code, response.text)
#
#
# def chunk(stream, chunk_size=32 * 1024):
#     for c in iter(lambda: stream.read(chunk_size), b""):
#         yield c
#
#
# # stream = io.BytesIO(b"This is a test")
# stream = open("/home/philip/conda-store.sqlite", "rb")
#
# import requests
#
# response = requests.post(
#     "http://127.0.0.1:8000/upload-document",
#     files={"file": stream},
# )
#
# print(response, response.history)
