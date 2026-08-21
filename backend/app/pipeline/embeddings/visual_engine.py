"""
Visual Retriever Engine (ColPali/ColQwen Wrapper)
Generates late-interaction multi-vector embeddings for document pages.
"""

import logging
from threading import Lock
from typing import Any

import numpy as np
import torch

# Import the ColPali architecture and processor
from colpali_engine.models import ColQwen2, ColQwen2Processor
from PIL import Image
from transformers import BitsAndBytesConfig

logger = logging.getLogger(__name__)


class VisualRetrieverEngine:
    """
    Handles lazy initialization, device management, and multi-vector generation
    using the ColQwen2/ColPali visual retrieval architecture.
    """

    _model_instance: Any = None
    _processor_instance: Any = None
    _engine_lock = Lock()

    # We default to a 2B model which is realistic for local/self-hosted execution.
    # You can change this to "vidore/colpali-v1.2" for the 7B Llama vision variant.
    MODEL_NAME = "vidore/colqwen2-v1.0"

    @classmethod
    def _initialize_engine(cls) -> None:
        if cls._model_instance is not None and cls._processor_instance is not None:
            return

        with cls._engine_lock:
            # Double-checked locking
            if cls._model_instance is None:
                # 1. Device Detection (CUDA > MPS (Apple Silicon) > CPU)
                if torch.cuda.is_available():
                    device = torch.device("cuda")
                    logger.info("Initializing Visual Engine on CUDA (NVIDIA GPU).")
                elif torch.backends.mps.is_available():
                    device = torch.device("mps")
                    logger.info("Initializing Visual Engine on MPS (Apple Silicon).")
                else:
                    device = torch.device("cpu")
                    logger.warning(
                        "No GPU found. Initializing Visual Engine on CPU (Very Slow!)."
                    )

                cls._device = device

                # 2. Load the Processor
                logger.info(f"Loading processor for {cls.MODEL_NAME}...")
                cls._processor_instance = ColQwen2Processor.from_pretrained(
                    cls.MODEL_NAME
                )

                # 3. Load the model, using 4-bit quantization on NVIDIA GPUs.
                logger.info(f"Loading model weights for {cls.MODEL_NAME}...")
                if cls._device.type == "cuda":
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.bfloat16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                        llm_int8_enable_fp32_cpu_offload=True
                    )
                    cls._model_instance = ColQwen2.from_pretrained(
                        cls.MODEL_NAME,
                        quantization_config=quantization_config,
                        device_map="auto",
                    ).eval()
                    logger.info("Model loaded in 4-bit quantized mode.")
                else:
                    # bitsandbytes quantization is unsupported on MPS and CPU.
                    cls._model_instance = ColQwen2.from_pretrained(
                        cls.MODEL_NAME,
                        torch_dtype=torch.bfloat16,
                        device_map=cls._device,
                    ).eval()

                logger.info("Visual Retriever Engine loaded successfully.")

    def embed_image(self, image: Image.Image) -> np.ndarray:
        """
        Processes a PIL Image and returns a 2D numpy array representing
        the multi-vector visual embedding (patches x 128 dimensions).
        """
        self._initialize_engine()

        assert self._model_instance is not None
        assert self._processor_instance is not None

        try:
            # 1. Preprocess the image
            # The processor handles resizing, patch extraction, and normalization
            # NEW
            inputs = self._processor_instance.process_images([image]).to(self._device)

            # 2. Run Inference (Generate embeddings)
            # torch.no_grad() is critical to prevent memory leaks during inference
            with torch.no_grad():
                outputs = self._model_instance(**inputs)

            # 3. Post-process to extract the patch embeddings
            # Outputs is a list of tensors (one per image). We only passed one image.
            embeddings = outputs[0]

            # 4. Move back to CPU and convert to standard float32 numpy array
            # Qdrant expects standard floats, not bfloat16
            numpy_embeddings = embeddings.cpu().float().numpy()

            logger.debug(f"Generated multi-vector shape: {numpy_embeddings.shape}")
            return numpy_embeddings

        except Exception:
            logger.exception("Failed to generate visual embeddings.")
            raise

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embeds a user text query for late-interaction visual search.
        """
        self._initialize_engine()
        assert self._model_instance is not None
        assert self._processor_instance is not None

        try:
            # ColQwen requires a specific prefix for query encoding
            # The processor handles the prompt formatting automatically
            # NEW
            inputs = self._processor_instance.process_queries([query]).to(self._device)

            with torch.no_grad():
                outputs = self._model_instance(**inputs)

            # Extract the query embeddings (Outputs is a list, we take the first item)
            query_embeddings = outputs[0].cpu().float().numpy()
            return query_embeddings

        except Exception:
            logger.exception("Failed to generate visual query embeddings.")
            raise
