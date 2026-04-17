"""
KiCad PCB Tools Suite
A comprehensive plugin with multiple tools:
- 3D Viewer with coordinate display
- 2D Bounding Box Selector (all layers)
- Top View with Bounding Box (top layer only)
- EMI Simulation with FDTD (openEMS-based, threaded)
- User-adjustable grid resolution (12-30 cells/wavelength, default 15)
- Automatic grid validation with warnings
- 3D Boundary Conditions (PML, PEC, PMC, Periodic)
- Ultra-conservative source (0.01 V/m)
- Comprehensive field monitoring
- (Extensible for more tools)

Author: John Carroll, using Claude (for the Visual Windows)
Version: 2.8.2
License: MIT
"""

import pcbnew
import wx
import os
import math

class KicadPCBToolsSuite(pcbnew.ActionPlugin):
    """
    Main plugin class that registers with KiCad
    """
    
    def defaults(self):
        """
        Method to define default plugin properties
        """
        self.name = "PCB Tools Suite"
        self.category = "PCB Utilities"
        self.description = "Multiple PCB tools: 3D Viewer, Bounding Box Selector, and more"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png')
    
    def Run(self):
        """
        Method called when the plugin is executed
        """
        # Get the current board
        board = pcbnew.GetBoard()
        
        if not board:
            wx.MessageBox("No board loaded!", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        # Create and show the main tools dialog
        tools_dialog = ToolsSuiteDialog(None, board)
        tools_dialog.Show()


class ToolsSuiteDialog(wx.Frame):
    """
    Main dialog showing available tools
    """
    
    def __init__(self, parent, board):
        """
        Initialize the tools suite dialog
        """
        super(ToolsSuiteDialog, self).__init__(
            parent, 
            title="KiCad PCB Tools Suite",
            size=(600, 400),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        self.board = board
        self.create_ui()
        self.Centre()
        
    def create_ui(self):
        """
        Create the user interface
        """
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="PCB Tools Suite")
        title_font = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL | wx.CENTER, 20)
        
        # Description
        desc = wx.StaticText(panel, label="Select a tool to use:")
        main_sizer.Add(desc, 0, wx.ALL | wx.LEFT, 20)
        
        # Tool buttons
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 3D Viewer button
        viewer_btn = wx.Button(panel, label="3D Viewer with Coordinates", size=(400, 50))
        viewer_btn.SetToolTip("View PCB in 3D with coordinate display on hover")
        viewer_btn.Bind(wx.EVT_BUTTON, self.on_open_3d_viewer)
        button_sizer.Add(viewer_btn, 0, wx.ALL | wx.CENTER, 10)
        
        # Bounding Box Selector button
        bbox_btn = wx.Button(panel, label="2D Bounding Box Selector", size=(400, 50))
        bbox_btn.SetToolTip("Select a rectangular region on the PCB using mouse or coordinates")
        bbox_btn.Bind(wx.EVT_BUTTON, self.on_open_bbox_selector)
        button_sizer.Add(bbox_btn, 0, wx.ALL | wx.CENTER, 10)
        
        # Top View with Bounding Box button
        topview_btn = wx.Button(panel, label="Top View with Bounding Box", size=(400, 50))
        topview_btn.SetToolTip("2D top-down view of board with bounding box selection")
        topview_btn.Bind(wx.EVT_BUTTON, self.on_open_top_view)
        button_sizer.Add(topview_btn, 0, wx.ALL | wx.CENTER, 10)
        
        # Placeholder for future tools
        future_label = wx.StaticText(panel, label="More tools coming soon...")
        future_label.SetForegroundColour(wx.Colour(128, 128, 128))
        button_sizer.Add(future_label, 0, wx.ALL | wx.CENTER, 20)
        
        main_sizer.Add(button_sizer, 1, wx.EXPAND | wx.ALL, 10)
        
        # Close button
        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        main_sizer.Add(close_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        
    def on_open_3d_viewer(self, event):
        """
        Open the 3D viewer tool
        """
        viewer = Viewer3DDialog(self, self.board)
        viewer.Show()
        
    def on_open_bbox_selector(self, event):
        """
        Open the bounding box selector tool
        """
        selector = BoundingBoxSelectorDialog(self, self.board)
        selector.Show()
    
    def on_open_top_view(self, event):
        """
        Open the top view with bounding box tool
        """
        topview = TopViewBoundingBoxDialog(self, self.board)
        topview.Show()


class Viewer3DDialog(wx.Frame):
    """
    3D Viewer Dialog Window (from v1.3.0)
    """
    
    def __init__(self, parent, board):
        super(Viewer3DDialog, self).__init__(
            parent, 
            title="3D Viewer with Coordinates",
            size=(1200, 800),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        self.board = board
        self.show_coordinates = True
        self.rotation_x = 30.0
        self.rotation_y = 0.0
        self.rotation_z = 45.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.last_mouse_pos = None
        
        self.create_ui()
        self.Centre()
        
    def create_ui(self):
        """Create the user interface"""
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Toolbar
        toolbar_panel = wx.Panel(main_panel)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.coord_toggle = wx.CheckBox(toolbar_panel, label="Show Coordinates on Hover")
        self.coord_toggle.SetValue(self.show_coordinates)
        self.coord_toggle.Bind(wx.EVT_CHECKBOX, self.on_toggle_coordinates)
        toolbar_sizer.Add(self.coord_toggle, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        reset_btn = wx.Button(toolbar_panel, label="Reset View")
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset_view)
        toolbar_sizer.Add(reset_btn, 0, wx.ALL, 5)
        
        toolbar_panel.SetSizer(toolbar_sizer)
        main_sizer.Add(toolbar_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # 3D Canvas
        self.canvas = Viewer3DCanvas(main_panel, self)
        main_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        
        # Status bar
        self.status_bar = self.CreateStatusBar(2)
        self.status_bar.SetStatusWidths([-3, -1])
        self.SetStatusText("Ready", 0)
        
        main_panel.SetSizer(main_sizer)
        
    def on_toggle_coordinates(self, event):
        self.show_coordinates = self.coord_toggle.GetValue()
        self.canvas.Refresh()
        
    def on_reset_view(self, event):
        self.rotation_x = 30.0
        self.rotation_y = 0.0
        self.rotation_z = 45.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.canvas.Refresh()


class Viewer3DCanvas(wx.Panel):
    """Canvas for rendering the 3D view"""
    
    def __init__(self, parent, viewer):
        super(Viewer3DCanvas, self).__init__(parent)
        self.viewer = viewer
        self.board = viewer.board
        self.hover_pos = None
        self.hover_coords_3d = None
        
        self.SetBackgroundColour(wx.Colour(40, 44, 52))
        
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, lambda e: (self.Refresh(), e.Skip()))
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        
        self.dragging = False
        self.panning = False
        
    def on_paint(self, event):
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)
        if gc:
            self.render(gc)
            
    def render(self, gc):
        """Render the 3D view"""
        width, height = self.GetSize()
        
        # Clear background
        gc.SetBrush(wx.Brush(wx.Colour(40, 44, 52)))
        gc.DrawRectangle(0, 0, width, height)
        
        # Get board bounds
        bbox = self.board.GetBoardEdgesBoundingBox()
        board_width = bbox.GetWidth() / 1e6
        board_height = bbox.GetHeight() / 1e6
        
        center_x = width / 2 + self.viewer.pan_x
        center_y = height / 2 + self.viewer.pan_y
        
        # Draw 3D representation
        self.draw_board_outline(gc, center_x, center_y, board_width, board_height)
        self.draw_tracks(gc, center_x, center_y)
        self.draw_vias(gc, center_x, center_y)
        self.draw_components(gc, center_x, center_y)
        
        # Draw coordinate overlay
        if self.viewer.show_coordinates and self.hover_coords_3d:
            self.draw_coordinate_overlay(gc)
            
        self.draw_orientation_indicator(gc, width, height)
    
    def draw_board_outline(self, gc, center_x, center_y, board_width, board_height):
        """Draw the board outline (fully opaque)"""
        scale = self.viewer.zoom * 2.0
        rx = math.radians(self.viewer.rotation_x)
        rz = math.radians(self.viewer.rotation_z)
        
        corners = [
            (-board_width/2, -board_height/2),
            (board_width/2, -board_height/2),
            (board_width/2, board_height/2),
            (-board_width/2, board_height/2)
        ]
        
        projected = []
        for x, y in corners:
            px = center_x + (x * math.cos(rz) - y * math.sin(rz)) * scale
            py = center_y + (x * math.sin(rz) * math.sin(rx) + y * math.cos(rz) * math.sin(rx)) * scale
            projected.append((px, py))
        
        path = gc.CreatePath()
        path.MoveToPoint(projected[0][0], projected[0][1])
        for px, py in projected[1:]:
            path.AddLineToPoint(px, py)
        path.CloseSubpath()
        
        gc.SetBrush(wx.Brush(wx.Colour(25, 85, 25, 255)))
        gc.SetPen(wx.Pen(wx.Colour(100, 255, 100, 255), 2))
        gc.FillPath(path)
        gc.StrokePath(path)
        
        # Draw board thickness
        thickness = 1.6
        for i in range(4):
            x1, y1 = projected[i]
            x2, y2 = projected[(i + 1) % 4]
            offset_y = thickness * scale * math.cos(rx)
            
            side_path = gc.CreatePath()
            side_path.MoveToPoint(x1, y1)
            side_path.AddLineToPoint(x2, y2)
            side_path.AddLineToPoint(x2, y2 + offset_y)
            side_path.AddLineToPoint(x1, y1 + offset_y)
            side_path.CloseSubpath()
            
            gc.SetBrush(wx.Brush(wx.Colour(15, 70, 15, 255)))
            gc.SetPen(wx.Pen(wx.Colour(80, 200, 80, 255), 1))
            gc.FillPath(side_path)
            gc.StrokePath(side_path)
    
    def draw_tracks(self, gc, center_x, center_y):
        """Draw tracks with layer culling"""
        scale = self.viewer.zoom * 2.0
        rz = math.radians(self.viewer.rotation_z)
        rx = math.radians(self.viewer.rotation_x)
        viewing_from_top = self.viewer.rotation_x >= 0
        
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        for track in self.board.GetTracks():
            track_class = track.GetClass()
            if track_class not in ["PCB_TRACE", "TRACK", "PCB_TRACK"]:
                continue
                
            layer = track.GetLayer()
            if viewing_from_top and layer == pcbnew.B_Cu:
                continue
            if not viewing_from_top and layer == pcbnew.F_Cu:
                continue
            
            start = track.GetStart()
            end = track.GetEnd()
            
            x1_mm = start.x / 1e6 - bbox_center_x
            y1_mm = start.y / 1e6 - bbox_center_y
            x2_mm = end.x / 1e6 - bbox_center_x
            y2_mm = end.y / 1e6 - bbox_center_y
            
            px1 = center_x + (x1_mm * math.cos(rz) - y1_mm * math.sin(rz)) * scale
            py1 = center_y + (x1_mm * math.sin(rz) * math.sin(rx) + y1_mm * math.cos(rz) * math.sin(rx)) * scale
            px2 = center_x + (x2_mm * math.cos(rz) - y2_mm * math.sin(rz)) * scale
            py2 = center_y + (x2_mm * math.sin(rz) * math.sin(rx) + y2_mm * math.cos(rz) * math.sin(rx)) * scale
            
            track_width = track.GetWidth() / 1e6
            pen_width = max(3, int(track_width * scale * 2))
            
            if layer == pcbnew.F_Cu:
                gc.SetPen(wx.Pen(wx.Colour(220, 120, 60), pen_width))
            elif layer == pcbnew.B_Cu:
                gc.SetPen(wx.Pen(wx.Colour(100, 140, 200), pen_width))
            else:
                gc.SetPen(wx.Pen(wx.Colour(200, 160, 80), pen_width))
            
            gc.StrokeLine(px1, py1, px2, py2)
    
    def draw_vias(self, gc, center_x, center_y):
        """Draw vias"""
        scale = self.viewer.zoom * 2.0
        rz = math.radians(self.viewer.rotation_z)
        rx = math.radians(self.viewer.rotation_x)
        
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        for track in self.board.GetTracks():
            if track.GetClass() == "PCB_VIA":
                pos = track.GetPosition()
                x_mm = pos.x / 1e6 - bbox_center_x
                y_mm = pos.y / 1e6 - bbox_center_y
                
                px = center_x + (x_mm * math.cos(rz) - y_mm * math.sin(rz)) * scale
                py = center_y + (x_mm * math.sin(rz) * math.sin(rx) + y_mm * math.cos(rz) * math.sin(rx)) * scale
                
                via_width = track.GetWidth() / 1e6
                via_radius = (via_width * scale) / 2
                
                gc.SetBrush(wx.Brush(wx.Colour(180, 140, 60)))
                gc.SetPen(wx.Pen(wx.Colour(140, 100, 40), 1))
                gc.DrawEllipse(px - via_radius, py - via_radius, via_radius * 2, via_radius * 2)
                
                drill_radius = via_radius * 0.5
                gc.SetBrush(wx.Brush(wx.Colour(40, 40, 40)))
                gc.SetPen(wx.Pen(wx.Colour(20, 20, 20), 1))
                gc.DrawEllipse(px - drill_radius, py - drill_radius, drill_radius * 2, drill_radius * 2)
    
    def draw_components(self, gc, center_x, center_y):
        """Draw components with layer culling"""
        scale = self.viewer.zoom * 2.0
        rz = math.radians(self.viewer.rotation_z)
        rx = math.radians(self.viewer.rotation_x)
        viewing_from_top = self.viewer.rotation_x >= 0
        
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        for footprint in self.board.GetFootprints():
            is_bottom = footprint.IsFlipped()
            
            if viewing_from_top and is_bottom:
                continue
            if not viewing_from_top and not is_bottom:
                continue
            
            for pad in footprint.Pads():
                self.draw_pad(gc, pad, bbox_center_x, bbox_center_y, center_x, center_y, scale, rz, rx, is_bottom)
    
    def draw_pad(self, gc, pad, bbox_cx, bbox_cy, center_x, center_y, scale, rz, rx, is_bottom):
        """Draw a pad"""
        pad_pos = pad.GetPosition()
        abs_x = pad_pos.x / 1e6 - bbox_cx
        abs_y = pad_pos.y / 1e6 - bbox_cy
        
        px = center_x + (abs_x * math.cos(rz) - abs_y * math.sin(rz)) * scale
        py = center_y + (abs_x * math.sin(rz) * math.sin(rx) + abs_y * math.cos(rz) * math.sin(rx)) * scale
        
        pad_size = pad.GetSize()
        pw = pad_size.x / 1e6 * scale
        ph = pad_size.y / 1e6 * scale
        
        if is_bottom:
            gc.SetBrush(wx.Brush(wx.Colour(150, 150, 220)))
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 180), 1))
        else:
            gc.SetBrush(wx.Brush(wx.Colour(220, 180, 100)))
            gc.SetPen(wx.Pen(wx.Colour(180, 140, 60), 1))
        
        pad_shape = pad.GetShape()
        if pad_shape == pcbnew.PAD_SHAPE_CIRCLE:
            gc.DrawEllipse(px - pw/2, py - ph/2, pw, ph)
        elif pad_shape == pcbnew.PAD_SHAPE_ROUNDRECT:
            corner_radius = min(pw, ph) * 0.25
            gc.DrawRoundedRectangle(px - pw/2, py - ph/2, pw, ph, corner_radius)
        else:
            gc.DrawRectangle(px - pw/2, py - ph/2, pw, ph)
        
        # Draw drill hole
        drill_size = pad.GetDrillSize()
        if drill_size.x > 0:
            drill_w = drill_size.x / 1e6 * scale
            gc.SetBrush(wx.Brush(wx.Colour(40, 40, 40)))
            gc.SetPen(wx.Pen(wx.Colour(20, 20, 20), 1))
            gc.DrawEllipse(px - drill_w/2, py - drill_w/2, drill_w, drill_w)
    
    def draw_coordinate_overlay(self, gc):
        """Draw coordinate overlay"""
        if not self.hover_pos:
            return
        
        x, y = self.hover_pos
        coords_3d = self.hover_coords_3d
        
        gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 180)))
        gc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 1))
        
        coord_text = f"X: {coords_3d[0]:.3f} mm\nY: {coords_3d[1]:.3f} mm\nZ: {coords_3d[2]:.3f} mm"
        
        font = wx.Font(10, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        gc.SetFont(font, wx.Colour(255, 255, 255))
        
        box_w, box_h = 150, 60
        box_x = x + 15
        box_y = y - box_h - 15
        
        width, height = self.GetSize()
        if box_x + box_w > width:
            box_x = x - box_w - 15
        if box_y < 0:
            box_y = y + 15
        
        gc.DrawRoundedRectangle(box_x, box_y, box_w, box_h, 5)
        
        lines = coord_text.split('\n')
        text_y = box_y + 10
        for line in lines:
            gc.DrawText(line, box_x + 10, text_y)
            text_y += 18
    
    def draw_orientation_indicator(self, gc, width, height):
        """Draw XYZ orientation indicator"""
        origin_x, origin_y = 50, height - 50
        axis_length = 30
        
        rx = math.radians(self.viewer.rotation_x)
        rz = math.radians(self.viewer.rotation_z)
        
        # X axis (red)
        x_end_x = origin_x + axis_length * math.cos(rz)
        x_end_y = origin_y + axis_length * math.sin(rz) * math.sin(rx)
        gc.SetPen(wx.Pen(wx.Colour(255, 0, 0), 2))
        gc.StrokeLine(origin_x, origin_y, x_end_x, x_end_y)
        gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.Colour(255, 0, 0))
        gc.DrawText("X", x_end_x + 5, x_end_y - 5)
        
        # Y axis (green)
        y_end_x = origin_x - axis_length * math.sin(rz)
        y_end_y = origin_y + axis_length * math.cos(rz) * math.sin(rx)
        gc.SetPen(wx.Pen(wx.Colour(0, 255, 0), 2))
        gc.StrokeLine(origin_x, origin_y, y_end_x, y_end_y)
        gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.Colour(0, 255, 0))
        gc.DrawText("Y", y_end_x + 5, y_end_y - 5)
        
        # Z axis (blue)
        z_end_y = origin_y - axis_length * math.cos(rx)
        gc.SetPen(wx.Pen(wx.Colour(0, 100, 255), 2))
        gc.StrokeLine(origin_x, origin_y, origin_x, z_end_y)
        gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.Colour(0, 100, 255))
        gc.DrawText("Z", origin_x + 5, z_end_y - 5)
    
    def update_hover_coordinates(self, pos):
        """Calculate 3D coordinates at hover position"""
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        width, height = self.GetSize()
        center_x = width / 2 + self.viewer.pan_x
        center_y = height / 2 + self.viewer.pan_y
        
        scale = self.viewer.zoom * 2.0
        rz = math.radians(self.viewer.rotation_z)
        rx = math.radians(self.viewer.rotation_x)
        
        dx = (pos.x - center_x) / scale
        dy = (pos.y - center_y) / scale
        
        x_rel_mm = dx * math.cos(-rz) - dy * math.sin(-rz) / math.sin(rx) if math.sin(rx) != 0 else dx * math.cos(-rz)
        y_rel_mm = dx * math.sin(-rz) + dy * math.cos(-rz) / math.sin(rx) if math.sin(rx) != 0 else dx * math.sin(-rz)
        
        x_mm = x_rel_mm + bbox_center_x
        y_mm = y_rel_mm + bbox_center_y
        z_mm = 0.8
        
        self.hover_coords_3d = (x_mm, y_mm, z_mm)
        self.viewer.SetStatusText(f"X: {x_mm:.3f} mm  Y: {y_mm:.3f} mm  Z: {z_mm:.3f} mm", 0)
    
    def on_mouse_move(self, event):
        """Handle mouse movement"""
        pos = event.GetPosition()
        
        if self.dragging and self.viewer.last_mouse_pos:
            dx = pos.x - self.viewer.last_mouse_pos.x
            dy = pos.y - self.viewer.last_mouse_pos.y
            self.viewer.rotation_z += dx * 0.5
            self.viewer.rotation_x += dy * 0.5
            self.viewer.rotation_x = max(-90, min(90, self.viewer.rotation_x))
            self.Refresh()
        elif self.panning and self.viewer.last_mouse_pos:
            dx = pos.x - self.viewer.last_mouse_pos.x
            dy = pos.y - self.viewer.last_mouse_pos.y
            self.viewer.pan_x += dx
            self.viewer.pan_y += dy
            self.Refresh()
        
        self.viewer.last_mouse_pos = pos
        self.hover_pos = (pos.x, pos.y)
        self.update_hover_coordinates(pos)
        
        if self.viewer.show_coordinates:
            self.Refresh()
    
    def on_left_down(self, event):
        self.dragging = True
        self.CaptureMouse()
    
    def on_left_up(self, event):
        if self.dragging:
            self.dragging = False
            if self.HasCapture():
                self.ReleaseMouse()
    
    def on_right_down(self, event):
        self.panning = True
        self.CaptureMouse()
    
    def on_right_up(self, event):
        if self.panning:
            self.panning = False
            if self.HasCapture():
                self.ReleaseMouse()
    
    def on_mouse_wheel(self, event):
        rotation = event.GetWheelRotation()
        if rotation > 0:
            self.viewer.zoom *= 1.1
        else:
            self.viewer.zoom *= 0.9
        self.viewer.zoom = max(0.1, min(10.0, self.viewer.zoom))
        self.Refresh()


