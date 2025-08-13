from krita import *
import os
import time
from PyQt5.QtWidgets import QApplication, QProgressDialog, QMessageBox
import xml.etree.ElementTree as ET


class Transform_Mask_Positioner(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction(
            "transform_mask_positioner_ext", "OFM Tmask Pos", "tools/scripts"
        )
        action.triggered.connect(self.action_triggered)

    def get_reference_rectangles(self):
        """Extract all reference rectangles from '#ref-' vector layers."""
        doc = Krita.instance().activeDocument()
        rectangles = {}

        for node in doc.rootNode().childNodes():
            if node.type() != "grouplayer" or node.name() == "xxx":
                continue

            vl_name_prefix = "#vl-"
            for child in node.childNodes():
                if (
                    child.name().startswith(vl_name_prefix)
                    and child.type() == "vectorlayer"
                ):
                    mockup = child.name().split(vl_name_prefix)[-1].lower()
                    if child.shapes():
                        for shape in child.shapes():
                            print("shape", shape.boundingBox())

                        bounds = child.shapes()[0].boundingBox()
                        dpi = doc.resolution()

                        rectangles[mockup] = {
                            "x": (bounds.x() + bounds.width() / 2) * dpi / 72.0,
                            "y": (bounds.y() + bounds.height() / 2) * dpi / 72.0,
                            "width": bounds.width() * dpi / 72.0,
                            "height": bounds.height() * dpi / 72.0,
                        }

        return rectangles

    def set_transform_mask_center_and_scale(
        self,
        transform_mask,
        center_x,
        center_y,
        scale_x,
        scale_y,
        keepAspectRatio: bool = True,
    ):
        """
        Set the transformed center position and scale of a Krita transform mask via XML.
        """
        print("new scale", scale_x, scale_y)
        print("new pos", center_x, center_y)

        xml_str = transform_mask.toXML()
        root = ET.fromstring(xml_str)

        # Update center
        tc = root.find(".//transformedCenter")
        if tc is not None:  # wtf is not accepting if tc:
            if center_x and center_y:
                print("pos")
                tc.set("x", str(center_x))
                tc.set("y", str(center_y))

        # Lanczos3 best for text i guess
        filter_id = root.find(".//filterId")
        if filter_id is not None:
            filter_id.set("value", "Lanczos3")

        # Update scale
        sx = root.find(".//scaleX")
        sy = root.find(".//scaleY")
        kar = root.find(".//keepAspectRatio")
        if sx is not None and sy is not None:
            print("sx_sy")
            sx.set("value", str(scale_x))
            sy.set("value", str(scale_y))
        if kar is not None:
            print("kar")
            kar.set("value", "1" if keepAspectRatio else "0")

        # Preserve original XML structure
        new_xml_str = ET.tostring(root, encoding="unicode")
        new_xml_str = f"<!DOCTYPE transform_params>\n{new_xml_str}"
        transform_mask.fromXML(new_xml_str)

        # print("-" * 5)
        # print(xml_str)
        # print("-" * 5)
        # print(new_xml_str)

    def fit_mask_to_rect(self, mask, rect):
        """Scale and position a transform mask to fit a reference rectangle (preserving aspect ratio)."""
        doc = Krita.instance().activeDocument()
        if not doc or not mask.type() == "transformmask":
            print(f"Error: {mask.name()} is not a transform mask or no document active")
            return

        # if not "black" in mask.name():
        #     return
        # else:
        #     print(mask.name())

        print("rect", rect)

        # scale
        mask_bounds = mask.bounds()  # design
        design_w = mask_bounds.width()
        design_h = mask_bounds.height()

        rect_w = rect["width"]
        rect_h = rect["height"]

        # print("rect", rect_w, rect_h)
        # print("design", design_w, design_h)

        scale_factor = min(rect_w / design_w, rect_h / design_h)

        # print("scales", rect_w / design_w, rect_h / design_h)
        # print("scale_factor", scale_factor)

        # pos/scale
        scale_x = scale_factor
        scale_y = scale_factor

        print("scaled dimesion", design_w * scale_x, design_h * scale_y)

        center_x = rect["x"]
        center_y = rect["y"]

        # position
        self.set_transform_mask_center_and_scale(
            mask, center_x, center_y, scale_x, scale_y, True
        )
        doc.waitForDone()
        doc.refreshProjection()
        doc.waitForDone()
        time.sleep(0.3)

    def action_triggered(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(None, "Error", "No active document!")
            return

        print(f"Document size: {doc.width()}x{doc.height()}px")

        rectangles = self.get_reference_rectangles()
        if not rectangles:
            QMessageBox.warning(None, "Error", "No '#vl-' vector layers found!")
            return

        # Process all transform masks
        for mask in self.find_all_transform_masks(doc.rootNode()):

            mask_name = mask.name().lower()
            for color, rect in rectangles.items():
                if color in mask_name:
                    self.fit_mask_to_rect(mask, rect)
                    doc.refreshProjection()
                    break

        # QMessageBox.information(None, "Done", "Masks fitted to rectangles!")

    def find_all_transform_masks(self, root_node):
        """Recursively find all transform masks in the layer tree."""
        masks = []
        for node in root_node.childNodes():
            if node.type() == "transformmask":
                masks.append(node)
            elif node.childNodes():  # Search groups/folders
                masks.extend(self.find_all_transform_masks(node))
        return masks
