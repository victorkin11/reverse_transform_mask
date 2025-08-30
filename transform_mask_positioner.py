from krita import *
import xml.etree.ElementTree as ET
import math

EXTENSION_ID = "reverse_transform_mask"
MENU_ENTRY = "Reverse Transform Mask"

class ReverseTransformMask(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction(EXTENSION_ID, MENU_ENTRY, "tools/scripts")
        action.triggered.connect(self.create_reverse_transform_mask)

    def get_transform_parameters(self, transform_mask):
        """Extract all transformation parameters from a transform mask."""
        xml_str = transform_mask.toXML()
        root = ET.fromstring(xml_str)
        
        params = {
            "center_x": float(root.find(".//transformedCenter").get("x")),
            "center_y": float(root.find(".//transformedCenter").get("y")),
            "scale_x": float(root.find(".//scaleX").get("value")),
            "scale_y": float(root.find(".//scaleY").get("value")),
            "keep_aspect_ratio": root.find(".//keepAspectRatio").get("value") == "1",
            "rotation_x": float(root.find(".//aX").get("value")),
            "rotation_y": float(root.find(".//aY").get("value")),
            "rotation_z": float(root.find(".//aZ").get("value")),
            "shear_x": float(root.find(".//shearX").get("value")),
            "shear_y": float(root.find(".//shearY").get("value")),
        }
        
        # Get perspective transform matrix if available
        persp = root.find(".//flattenedPerspectiveTransform")
        if persp is not None:
            params["perspective"] = {
                "m11": float(persp.get("m11")),
                "m12": float(persp.get("m12")),
                "m13": float(persp.get("m13")),
                "m21": float(persp.get("m21")),
                "m22": float(persp.get("m22")),
                "m23": float(persp.get("m23")),
                "m31": float(persp.get("m31")),
                "m32": float(persp.get("m32")),
                "m33": float(persp.get("m33")),
            }
        
        return params

    def calculate_inverse_parameters(self, params):
        """Calculate the inverse transformation parameters."""
        inverse_params = {}
        
        # Inverse scale (1/scale)
        inverse_params["scale_x"] = 1.0 / params["scale_x"] if params["scale_x"] != 0 else 1.0
        inverse_params["scale_y"] = 1.0 / params["scale_y"] if params["scale_y"] != 0 else 1.0
        
        # Inverse rotation (negative angle)
        inverse_params["rotation_x"] = -params["rotation_x"]
        inverse_params["rotation_y"] = -params["rotation_y"]
        inverse_params["rotation_z"] = -params["rotation_z"]
        
        # Inverse shear (negative)
        inverse_params["shear_x"] = -params["shear_x"]
        inverse_params["shear_y"] = -params["shear_y"]
        
        # Keep aspect ratio setting remains the same
        inverse_params["keep_aspect_ratio"] = params["keep_aspect_ratio"]
        
        # Calculate inverse center position (more complex)
        # This accounts for the scale and rotation of the original transform
        # Formula: new_center = original_center - (offset * scale)
        # For simplicity, we'll keep the same center point for the reverse transform
        inverse_params["center_x"] = params["center_x"]
        inverse_params["center_y"] = params["center_y"]
        
        # Calculate inverse perspective matrix if available
        if "perspective" in params:
            # This is a simplified approach - in reality, matrix inversion is more complex
            # For a proper implementation, you'd need to calculate the actual matrix inverse
            p = params["perspective"]
            det = (p["m11"] * p["m22"] * p["m33"] +
                   p["m12"] * p["m23"] * p["m31"] +
                   p["m13"] * p["m21"] * p["m32"] -
                   p["m13"] * p["m22"] * p["m31"] -
                   p["m11"] * p["m23"] * p["m32"] -
                   p["m12"] * p["m21"] * p["m33"])
            
            if abs(det) > 1e-6:  # If determinant is not zero (invertible)
                inv_det = 1.0 / det
                inverse_params["perspective"] = {
                    "m11": (p["m22"] * p["m33"] - p["m23"] * p["m32"]) * inv_det,
                    "m12": (p["m13"] * p["m32"] - p["m12"] * p["m33"]) * inv_det,
                    "m13": (p["m12"] * p["m23"] - p["m13"] * p["m22"]) * inv_det,
                    "m21": (p["m23"] * p["m31"] - p["m21"] * p["m33"]) * inv_det,
                    "m22": (p["m11"] * p["m33"] - p["m13"] * p["m31"]) * inv_det,
                    "m23": (p["m13"] * p["m21"] - p["m11"] * p["m23"]) * inv_det,
                    "m31": (p["m21"] * p["m32"] - p["m22"] * p["m31"]) * inv_det,
                    "m32": (p["m12"] * p["m31"] - p["m11"] * p["m32"]) * inv_det,
                    "m33": (p["m11"] * p["m22"] - p["m12"] * p["m21"]) * inv_det,
                }
        
        return inverse_params

    def apply_transform_parameters(self, transform_mask, params):
        """Apply transformation parameters to a transform mask via XML."""
        xml_str = transform_mask.toXML()
        root = ET.fromstring(xml_str)
        
        # Update center
        tc = root.find(".//transformedCenter")
        if tc is not None:
            tc.set("x", str(params["center_x"]))
            tc.set("y", str(params["center_y"]))
        
        # Update scale
        sx = root.find(".//scaleX")
        sy = root.find(".//scaleY")
        if sx is not None and sy is not None:
            sx.set("value", str(params["scale_x"]))
            sy.set("value", str(params["scale_y"]))
        
        # Update aspect ratio
        kar = root.find(".//keepAspectRatio")
        if kar is not None:
            kar.set("value", "1" if params["keep_aspect_ratio"] else "0")
        
        # Update rotation
        ax = root.find(".//aX")
        ay = root.find(".//aY")
        az = root.find(".//aZ")
        if ax is not None:
            ax.set("value", str(params["rotation_x"]))
        if ay is not None:
            ay.set("value", str(params["rotation_y"]))
        if az is not None:
            az.set("value", str(params["rotation_z"]))
        
        # Update shear
        shx = root.find(".//shearX")
        shy = root.find(".//shearY")
        if shx is not None:
            shx.set("value", str(params["shear_x"]))
        if shy is not None:
            shy.set("value", str(params["shear_y"]))
        
        # Update perspective matrix if available
        if "perspective" in params:
            persp = root.find(".//flattenedPerspectiveTransform")
            if persp is not None:
                p = params["perspective"]
                persp.set("m11", str(p["m11"]))
                persp.set("m12", str(p["m12"]))
                persp.set("m13", str(p["m13"]))
                persp.set("m21", str(p["m21"]))
                persp.set("m22", str(p["m22"]))
                persp.set("m23", str(p["m23"]))
                persp.set("m31", str(p["m31"]))
                persp.set("m32", str(p["m32"]))
                persp.set("m33", str(p["m33"]))
        
        # Preserve original XML structure
        new_xml_str = ET.tostring(root, encoding="unicode")
        new_xml_str = f"<!DOCTYPE transform_params>\n{new_xml_str}"
        transform_mask.fromXML(new_xml_str)

    def create_reverse_transform_mask(self):
        """Create a reverse transform mask for the currently selected layer."""
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(None, "Error", "No active document!")
            return
        
        # Get the currently selected layer
        selected_layer = doc.activeNode()
        if not selected_layer:
            QMessageBox.warning(None, "Error", "No layer selected!")
            return
        
        # Check if the user has a transform mask selected
        source_mask = None
        for node in doc.rootNode().childNodes():
            if self.find_transform_mask_in_tree(node):
                source_mask = self.find_transform_mask_in_tree(node)
                break
        
        if not source_mask:
            # Check if the selected layer is a transform mask itself
            if selected_layer.type() == "transformmask":
                source_mask = selected_layer
            else:
                # Let user select which transform mask to reverse
                QMessageBox.warning(None, "Error", "No transform mask found! Please select a layer with a transform mask.")
                return
        
        # Create a new transform mask on the selected layer
        reverse_mask = doc.createNode("transformmask", "Reverse Transform")
        selected_layer.addChildNode(reverse_mask, None)
        
        # Get parameters from source transform mask
        params = self.get_transform_parameters(source_mask)
        
        # Calculate inverse parameters
        inverse_params = self.calculate_inverse_parameters(params)
        
        # Apply inverse parameters to the new transform mask
        self.apply_transform_parameters(reverse_mask, inverse_params)
        
        # Refresh the document to see changes
        doc.refreshProjection()
        
        QMessageBox.information(None, "Success", "Reverse transform mask created successfully!")

    def find_transform_mask_in_tree(self, node):
        """Recursively find a transform mask in the layer tree."""
        if node.type() == "transformmask":
            return node
        
        for child in node.childNodes():
            result = self.find_transform_mask_in_tree(child)
            if result:
                return result
        
        return None
