from .. import am

checked_print_parameters = [
            'layer_width',
            'layer_height',
            'walls',
            'bottom_layers',
            'top_layers',
            'skin_orientations',
            'infill.pattern',
            'infill.density',
            'infill.orientation',
            'infill_angles',
            "extruders_enabled_count",
            "layer_height_0",
            "infill_line_width",
            "skin_line_width",
            "wall_line_width_0",
            "wall_line_width_x",
            "wall_line_width",
            "initial_layer_line_width_factor",
            "top_bottom_pattern",
            "top_bottom_pattern_0",
            "infill_sparse_thickness",
            "gradual_infill_steps",
            "mold_enabled",
            "magic_mesh_surface_mode",
            "magic_spiralize",
            "spaghetti_infill_enabled",
            "magic_fuzzy_skin_enabled",
            "wireframe_enabled",
            "adaptive_layer_height_enabled"
        ]

compatibility_parameters = { "layer_height": "Layer Height", "layer_width": "Line Width"}

specific_reqs = {
    "extruders_enabled_count": [1, "Number of Extruders That Are Enabled"],
    "initial_layer_line_width_factor": [100, "Initial Layer Line Width"],
    "top_bottom_pattern": ["lines", "Top/Bottom Pattern"],
    "top_bottom_pattern_0": ["lines", "Bottom Pattern Initial Layer"],
    "gradual_infill_steps": [0, "Gradual Infill Steps"],
    "mold_enabled": ['false', "Mold"],
    "magic_mesh_surface_mode": ["normal", "Surface Mode"],
    "magic_spiralize": ['false', "Spiralize Outer Contour"],
    "spaghetti_infill_enabled": ['false', "Spaghetti Infill"],
    "magic_fuzzy_skin_enabled": ['false', "Fuzzy Skin"],
    "wireframe_enabled": ['false', "Wire Printing"],
    "adaptive_layer_height_enabled": ['false', "Use Adaptive Layers"]
}

comparative_reqs = {
    "layer_height_0": ['layer_height', "Initial Layer Height", "Layer Height"],
    "infill_line_width": ['layer_width', "Infill Line Width", "Layer Width"],
    "skin_line_width": ['layer_width', "Top/Bottom Line Width", "Layer Width"],
    "wall_line_width_0": ['layer_width', "Outer Wall Line Width", "Layer Width"],
    "wall_line_width_x": ['layer_width', "Inner Wall(s) Line Width", "Layer Width"],
    "wall_line_width": ['layer_width', "Wall Line Width", "Layer Width"],
    "infill_sparse_thickness": ['layer_height', "Infill Layer Thickness", "Layer Height"],
}

# Infill specific settings
infill_reqs = [
    ["density",20, 100, "Infill Density"],
    ["pattern", [am.InfillType.grid, am.InfillType.triangle], "Infill Pattern"],
    ["infill_angles", 0, 1, "Infill Line Directions"]
]

class PrevalidationError:
    pass

class InvalidPrintSetting(PrevalidationError):
    def __init__(self, mesh, setting_name, mesh_value, setting_value):
        self.mesh = mesh
        self.setting_name = setting_name
        self.mesh_value = mesh_value
        self.setting_value = setting_value

class OutOfBoundsPrintSetting(PrevalidationError):
    def __init__(self, mesh, setting_name, min_value, max_value):
        self.mesh = mesh
        self.setting_name = setting_name
        self.min_value = min_value
        self.max_value = max_value

class UnsupportedPrintOptionSetting(PrevalidationError):
    def __init__(self, mesh, setting_name, allowable_values):
        self.mesh = mesh
        self.setting_name = setting_name
        self.allowable_values = allowable_values

class IncompatiblePrintSetting(PrevalidationError):
    def __init__(self, mesh, setting_name, mesh_value, target_name, target_value):
        self.mesh = mesh
        self.setting_name = setting_name
        self.mesh_value = mesh_value
        self.target_name = target_name
        self.target_value = target_value

class MismatchedPrintSetting(PrevalidationError):
    def __init__(self, mesh1, mesh2, setting_name):
        self.mesh1 = mesh1
        self.mesh2 = mesh2
        self.setting_name = setting_name