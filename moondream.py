# # Create a Moondream-2 webserver

# This example demonstrates how to create a web endpoint that can handle visual
# queries using Moondream-2.

import io
import base64
from PIL import Image

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

import modal

# Build the app and the image, which includes all the dependencies.
app = modal.App("moondream")

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "vllm==0.6.3post1", "fastapi[standard]==0.115.4", "torch",
    "accelerate>=0.26.0", "pyvips", "pyvips-binary", "kokoro",
    "soundfile"
).apt_install("libvips")

# We also create a volume to store the model after it is downloaded
# from HuggingFace, so we don't have to re-download every time.
volume = modal.Volume.from_name(
    "moondream-model-volume", create_if_missing=True)

# Use a GPU for inference.
GPU_CONFIG = 't4'

moondream_hf = "vikhyatk/moondream2"


# ## Storing the model on Modal

# This method simply calls `from_pretrained` to load the model into the local
# cache. Because we connect a volume it is stored between runs so it can be
# reused without re-downloading.
@app.function(
    image=image,
    volumes={"/model": volume},  # Volume connected here.
    timeout=3600
)
def download_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model = AutoModelForCausalLM.from_pretrained(
        moondream_hf,
        revision="2025-01-09",
        trust_remote_code=True
    )

# ## Build the web endpoints

# We use FastAPI to support the web endpoints.

web_app = FastAPI()

# This method handles the visual queries using Moondream-2
def get_response(prompt, image):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f'Processing prompt "{prompt}" for image')

    model = AutoModelForCausalLM.from_pretrained(
        moondream_hf,
        trust_remote_code=True,
        local_files_only=True,
        device_map={"": "cuda"})

    # Captioning (not returned to caller)
    print("Short caption:")
    print(model.caption(image, length="short")["caption"])

    # Visual Querying
    print(f"\nVisual query: {prompt}")
    response = model.query(image, prompt)["answer"]

    print(response)

    return response

# This is the primary method to handle requests. It accepts images base64 as
# well as a prompt and handles the request using `get_response`
@web_app.post("/foo")
async def foo(request: Request):
    body = await request.json()
    prompt = body["prompt"]
    image_bytes = base64.b64decode(body["image"])
    image = Image.open(io.BytesIO(image_bytes))

    response = get_response(prompt, image)

    return {"response": response}

# These decorators set up this as the primary web server. It then inherits the
# web endpoints defined with the FastAPI and exposes them. When run, this will
# provide a public URL at which the endpoints can be accessed.
@app.function(
    image=image,
    volumes={"/model": volume},
    gpu=GPU_CONFIG,
    secrets=[modal.Secret.from_dict({"HF_HOME": "/model/moondream2"})]
)
@modal.asgi_app()
def fastapi_app():
    return web_app


# If you want to run this locally instead, use this:

# @app.local_entrypoint()
# def main(
#     prompt: str = None,
#     image_path: str = None
# ):
#     """Run S1 inference on Modal."""

#     image_path = 'duck.jpeg'

#     image_PIL = Image.open(image_path)
#     img_byte_arr = io.BytesIO()
#     image_PIL.save(img_byte_arr, format=image_PIL.format)
#     img_byte_arr = img_byte_arr.getvalue()

#     response = get_response.remote(prompt, img_byte_arr)
