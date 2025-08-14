from krita import *
import os
import time
from PyQt5.QtWidgets import QApplication, QProgressDialog, QMessageBox, QMenu
import xml.etree.ElementTree as ET

EXTENSION_ID = "transform_mask_positioner"
MENU_ENTRY = "1 OFM Transform T-masks"


class Transform_Mask_Positioner(Extension):
    VECTOR_LAYER_DPI = 72.0

    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction(EXTENSION_ID, MENU_ENTRY, "tools/scripts")
        menu = QtWidgets.QMenu(EXTENSION_ID, window.qwindow())
        action.setMenu(menu)

        # sub menu do for all
        subaction1 = window.createAction(
            f"{EXTENSION_ID}_doForAll", "Do For All", f"tools/scripts/{EXTENSION_ID}"
        )
        subaction1.triggered.connect(self.action_do_for_all)

        # sub menu do for selected
        subaction1 = window.createAction(
            f"{EXTENSION_ID}_doForSelected",
            "Do For Selected",
            f"tools/scripts/{EXTENSION_ID}",
        )
        subaction1.triggered.connect(self.action_do_for_selected)

    # scriptttt

    def get_reference_rectangles(self, vl_name_prefix):
        """Extract all reference rectangles from vector layers."""
        doc = Krita.instance().activeDocument()
        rectangles = {}

        QMessageBox.information(None, "Error", root_node.name())

        for node in doc.rootNode().childNodes():
            if node.type() != "grouplayer" or node.name() == "xxx":
                print("no yow")
                continue
            print("yow")
            for child in node.childNodes():
                if (
                    child.name().startswith(vl_name_prefix)
                    and child.type() == "vectorlayer"
                ):
                    mockup = child.name().split(vl_name_prefix)[-1].lower()
                    if child.shapes():
                        bounds = child.shapes()[0].boundingBox()
                        dpi = doc.resolution()

                        # center x and y
                        # fmt:off
                        rectangles[mockup] = {
                            "x": (bounds.x() + bounds.width() / 2) * dpi / self.VECTOR_LAYER_DPI,
                            "y": (bounds.y() + bounds.height() / 2) * dpi / self.VECTOR_LAYER_DPI, 
                            "width": bounds.width() * dpi / self.VECTOR_LAYER_DPI, 
                            "height": bounds.height() * dpi / self.VECTOR_LAYER_DPI,
                        }
                        # fmt:on
        return rectangles

    def get_reference_rectangle_single(self, group_node, vl_name_prefix):
        """Extract all reference rectangles from vector layers. DRY man DRY"""
        doc = Krita.instance().activeDocument()
        rectangles = {}

        for child in group_node.childNodes():
            if (
                child.name().startswith(vl_name_prefix)
                and child.type() == "vectorlayer"
            ):
                mockup = child.name().split(vl_name_prefix)[-1].lower()
                if child.shapes():
                    bounds = child.shapes()[0].boundingBox()
                    dpi = doc.resolution()

                    # center x and y
                    # fmt:off
                    rectangles[mockup] = {
                        "x": (bounds.x() + bounds.width() / 2) * dpi / self.VECTOR_LAYER_DPI,
                        "y": (bounds.y() + bounds.height() / 2) * dpi / self.VECTOR_LAYER_DPI, 
                        "width": bounds.width() * dpi / self.VECTOR_LAYER_DPI, 
                        "height": bounds.height() * dpi / self.VECTOR_LAYER_DPI,
                    }
                    # fmt:on
        return rectangles

    def find_all_transform_masks(self, root_node):
        """Recursively find all transform masks in the layer tree."""
        masks = []
        for node in root_node.childNodes():
            if node.type() == "transformmask":
                masks.append(node)
            elif node.childNodes():  # Search groups/folders
                masks.extend(self.find_all_transform_masks(node))
        return masks

    def transform_mask_xml_transform(
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

        # print("rect", rect)

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
        self.transform_mask_xml_transform(
            mask, center_x, center_y, scale_x, scale_y, True
        )

        doc.refreshProjection()
        doc.waitForDone()
        time.sleep(0.1)

    def reset_transform_mask_xml(self, transform_mask):
        """
        Reset a Krita transform mask to default (no transform).
        """
        xml_str = transform_mask.toXML()
        root = ET.fromstring(xml_str)

        # Reset position
        tc = root.find(".//transformedCenter")
        oc = root.find(".//originalCenter")
        if tc is not None and oc is not None:
            tc.set("x", oc.get("x"))
            tc.set("y", oc.get("y"))

        # Reset scale
        sx = root.find(".//scaleX")
        if sx is not None:
            sx.set("value", "1")
        sy = root.find(".//scaleY")
        if sy is not None:
            sy.set("value", "1")

        # Reset rotation
        ax = root.find(".//aX")
        if ax is not None:
            ax.set("value", "0")
        ay = root.find(".//aY")
        if ay is not None:
            ay.set("value", "0")
        az = root.find(".//aZ")
        if az is not None:
            az.set("value", "0")

        # Reset shear
        shx = root.find(".//shearX")
        if shx is not None:
            shx.set("value", "0")
        shy = root.find(".//shearY")
        if shy is not None:
            shy.set("value", "0")

        # Reset perspective matrix
        persp = root.find(".//flattenedPerspectiveTransform")
        if persp is not None:
            persp.set("m11", "1")
            persp.set("m12", "0")
            persp.set("m13", "0")
            persp.set("m21", "0")
            persp.set("m22", "1")
            persp.set("m23", "0")
            persp.set("m31", "0")
            persp.set("m32", "0")
            persp.set("m33", "1")

        # Apply back
        new_xml_str = ET.tostring(root, encoding="unicode")
        transform_mask.fromXML(new_xml_str)

    def action_do_for_all(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(None, "Error", "No active document!")
            return

        if (
            QMessageBox.question(
                None,
                "Transforming the Transformmasks!!",
                "Do you want to contunie?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.No
        ):
            return

        # progress bar
        total_groups = sum(
            1 for node in doc.rootNode().childNodes() if node.type() == "grouplayer"
        )
        progress = QProgressDialog(
            "Transforming the Transform Layers...", "Cancel", 0, total_groups
        )
        progress.setWindowTitle("Batch Transform")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        # print(f"Document size: {doc.width()}x{doc.height()}px")

        # force long!
        reply = QMessageBox.question(
            None,
            "Force Long Rectangle",
            "Do you want to force long rectangle ?",
            QMessageBox.Yes | QMessageBox.No,
        )

        do_force_long = False
        if reply == QMessageBox.Yes:
            do_force_long = True

        vl_name_prefix_long = "#vl_long-"
        rectangles_long = self.get_reference_rectangles(vl_name_prefix_long)
        vl_name_prefix_wide = "#vl_wide-"
        rectangles_wide = self.get_reference_rectangles(vl_name_prefix_wide)

        if not rectangles_long:
            QMessageBox.warning(
                None, "Error", f"No {vl_name_prefix_long} vector layers found!"
            )
            return

        if not rectangles_wide:
            QMessageBox.warning(
                None, "Error", f"No {vl_name_prefix_wide} vector layers found!"
            )
            return

        # Process all transform masks
        for mask in self.find_all_transform_masks(doc.rootNode()):
            # reset the t-mask
            self.reset_transform_mask_xml(mask)

            mask_bounds = mask.bounds()  # design
            design_w = mask_bounds.width()
            design_h = mask_bounds.height()
            if do_force_long:  # long
                rectangles = rectangles_long
            else:
                if design_h >= design_w:
                    # long
                    rectangles = rectangles_long
                else:
                    # wide
                    rectangles = rectangles_wide

            # match the t-mask name with vector layer name (#vl_long-black->black must be inside tmaks layer name eg. tm-black)
            mask_name = mask.name().lower()
            for color, rect in rectangles.items():
                if color in mask_name:
                    self.fit_mask_to_rect(mask, rect)
                    break

            # progress
            progress.setValue(progress.value() + 1)
            QApplication.processEvents()

        progress.close()
        QMessageBox.information(None, "Done", "Transform Masks fitted to rectangles!")

    def action_do_for_selected(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(None, "Error", "No active document!")
            return

        if (
            QMessageBox.question(
                None,
                "Transforming the One Transformmasks!!",
                "Do you want to contunie?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.No
        ):
            return
        # THE ONE!
        mask = doc.activeNode()

        if mask.type() != "transformmask":
            QMessageBox.warning(None, "Error", "Selected layer must be transform mask!")
            return

        # force long!
        reply = QMessageBox.question(
            None,
            "Force Long Rectangle",
            "Do you want to force long rectangle ?",
            QMessageBox.Yes | QMessageBox.No,
        )

        do_force_long = False
        if reply == QMessageBox.Yes:
            do_force_long = True

        vl_name_prefix_long = "#vl_long-"
        rectangle_long = self.get_reference_rectangle_single(
            mask.parentNode().parentNode(), vl_name_prefix_long
        )
        vl_name_prefix_wide = "#vl_wide-"
        rectangle_wide = self.get_reference_rectangle_single(
            mask.parentNode().parentNode(), vl_name_prefix_wide
        )

        if not rectangle_long:
            QMessageBox.warning(
                None, "Error", f"No {vl_name_prefix_long} vector layers found!"
            )
            return

        if not rectangle_wide:
            QMessageBox.warning(
                None, "Error", f"No {vl_name_prefix_wide} vector layers found!"
            )
            return

        # reset the t-mask
        self.reset_transform_mask_xml(mask)

        mask_bounds = mask.bounds()  # design
        design_w = mask_bounds.width()
        design_h = mask_bounds.height()
        if do_force_long:  # long
            rectangles = rectangle_long
        else:
            if design_h >= design_w:
                # long
                rectangles = rectangle_long
            else:
                # wide
                rectangles = rectangle_wide

        # match the t-mask name with vector layer name (#vl_long-black->black must be inside tmaks layer name eg. tm-black)
        mask_name = mask.name().lower()
        for color, rect in rectangles.items():
            if color in mask_name:
                self.fit_mask_to_rect(mask, rect)
                break

        QMessageBox.information(None, "Done", "1T-mask fitted to rectangles!")
