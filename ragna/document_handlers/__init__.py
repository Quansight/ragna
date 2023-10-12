from ._pdf import PdfDocumentHandler
from ._txt import TxtDocumentHandler

from ragna._utils import _fix_module  # usort: skip

_fix_module(globals())
del _fix_module
