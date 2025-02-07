# # Local Web App for Visual Querying

# requirements.txt
#   fastapi
#   opencv-python
#   uvicorn

# After installing the above requirements, run the server with:
# `python web_app.py`. This will start a web app that can be
# accessed at http://0.0.0.0:8000.

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import requests
import base64
import cv2

# This is the URL of the Moondream-2 server on Modal.
url = 'https://benklingher--moondream-fastapi-app.modal.run/foo'


# ## Camera Access

# This takes a photo on the local camera. Assumes the webserver
# is running locally on your computer and camera permissions have
# been granted.
def take_photo():
    # Initialize the camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return None
    
    # Capture a single frame
    ret, frame = cap.read()
    
    # Release the camera
    cap.release()
    
    if ret:
        # Convert the image to jpg format
        _, buffer = cv2.imencode('.jpg', frame)
        # Convert to base64 string
        base64_image = base64.b64encode(buffer).decode('utf-8')
        return base64_image
    else:
        print("Error: Couldn't capture photo")
        return None


# ## Set up the web server

# We set up the web server using the Fast API. 
app = FastAPI()

# This method is used to fetch an image from the camera and then query the
# Moondream server to answer the visual query. The query is read from the
# text box in the web UI. Returns both the image and query response to
# the user.
@app.get("/get_image")
async def get_image(prompt: str = ""):
    encoded_image = take_photo()

    print(prompt)

    response = requests.post(url, json={
        'prompt': prompt,
        'image': encoded_image
    })
    print(response)
    result = response.json()["response"]
    print(result)

    return {
        "image": encoded_image,
        "response": result
    }

# ## Web Page

# This the HTML for the web page. It has a text box in which the user can type
# the prompt. Every 5 seconds the prompt is read the sent to `get_image` where
# the visual query is executed, then the image and response are displayed on
# the screen.
html_content = """
<!DOCTYPE html>
<head>
   <title>Image Upload</title>
</head>
<body>
   <div>
       <label for="prompt">Prompt:</label><br>
       <textarea id="prompt" onchange="getImage()"></textarea>
       <div id="response"></div>
       <img id="latest_image" style="max-width: 300px;">
   </div>

   <script>
       async function getImage() {
           const prompt = document.getElementById('prompt').value;
           const response = await fetch(`/get_image?prompt=${encodeURIComponent(prompt)}`);
           const data = await response.json();
           document.getElementById('latest_image').src = `data:image/jpeg;base64,${data.image}`;
           document.getElementById('response').textContent = data.response;
       }

       setInterval(() => getImage(), 5000);
       getImage();
   </script>
</body>
</html>
"""


# The endpoint that serves the HTML.
@app.get("/", response_class=HTMLResponse)
async def root():
   return html_content


uvicorn.run(app, host="0.0.0.0", port=8000)