class TopViewBoundingBoxDialog(wx.Frame):
    """
    Dialog for viewing top of board in 2D and selecting bounding boxes
    Shows only top layer components and traces
    """
    
    def __init__(self, parent, board):
        super(TopViewBoundingBoxDialog, self).__init__(
            parent,
            title="Top View with Bounding Box",
            size=(1200, 800),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        self.board = board
        self.bbox_start = None  # (x_mm, y_mm)
        self.bbox_end = None    # (x_mm, y_mm)
        
        # Boundary conditions for each side (3D)
        self.boundary_conditions = {
            'x_min': {'magnitude': '', 'type': 'PML'},  # Left side
            'x_max': {'magnitude': '', 'type': 'PML'},  # Right side
            'y_min': {'magnitude': '', 'type': 'PML'},  # Front (toward you)
            'y_max': {'magnitude': '', 'type': 'PML'},  # Back (away from you)
            'z_min': {'magnitude': '', 'type': 'PEC'},  # Bottom (ground plane)
            'z_max': {'magnitude': '', 'type': 'PML'}   # Top (open air)
        }
        
        self.create_ui()
        self.Centre()
    
    def create_ui(self):
        """Create the user interface"""
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Toolbar
        toolbar_panel = wx.Panel(main_panel)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Title/Instructions
        title = wx.StaticText(toolbar_panel, 
            label="Top View (F.Cu + Top Components Only)")
        title_font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        toolbar_sizer.Add(title, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        toolbar_sizer.AddStretchSpacer()
        
        # Instructions
        instructions = wx.StaticText(toolbar_panel, 
            label="Click and drag to select bounding box")
        toolbar_sizer.Add(instructions, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        toolbar_panel.SetSizer(toolbar_sizer)
        main_sizer.Add(toolbar_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # 2D Canvas (Top View Only)
        self.canvas = TopViewCanvas(main_panel, self)
        main_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        
        # Coordinate input panel
        coord_panel = wx.Panel(main_panel)
        coord_sizer = wx.GridBagSizer(5, 10)
        
        # Start coordinates
        coord_sizer.Add(wx.StaticText(coord_panel, label="Start Point:"), (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        coord_sizer.Add(wx.StaticText(coord_panel, label="X:"), (0, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        self.start_x_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.start_x_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.start_x_ctrl, (0, 2))
        coord_sizer.Add(wx.StaticText(coord_panel, label="Y:"), (0, 3), flag=wx.ALIGN_CENTER_VERTICAL)
        self.start_y_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.start_y_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.start_y_ctrl, (0, 4))
        coord_sizer.Add(wx.StaticText(coord_panel, label="mm"), (0, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        
        # End coordinates
        coord_sizer.Add(wx.StaticText(coord_panel, label="End Point:"), (1, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        coord_sizer.Add(wx.StaticText(coord_panel, label="X:"), (1, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        self.end_x_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.end_x_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.end_x_ctrl, (1, 2))
        coord_sizer.Add(wx.StaticText(coord_panel, label="Y:"), (1, 3), flag=wx.ALIGN_CENTER_VERTICAL)
        self.end_y_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.end_y_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.end_y_ctrl, (1, 4))
        coord_sizer.Add(wx.StaticText(coord_panel, label="mm"), (1, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        
        # Dimensions display
        coord_sizer.Add(wx.StaticText(coord_panel, label="Dimensions:"), (2, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.width_label = wx.StaticText(coord_panel, label="Width: --")
        coord_sizer.Add(self.width_label, (2, 1), (1, 2))
        self.height_label = wx.StaticText(coord_panel, label="Height: --")
        coord_sizer.Add(self.height_label, (2, 3), (1, 2))
        self.area_label = wx.StaticText(coord_panel, label="Area: --")
        coord_sizer.Add(self.area_label, (2, 5), (1, 2))
        
        # Buttons
        clear_btn = wx.Button(coord_panel, label="Clear Selection")
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_selection)
        coord_sizer.Add(clear_btn, (3, 0), (1, 2))
        
        copy_btn = wx.Button(coord_panel, label="Copy Coordinates")
        copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_coordinates)
        coord_sizer.Add(copy_btn, (3, 2), (1, 2))
        
        export_btn = wx.Button(coord_panel, label="Export Selection")
        export_btn.Bind(wx.EVT_BUTTON, self.on_export_selection)
        coord_sizer.Add(export_btn, (3, 4), (1, 2))
        
        # EMI Simulation button
        emi_btn = wx.Button(coord_panel, label="Run EMI Simulation")
        emi_btn.Bind(wx.EVT_BUTTON, self.on_run_emi_simulation)
        emi_btn.SetBackgroundColour(wx.Colour(60, 120, 180))
        emi_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        coord_sizer.Add(emi_btn, (3, 6), (1, 2))
        
        coord_panel.SetSizer(coord_sizer)
        main_sizer.Add(coord_panel, 0, wx.EXPAND | wx.ALL, 10)
        
        # Boundary Conditions Panel
        bc_panel = wx.Panel(main_panel)
        bc_panel.SetBackgroundColour(wx.Colour(50, 50, 50))
        bc_sizer = wx.StaticBoxSizer(wx.VERTICAL, bc_panel, "3D Boundary Conditions")
        
        # Add explanation
        bc_info = wx.StaticText(bc_panel, 
            label="Define electromagnetic boundary conditions for the 3D simulation volume")
        bc_info.SetForegroundColour(wx.Colour(200, 200, 200))
        bc_sizer.Add(bc_info, 0, wx.ALL, 5)
        
        # Grid for BC inputs
        bc_grid = wx.GridBagSizer(5, 10)
        
        # Header row
        bc_grid.Add(wx.StaticText(bc_panel, label="Boundary"), (0, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER)
        bc_grid.Add(wx.StaticText(bc_panel, label="Location"), (0, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER)
        bc_grid.Add(wx.StaticText(bc_panel, label="Type"), (0, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER)
        bc_grid.Add(wx.StaticText(bc_panel, label="Notes"), (0, 3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER)
        
        # Create controls for each boundary with clear 3D labels
        self.bc_controls = {}
        
        # X-axis boundaries (left/right in plan view)
        boundaries = [
            ('x_min', 'X-Min', 'Left edge (-X)', 'Left side of selection box'),
            ('x_max', 'X-Max', 'Right edge (+X)', 'Right side of selection box'),
            ('y_min', 'Y-Min', 'Front edge (-Y)', 'Front side (toward you)'),
            ('y_max', 'Y-Max', 'Back edge (+Y)', 'Back side (away from you)'),
            ('z_min', 'Z-Min', 'Bottom (PCB)', 'Bottom of simulation (often ground)'),
            ('z_max', 'Z-Max', 'Top (Air)', 'Top of simulation (open air)')
        ]
        
        bc_types = ['PML', 'PEC', 'PMC', 'Periodic']
        
        for i, (key, label, location, notes) in enumerate(boundaries, start=1):
            # Boundary label
            label_widget = wx.StaticText(bc_panel, label=label + ":")
            label_widget.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            bc_grid.Add(label_widget, (i, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
            
            # Location description
            loc_widget = wx.StaticText(bc_panel, label=location)
            loc_widget.SetForegroundColour(wx.Colour(180, 180, 180))
            bc_grid.Add(loc_widget, (i, 1), flag=wx.ALIGN_CENTER_VERTICAL)
            
            # Type dropdown with meaningful BC types
            type_ctrl = wx.Choice(bc_panel, choices=bc_types)
            # Set defaults
            if key == 'z_min':
                type_ctrl.SetSelection(1)  # PEC for bottom (ground plane)
            else:
                type_ctrl.SetSelection(0)  # PML for others (absorbing)
            
            type_ctrl.Bind(wx.EVT_CHOICE, lambda e, k=key: self.on_bc_changed(k, 'type', e))
            bc_grid.Add(type_ctrl, (i, 2))
            
            # Notes
            notes_widget = wx.StaticText(bc_panel, label=notes)
            notes_widget.SetForegroundColour(wx.Colour(150, 150, 150))
            notes_widget.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
            bc_grid.Add(notes_widget, (i, 3), flag=wx.ALIGN_CENTER_VERTICAL)
            
            # Store controls
            self.bc_controls[key] = {
                'type': type_ctrl
            }
        
        bc_sizer.Add(bc_grid, 0, wx.ALL | wx.EXPAND, 10)
        
        # Add BC type legend
        legend_sizer = wx.BoxSizer(wx.VERTICAL)
        legend_title = wx.StaticText(bc_panel, label="Boundary Condition Types:")
        legend_title.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        legend_sizer.Add(legend_title, 0, wx.ALL, 5)
        
        legend_text = wx.StaticText(bc_panel, 
            label="• PML (Perfectly Matched Layer): Absorbing boundary - simulates open space\n"
                  "• PEC (Perfect Electric Conductor): Reflecting boundary - metal wall (E tangential = 0)\n"
                  "• PMC (Perfect Magnetic Conductor): Reflecting boundary - magnetic wall (H tangential = 0)\n"
                  "• Periodic: Repeating structure (for array analysis)")
        legend_text.SetForegroundColour(wx.Colour(180, 180, 180))
        legend_text.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        legend_sizer.Add(legend_text, 0, wx.ALL, 5)
        
        bc_sizer.Add(legend_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        bc_panel.SetSizer(bc_sizer)
        main_sizer.Add(bc_panel, 0, wx.EXPAND | wx.ALL, 10)
        
        # Simulation Settings Panel
        settings_panel = wx.Panel(main_panel)
        settings_panel.SetBackgroundColour(wx.Colour(50, 50, 50))
        settings_sizer = wx.StaticBoxSizer(wx.VERTICAL, settings_panel, "Simulation Settings")
        
        # Grid resolution control
        grid_res_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        grid_res_label = wx.StaticText(settings_panel, label="Grid Resolution (cells/wavelength):")
        grid_res_label.SetForegroundColour(wx.Colour(200, 200, 200))
        grid_res_sizer.Add(grid_res_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        self.grid_resolution_ctrl = wx.SpinCtrl(settings_panel, value="15", min=12, max=30, size=(70, -1))
        self.grid_resolution_ctrl.SetToolTip(
            "Higher = More accurate but slower\n"
            "Lower = Faster but less accurate\n"
            "Recommended: 15-20 for stability\n"
            "12 = Coarse (fast, may be unstable)\n"
            "15 = Balanced (recommended)\n"
            "20 = Fine (slow, very stable)\n"
            "30 = Very fine (very slow)"
        )
        grid_res_sizer.Add(self.grid_resolution_ctrl, 0, wx.ALL, 5)
        
        grid_res_info = wx.StaticText(settings_panel, 
            label="(Lower = faster/less stable, Higher = slower/more stable)")
        grid_res_info.SetForegroundColour(wx.Colour(150, 150, 150))
        grid_res_info.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        grid_res_sizer.Add(grid_res_info, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        settings_sizer.Add(grid_res_sizer, 0, wx.ALL, 5)
        
        # Info text
        settings_info = wx.StaticText(settings_panel,
            label="Grid resolution affects simulation accuracy and stability.\n"
                  "If simulation becomes unstable, try increasing this value.")
        settings_info.SetForegroundColour(wx.Colour(180, 180, 180))
        settings_info.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        settings_sizer.Add(settings_info, 0, wx.ALL, 5)
        
        settings_panel.SetSizer(settings_sizer)
        main_sizer.Add(settings_panel, 0, wx.EXPAND | wx.ALL, 10)
        
        # Status bar
        self.status_bar = self.CreateStatusBar(1)
        self.SetStatusText("Viewing top layer only - Click and drag to select bounding box", 0)
        
        main_panel.SetSizer(main_sizer)
    
    def update_bbox_from_controls(self):
        """Update bounding box from text controls"""
        try:
            start_x = float(self.start_x_ctrl.GetValue())
            start_y = float(self.start_y_ctrl.GetValue())
            end_x = float(self.end_x_ctrl.GetValue())
            end_y = float(self.end_y_ctrl.GetValue())
            
            self.bbox_start = (start_x, start_y)
            self.bbox_end = (end_x, end_y)
            self.update_dimensions()
            self.canvas.Refresh()
            return True
        except ValueError:
            return False
    
    def update_controls_from_bbox(self):
        """Update text controls from bounding box"""
        if self.bbox_start and self.bbox_end:
            self.start_x_ctrl.SetValue(f"{self.bbox_start[0]:.3f}")
            self.start_y_ctrl.SetValue(f"{self.bbox_start[1]:.3f}")
            self.end_x_ctrl.SetValue(f"{self.bbox_end[0]:.3f}")
            self.end_y_ctrl.SetValue(f"{self.bbox_end[1]:.3f}")
            self.update_dimensions()
    
    def update_dimensions(self):
        """Update dimension labels"""
        if self.bbox_start and self.bbox_end:
            width = abs(self.bbox_end[0] - self.bbox_start[0])
            height = abs(self.bbox_end[1] - self.bbox_start[1])
            area = width * height
            
            self.width_label.SetLabel(f"Width: {width:.3f} mm")
            self.height_label.SetLabel(f"Height: {height:.3f} mm")
            self.area_label.SetLabel(f"Area: {area:.3f} mm²")
        else:
            self.width_label.SetLabel("Width: --")
            self.height_label.SetLabel("Height: --")
            self.area_label.SetLabel("Area: --")
    
    def on_coord_changed(self, event):
        """Handle manual coordinate entry"""
        self.update_bbox_from_controls()
    
    def on_bc_changed(self, side, field, event):
        """Handle boundary condition changes"""
        if field == 'type':
            ctrl = event.GetEventObject()
            self.boundary_conditions[side]['type'] = ctrl.GetStringSelection()
    
    def on_clear_selection(self, event):
        """Clear the selection"""
        self.bbox_start = None
        self.bbox_end = None
        self.start_x_ctrl.Clear()
        self.start_y_ctrl.Clear()
        self.end_x_ctrl.Clear()
        self.end_y_ctrl.Clear()
        self.update_dimensions()
        self.canvas.Refresh()
        self.SetStatusText("Selection cleared - Top layer view", 0)
    
    def on_copy_coordinates(self, event):
        """Copy coordinates to clipboard"""
        if self.bbox_start and self.bbox_end:
            text = f"Top View Selection\n"
            text += f"Start: ({self.bbox_start[0]:.3f}, {self.bbox_start[1]:.3f}) mm\n"
            text += f"End: ({self.bbox_end[0]:.3f}, {self.bbox_end[1]:.3f}) mm\n"
            width = abs(self.bbox_end[0] - self.bbox_start[0])
            height = abs(self.bbox_end[1] - self.bbox_start[1])
            text += f"Width: {width:.3f} mm, Height: {height:.3f} mm"
            
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
                self.SetStatusText("Coordinates copied to clipboard", 0)
        else:
            wx.MessageBox("No bounding box selected", "Info", wx.OK | wx.ICON_INFORMATION)
    
    def on_export_selection(self, event):
        """Export selection to file"""
        if not self.bbox_start or not self.bbox_end:
            wx.MessageBox("No bounding box selected", "Info", wx.OK | wx.ICON_INFORMATION)
            return
        
        dlg = wx.FileDialog(
            self, "Save top view bounding box",
            wildcard="Text files (*.txt)|*.txt|CSV files (*.csv)|*.csv",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            
            with open(filepath, 'w') as f:
                if filepath.endswith('.csv'):
                    f.write("Layer,Top (F.Cu)\n")
                    f.write("Parameter,X (mm),Y (mm)\n")
                    f.write(f"Start,{self.bbox_start[0]:.3f},{self.bbox_start[1]:.3f}\n")
                    f.write(f"End,{self.bbox_end[0]:.3f},{self.bbox_end[1]:.3f}\n")
                    width = abs(self.bbox_end[0] - self.bbox_start[0])
                    height = abs(self.bbox_end[1] - self.bbox_start[1])
                    f.write(f"Width,{width:.3f},\n")
                    f.write(f"Height,,{height:.3f}\n")
                    f.write("\n3D Boundary Conditions\n")
                    f.write("Boundary,Type\n")
                    bc_labels = {
                        'x_min': 'X-Min (Left)',
                        'x_max': 'X-Max (Right)',
                        'y_min': 'Y-Min (Front)',
                        'y_max': 'Y-Max (Back)',
                        'z_min': 'Z-Min (Bottom)',
                        'z_max': 'Z-Max (Top)'
                    }
                    for key in ['x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max']:
                        bc = self.boundary_conditions[key]
                        f.write(f"{bc_labels[key]},{bc['type']}\n")
                else:
                    f.write(f"Top View Bounding Box Coordinates\n")
                    f.write(f"==================================\n\n")
                    f.write(f"Layer: Top (F.Cu) only\n\n")
                    f.write(f"Start Point: ({self.bbox_start[0]:.3f}, {self.bbox_start[1]:.3f}) mm\n")
                    f.write(f"End Point: ({self.bbox_end[0]:.3f}, {self.bbox_end[1]:.3f}) mm\n\n")
                    width = abs(self.bbox_end[0] - self.bbox_start[0])
                    height = abs(self.bbox_end[1] - self.bbox_start[1])
                    area = width * height
                    f.write(f"Dimensions:\n")
                    f.write(f"  Width: {width:.3f} mm\n")
                    f.write(f"  Height: {height:.3f} mm\n")
                    f.write(f"  Area: {area:.3f} mm²\n\n")
                    f.write(f"3D Boundary Conditions:\n")
                    bc_labels = {
                        'x_min': 'X-Min (Left)',
                        'x_max': 'X-Max (Right)',
                        'y_min': 'Y-Min (Front)',
                        'y_max': 'Y-Max (Back)',
                        'z_min': 'Z-Min (Bottom/PCB)',
                        'z_max': 'Z-Max (Top/Air)'
                    }
                    for key in ['x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max']:
                        bc = self.boundary_conditions[key]
                        f.write(f"  {bc_labels[key]}: {bc['type']}\n")
            
            self.SetStatusText(f"Top view selection exported to {filepath}", 0)
        
        dlg.Destroy()
    
    def on_run_emi_simulation(self, event):
        """Run EMI simulation on selected region"""
        if not self.bbox_start or not self.bbox_end:
            wx.MessageBox(
                "Please select a bounding box first",
                "No Selection",
                wx.OK | wx.ICON_WARNING
            )
            return
        
        # Show info dialog
        info_msg = (
            f"Starting EMI simulation on region:\n"
            f"Start: ({self.bbox_start[0]:.2f}, {self.bbox_start[1]:.2f}) mm\n"
            f"End: ({self.bbox_end[0]:.2f}, {self.bbox_end[1]:.2f}) mm\n\n"
            f"This may take a few seconds to minutes depending on size.\n"
            f"The UI will remain responsive."
        )
        
        dlg = wx.MessageDialog(self, info_msg, "EMI Simulation", 
                              wx.OK | wx.CANCEL | wx.ICON_INFORMATION)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        dlg.Destroy()
        
        # Create progress dialog
        self.progress_dlg = wx.ProgressDialog(
            "EMI Simulation",
            "Initializing FDTD simulation...",
            maximum=100,
            parent=self,
            style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT
        )
        
        # Get grid resolution from UI
        grid_resolution = self.grid_resolution_ctrl.GetValue()
        
        # Create simulator
        try:
            simulator = EMISimulator(
                self.board,
                self.bbox_start,
                self.bbox_end,
                self.boundary_conditions,
                cells_per_wavelength=grid_resolution
            )
        except Exception as e:
            self.progress_dlg.Destroy()
            self.progress_dlg = None
            wx.MessageBox(
                f"Failed to initialize simulator: {str(e)}\n\n"
                f"This might be due to invalid geometry or grid settings.",
                "Initialization Error",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        # Thread-safe progress callback
        self.simulation_cancelled = False
        self.progress_value = 0
        self.progress_status = "Initializing..."
        
        def update_progress(percent, status=None):
            self.progress_value = percent
            if status:
                self.progress_status = status
            
            def _update():
                if self.progress_dlg:
                    try:
                        # Update with both percent and status
                        (cont, skip) = self.progress_dlg.Update(
                            self.progress_value,
                            self.progress_status
                        )
                        if not cont:
                            self.simulation_cancelled = True
                        return cont
                    except:
                        return False
                return False
            
            # Use CallAfter for thread-safe GUI updates
            wx.CallAfter(_update)
            return not self.simulation_cancelled
        
        # Run simulation in separate thread
        import threading
        
        def run_simulation_thread():
            results = None
            error = None
            
            try:
                # Run simulation
                self.SetStatusText("Running EMI simulation...", 0)
                results = simulator.run_simulation(progress_callback=update_progress)
                
                if results is None:
                    error = "Simulation returned no results"
                elif self.simulation_cancelled:
                    error = "Simulation was cancelled by user"
                    
            except Exception as e:
                error = f"Simulation error: {str(e)}\n\nDetails: {repr(e)}"
                import traceback
                error += f"\n\nTraceback:\n{traceback.format_exc()}"
            
            # Update UI on main thread
            def finish_simulation():
                if self.progress_dlg:
                    self.progress_dlg.Destroy()
                    self.progress_dlg = None
                
                if error:
                    wx.MessageBox(
                        error,
                        "Simulation Error",
                        wx.OK | wx.ICON_ERROR
                    )
                    self.SetStatusText("Simulation failed", 0)
                elif results:
                    # Check if simulation succeeded
                    if results.get('success', True) == False:
                        # Simulation failed internally - show detailed error with log
                        error_msg = results.get('error', 'Unknown error')
                        error_trace = results.get('error_trace', '')
                        sim_log = results.get('simulation_log', 'No log available')
                        
                        # Create detailed error dialog
                        error_dialog = wx.Dialog(self, title="Simulation Failed - Detailed Error Report",
                                                size=(800, 600),
                                                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
                        
                        panel = wx.Panel(error_dialog)
                        sizer = wx.BoxSizer(wx.VERTICAL)
                        
                        # Error message
                        error_label = wx.StaticText(panel, label="Error:")
                        error_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                        sizer.Add(error_label, 0, wx.ALL, 5)
                        
                        error_text = wx.TextCtrl(panel, value=error_msg, 
                                                style=wx.TE_MULTILINE | wx.TE_READONLY)
                        error_text.SetFont(wx.Font(9, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                        sizer.Add(error_text, 0, wx.EXPAND | wx.ALL, 5)
                        
                        # Simulation log
                        log_label = wx.StaticText(panel, label="Simulation Log (shows what was attempted):")
                        log_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                        sizer.Add(log_label, 0, wx.ALL, 5)
                        
                        log_text = wx.TextCtrl(panel, value=sim_log,
                                              style=wx.TE_MULTILINE | wx.TE_READONLY)
                        log_text.SetFont(wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                        sizer.Add(log_text, 1, wx.EXPAND | wx.ALL, 5)
                        
                        # Trace (if available)
                        if error_trace:
                            trace_label = wx.StaticText(panel, label="Python Traceback:")
                            trace_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                            sizer.Add(trace_label, 0, wx.ALL, 5)
                            
                            trace_text = wx.TextCtrl(panel, value=error_trace,
                                                    style=wx.TE_MULTILINE | wx.TE_READONLY)
                            trace_text.SetFont(wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                            sizer.Add(trace_text, 1, wx.EXPAND | wx.ALL, 5)
                        
                        # OK button
                        ok_btn = wx.Button(panel, wx.ID_OK, "Close")
                        sizer.Add(ok_btn, 0, wx.ALL | wx.CENTER, 10)
                        
                        panel.SetSizer(sizer)
                        error_dialog.ShowModal()
                        error_dialog.Destroy()
                        
                        self.SetStatusText("Simulation failed - see error dialog", 0)
                    else:
                        # Show results dialog
                        self.SetStatusText("Simulation complete - showing results", 0)
                        try:
                            results_dlg = EMIResultsDialog(self, results, simulator)
                            results_dlg.Show()
                        except Exception as e:
                            import traceback
                            wx.MessageBox(
                                f"Failed to display results: {str(e)}\n\n"
                                f"Traceback:\n{traceback.format_exc()}",
                                "Display Error",
                                wx.OK | wx.ICON_ERROR
                            )
                else:
                    wx.MessageBox(
                        "Simulation completed but produced no results",
                        "No Results",
                        wx.OK | wx.ICON_WARNING
                    )
                    self.SetStatusText("Simulation completed with no results", 0)
            
            wx.CallAfter(finish_simulation)
        
        # Start simulation thread
        sim_thread = threading.Thread(target=run_simulation_thread, daemon=True)
        sim_thread.start()
        
        self.SetStatusText("EMI simulation started in background...", 0)


class EMIResultsDialog(wx.Frame):
    """Dialog to display EMI simulation results"""
    
    def __init__(self, parent, results, simulator):
        super(EMIResultsDialog, self).__init__(
            parent,
            title="EMI Simulation Results",
            size=(800, 600),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        self.results = results
        self.simulator = simulator
        
        self.create_ui()
        self.Centre()
    
    def create_ui(self):
        """Create the results UI"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="EMI Simulation Results")
        title_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)
        
        # Results notebook
        notebook = wx.Notebook(panel)
        
        # Summary tab
        summary_panel = self.create_summary_panel(notebook)
        notebook.AddPage(summary_panel, "Summary")
        
        # Field visualization tab
        field_panel = self.create_field_panel(notebook)
        notebook.AddPage(field_panel, "Field Visualization")
        
        # Simulation log tab (ALWAYS show - helps debug issues)
        log_panel = self.create_log_panel(notebook)
        notebook.AddPage(log_panel, "Simulation Log")
        
        # Export tab
        export_panel = self.create_export_panel(notebook)
        notebook.AddPage(export_panel, "Export")
        
        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)
        
        # Close button
        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        main_sizer.Add(close_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
    
    def create_summary_panel(self, parent):
        """Create summary results panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create summary text
        summary_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        summary_text.SetFont(wx.Font(10, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        # Build summary with safe access
        try:
            grid_info = self.results.get('grid_info', {})
            grid_size = grid_info.get('grid_size', (0,0,0))
            cell_size = grid_info.get('cell_size', (0,0,0))
            num_steps = grid_info.get('num_steps', 0)
            time_step = grid_info.get('time_step', 0)
            
            frequency = self.results.get('frequency', 0)
            num_traces = self.results.get('num_traces', 0)
            num_vias = self.results.get('num_vias', 0)
            num_pads = self.results.get('num_pads', 0)
            max_e_field = self.results.get('max_e_field', 0.0)
            
            bc = self.results.get('boundary_conditions', {})
            
            summary = f"""EMI Simulation Summary
{'='*50}

Simulation Parameters:
  Frequency: {frequency/1e9:.2f} GHz
  Grid Size: {grid_size}
  Cell Size: ({cell_size[0]:.4f}, {cell_size[1]:.4f}, {cell_size[2]:.4f}) mm
  Time Steps: {num_steps}
  Time Step: {time_step*1e12:.4f} ps

PCB Geometry:
  Traces: {num_traces}
  Vias: {num_vias}
  Pads: {num_pads}

Boundary Conditions (3D):
  X-Min (Left):   {bc.get('x_min', {}).get('type', 'N/A')}
  X-Max (Right):  {bc.get('x_max', {}).get('type', 'N/A')}
  Y-Min (Front):  {bc.get('y_min', {}).get('type', 'N/A')}
  Y-Max (Back):   {bc.get('y_max', {}).get('type', 'N/A')}
  Z-Min (Bottom): {bc.get('z_min', {}).get('type', 'N/A')}
  Z-Max (Top):    {bc.get('z_max', {}).get('type', 'N/A')}

Results:
  Maximum E-field: {max_e_field:.6e} V/m
  
Note: Components are currently treated as passive metal structures.
      Component emission profiles can be added in future versions.

FDTD Method: Yee grid with leapfrog time-stepping
Based on: openEMS and gerber2EMS approaches
"""
        except Exception as e:
            summary = f"Error displaying results: {str(e)}\n\nRaw results data available for export."
        
        summary_text.SetValue(summary)
        sizer.Add(summary_text, 1, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_field_panel(self, parent):
        """Create field visualization panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        info = wx.StaticText(panel, 
            label="Field visualization shows E-field magnitude time history at domain center")
        sizer.Add(info, 0, wx.ALL, 10)
        
        # Simple text plot of field history
        plot_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        plot_text.SetFont(wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        # Create ASCII plot
        try:
            history = self.results.get('e_field_history', [])
            
            if not history or len(history) == 0:
                plot_str = "No field history data available.\n\n"
                plot_str += "This could mean:\n"
                plot_str += "- Simulation did not complete\n"
                plot_str += "- Grid size was invalid\n"
                plot_str += "- Field sampling failed\n"
            else:
                max_val = max(history) if history else 1.0
                plot_str = "E-field vs Time (ASCII Plot)\n\n"
                plot_str += f"Maximum E-field: {max_val:.6e} V/m\n"
                plot_str += f"Number of samples: {len(history)}\n\n"
                
                # Sample points for display
                num_samples = min(50, len(history))
                step = max(1, len(history) // num_samples)
                
                for i in range(0, len(history), step):
                    val = history[i]
                    if max_val > 0:
                        bar_len = int(40 * val / max_val)
                    else:
                        bar_len = 0
                    plot_str += f"{i:4d} | {'#' * bar_len}\n"
                
            plot_text.SetValue(plot_str)
            
        except Exception as e:
            plot_text.SetValue(f"Error creating field plot: {str(e)}")
        
        sizer.Add(plot_text, 1, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_log_panel(self, parent):
        """Create simulation log panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        info = wx.StaticText(panel,
            label="Complete simulation log - shows every step attempted (useful for debugging)")
        sizer.Add(info, 0, wx.ALL, 10)
        
        # Log display
        log_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        log_text.SetFont(wx.Font(9, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        try:
            simulation_log = self.results.get('simulation_log', 'No log available')
            if not simulation_log or simulation_log.strip() == '':
                simulation_log = "No simulation log was recorded.\n\nThis may indicate:\n"
                simulation_log += "- Simulation failed before logging started\n"
                simulation_log += "- Logger was not initialized\n"
                simulation_log += "- Check Python console for output"
            
            log_text.SetValue(simulation_log)
            
        except Exception as e:
            log_text.SetValue(f"Error loading simulation log: {str(e)}")
        
        sizer.Add(log_text, 1, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_export_panel(self, parent):
        """Create export options panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        info = wx.StaticText(panel, 
            label="Export simulation results to file")
        sizer.Add(info, 0, wx.ALL, 10)
        
        # Export buttons
        export_btn = wx.Button(panel, label="Export Results to Text File")
        export_btn.Bind(wx.EVT_BUTTON, self.on_export_results)
        sizer.Add(export_btn, 0, wx.ALL | wx.CENTER, 10)
        
        export_csv_btn = wx.Button(panel, label="Export Field Data to CSV")
        export_csv_btn.Bind(wx.EVT_BUTTON, self.on_export_field_data)
        sizer.Add(export_csv_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def on_export_results(self, event):
        """Export results summary to text file"""
        dlg = wx.FileDialog(
            self, "Save EMI simulation results",
            wildcard="Text files (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            
            with open(filepath, 'w') as f:
                f.write("EMI Simulation Results\n")
                f.write("="*60 + "\n\n")
                f.write(f"Frequency: {self.results['frequency']/1e9:.2f} GHz\n")
                f.write(f"Grid: {self.results['grid_info']['grid_size']}\n")
                f.write(f"Max E-field: {self.results['max_e_field']:.6e} V/m\n\n")
                f.write(f"Geometry:\n")
                f.write(f"  Traces: {self.results['num_traces']}\n")
                f.write(f"  Vias: {self.results['num_vias']}\n")
                f.write(f"  Pads: {self.results['num_pads']}\n")
            
            wx.MessageBox(f"Results exported to {filepath}", "Export Complete", wx.OK | wx.ICON_INFORMATION)
        
        dlg.Destroy()
    
    def on_export_field_data(self, event):
        """Export field data to CSV"""
        dlg = wx.FileDialog(
            self, "Save field data",
            wildcard="CSV files (*.csv)|*.csv",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            
            with open(filepath, 'w') as f:
                f.write("Time Step,E-field Magnitude (V/m)\n")
                for i, e_val in enumerate(self.results['e_field_history']):
                    f.write(f"{i},{e_val:.6e}\n")
            
            wx.MessageBox(f"Field data exported to {filepath}", "Export Complete", wx.OK | wx.ICON_INFORMATION)
        
        dlg.Destroy()


class EMISimulator:
    """
    Electromagnetic Interference Simulator using FDTD methods
    Based on openEMS structure and methodology
    """
    
    def __init__(self, board, bbox_start, bbox_end, boundary_conditions, cells_per_wavelength=15):
        """
        Initialize EMI simulator
        
        Args:
            board: KiCad board object
            bbox_start: (x_mm, y_mm) start of simulation region
            bbox_end: (x_mm, y_mm) end of simulation region
            boundary_conditions: dict with BC for each side
            cells_per_wavelength: Grid resolution (10-30, default 15)
                                Lower = faster but less stable
                                Higher = slower but more stable
        """
        self.board = board
        self.bbox_start = bbox_start
        self.bbox_end = bbox_end
        self.boundary_conditions = boundary_conditions
        self.cells_per_wavelength = cells_per_wavelength
        
        # Debug/error log
        self.log = []
        
        self.log_message("EMI Simulator initialized")
        self.log_message(f"Region: {bbox_start} to {bbox_end}")
        
        # Physical constants
        self.c0 = 299792458.0  # Speed of light [m/s]
        self.mu0 = 4.0 * 3.14159265359e-7  # Permeability of free space [H/m]
        self.eps0 = 8.854187817e-12  # Permittivity of free space [F/m]
        
        # Material properties (FR4 substrate)
        self.substrate_eps_r = 4.5  # Relative permittivity
        self.substrate_thickness = 1.6  # mm
        
        # Copper properties
        # Note: Using effective conductivity for FDTD stability
        # Real copper: 5.8e7 S/m, but this causes numerical instability
        # Using reduced value that still represents good conductor behavior
        self.copper_conductivity = 1e6  # S/m (effective value for FDTD)
        
        # Simulation parameters
        self.frequency = 1e9  # 1 GHz default excitation
        
        # Grid will be set up during setup_fdtd_grid
        self.nx = 0
        self.ny = 0
        self.nz = 0
        self.dx = 0.0
        self.dy = 0.0
        self.dz = 0.0
        self.dt = 0.0
        self.num_time_steps = 0
        
        # Results storage
        self.e_field = None
        self.h_field = None
    
    def log_message(self, message):
        """Add message to debug log and print to console"""
        self.log.append(message)
        try:
            print(f"[EMI Simulation] {message}")
            import sys
            if sys.stdout is not None:
                sys.stdout.flush()
        except:
            pass  # Ignore printing errors in environments where stdout isn't available
    
    def get_log(self):
        """Get full debug log"""
        return "\n".join(self.log)
    
    def setup_fdtd_grid(self):
        """Set up the FDTD computational grid with validation"""
        try:
            self.log_message("\n=== GRID SETUP ===")
            
            # Calculate simulation region dimensions
            width = abs(self.bbox_end[0] - self.bbox_start[0])
            height = abs(self.bbox_end[1] - self.bbox_start[1])
            
            self.log_message(f"PCB region: {width:.3f} x {height:.3f} mm")
            
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid region dimensions: {width} x {height} mm")
            
            # Add air layers above and below
            depth = self.substrate_thickness + 4.0  # 2mm air above + 2mm below
            
            self.log_message(f"Simulation volume: {width:.3f} x {height:.3f} x {depth:.3f} mm")
            
            # Calculate wavelength and cell size
            wavelength_mm = (self.c0 / self.frequency) * 1000  # Convert to mm
            max_cell_size = wavelength_mm / self.cells_per_wavelength
            
            self.log_message(f"Wavelength: {wavelength_mm:.3f} mm")
            self.log_message(f"Grid resolution: {self.cells_per_wavelength} cells/wavelength")
            self.log_message(f"Max cell size: {max_cell_size:.3f} mm")
            
            # Calculate grid dimensions (ensure minimum size)
            self.nx = max(20, int(width / max_cell_size) + 1)
            self.ny = max(20, int(height / max_cell_size) + 1)
            self.nz = max(10, int(depth / max_cell_size) + 1)
            
            # Cap maximum size for performance
            self.nx = min(self.nx, 150)
            self.ny = min(self.ny, 150)
            self.nz = min(self.nz, 80)
            
            self.log_message(f"Grid dimensions: {self.nx} x {self.ny} x {self.nz} = {self.nx*self.ny*self.nz} cells")
            
            # Calculate actual cell sizes
            self.dx = width / self.nx
            self.dy = height / self.ny
            self.dz = depth / self.nz
            
            self.log_message(f"Cell size: dx={self.dx:.4f}, dy={self.dy:.4f}, dz={self.dz:.4f} mm")
            
            # Time step using Courant stability condition
            # dt < 1 / (c * sqrt(1/dx^2 + 1/dy^2 + 1/dz^2))
            # Using conservative safety factor for lossy media
            # Convert to meters for calculation
            dx_m = self.dx / 1000.0
            dy_m = self.dy / 1000.0
            dz_m = self.dz / 1000.0
            
            # Courant number - use 0.5 for better stability (openEMS uses 0.5-0.7)
            courant_factor = 0.5
            
            dt_max = 1.0 / (self.c0 * math.sqrt(1.0/(dx_m**2) + 1.0/(dy_m**2) + 1.0/(dz_m**2)))
            self.dt = courant_factor * dt_max  # Conservative for lossy media
            
            self.log_message(f"Time step: {self.dt*1e12:.4f} ps (Courant factor: {courant_factor}, max: {dt_max*1e12:.4f} ps)")
            
            # Number of time steps (simulate several periods)
            period = 1.0 / self.frequency
            num_periods = 5  # Reduced from 10 for stability
            self.num_time_steps = max(100, int(num_periods * period / self.dt))
            self.num_time_steps = min(self.num_time_steps, 1000)  # Cap at 1000 for stability testing
            
            self.log_message(f"Time steps: {self.num_time_steps} ({self.num_time_steps * self.dt * 1e9:.3f} ns total, {num_periods} periods)")
            
            # Calculate source parameters for later use
            # Using ultra-weak source for maximum stability
            self.source_amplitude = 0.01  # V/m - Ultra-weak (100x less than v2.7.0)
            self.source_sigma = 3.0 * self.dt  # Gaussian width (3 time steps)
            self.source_cutoff_step = int(20 * self.source_sigma / self.dt)  # Turn off after 20σ
            
            self.log_message(f"\nSource Configuration:")
            self.log_message(f"  Amplitude: {self.source_amplitude} V/m (ultra-conservative)")
            self.log_message(f"  Pulse width: {self.source_sigma*1e12:.4f} ps")
            self.log_message(f"  Source cutoff at step: {self.source_cutoff_step}")
            self.log_message(f"  This is 100x weaker than typical for maximum stability")
            
            # Validate grid configuration and warn about potential instability
            self.log_message("\n=== GRID VALIDATION ===")
            
            total_cells = self.nx * self.ny * self.nz
            warnings = []
            critical_warnings = []
            
            # Check grid resolution (CRITICAL)
            if self.cells_per_wavelength < 12:
                critical_warnings.append(f"❌ CRITICAL: Grid resolution ({self.cells_per_wavelength}) is too low!")
                critical_warnings.append(f"   → SOLUTION: Increase to 15-20 for stability")
            elif self.cells_per_wavelength < 15:
                warnings.append(f"⚠️  Grid resolution ({self.cells_per_wavelength}) is low. Recommended: 15-20.")
            
            # Check total cells
            if total_cells < 1500:
                critical_warnings.append(f"❌ CRITICAL: Total cells ({total_cells}) is too small!")
                critical_warnings.append(f"   → SOLUTION: Select larger region (30-80mm)")
            elif total_cells < 2500:
                warnings.append(f"⚠️  Total cells ({total_cells}) is small. Recommended: > 2500 cells.")
            
            # Check for thin dimensions
            min_dim = min(self.nx, self.ny, self.nz)
            if min_dim < 6:
                critical_warnings.append(f"❌ CRITICAL: Smallest dimension has only {min_dim} cells!")
                critical_warnings.append(f"   → SOLUTION: Select larger/different region")
            elif min_dim < 10:
                warnings.append(f"⚠️  Smallest dimension has only {min_dim} cells. Recommended: > 10 cells.")
            
            # Check aspect ratio of cells (CRITICAL if high)
            max_cell_size = max(self.dx, self.dy, self.dz)
            min_cell_size = min(self.dx, self.dy, self.dz)
            aspect_ratio = max_cell_size / min_cell_size
            if aspect_ratio > 5.0:
                critical_warnings.append(f"❌ CRITICAL: Very high cell aspect ratio ({aspect_ratio:.1f}:1)!")
                critical_warnings.append(f"   → SOLUTION: Select more square region")
            elif aspect_ratio > 3.0:
                warnings.append(f"⚠️  High cell aspect ratio ({aspect_ratio:.1f}:1). Try more square region.")
            
            # Check region dimensions
            region_width = abs(self.bbox_end[0] - self.bbox_start[0])
            region_height = abs(self.bbox_end[1] - self.bbox_start[1])
            if region_width < 15.0 or region_height < 15.0:
                critical_warnings.append(f"❌ CRITICAL: Region size ({region_width:.1f}×{region_height:.1f} mm) is too small!")
                critical_warnings.append(f"   → SOLUTION: Select 30-80mm per side")
            elif region_width < 25.0 or region_height < 25.0:
                warnings.append(f"⚠️  Region size ({region_width:.1f}×{region_height:.1f} mm) is small. Recommended: > 30mm.")
            
            region_aspect = max(region_width, region_height) / min(region_width, region_height)
            if region_aspect > 4.0:
                critical_warnings.append(f"❌ CRITICAL: Region aspect ratio ({region_aspect:.1f}:1) is too high!")
                critical_warnings.append(f"   → SOLUTION: Select more square region")
            elif region_aspect > 3.0:
                warnings.append(f"⚠️  Region aspect ratio ({region_aspect:.1f}:1) is high. Try more square region.")
            
            # Display validation results
            if critical_warnings:
                self.log_message("\n🚨 CRITICAL ISSUES DETECTED - INSTABILITY VERY LIKELY:")
                for warning in critical_warnings:
                    self.log_message(f"  {warning}")
                self.log_message("\n⚠️  RECOMMENDED ACTIONS (do these before running):")
                if self.cells_per_wavelength < 12:
                    self.log_message(f"  1. INCREASE Grid Resolution from {self.cells_per_wavelength} to 20")
                if total_cells < 1500 or min_dim < 6:
                    self.log_message(f"  2. SELECT LARGER REGION (current: {region_width:.1f}×{region_height:.1f} mm → try 40×40 mm)")
                if aspect_ratio > 5.0 or region_aspect > 4.0:
                    self.log_message(f"  3. SELECT MORE SQUARE REGION")
                self.log_message("\n  Simulation will likely fail. Please fix these issues first!\n")
            elif warnings:
                self.log_message("Validation warnings:")
                for warning in warnings:
                    self.log_message(f"  {warning}")
                self.log_message("\nRecommended improvements:")
                if self.cells_per_wavelength < 15:
                    self.log_message("  → Increase Grid Resolution to 15-20")
                if total_cells < 2500 or min_dim < 10:
                    self.log_message("  → Select larger region (30-80mm per side)")
                if aspect_ratio > 3.0 or region_aspect > 3.0:
                    self.log_message("  → Select more square region")
                self.log_message("\nSimulation may complete, but results may not be reliable.\n")
            else:
                self.log_message("✓ Grid validation passed - configuration looks good!")
                self.log_message(f"  Total cells: {total_cells}")
                self.log_message(f"  Dimensions: {self.nx}×{self.ny}×{self.nz} cells")
                self.log_message(f"  Region: {region_width:.1f}×{region_height:.1f} mm")
                self.log_message(f"  Grid resolution: {self.cells_per_wavelength} cells/wavelength ✓\n")
            
            return {
                'grid_size': (self.nx, self.ny, self.nz),
                'cell_size': (self.dx, self.dy, self.dz),
                'time_step': self.dt,
                'num_steps': self.num_time_steps,
                'wavelength': wavelength_mm
            }
            
        except Exception as e:
            self.log_message(f"ERROR in grid setup: {str(e)}")
            raise
    
    def create_fdtd_arrays(self):
        """Create and initialize FDTD field arrays"""
        try:
            self.log_message("\n=== CREATING FIELD ARRAYS ===")
            self.log_message(f"Allocating {self.nx}x{self.ny}x{self.nz} arrays")
            
            # Pre-allocate all arrays at once to catch memory errors early
            total_cells = self.nx * self.ny * self.nz
            self.log_message(f"Total cells: {total_cells}")
            
            if total_cells > 5000000:  # Safety limit
                raise ValueError(f"Grid too large: {total_cells} cells (max 5M)")
            
            # Initialize E-field components
            ex = [[[0.0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Ex allocated")
            
            ey = [[[0.0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Ey allocated")
            
            ez = [[[0.0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Ez allocated")
            
            # Initialize H-field components
            hx = [[[0.0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Hx allocated")
            
            hy = [[[0.0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Hy allocated")
            
            hz = [[[0.0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Hz allocated")
            
            # Material property arrays
            eps = [[[self.eps0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Epsilon allocated")
            
            sigma = [[[0.0 for _ in range(self.nz)] for _ in range(self.ny)] for _ in range(self.nx)]
            self.log_message("Sigma allocated")
            
            self.log_message("All arrays created successfully")
            
            return {
                'ex': ex, 'ey': ey, 'ez': ez,
                'hx': hx, 'hy': hy, 'hz': hz,
                'eps': eps, 'sigma': sigma
            }
            
        except MemoryError as e:
            self.log_message(f"MEMORY ERROR: Not enough RAM for {self.nx}x{self.ny}x{self.nz} grid")
            raise ValueError(f"Grid too large for available memory: {self.nx}x{self.ny}x{self.nz}")
        except Exception as e:
            self.log_message(f"ERROR creating arrays: {str(e)}")
            raise
    
    def parse_pcb_geometry(self):
        """Parse PCB geometry within bounding box"""
        try:
            self.log_message("\n=== PARSING PCB GEOMETRY ===")
            
            geometry = {
                'traces': [],
                'vias': [],
                'pads': []
            }
            
            # Get board bounding box center
            bbox = self.board.GetBoardEdgesBoundingBox()
            bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
            bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
            
            # Define simulation region bounds
            sim_x_min = min(self.bbox_start[0], self.bbox_end[0])
            sim_x_max = max(self.bbox_start[0], self.bbox_end[0])
            sim_y_min = min(self.bbox_start[1], self.bbox_end[1])
            sim_y_max = max(self.bbox_start[1], self.bbox_end[1])
            
            self.log_message(f"Simulation bounds: X[{sim_x_min:.2f}, {sim_x_max:.2f}], Y[{sim_y_min:.2f}, {sim_y_max:.2f}]")
            
            # Parse traces
            trace_count = 0
            for track in self.board.GetTracks():
                try:
                    track_class = track.GetClass()
                    if track_class not in ["PCB_TRACE", "TRACK", "PCB_TRACK"]:
                        continue
                    
                    layer = track.GetLayer()
                    if layer != pcbnew.F_Cu:
                        continue
                    
                    start = track.GetStart()
                    end = track.GetEnd()
                    width = track.GetWidth() / 1e6
                    
                    x1 = start.x / 1e6 - bbox_center_x
                    y1 = start.y / 1e6 - bbox_center_y
                    x2 = end.x / 1e6 - bbox_center_x
                    y2 = end.y / 1e6 - bbox_center_y
                    
                    # Check if in region
                    in_region = False
                    if (sim_x_min <= x1 <= sim_x_max and sim_y_min <= y1 <= sim_y_max) or \
                       (sim_x_min <= x2 <= sim_x_max and sim_y_min <= y2 <= sim_y_max):
                        in_region = True
                    
                    if in_region:
                        geometry['traces'].append({
                            'start': (x1, y1, self.substrate_thickness),
                            'end': (x2, y2, self.substrate_thickness),
                            'width': width
                        })
                        trace_count += 1
                except Exception as e:
                    self.log_message(f"Warning: Failed to parse trace: {str(e)}")
            
            self.log_message(f"Found {trace_count} traces in region")
            
            # Parse pads
            pad_count = 0
            for footprint in self.board.GetFootprints():
                try:
                    if footprint.IsFlipped():
                        continue
                    
                    for pad in footprint.Pads():
                        try:
                            pad_pos = pad.GetPosition()
                            x = pad_pos.x / 1e6 - bbox_center_x
                            y = pad_pos.y / 1e6 - bbox_center_y
                            
                            if sim_x_min <= x <= sim_x_max and sim_y_min <= y <= sim_y_max:
                                pad_size = pad.GetSize()
                                geometry['pads'].append({
                                    'position': (x, y, self.substrate_thickness),
                                    'size': (pad_size.x / 1e6, pad_size.y / 1e6)
                                })
                                pad_count += 1
                        except Exception as e:
                            self.log_message(f"Warning: Failed to parse pad: {str(e)}")
                except Exception as e:
                    self.log_message(f"Warning: Failed to parse footprint: {str(e)}")
            
            self.log_message(f"Found {pad_count} pads in region")
            
            self.log_message(f"Geometry parsing complete: {len(geometry['traces'])} traces, {len(geometry['pads'])} pads")
            
            return geometry
            
        except Exception as e:
            self.log_message(f"ERROR parsing geometry: {str(e)}")
            raise
    
    def apply_geometry_to_grid(self, fields, geometry):
        """Apply PCB geometry to FDTD grid"""
        try:
            self.log_message("\n=== APPLYING GEOMETRY TO GRID ===")
            
            eps = fields['eps']
            sigma = fields['sigma']
            
            # Apply substrate (FR4) properties
            z_substrate_start = 2.0 / self.dz  # 2mm air below
            z_substrate_end = (2.0 + self.substrate_thickness) / self.dz
            
            substrate_cells = 0
            for i in range(self.nx):
                for j in range(self.ny):
                    for k in range(int(z_substrate_start), min(int(z_substrate_end) + 1, self.nz)):
                        eps[i][j][k] = self.eps0 * self.substrate_eps_r
                        substrate_cells += 1
            
            self.log_message(f"Applied FR4 substrate to {substrate_cells} cells (εr={self.substrate_eps_r})")
            
            # Apply copper traces
            sim_x_min = min(self.bbox_start[0], self.bbox_end[0])
            sim_y_min = min(self.bbox_start[1], self.bbox_end[1])
            
            copper_cells = 0
            for trace in geometry['traces']:
                try:
                    x1, y1, z1 = trace['start']
                    x2, y2, z2 = trace['end']
                    
                    # Convert to grid indices
                    i1 = int((x1 - sim_x_min) / self.dx)
                    i2 = int((x2 - sim_x_min) / self.dx)
                    j1 = int((y1 - sim_y_min) / self.dy)
                    j2 = int((y2 - sim_y_min) / self.dy)
                    k = int((z1 + 2.0) / self.dz)  # +2mm for air below
                    
                    # Mark cells as copper
                    for i in range(max(0, min(i1, i2)), min(self.nx, max(i1, i2) + 1)):
                        for j in range(max(0, min(j1, j2)), min(self.ny, max(j1, j2) + 1)):
                            if 0 <= k < self.nz:
                                sigma[i][j][k] = self.copper_conductivity
                                copper_cells += 1
                except Exception as e:
                    self.log_message(f"Warning: Failed to apply trace: {str(e)}")
            
            self.log_message(f"Applied copper to {copper_cells} cells (σ={self.copper_conductivity:.2e} S/m)")
            
            # Apply pads
            pad_cells = 0
            for pad in geometry['pads']:
                try:
                    x, y, z = pad['position']
                    w, h = pad['size']
                    
                    i = int((x - sim_x_min) / self.dx)
                    j = int((y - sim_y_min) / self.dy)
                    k = int((z + 2.0) / self.dz)
                    
                    # Apply pad as copper
                    if 0 <= i < self.nx and 0 <= j < self.ny and 0 <= k < self.nz:
                        sigma[i][j][k] = self.copper_conductivity
                        pad_cells += 1
                except Exception as e:
                    self.log_message(f"Warning: Failed to apply pad: {str(e)}")
            
            self.log_message(f"Applied {pad_cells} pads")
            self.log_message(f"Geometry application complete")
            
            return fields
            
        except Exception as e:
            self.log_message(f"ERROR applying geometry: {str(e)}")
            raise
    
    def apply_boundary_conditions_to_grid(self, fields):
        """
        Apply boundary conditions to FDTD grid
        
        BC types:
        - PML (Perfectly Matched Layer): Absorbing boundary - simulates open space
        - PEC (Perfect Electric Conductor): Reflecting - E tangential = 0
        - PMC (Perfect Magnetic Conductor): Reflecting - H tangential = 0
        - Periodic: Repeating structure
        """
        ex, ey, ez = fields['ex'], fields['ey'], fields['ez']
        hx, hy, hz = fields['hx'], fields['hy'], fields['hz']
        
        # X-Min boundary (left)
        bc_type = self.boundary_conditions['x_min']['type']
        if bc_type == 'PEC':
            # Perfect Electric Conductor: E tangential = 0
            for j in range(self.ny):
                for k in range(self.nz):
                    ey[0][j][k] = 0.0
                    ez[0][j][k] = 0.0
        elif bc_type == 'PMC':
            # Perfect Magnetic Conductor: H tangential = 0
            for j in range(self.ny):
                for k in range(self.nz):
                    hy[0][j][k] = 0.0
                    hz[0][j][k] = 0.0
        elif bc_type == 'Periodic':
            # Periodic: Copy from opposite boundary
            for j in range(self.ny):
                for k in range(self.nz):
                    ex[0][j][k] = ex[self.nx-1][j][k]
                    ey[0][j][k] = ey[self.nx-1][j][k]
                    ez[0][j][k] = ez[self.nx-1][j][k]
        # PML is handled through absorption layers (simplified here)
        
        # X-Max boundary (right)
        bc_type = self.boundary_conditions['x_max']['type']
        if bc_type == 'PEC':
            for j in range(self.ny):
                for k in range(self.nz):
                    ey[self.nx-1][j][k] = 0.0
                    ez[self.nx-1][j][k] = 0.0
        elif bc_type == 'PMC':
            for j in range(self.ny):
                for k in range(self.nz):
                    hy[self.nx-1][j][k] = 0.0
                    hz[self.nx-1][j][k] = 0.0
        elif bc_type == 'Periodic':
            for j in range(self.ny):
                for k in range(self.nz):
                    ex[self.nx-1][j][k] = ex[0][j][k]
                    ey[self.nx-1][j][k] = ey[0][j][k]
                    ez[self.nx-1][j][k] = ez[0][j][k]
        
        # Y-Min boundary (front)
        bc_type = self.boundary_conditions['y_min']['type']
        if bc_type == 'PEC':
            for i in range(self.nx):
                for k in range(self.nz):
                    ex[i][0][k] = 0.0
                    ez[i][0][k] = 0.0
        elif bc_type == 'PMC':
            for i in range(self.nx):
                for k in range(self.nz):
                    hx[i][0][k] = 0.0
                    hz[i][0][k] = 0.0
        elif bc_type == 'Periodic':
            for i in range(self.nx):
                for k in range(self.nz):
                    ex[i][0][k] = ex[i][self.ny-1][k]
                    ey[i][0][k] = ey[i][self.ny-1][k]
                    ez[i][0][k] = ez[i][self.ny-1][k]
        
        # Y-Max boundary (back)
        bc_type = self.boundary_conditions['y_max']['type']
        if bc_type == 'PEC':
            for i in range(self.nx):
                for k in range(self.nz):
                    ex[i][self.ny-1][k] = 0.0
                    ez[i][self.ny-1][k] = 0.0
        elif bc_type == 'PMC':
            for i in range(self.nx):
                for k in range(self.nz):
                    hx[i][self.ny-1][k] = 0.0
                    hz[i][self.ny-1][k] = 0.0
        elif bc_type == 'Periodic':
            for i in range(self.nx):
                for k in range(self.nz):
                    ex[i][self.ny-1][k] = ex[i][0][k]
                    ey[i][self.ny-1][k] = ey[i][0][k]
                    ez[i][self.ny-1][k] = ez[i][0][k]
        
        # Z-Min boundary (bottom)
        bc_type = self.boundary_conditions['z_min']['type']
        if bc_type == 'PEC':
            # Ground plane - E tangential = 0
            for i in range(self.nx):
                for j in range(self.ny):
                    ex[i][j][0] = 0.0
                    ey[i][j][0] = 0.0
        elif bc_type == 'PMC':
            for i in range(self.nx):
                for j in range(self.ny):
                    hx[i][j][0] = 0.0
                    hy[i][j][0] = 0.0
        elif bc_type == 'Periodic':
            for i in range(self.nx):
                for j in range(self.ny):
                    ex[i][j][0] = ex[i][j][self.nz-1]
                    ey[i][j][0] = ey[i][j][self.nz-1]
                    ez[i][j][0] = ez[i][j][self.nz-1]
        
        # Z-Max boundary (top)
        bc_type = self.boundary_conditions['z_max']['type']
        if bc_type == 'PEC':
            for i in range(self.nx):
                for j in range(self.ny):
                    ex[i][j][self.nz-1] = 0.0
                    ey[i][j][self.nz-1] = 0.0
        elif bc_type == 'PMC':
            for i in range(self.nx):
                for j in range(self.ny):
                    hx[i][j][self.nz-1] = 0.0
                    hy[i][j][self.nz-1] = 0.0
        elif bc_type == 'Periodic':
            for i in range(self.nx):
                for j in range(self.ny):
                    ex[i][j][self.nz-1] = ex[i][j][0]
                    ey[i][j][self.nz-1] = ey[i][j][0]
                    ez[i][j][self.nz-1] = ez[i][j][0]
        
        # PML implementation (absorbing layers at boundaries)
        # Apply damping in PML region with proper profile
        pml_thickness = min(8, self.nx // 10, self.ny // 10, self.nz // 10)  # Adaptive thickness
        pml_damping_coef = 0.5  # Increased from 0.3 for better absorption
        
        for boundary, bc_info in self.boundary_conditions.items():
            if bc_info['type'] == 'PML':
                # PML conductivity profile: damping = 1 - coef * ((distance/thickness)^3)
                # Cubic profile provides smooth transition
                
                if boundary == 'x_min':
                    for i in range(min(pml_thickness, self.nx)):
                        dist = pml_thickness - i
                        damping_factor = 1.0 - pml_damping_coef * (dist / float(pml_thickness)) ** 3
                        for j in range(self.ny):
                            for k in range(self.nz):
                                ex[i][j][k] *= damping_factor
                                ey[i][j][k] *= damping_factor
                                ez[i][j][k] *= damping_factor
                
                elif boundary == 'x_max':
                    for i in range(max(0, self.nx - pml_thickness), self.nx):
                        dist = i - (self.nx - pml_thickness)
                        damping_factor = 1.0 - pml_damping_coef * (dist / float(pml_thickness)) ** 3
                        for j in range(self.ny):
                            for k in range(self.nz):
                                ex[i][j][k] *= damping_factor
                                ey[i][j][k] *= damping_factor
                                ez[i][j][k] *= damping_factor
                
                elif boundary == 'y_min':
                    for j in range(min(pml_thickness, self.ny)):
                        dist = pml_thickness - j
                        damping_factor = 1.0 - pml_damping_coef * (dist / float(pml_thickness)) ** 3
                        for i in range(self.nx):
                            for k in range(self.nz):
                                ex[i][j][k] *= damping_factor
                                ey[i][j][k] *= damping_factor
                                ez[i][j][k] *= damping_factor
                
                elif boundary == 'y_max':
                    for j in range(max(0, self.ny - pml_thickness), self.ny):
                        dist = j - (self.ny - pml_thickness)
                        damping_factor = 1.0 - pml_damping_coef * (dist / float(pml_thickness)) ** 3
                        for i in range(self.nx):
                            for k in range(self.nz):
                                ex[i][j][k] *= damping_factor
                                ey[i][j][k] *= damping_factor
                                ez[i][j][k] *= damping_factor
                
                elif boundary == 'z_min':
                    for k in range(min(pml_thickness, self.nz)):
                        dist = pml_thickness - k
                        damping_factor = 1.0 - pml_damping_coef * (dist / float(pml_thickness)) ** 3
                        for i in range(self.nx):
                            for j in range(self.ny):
                                ex[i][j][k] *= damping_factor
                                ey[i][j][k] *= damping_factor
                                ez[i][j][k] *= damping_factor
                
                elif boundary == 'z_max':
                    for k in range(max(0, self.nz - pml_thickness), self.nz):
                        dist = k - (self.nz - pml_thickness)
                        damping_factor = 1.0 - pml_damping_coef * (dist / float(pml_thickness)) ** 3
                        for i in range(self.nx):
                            for j in range(self.ny):
                                ex[i][j][k] *= damping_factor
                                ey[i][j][k] *= damping_factor
                                ez[i][j][k] *= damping_factor
        
        return fields
    
    def add_excitation_source(self, fields, time_step):
        """
        Add Gaussian pulse excitation following openEMS methodology
        Uses soft source (additive) with proper amplitude scaling
        Source turns off after initial pulse to prevent continuous energy addition
        """
        try:
            # Turn off source after initial pulse
            if time_step > self.source_cutoff_step:
                return fields  # No more excitation
            
            # Current time
            t = time_step * self.dt
            
            # Gaussian pulse parameters (following openEMS)
            # Pulse centered at t0 with width sigma
            t0 = 6.0 * self.source_sigma  # Delay (6σ ensures pulse starts from ~zero)
            
            # Gaussian derivative pulse (better frequency content)
            # E(t) = A * (t-t0)/σ² * exp(-((t-t0)/σ)²)
            t_norm = (t - t0) / self.source_sigma
            pulse_amplitude = -2.0 * t_norm * math.exp(-t_norm**2)
            
            # Scale by source amplitude
            scaled_pulse = self.source_amplitude * pulse_amplitude
            
            # Find safe source location (air region, not in copper or substrate)
            # Place in upper air region, away from boundaries
            i_center = self.nx // 2
            j_center = self.ny // 2
            k_source = int(self.nz * 0.8)  # 80% up (high in air, away from PCB)
            
            # Keep away from boundaries (at least 3 cells)
            i_center = max(3, min(i_center, self.nx - 4))
            j_center = max(3, min(j_center, self.ny - 4))
            k_source = max(3, min(k_source, self.nz - 4))
            
            # Validate location is in air (low conductivity)
            if 0 <= i_center < self.nx and 0 <= j_center < self.ny and 0 <= k_source < self.nz:
                sigma_at_source = fields['sigma'][i_center][j_center][k_source]
                
                # Log source placement on first step
                if time_step == 0:
                    self.log_message(f"\nSource placement:")
                    self.log_message(f"  Location: grid[{i_center}, {j_center}, {k_source}]")
                    self.log_message(f"  Conductivity at source: {sigma_at_source:.2e} S/m")
                    if sigma_at_source < 0.1:
                        self.log_message(f"  ✓ Source in air region (good)")
                    else:
                        self.log_message(f"  ⚠ Source in conductive region (will be moved)")
                
                # Check conductivity - must be in air (< 0.1 S/m)
                if sigma_at_source < 0.1:
                    # Good location - apply excitation
                    fields['ez'][i_center][j_center][k_source] += scaled_pulse
                else:
                    # Source in conductor - search for air region
                    found_air = False
                    # Search upward first
                    for k_test in range(k_source, self.nz - 3):
                        if fields['sigma'][i_center][j_center][k_test] < 0.1:
                            fields['ez'][i_center][j_center][k_test] += scaled_pulse
                            if time_step == 0:
                                self.log_message(f"  → Moved source to grid[{i_center}, {j_center}, {k_test}]")
                            found_air = True
                            break
                    
                    if not found_air:
                        # Try searching downward
                        for k_test in range(k_source, 2, -1):
                            if fields['sigma'][i_center][j_center][k_test] < 0.1:
                                fields['ez'][i_center][j_center][k_test] += scaled_pulse
                                if time_step == 0:
                                    self.log_message(f"  → Moved source to grid[{i_center}, {j_center}, {k_test}]")
                                break
            
            return fields
            
        except Exception as e:
            self.log_message(f"ERROR in excitation: {str(e)}")
            raise
    
    def update_h_field(self, fields):
        """
        Update H-field using Yee algorithm
        H^(n+1/2) = H^(n-1/2) + (dt/mu) * curl(E^n)
        """
        try:
            ex, ey, ez = fields['ex'], fields['ey'], fields['ez']
            hx, hy, hz = fields['hx'], fields['hy'], fields['hz']
            
            coef = self.dt / self.mu0
            
            # Update Hx (avoid boundaries)
            for i in range(1, self.nx-1):
                for j in range(1, self.ny-1):
                    for k in range(1, self.nz-1):
                        curl_e_x = (ey[i][j][k] - ey[i][j][k-1]) / (self.dz/1000.0) - \
                                  (ez[i][j][k] - ez[i][j-1][k]) / (self.dy/1000.0)
                        hx[i][j][k] += coef * curl_e_x
            
            # Update Hy (avoid boundaries)
            for i in range(1, self.nx-1):
                for j in range(1, self.ny-1):
                    for k in range(1, self.nz-1):
                        curl_e_y = (ez[i][j][k] - ez[i-1][j][k]) / (self.dx/1000.0) - \
                                  (ex[i][j][k] - ex[i][j][k-1]) / (self.dz/1000.0)
                        hy[i][j][k] += coef * curl_e_y
            
            # Update Hz (avoid boundaries)
            for i in range(1, self.nx-1):
                for j in range(1, self.ny-1):
                    for k in range(1, self.nz-1):
                        curl_e_z = (ex[i][j][k] - ex[i][j-1][k]) / (self.dy/1000.0) - \
                                  (ey[i][j][k] - ey[i-1][j][k]) / (self.dx/1000.0)
                        hz[i][j][k] += coef * curl_e_z
            
            return fields
            
        except Exception as e:
            self.log_message(f"ERROR in H-field update: {str(e)}")
            raise
    
    def update_e_field(self, fields):
        """
        Update E-field using Yee algorithm with proper lossy media formulation
        
        For lossy media: ε ∂E/∂t + σE = curl(H)
        Discretized: E^(n+1) = ca * E^n + cb * curl(H^(n+1/2))
        where:
            ca = (2ε - σΔt) / (2ε + σΔt)  [always in [0,1] for physical materials]
            cb = 2Δt / (2ε + σΔt)          [always > 0]
        """
        try:
            ex, ey, ez = fields['ex'], fields['ey'], fields['ez']
            hx, hy, hz = fields['hx'], fields['hy'], fields['hz']
            eps, sigma = fields['eps'], fields['sigma']
            
            # Update Ex (avoid boundaries)
            for i in range(1, self.nx-1):
                for j in range(1, self.ny-1):
                    for k in range(1, self.nz-1):
                        curl_h_x = (hy[i][j][k+1] - hy[i][j][k]) / (self.dz/1000.0) - \
                                  (hz[i][j+1][k] - hz[i][j][k]) / (self.dy/1000.0)
                        
                        eps_val = eps[i][j][k]
                        if eps_val < 1e-15:
                            eps_val = self.eps0
                        
                        sigma_val = sigma[i][j][k]
                        
                        # Proper lossy media coefficients
                        denom = 2.0 * eps_val + sigma_val * self.dt
                        ca = (2.0 * eps_val - sigma_val * self.dt) / denom
                        cb = (2.0 * self.dt) / denom
                        
                        # Stability check (ca should be in [0, 1])
                        if ca < 0.0:
                            ca = 0.0
                        elif ca > 1.0:
                            ca = 1.0
                        
                        ex[i][j][k] = ca * ex[i][j][k] + cb * curl_h_x
            
            # Update Ey (avoid boundaries)
            for i in range(1, self.nx-1):
                for j in range(1, self.ny-1):
                    for k in range(1, self.nz-1):
                        curl_h_y = (hz[i+1][j][k] - hz[i][j][k]) / (self.dx/1000.0) - \
                                  (hx[i][j][k+1] - hx[i][j][k]) / (self.dz/1000.0)
                        
                        eps_val = eps[i][j][k]
                        if eps_val < 1e-15:
                            eps_val = self.eps0
                        
                        sigma_val = sigma[i][j][k]
                        
                        # Proper lossy media coefficients
                        denom = 2.0 * eps_val + sigma_val * self.dt
                        ca = (2.0 * eps_val - sigma_val * self.dt) / denom
                        cb = (2.0 * self.dt) / denom
                        
                        # Stability check
                        if ca < 0.0:
                            ca = 0.0
                        elif ca > 1.0:
                            ca = 1.0
                        
                        ey[i][j][k] = ca * ey[i][j][k] + cb * curl_h_y
            
            # Update Ez (avoid boundaries)
            for i in range(1, self.nx-1):
                for j in range(1, self.ny-1):
                    for k in range(1, self.nz-1):
                        curl_h_z = (hx[i][j+1][k] - hx[i][j][k]) / (self.dy/1000.0) - \
                                  (hy[i+1][j][k] - hy[i][j][k]) / (self.dx/1000.0)
                        
                        eps_val = eps[i][j][k]
                        if eps_val < 1e-15:
                            eps_val = self.eps0
                        
                        sigma_val = sigma[i][j][k]
                        
                        # Proper lossy media coefficients
                        denom = 2.0 * eps_val + sigma_val * self.dt
                        ca = (2.0 * eps_val - sigma_val * self.dt) / denom
                        cb = (2.0 * self.dt) / denom
                        
                        # Stability check
                        if ca < 0.0:
                            ca = 0.0
                        elif ca > 1.0:
                            ca = 1.0
                        
                        ez[i][j][k] = ca * ez[i][j][k] + cb * curl_h_z
            
            return fields
            
        except Exception as e:
            self.log_message(f"ERROR in E-field update: {str(e)}")
            import traceback
            self.log_message(f"Traceback: {traceback.format_exc()}")
            raise
    
    def run_simulation(self, progress_callback=None):
        """
        Run the FDTD simulation with comprehensive error handling
        
        Args:
            progress_callback: Function to call with progress updates
        
        Returns:
            Dictionary with simulation results including success flag and error log
        """
        try:
            self.log_message("\n" + "="*60)
            self.log_message("STARTING EMI SIMULATION")
            self.log_message("="*60)
            
            # Step 1: Setup grid
            if progress_callback:
                progress_callback(0, "Step 1/6: Setting up FDTD grid...")
            
            self.log_message("\nStep 1: Setting up FDTD grid...")
            grid_info = self.setup_fdtd_grid()
            
            if not grid_info or self.nx == 0 or self.ny == 0 or self.nz == 0:
                raise ValueError("Grid setup failed - invalid dimensions")
            
            self.log_message(f"Grid setup complete: {self.nx}x{self.ny}x{self.nz}")
            
            # Step 2: Parse geometry
            if progress_callback:
                progress_callback(10, f"Step 2/6: Parsing PCB geometry...")
            
            self.log_message("\nStep 2: Parsing PCB geometry...")
            geometry = self.parse_pcb_geometry()
            
            if not geometry:
                raise ValueError("Geometry parsing failed")
            
            self.log_message(f"Geometry parsed: {len(geometry['traces'])} traces, {len(geometry['pads'])} pads")
            
            # Step 3: Create field arrays
            if progress_callback:
                progress_callback(15, f"Step 3/6: Creating field arrays ({self.nx}x{self.ny}x{self.nz})...")
            
            self.log_message("\nStep 3: Creating FDTD field arrays...")
            fields = self.create_fdtd_arrays()
            
            if not fields or 'ex' not in fields:
                raise ValueError("Field array creation failed")
            
            self.log_message("Field arrays created successfully")
            
            # Log source parameters
            self.log_message(f"\nSource Parameters:")
            self.log_message(f"  Amplitude: {self.source_amplitude} V/m")
            self.log_message(f"  Pulse width (σ): {self.source_sigma*1e12:.4f} ps")
            self.log_message(f"  Pulse delay: {6*self.source_sigma*1e12:.4f} ps")
            
            # Step 4: Apply geometry
            if progress_callback:
                progress_callback(20, f"Step 4/6: Applying {len(geometry['traces'])} traces to grid...")
            
            self.log_message("\nStep 4: Applying geometry to grid...")
            fields = self.apply_geometry_to_grid(fields, geometry)
            self.log_message("Geometry applied to grid")
            
            # Step 5: Apply boundary conditions
            if progress_callback:
                progress_callback(25, "Step 5/6: Applying boundary conditions...")
            
            self.log_message("\nStep 5: Applying boundary conditions...")
            fields = self.apply_boundary_conditions_to_grid(fields)
            self.log_message("Boundary conditions applied")
            
            # Step 6: Time-stepping loop
            if progress_callback:
                progress_callback(30, f"Step 6/6: Running FDTD time-stepping (0/{self.num_time_steps})...")
            
            self.log_message(f"\nStep 6: Running FDTD time-stepping ({self.num_time_steps} steps)...")
            
            max_e_field = 0.0
            e_field_history = []
            cancelled = False
            
            for n in range(self.num_time_steps):
                # Check for cancellation
                if cancelled:
                    self.log_message("Simulation cancelled by user")
                    raise InterruptedError("Simulation cancelled")
                
                try:
                    # Update H field
                    fields = self.update_h_field(fields)
                    
                    # Update E field
                    fields = self.update_e_field(fields)
                    
                    # Add excitation
                    fields = self.add_excitation_source(fields, n)
                    
                    # Apply boundary conditions
                    fields = self.apply_boundary_conditions_to_grid(fields)
                    
                    # Record field magnitude at center
                    i_center = self.nx // 2
                    j_center = self.ny // 2
                    k_center = self.nz // 2
                    
                    # Monitor fields at center
                    if 0 <= i_center < self.nx and 0 <= j_center < self.ny and 0 <= k_center < self.nz:
                        e_mag = math.sqrt(
                            fields['ex'][i_center][j_center][k_center]**2 +
                            fields['ey'][i_center][j_center][k_center]**2 +
                            fields['ez'][i_center][j_center][k_center]**2
                        )
                        
                        # Check for numerical instability
                        if math.isnan(e_mag) or math.isinf(e_mag):
                            raise ValueError(f"Field became NaN or Inf at time step {n}")
                        
                        # Also check maximum field anywhere in grid (every 5 steps for performance)
                        if n % 5 == 0:
                            max_field_in_grid = 0.0
                            for i in range(1, self.nx-1):
                                for j in range(1, self.ny-1):
                                    for k in range(1, self.nz-1):
                                        e_local = math.sqrt(
                                            fields['ex'][i][j][k]**2 +
                                            fields['ey'][i][j][k]**2 +
                                            fields['ez'][i][j][k]**2
                                        )
                                        max_field_in_grid = max(max_field_in_grid, e_local)
                            
                            # Use the larger of center or max
                            e_mag = max(e_mag, max_field_in_grid)
                        
                        # Progressive warning system with lower thresholds
                        if e_mag > 1.0:  # Even 1 V/m is large with 0.01 V/m source
                            if n % 5 == 0:
                                self.log_message(f"INFO: E-field at step {n}: {e_mag:.3e} V/m")
                        
                        if e_mag > 10.0:  # 1000x source amplitude
                            self.log_message(f"NOTE: E-field growing at step {n}: {e_mag:.3e} V/m (1000x source)")
                        
                        if e_mag > 1e3:  # Starting to get large
                            self.log_message(f"WARNING: Large E-field at step {n}: {e_mag:.3e} V/m - possible instability developing")
                        
                        if e_mag > 1e6:  # Very large
                            self.log_message(f"CRITICAL: Very large E-field at step {n}: {e_mag:.3e} V/m - instability likely")
                            self.log_message(f"Grid: {self.nx}×{self.ny}×{self.nz}, Cell size: {self.dx:.3f}×{self.dy:.3f}×{self.dz:.3f} mm")
                        
                        if e_mag > 1e9:  # About to fail
                            raise ValueError(
                                f"E-field magnitude exceeded safe limits at step {n}: {e_mag:.6e} V/m\n"
                                f"This indicates numerical instability.\n\n"
                                f"Simulation parameters:\n"
                                f"  Grid: {self.nx}×{self.ny}×{self.nz} cells ({self.nx*self.ny*self.nz} total)\n"
                                f"  Cell size: {self.dx:.4f}×{self.dy:.4f}×{self.dz:.4f} mm\n"
                                f"  Time step: {self.dt*1e12:.4f} ps (Courant factor: 0.5)\n"
                                f"  Frequency: {self.frequency/1e9:.2f} GHz\n"
                                f"  Source amplitude: {self.source_amplitude} V/m\n"
                                f"  Grid resolution: {self.cells_per_wavelength} cells/wavelength\n\n"
                                f"Possible causes:\n"
                                f"  1. Grid resolution too low - try increasing to 20-25 cells/wavelength\n"
                                f"  2. Region too small (< 20mm) - select larger region (30-80mm)\n"
                                f"  3. Too many traces in small area - reduce selection\n"
                                f"  4. Boundary conditions incorrect - use PML for most boundaries\n"
                                f"  5. PCB geometry too complex for current grid\n\n"
                                f"Solutions:\n"
                                f"  - Increase 'Grid Resolution' to 20 or higher\n"
                                f"  - Select a larger/simpler region\n"
                                f"  - Check boundary conditions (use PML)\n\n"
                                f"Check simulation log for details."
                            )
                        
                        e_field_history.append(e_mag)
                        max_e_field = max(max_e_field, e_mag)
                    
                except Exception as e:
                    self.log_message(f"ERROR at timestep {n}: {str(e)}")
                    raise
                
                # Progress update with status (every 2%)
                if progress_callback and n % max(1, self.num_time_steps // 50) == 0:
                    progress_percent = 30 + int(65 * n / self.num_time_steps)
                    status_msg = f"Step 6/6: Time-stepping {n}/{self.num_time_steps} (E-field: {max_e_field:.2e} V/m)"
                    try:
                        cont = progress_callback(progress_percent, status_msg)
                        if cont is False:
                            cancelled = True
                    except:
                        pass  # Continue even if callback fails
            
            # Final progress update
            if progress_callback:
                try:
                    progress_callback(95, "Finalizing results...")
                except:
                    pass
            
            self.log_message(f"Time-stepping complete: {len(e_field_history)} samples recorded")
            self.log_message(f"Maximum E-field: {max_e_field:.6e} V/m")
            
            # Store final fields
            self.e_field = fields['ez']
            self.h_field = fields['hz']
            
            self.log_message("\n" + "="*60)
            self.log_message("SIMULATION COMPLETE")
            self.log_message("="*60)
            
            # Final completion update
            if progress_callback:
                try:
                    progress_callback(100, "Simulation complete!")
                except:
                    pass
            
            # Compile results
            results = {
                'success': True,
                'grid_info': grid_info,
                'geometry': geometry,
                'max_e_field': max_e_field,
                'e_field_history': e_field_history,
                'frequency': self.frequency,
                'num_traces': len(geometry['traces']),
                'num_vias': len(geometry.get('vias', [])),
                'num_pads': len(geometry['pads']),
                'boundary_conditions': self.boundary_conditions,
                'final_e_field': self.e_field,
                'final_h_field': self.h_field,
                'simulation_log': self.get_log()
            }
            
            return results
            
        except Exception as e:
            # Detailed error logging
            import traceback
            error_trace = traceback.format_exc()
            
            self.log_message(f"\n{'='*60}")
            self.log_message("SIMULATION FAILED")
            self.log_message(f"{'='*60}")
            self.log_message(f"Error: {str(e)}")
            self.log_message(f"\nFull traceback:\n{error_trace}")
            
            # Return error information
            return {
                'success': False,
                'error': str(e),
                'error_trace': error_trace,
                'simulation_log': self.get_log(),
                'grid_info': {'grid_size': (self.nx, self.ny, self.nz), 
                             'cell_size': (self.dx, self.dy, self.dz), 
                             'time_step': self.dt, 
                             'num_steps': self.num_time_steps},
                'geometry': {'traces': [], 'vias': [], 'pads': []},
                'max_e_field': 0.0,
                'e_field_history': [],
                'frequency': self.frequency,
                'num_traces': 0,
                'num_vias': 0,
                'num_pads': 0,
                'boundary_conditions': self.boundary_conditions
            }


class TopViewCanvas(wx.Panel):
    """
    Canvas for displaying PCB top view in 2D with bounding box selection
    Only shows top layer (F.Cu) and top components
    """
    
    def __init__(self, parent, dialog):
        super(TopViewCanvas, self).__init__(parent)
        
        self.dialog = dialog
        self.board = dialog.board
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.last_mouse_pos = None
        
        self.selecting = False
        self.selection_start_screen = None
        
        # Bitmap cache for PCB rendering
        self.pcb_bitmap = None
        self.cached_zoom = None
        self.cached_pan_x = None
        self.cached_pan_y = None
        self.cache_valid = False
        
        self.SetBackgroundColour(wx.Colour(30, 30, 30))
        
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        
        self.panning = False
        
        # Trigger initial PCB render
        wx.CallAfter(self.render_pcb_to_cache)
    
    def screen_to_board_coords(self, screen_x, screen_y):
        """Convert screen coordinates to board coordinates in mm"""
        width, height = self.GetSize()
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        center_x = width / 2 + self.pan_x
        center_y = height / 2 + self.pan_y
        scale = self.zoom * 2.0
        
        board_x = bbox_center_x + (screen_x - center_x) / scale
        board_y = bbox_center_y + (screen_y - center_y) / scale
        
        return (board_x, board_y)
    
    def board_to_screen_coords(self, board_x, board_y):
        """Convert board coordinates (mm) to screen coordinates"""
        width, height = self.GetSize()
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        center_x = width / 2 + self.pan_x
        center_y = height / 2 + self.pan_y
        scale = self.zoom * 2.0
        
        screen_x = center_x + (board_x - bbox_center_x) * scale
        screen_y = center_y + (board_y - bbox_center_y) * scale
        
        return (screen_x, screen_y)
    
    def on_size(self, event):
        """Handle window resize - invalidate cache"""
        self.cache_valid = False
        self.Refresh()
        event.Skip()
    
    def render_pcb_to_cache(self):
        """Render PCB to a cached bitmap for performance"""
        width, height = self.GetSize()
        if width <= 0 or height <= 0:
            return
        
        # Create bitmap for caching
        self.pcb_bitmap = wx.Bitmap(width, height)
        memdc = wx.MemoryDC(self.pcb_bitmap)
        gc = wx.GraphicsContext.Create(memdc)
        
        if gc:
            # Clear background
            gc.SetBrush(wx.Brush(wx.Colour(30, 30, 30)))
            gc.DrawRectangle(0, 0, width, height)
            
            # Get board bounds
            bbox = self.board.GetBoardEdgesBoundingBox()
            board_width = bbox.GetWidth() / 1e6
            board_height = bbox.GetHeight() / 1e6
            
            center_x = width / 2 + self.pan_x
            center_y = height / 2 + self.pan_y
            scale = self.zoom * 2.0
            
            # Draw static PCB elements
            self.draw_board_outline_2d(gc, center_x, center_y, board_width, board_height, scale)
            self.draw_top_tracks(gc, center_x, center_y, scale)
            self.draw_top_components(gc, center_x, center_y, scale)
            self.draw_grid(gc, center_x, center_y, scale)
        
        # Mark cache as valid and store parameters
        self.cache_valid = True
        self.cached_zoom = self.zoom
        self.cached_pan_x = self.pan_x
        self.cached_pan_y = self.pan_y
        
        memdc.SelectObject(wx.NullBitmap)
    
    def on_paint(self, event):
        """Handle paint event - use cached bitmap"""
        dc = wx.PaintDC(self)
        
        # Check if cache needs updating
        if not self.cache_valid or self.pcb_bitmap is None or \
           self.cached_zoom != self.zoom or \
           self.cached_pan_x != self.pan_x or \
           self.cached_pan_y != self.pan_y:
            self.render_pcb_to_cache()
        
        # Draw cached PCB
        if self.pcb_bitmap:
            dc.DrawBitmap(self.pcb_bitmap, 0, 0)
        
        # Draw dynamic overlay (selection, etc.) using graphics context
        gc = wx.GraphicsContext.Create(dc)
        if gc:
            # Draw bounding box if selected
            if self.dialog.bbox_start and self.dialog.bbox_end:
                self.draw_bounding_box(gc)
            
            # Draw temporary selection rectangle
            if self.selecting and self.selection_start_screen and self.last_mouse_pos:
                self.draw_selection_rect(gc)
    
    def render(self, gc):
        """Legacy render method - now handled by cache"""
        # This method is kept for compatibility but not used
        pass
    
    def draw_board_outline_2d(self, gc, center_x, center_y, board_width, board_height, scale):
        """Draw board outline in 2D"""
        x = center_x - (board_width / 2) * scale
        y = center_y - (board_height / 2) * scale
        w = board_width * scale
        h = board_height * scale
        
        gc.SetBrush(wx.Brush(wx.Colour(40, 80, 40)))
        gc.SetPen(wx.Pen(wx.Colour(100, 200, 100), 2))
        gc.DrawRectangle(x, y, w, h)
    
    def draw_top_tracks(self, gc, center_x, center_y, scale):
        """Draw only top layer (F.Cu) tracks"""
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        for track in self.board.GetTracks():
            track_class = track.GetClass()
            if track_class not in ["PCB_TRACE", "TRACK", "PCB_TRACK"]:
                continue
            
            # Only show front copper
            layer = track.GetLayer()
            if layer != pcbnew.F_Cu:
                continue
            
            start = track.GetStart()
            end = track.GetEnd()
            
            x1_mm = start.x / 1e6 - bbox_center_x
            y1_mm = start.y / 1e6 - bbox_center_y
            x2_mm = end.x / 1e6 - bbox_center_x
            y2_mm = end.y / 1e6 - bbox_center_y
            
            px1 = center_x + x1_mm * scale
            py1 = center_y + y1_mm * scale
            px2 = center_x + x2_mm * scale
            py2 = center_y + y2_mm * scale
            
            track_width = track.GetWidth() / 1e6
            pen_width = max(2, int(track_width * scale))
            
            # Front copper - bright copper color
            gc.SetPen(wx.Pen(wx.Colour(220, 120, 60), pen_width))
            gc.StrokeLine(px1, py1, px2, py2)
    
    def draw_top_components(self, gc, center_x, center_y, scale):
        """Draw only top layer components"""
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        for footprint in self.board.GetFootprints():
            # Only show top components
            if footprint.IsFlipped():
                continue
            
            for pad in footprint.Pads():
                pad_pos = pad.GetPosition()
                x_mm = pad_pos.x / 1e6 - bbox_center_x
                y_mm = pad_pos.y / 1e6 - bbox_center_y
                
                px = center_x + x_mm * scale
                py = center_y + y_mm * scale
                
                pad_size = pad.GetSize()
                pw = pad_size.x / 1e6 * scale
                ph = pad_size.y / 1e6 * scale
                
                # Top pads - gold color
                gc.SetBrush(wx.Brush(wx.Colour(220, 180, 100)))
                gc.SetPen(wx.Pen(wx.Colour(180, 140, 60), 1))
                
                pad_shape = pad.GetShape()
                if pad_shape == pcbnew.PAD_SHAPE_CIRCLE:
                    gc.DrawEllipse(px - pw/2, py - ph/2, pw, ph)
                elif pad_shape == pcbnew.PAD_SHAPE_ROUNDRECT:
                    corner_radius = min(pw, ph) * 0.25
                    gc.DrawRoundedRectangle(px - pw/2, py - ph/2, pw, ph, corner_radius)
                else:
                    gc.DrawRectangle(px - pw/2, py - ph/2, pw, ph)
                
                # Draw drill holes if present
                drill_size = pad.GetDrillSize()
                if drill_size.x > 0:
                    drill_w = drill_size.x / 1e6 * scale
                    gc.SetBrush(wx.Brush(wx.Colour(40, 40, 40)))
                    gc.SetPen(wx.Pen(wx.Colour(20, 20, 20), 1))
                    gc.DrawEllipse(px - drill_w/2, py - drill_w/2, drill_w, drill_w)
    
    def draw_grid(self, gc, center_x, center_y, scale):
        """Draw grid lines for alignment (optional)"""
        if self.zoom < 0.5:
            return  # Don't show grid when zoomed out
        
        width, height = self.GetSize()
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        # Grid spacing in mm (adjust based on zoom)
        grid_spacing = 10.0 if self.zoom < 1.5 else 5.0
        
        gc.SetPen(wx.Pen(wx.Colour(60, 60, 60), 1))
        
        # Vertical lines
        start_x = int(bbox_center_x - width / scale / 2)
        end_x = int(bbox_center_x + width / scale / 2)
        for x_mm in range(start_x - start_x % int(grid_spacing), end_x + int(grid_spacing), int(grid_spacing)):
            screen_x = center_x + (x_mm - bbox_center_x) * scale
            if 0 <= screen_x <= width:
                gc.StrokeLine(screen_x, 0, screen_x, height)
        
        # Horizontal lines
        start_y = int(bbox_center_y - height / scale / 2)
        end_y = int(bbox_center_y + height / scale / 2)
        for y_mm in range(start_y - start_y % int(grid_spacing), end_y + int(grid_spacing), int(grid_spacing)):
            screen_y = center_y + (y_mm - bbox_center_y) * scale
            if 0 <= screen_y <= height:
                gc.StrokeLine(0, screen_y, width, screen_y)
    
    def draw_bounding_box(self, gc):
        """Draw the selected bounding box"""
        if not self.dialog.bbox_start or not self.dialog.bbox_end:
            return
        
        x1, y1 = self.board_to_screen_coords(self.dialog.bbox_start[0], self.dialog.bbox_start[1])
        x2, y2 = self.board_to_screen_coords(self.dialog.bbox_end[0], self.dialog.bbox_end[1])
        
        gc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 50)))
        gc.SetPen(wx.Pen(wx.Colour(255, 255, 0), 3))
        
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        
        gc.DrawRectangle(x, y, w, h)
        
        # Draw corner handles
        handle_size = 10
        gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
        gc.SetPen(wx.Pen(wx.Colour(0, 0, 0), 2))
        
        for corner_x, corner_y in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
            gc.DrawRectangle(corner_x - handle_size/2, corner_y - handle_size/2, handle_size, handle_size)
    
    def draw_selection_rect(self, gc):
        """Draw temporary selection rectangle while dragging"""
        x1, y1 = self.selection_start_screen
        x2, y2 = self.last_mouse_pos.x, self.last_mouse_pos.y
        
        gc.SetBrush(wx.Brush(wx.Colour(100, 150, 255, 30)))
        gc.SetPen(wx.Pen(wx.Colour(100, 150, 255), 2))
        
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        
        gc.DrawRectangle(x, y, w, h)
    
    def on_mouse_move(self, event):
        """Handle mouse movement"""
        pos = event.GetPosition()
        
        if self.selecting:
            self.Refresh()
        elif self.panning and self.last_mouse_pos:
            dx = pos.x - self.last_mouse_pos.x
            dy = pos.y - self.last_mouse_pos.y
            self.pan_x += dx
            self.pan_y += dy
            self.Refresh()
        
        # Update cursor position in status bar
        board_x, board_y = self.screen_to_board_coords(pos.x, pos.y)
        self.dialog.SetStatusText(f"Top View | Cursor: ({board_x:.3f}, {board_y:.3f}) mm", 0)
        
        self.last_mouse_pos = pos
    
    def on_left_down(self, event):
        """Start bounding box selection"""
        pos = event.GetPosition()
        self.selecting = True
        self.selection_start_screen = (pos.x, pos.y)
        self.CaptureMouse()
    
    def on_left_up(self, event):
        """Finish bounding box selection"""
        if self.selecting:
            self.selecting = False
            if self.HasCapture():
                self.ReleaseMouse()
            
            if self.selection_start_screen:
                start_board = self.screen_to_board_coords(
                    self.selection_start_screen[0],
                    self.selection_start_screen[1]
                )
                end_board = self.screen_to_board_coords(
                    self.last_mouse_pos.x,
                    self.last_mouse_pos.y
                )
                
                self.dialog.bbox_start = start_board
                self.dialog.bbox_end = end_board
                self.dialog.update_controls_from_bbox()
                self.Refresh()
                
                width = abs(end_board[0] - start_board[0])
                height = abs(end_board[1] - start_board[1])
                self.dialog.SetStatusText(
                    f"Top View | Selected: {width:.3f} × {height:.3f} mm", 0
                )
    
    def on_right_down(self, event):
        """Start panning"""
        self.panning = True
        self.CaptureMouse()
    
    def on_right_up(self, event):
        """Stop panning"""
        if self.panning:
            self.panning = False
            if self.HasCapture():
                self.ReleaseMouse()
    
    def on_mouse_wheel(self, event):
        """Handle zoom"""
        rotation = event.GetWheelRotation()
        if rotation > 0:
            self.zoom *= 1.1
        else:
            self.zoom *= 0.9
        self.zoom = max(0.1, min(10.0, self.zoom))
        self.Refresh()


class BoundingBoxSelectorDialog(wx.Frame):
    """
    Dialog for selecting a 2D bounding box on the PCB
    """
    
    def __init__(self, parent, board):
        super(BoundingBoxSelectorDialog, self).__init__(
            parent,
            title="2D Bounding Box Selector",
            size=(1200, 800),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        self.board = board
        self.bbox_start = None  # (x_mm, y_mm)
        self.bbox_end = None    # (x_mm, y_mm)
        
        self.create_ui()
        self.Centre()
    
    def create_ui(self):
        """Create the user interface"""
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Toolbar
        toolbar_panel = wx.Panel(main_panel)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Instructions
        instructions = wx.StaticText(toolbar_panel, 
            label="Click and drag to select a bounding box, or enter coordinates manually:")
        toolbar_sizer.Add(instructions, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        toolbar_panel.SetSizer(toolbar_sizer)
        main_sizer.Add(toolbar_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # 2D Canvas
        self.canvas = BoundingBoxCanvas(main_panel, self)
        main_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        
        # Coordinate input panel
        coord_panel = wx.Panel(main_panel)
        coord_sizer = wx.GridBagSizer(5, 10)
        
        # Start coordinates
        coord_sizer.Add(wx.StaticText(coord_panel, label="Start Point:"), (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        coord_sizer.Add(wx.StaticText(coord_panel, label="X:"), (0, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        self.start_x_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.start_x_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.start_x_ctrl, (0, 2))
        coord_sizer.Add(wx.StaticText(coord_panel, label="Y:"), (0, 3), flag=wx.ALIGN_CENTER_VERTICAL)
        self.start_y_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.start_y_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.start_y_ctrl, (0, 4))
        coord_sizer.Add(wx.StaticText(coord_panel, label="mm"), (0, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        
        # End coordinates
        coord_sizer.Add(wx.StaticText(coord_panel, label="End Point:"), (1, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        coord_sizer.Add(wx.StaticText(coord_panel, label="X:"), (1, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        self.end_x_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.end_x_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.end_x_ctrl, (1, 2))
        coord_sizer.Add(wx.StaticText(coord_panel, label="Y:"), (1, 3), flag=wx.ALIGN_CENTER_VERTICAL)
        self.end_y_ctrl = wx.TextCtrl(coord_panel, size=(100, -1))
        self.end_y_ctrl.Bind(wx.EVT_TEXT, self.on_coord_changed)
        coord_sizer.Add(self.end_y_ctrl, (1, 4))
        coord_sizer.Add(wx.StaticText(coord_panel, label="mm"), (1, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        
        # Dimensions display
        coord_sizer.Add(wx.StaticText(coord_panel, label="Dimensions:"), (2, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.width_label = wx.StaticText(coord_panel, label="Width: --")
        coord_sizer.Add(self.width_label, (2, 1), (1, 2))
        self.height_label = wx.StaticText(coord_panel, label="Height: --")
        coord_sizer.Add(self.height_label, (2, 3), (1, 2))
        self.area_label = wx.StaticText(coord_panel, label="Area: --")
        coord_sizer.Add(self.area_label, (2, 5), (1, 2))
        
        # Buttons
        clear_btn = wx.Button(coord_panel, label="Clear Selection")
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_selection)
        coord_sizer.Add(clear_btn, (3, 0), (1, 2))
        
        copy_btn = wx.Button(coord_panel, label="Copy Coordinates")
        copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_coordinates)
        coord_sizer.Add(copy_btn, (3, 2), (1, 2))
        
        export_btn = wx.Button(coord_panel, label="Export Selection")
        export_btn.Bind(wx.EVT_BUTTON, self.on_export_selection)
        coord_sizer.Add(export_btn, (3, 4), (1, 2))
        
        coord_panel.SetSizer(coord_sizer)
        main_sizer.Add(coord_panel, 0, wx.EXPAND | wx.ALL, 10)
        
        # Status bar
        self.status_bar = self.CreateStatusBar(1)
        self.SetStatusText("Click and drag on the PCB to select a bounding box", 0)
        
        main_panel.SetSizer(main_sizer)
    
    def update_bbox_from_controls(self):
        """Update bounding box from text controls"""
        try:
            start_x = float(self.start_x_ctrl.GetValue())
            start_y = float(self.start_y_ctrl.GetValue())
            end_x = float(self.end_x_ctrl.GetValue())
            end_y = float(self.end_y_ctrl.GetValue())
            
            self.bbox_start = (start_x, start_y)
            self.bbox_end = (end_x, end_y)
            self.update_dimensions()
            self.canvas.Refresh()
            return True
        except ValueError:
            return False
    
    def update_controls_from_bbox(self):
        """Update text controls from bounding box"""
        if self.bbox_start and self.bbox_end:
            self.start_x_ctrl.SetValue(f"{self.bbox_start[0]:.3f}")
            self.start_y_ctrl.SetValue(f"{self.bbox_start[1]:.3f}")
            self.end_x_ctrl.SetValue(f"{self.bbox_end[0]:.3f}")
            self.end_y_ctrl.SetValue(f"{self.bbox_end[1]:.3f}")
            self.update_dimensions()
    
    def update_dimensions(self):
        """Update dimension labels"""
        if self.bbox_start and self.bbox_end:
            width = abs(self.bbox_end[0] - self.bbox_start[0])
            height = abs(self.bbox_end[1] - self.bbox_start[1])
            area = width * height
            
            self.width_label.SetLabel(f"Width: {width:.3f} mm")
            self.height_label.SetLabel(f"Height: {height:.3f} mm")
            self.area_label.SetLabel(f"Area: {area:.3f} mm²")
        else:
            self.width_label.SetLabel("Width: --")
            self.height_label.SetLabel("Height: --")
            self.area_label.SetLabel("Area: --")
    
    def on_coord_changed(self, event):
        """Handle manual coordinate entry"""
        self.update_bbox_from_controls()
    
    def on_clear_selection(self, event):
        """Clear the selection"""
        self.bbox_start = None
        self.bbox_end = None
        self.start_x_ctrl.Clear()
        self.start_y_ctrl.Clear()
        self.end_x_ctrl.Clear()
        self.end_y_ctrl.Clear()
        self.update_dimensions()
        self.canvas.Refresh()
        self.SetStatusText("Selection cleared", 0)
    
    def on_copy_coordinates(self, event):
        """Copy coordinates to clipboard"""
        if self.bbox_start and self.bbox_end:
            text = f"Start: ({self.bbox_start[0]:.3f}, {self.bbox_start[1]:.3f}) mm\n"
            text += f"End: ({self.bbox_end[0]:.3f}, {self.bbox_end[1]:.3f}) mm\n"
            width = abs(self.bbox_end[0] - self.bbox_start[0])
            height = abs(self.bbox_end[1] - self.bbox_start[1])
            text += f"Width: {width:.3f} mm, Height: {height:.3f} mm"
            
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
                self.SetStatusText("Coordinates copied to clipboard", 0)
        else:
            wx.MessageBox("No bounding box selected", "Info", wx.OK | wx.ICON_INFORMATION)
    
    def on_export_selection(self, event):
        """Export selection to file"""
        if not self.bbox_start or not self.bbox_end:
            wx.MessageBox("No bounding box selected", "Info", wx.OK | wx.ICON_INFORMATION)
            return
        
        dlg = wx.FileDialog(
            self, "Save bounding box coordinates",
            wildcard="Text files (*.txt)|*.txt|CSV files (*.csv)|*.csv",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            
            with open(filepath, 'w') as f:
                if filepath.endswith('.csv'):
                    f.write("Parameter,X (mm),Y (mm)\n")
                    f.write(f"Start,{self.bbox_start[0]:.3f},{self.bbox_start[1]:.3f}\n")
                    f.write(f"End,{self.bbox_end[0]:.3f},{self.bbox_end[1]:.3f}\n")
                    width = abs(self.bbox_end[0] - self.bbox_start[0])
                    height = abs(self.bbox_end[1] - self.bbox_start[1])
                    f.write(f"Width,{width:.3f},\n")
                    f.write(f"Height,,{height:.3f}\n")
                else:
                    f.write(f"Bounding Box Coordinates\n")
                    f.write(f"========================\n\n")
                    f.write(f"Start Point: ({self.bbox_start[0]:.3f}, {self.bbox_start[1]:.3f}) mm\n")
                    f.write(f"End Point: ({self.bbox_end[0]:.3f}, {self.bbox_end[1]:.3f}) mm\n\n")
                    width = abs(self.bbox_end[0] - self.bbox_start[0])
                    height = abs(self.bbox_end[1] - self.bbox_start[1])
                    area = width * height
                    f.write(f"Dimensions:\n")
                    f.write(f"  Width: {width:.3f} mm\n")
                    f.write(f"  Height: {height:.3f} mm\n")
                    f.write(f"  Area: {area:.3f} mm²\n")
            
            self.SetStatusText(f"Selection exported to {filepath}", 0)
        
        dlg.Destroy()


class BoundingBoxCanvas(wx.Panel):
    """
    Canvas for displaying PCB in 2D and selecting bounding box
    """
    
    def __init__(self, parent, dialog):
        super(BoundingBoxCanvas, self).__init__(parent)
        
        self.dialog = dialog
        self.board = dialog.board
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.last_mouse_pos = None
        
        self.selecting = False
        self.selection_start_screen = None
        
        self.SetBackgroundColour(wx.Colour(30, 30, 30))
        
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, lambda e: (self.Refresh(), e.Skip()))
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        
        self.panning = False
    
    def screen_to_board_coords(self, screen_x, screen_y):
        """Convert screen coordinates to board coordinates in mm"""
        width, height = self.GetSize()
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        center_x = width / 2 + self.pan_x
        center_y = height / 2 + self.pan_y
        scale = self.zoom * 2.0
        
        board_x = bbox_center_x + (screen_x - center_x) / scale
        board_y = bbox_center_y + (screen_y - center_y) / scale
        
        return (board_x, board_y)
    
    def board_to_screen_coords(self, board_x, board_y):
        """Convert board coordinates (mm) to screen coordinates"""
        width, height = self.GetSize()
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        center_x = width / 2 + self.pan_x
        center_y = height / 2 + self.pan_y
        scale = self.zoom * 2.0
        
        screen_x = center_x + (board_x - bbox_center_x) * scale
        screen_y = center_y + (board_y - bbox_center_y) * scale
        
        return (screen_x, screen_y)
    
    def on_paint(self, event):
        """Handle paint event"""
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)
        
        if gc:
            self.render(gc)
    
    def render(self, gc):
        """Render the 2D PCB view"""
        width, height = self.GetSize()
        
        # Clear background
        gc.SetBrush(wx.Brush(wx.Colour(30, 30, 30)))
        gc.DrawRectangle(0, 0, width, height)
        
        # Get board bounds
        bbox = self.board.GetBoardEdgesBoundingBox()
        board_width = bbox.GetWidth() / 1e6
        board_height = bbox.GetHeight() / 1e6
        
        center_x = width / 2 + self.pan_x
        center_y = height / 2 + self.pan_y
        scale = self.zoom * 2.0
        
        # Draw board outline
        self.draw_board_outline_2d(gc, center_x, center_y, board_width, board_height, scale)
        
        # Draw tracks
        self.draw_tracks_2d(gc, center_x, center_y, scale)
        
        # Draw components
        self.draw_components_2d(gc, center_x, center_y, scale)
        
        # Draw bounding box if selected
        if self.dialog.bbox_start and self.dialog.bbox_end:
            self.draw_bounding_box(gc)
        
        # Draw temporary selection rectangle
        if self.selecting and self.selection_start_screen and self.last_mouse_pos:
            self.draw_selection_rect(gc)
    
    def draw_board_outline_2d(self, gc, center_x, center_y, board_width, board_height, scale):
        """Draw board outline in 2D"""
        # Board rectangle
        x = center_x - (board_width / 2) * scale
        y = center_y - (board_height / 2) * scale
        w = board_width * scale
        h = board_height * scale
        
        gc.SetBrush(wx.Brush(wx.Colour(40, 80, 40)))
        gc.SetPen(wx.Pen(wx.Colour(100, 200, 100), 2))
        gc.DrawRectangle(x, y, w, h)
    
    def draw_tracks_2d(self, gc, center_x, center_y, scale):
        """Draw tracks in 2D"""
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        for track in self.board.GetTracks():
            track_class = track.GetClass()
            if track_class not in ["PCB_TRACE", "TRACK", "PCB_TRACK"]:
                continue
            
            start = track.GetStart()
            end = track.GetEnd()
            
            x1_mm = start.x / 1e6 - bbox_center_x
            y1_mm = start.y / 1e6 - bbox_center_y
            x2_mm = end.x / 1e6 - bbox_center_x
            y2_mm = end.y / 1e6 - bbox_center_y
            
            px1 = center_x + x1_mm * scale
            py1 = center_y + y1_mm * scale
            px2 = center_x + x2_mm * scale
            py2 = center_y + y2_mm * scale
            
            track_width = track.GetWidth() / 1e6
            pen_width = max(1, int(track_width * scale))
            
            layer = track.GetLayer()
            if layer == pcbnew.F_Cu:
                gc.SetPen(wx.Pen(wx.Colour(200, 100, 50), pen_width))
            elif layer == pcbnew.B_Cu:
                gc.SetPen(wx.Pen(wx.Colour(100, 120, 180), pen_width))
            else:
                gc.SetPen(wx.Pen(wx.Colour(150, 150, 50), pen_width))
            
            gc.StrokeLine(px1, py1, px2, py2)
    
    def draw_components_2d(self, gc, center_x, center_y, scale):
        """Draw components in 2D"""
        bbox = self.board.GetBoardEdgesBoundingBox()
        bbox_center_x = (bbox.GetLeft() + bbox.GetRight()) / 2.0 / 1e6
        bbox_center_y = (bbox.GetTop() + bbox.GetBottom()) / 2.0 / 1e6
        
        for footprint in self.board.GetFootprints():
            for pad in footprint.Pads():
                pad_pos = pad.GetPosition()
                x_mm = pad_pos.x / 1e6 - bbox_center_x
                y_mm = pad_pos.y / 1e6 - bbox_center_y
                
                px = center_x + x_mm * scale
                py = center_y + y_mm * scale
                
                pad_size = pad.GetSize()
                pw = pad_size.x / 1e6 * scale
                ph = pad_size.y / 1e6 * scale
                
                is_bottom = footprint.IsFlipped()
                if is_bottom:
                    gc.SetBrush(wx.Brush(wx.Colour(120, 120, 180)))
                else:
                    gc.SetBrush(wx.Brush(wx.Colour(180, 140, 80)))
                
                gc.SetPen(wx.Pen(wx.Colour(100, 100, 100), 1))
                gc.DrawRectangle(px - pw/2, py - ph/2, pw, ph)
    
    def draw_bounding_box(self, gc):
        """Draw the selected bounding box"""
        if not self.dialog.bbox_start or not self.dialog.bbox_end:
            return
        
        # Convert board coordinates to screen coordinates
        x1, y1 = self.board_to_screen_coords(self.dialog.bbox_start[0], self.dialog.bbox_start[1])
        x2, y2 = self.board_to_screen_coords(self.dialog.bbox_end[0], self.dialog.bbox_end[1])
        
        # Draw rectangle
        gc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 50)))  # Semi-transparent yellow
        gc.SetPen(wx.Pen(wx.Colour(255, 255, 0), 2))  # Solid yellow border
        
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        
        gc.DrawRectangle(x, y, w, h)
        
        # Draw corner handles
        handle_size = 8
        gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
        gc.SetPen(wx.Pen(wx.Colour(0, 0, 0), 1))
        
        for corner_x, corner_y in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
            gc.DrawRectangle(corner_x - handle_size/2, corner_y - handle_size/2, handle_size, handle_size)
    
    def draw_selection_rect(self, gc):
        """Draw temporary selection rectangle while dragging"""
        x1, y1 = self.selection_start_screen
        x2, y2 = self.last_mouse_pos.x, self.last_mouse_pos.y
        
        gc.SetBrush(wx.Brush(wx.Colour(100, 150, 255, 30)))
        gc.SetPen(wx.Pen(wx.Colour(100, 150, 255), 1))
        
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        
        gc.DrawRectangle(x, y, w, h)
    
    def on_mouse_move(self, event):
        """Handle mouse movement"""
        pos = event.GetPosition()
        
        if self.selecting:
            # Update temporary selection
            self.Refresh()
        elif self.panning and self.last_mouse_pos:
            # Pan view
            dx = pos.x - self.last_mouse_pos.x
            dy = pos.y - self.last_mouse_pos.y
            self.pan_x += dx
            self.pan_y += dy
            self.Refresh()
        
        # Update cursor position in status bar
        board_x, board_y = self.screen_to_board_coords(pos.x, pos.y)
        self.dialog.SetStatusText(f"Cursor: ({board_x:.3f}, {board_y:.3f}) mm", 0)
        
        self.last_mouse_pos = pos
    
    def on_left_down(self, event):
        """Start bounding box selection"""
        pos = event.GetPosition()
        self.selecting = True
        self.selection_start_screen = (pos.x, pos.y)
        self.CaptureMouse()
    
    def on_left_up(self, event):
        """Finish bounding box selection"""
        if self.selecting:
            self.selecting = False
            if self.HasCapture():
                self.ReleaseMouse()
            
            # Convert screen coordinates to board coordinates
            if self.selection_start_screen:
                start_board = self.screen_to_board_coords(
                    self.selection_start_screen[0],
                    self.selection_start_screen[1]
                )
                end_board = self.screen_to_board_coords(
                    self.last_mouse_pos.x,
                    self.last_mouse_pos.y
                )
                
                self.dialog.bbox_start = start_board
                self.dialog.bbox_end = end_board
                self.dialog.update_controls_from_bbox()
                self.Refresh()
                
                width = abs(end_board[0] - start_board[0])
                height = abs(end_board[1] - start_board[1])
                self.dialog.SetStatusText(
                    f"Selected: {width:.3f} × {height:.3f} mm", 0
                )
    
    def on_right_down(self, event):
        """Start panning"""
        self.panning = True
        self.CaptureMouse()
    
    def on_right_up(self, event):
        """Stop panning"""
        if self.panning:
            self.panning = False
            if self.HasCapture():
                self.ReleaseMouse()
    
    def on_mouse_wheel(self, event):
        """Handle zoom"""
        rotation = event.GetWheelRotation()
        if rotation > 0:
            self.zoom *= 1.1
        else:
            self.zoom *= 0.9
        self.zoom = max(0.1, min(10.0, self.zoom))
        self.Refresh()


# Register the plugin
KicadPCBToolsSuite().register()
