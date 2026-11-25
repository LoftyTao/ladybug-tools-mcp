from honeybee.properties import ModelProperties
import honeybee.writer.model as model_writer

from .properties.model import ModelGbasProperties
from .writer import model_to_dwg

ModelProperties._gbas = None


def model_gbas_properties(self):
    """Return the ModelGbasProperties instance for this Model."""
    if self._gbas is None:
        self._gbas = ModelGbasProperties(self.host)
    return self._gbas


ModelProperties.gbas = property(model_gbas_properties)

model_writer.dwg = model_to_dwg
