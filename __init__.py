from .reverse_transform_mask.py import Reverse_transform_mask

# And add the extension to Krita's list of extensions:
app = Krita.instance()
# Instantiate your class:
extension = Reverse_transform_mask(parent=app)
app.addExtension(extension)
