from .transform_mask_positioner import Transform_Mask_Positioner

# And add the extension to Krita's list of extensions:
app = Krita.instance()
# Instantiate your class:
extension = Transform_Mask_Positioner(parent=app)
app.addExtension(extension)
