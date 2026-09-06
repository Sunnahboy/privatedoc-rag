import httpx
import numpy as np
import io
from PIL import Image
from app.config import settings
class VisualAPIClient:
    """
    A lightweight proxy that acts exactly like the heavy ML model, 
    but offloads the compute to the centralized FastAPI service.
    """
    def __init__(self, api_url: str = settings.visual_api_url):
        self.api_url = api_url
        self.client = httpx.AsyncClient(timeout=60.0) # 60s timeout for heavy inference

    async def embed_image(self, image: Image.Image) -> np.ndarray:
        """Sends the PIL Image to the centralized API."""
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        files = {'file': ('page.png', img_byte_arr, 'image/png')}
        response = await self.client.post(f"{self.api_url}/embed/image", files=files)
        response.raise_for_status()
        
        return np.array(response.json()["vector"])

    async def embed_query(self, text: str) -> np.ndarray:
        """Sends the text query to the centralized API."""
        response = await self.client.post(
            f"{self.api_url}/embed/text", 
            json={"text": text}
        )
        response.raise_for_status()
        
        return np.array(response.json()["vector"])

    async def close(self):
        await self.client.aclose()