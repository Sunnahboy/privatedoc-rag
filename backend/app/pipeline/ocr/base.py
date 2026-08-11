from abc import ABC, abstractmethod

import numpy as np


class BaseOCR(ABC):
    """Abstract base class for all OCR engines.
    Any new OCR provider must implement this interface."""

    @abstractmethod
    def extract(self, image: np.ndarray) -> str:
        """Extract text from an image.
        Args:
            image: A Numpy array representing the image(typically RGB/GGR).
        Returns:
            The extracted text as a string. Return an empty string if no text is found.
        """
        ...
