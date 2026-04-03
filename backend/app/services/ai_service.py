import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from io import BytesIO
import requests

model_id = "openai/clip-vit-base-patch32"
model = CLIPModel.from_pretrained(model_id)
processor = CLIPProcessor.from_pretrained(model_id)

def get_image_embedding(image_url: str):
    """Tải ảnh từ link và dùng AI biến thành Vector 512 chiều"""
    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code != 200:
            print(f"[AI] Image download failed status={response.status_code} url={image_url}")
            return None
            
        img = Image.open(BytesIO(response.content)).convert("RGB")
        
        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)

        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        elif hasattr(features, "image_embeds"):
            features = features.image_embeds

        if not hasattr(features, "squeeze"):
            print(f"[AI] Unexpected CLIP output type={type(features)} url={image_url}")
            return None

        return features.squeeze().tolist()
    except Exception as e:
        print(f"[AI] Embedding failed url={image_url} error={type(e).__name__}: {e}")
        return None
