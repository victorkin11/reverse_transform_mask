from krita import *
import os
import time
from PyQt5.QtWidgets import QApplication, QProgressDialog
from PyQt5.QtWidgets import QMessageBox
from .positions import positions


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

    def find_mask_recursive(self, root_node, name):
        """Recursively search for a node by name in layer groups."""
        for child in root_node.childNodes():
            # QMessageBox.warning(None, "Error", child.name() + "/*\\" + name)
            if child.name() == name:
                return child
            if child.childNodes():  # If it's a group, search deeper
                found = self.find_mask_recursive(child, name)
                if found:
                    return found
        return None

    def action_triggered(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(None, "Error", "No active document found!")
            return

        # progress bar
        total_groups = sum(
            1 for node in doc.rootNode().childNodes() if node.type() == "grouplayer"
        )
        progress = QProgressDialog(
            "Positioning Transform Masks...", "Cancel", 0, total_groups
        )
        progress.setWindowTitle("Positioning")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        for name, (x, y) in positions.items():
            root = doc.rootNode()  # Start from the top-level node
            mask = self.find_mask_recursive(root, name)
            if not mask:
                # QMessageBox.warning(None, "Error", f"{name} not found")
                continue
            # QMessageBox.warning(None, "Error", f"{mask.type()} /*\\ {mask.bounds()}")

            if mask and mask.type() == "transformationmask":
                # Select the parent layer (required for transform masks)
                doc.setActiveNode(mask)
                doc.refreshProjection()
                doc.waitForDone()
                time.sleep(0.3)

                # bounds = mask.bounds()
                # dx = x - bounds.x()
                # dy = y - bounds.y()
                mask.move(x, y)

                doc.waitForDone()
                doc.refreshProjection()
                doc.waitForDone()
                time.sleep(0.3)
                print(f"Moved {name} by ({x}, {x})")

            # progress
            progress.setValue(progress.value() + 1)
            QApplication.processEvents()
            time.sleep(0.5)

        progress.close()
        QMessageBox.information(None, "Done", "All mask repositioned!")
