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
            return None
            
        img = Image.open(BytesIO(response.content)).convert("RGB")
        
        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
            
        return features.squeeze().tolist()
    except Exception:
        return None
