import panel as pn

js_code = """
<script>
const presignedUrl = '{presigned_url}';
function importData() {{
  let input = document.createElement('input');
  input.type = 'file';
  // input.multiple = true; // Allows multiple files to be selected
  input.onchange = _ => {{
    // you can use this method to get file and perform respective operations
    let files = Array.from(input.files);

    files.forEach((file) => {{
      console.log(file);
      // Send a PUT request to the presigned URL for each file
      fetch(presignedUrl, {{
        method: 'PUT',
        body: file,
      }})
        .then((response) => {{
          if (response.ok) {{
            console.log('File uploaded successfully!');
          }} else {{
            console.error('Error uploading file:', response.statusText);
          }}
        }})
        .catch((error) => {{
          console.error('Error uploading file:', error);
        }});
    }});

    console.log(files);
  }};
  input.click();
}}

importData();
</script>
"""


def timestamp():
    import datetime

    current_time = datetime.datetime.now()
    timestamp = current_time.strftime("%Y%m%d_%H%M%S")

    return timestamp


button = pn.widgets.Button(name="Upload File")
html = pn.pane.HTML("")


def generate_presigned_url():
    import boto3

    boto3.Session(
        aws_access_key_id="AKIA37YRZN3V5LNM3BE2",
        aws_secret_access_key="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",
        region_name="eu-central-1",
    )

    # Create a Boto3 client for S3
    s3_client = boto3.client("s3")

    # Generate a presigned URL for uploading an object
    bucket_name = "pmeier-presigned-urls-test"
    object_key = f"{timestamp()}.pdf"

    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket_name, "Key": object_key},
        ExpiresIn=300,  # URL expiration time in seconds
    )

    return presigned_url


def run_python_func(event):
    presigned_url = generate_presigned_url()

    js = js_code.format(presigned_url=presigned_url)
    html.object = js
    html.param.trigger("object")
    html.object = ""


button.param.watch(run_python_func, "clicks")

app = pn.Column(button, html)

pn.serve(app)
