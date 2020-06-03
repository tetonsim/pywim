from .. import am
import enum

def get_config_value(config, attr_name, level_modifier=None):
    if not level_modifier:
        is_aux = not hasattr(config, attr_name)

        if is_aux:
            if attr_name in config.auxiliary.keys():
                return config.auxiliary[attr_name]

        else:
            attr_val = getattr(config, attr_name)

            if attr_val:
                return attr_val
    else:
        cur_lev = config
        for lev in level_modifier:
            cur_lev = getattr(cur_lev, lev)

        return getattr(cur_lev, attr_name)

    return None

class PrevalidationError:
    def __str__(self):
        return self.error() + ' ' + self.resolution()

    def error(self):
        raise NotImplementedError()

    def resolution(self):
        raise NotImplementedError()

class InvalidSetup(PrevalidationError):
    '''
    General error
    '''
    def __init__(self, error, resolution):
        self._error = error
        self._resolution = resolution

    def error(self):
        return self._error

    def resolution(self):
        return self._resolution

class InvalidPrintSetting(PrevalidationError):
    '''
    Error for when a print setting does not take a required value.
    '''
    def __init__(self, mesh_name, setting_name, setting_value):
        self.mesh_name = mesh_name
        self.setting_name = setting_name
        self.setting_value = setting_value

    def error(self):
        return 'Unsupported <i>{}</i> for mesh <i>{}</i>.'.format(self.setting_name, self.mesh_name)

    def resolution(self):
        return '<i>{}</i> must equal to {}'.format(self.setting_name, self.setting_value)

class OutOfBoundsPrintSetting(PrevalidationError):
    '''
    Error for when a print setting does not lie within the set bounds.
    '''
    def __init__(self, mesh_name, setting_name, min_value, max_value):
        self.mesh_name = mesh_name
        self.setting_name = setting_name
        self.min_value = min_value
        self.max_value = max_value

    def error(self):
        return 'Unsupported <i>{}</i> for mesh <i>{}</i>. '.format(self.setting_name, self.mesh_name)

    def resolution(self):
        return '<i>{}</i> must be between {} and {}.'.format(self.setting_name, self.min_value, self.max_value)

class ListLengthSetting(PrevalidationError):
    '''
    Error for when a print setting is a list an contains too many or too few elements.
    '''
    def __init__(self, mesh_name, setting_name, min_value, max_value):
        self.mesh_name = mesh_name
        self.setting_name = setting_name
        self.min_value = min_value
        self.max_value = max_value

    def error(self):
        return 'Unsupported <i>{}</i> for mesh <i>{}</i>.'.format(self.setting_name, self.mesh_name)

    def resolution(self):
        return 'Total number of values for <i>{}</i> must be between {} and {}.'.format(self.setting_name, self.min_value, self.max_value)

class UnsupportedPrintOptionSetting(PrevalidationError):
    '''
    Error for when a print setting takes an unsupported value.
    '''
    def __init__(self, mesh_name, setting_name, allowable_values):
        self.mesh_name = mesh_name
        self.setting_name = setting_name
        self.allowable_values = allowable_values

    def error(self):
        return 'Unsupported <i>{}</i> for mesh <i>{}</i>.'.format(self.setting_name, self.mesh_name)

    def resolution(self):
        if len(self.allowable_values) > 0 and isinstance(self.allowable_values[0], enum.Enum):
            allowable_names = ', '.join([ v.name for v in self.allowable_values])
        else:
            allowable_names = ', '.join(self.allowable_values)

        return '<i>{}</i> must be one of [<i>{}</i>].'.format(self.setting_name, allowable_names)


class IncompatiblePrintSetting(PrevalidationError):
    '''
    Error for when a print setting should equal another print setting, but it does not.
    '''
    def __init__(self, mesh_name, setting_name, target_name):
        self.mesh_name = mesh_name
        self.setting_name = setting_name
        self.target_name = target_name

    def error(self):
        return 'Unsupported <i>{}</i> for mesh <i>{}</i>.'.format(self.setting_name, self.mesh_name)

    def resolution(self):
        return '<i>{}</i> must be <i>{}</i>.'.format(self.setting_name, self.target_name)

class MismatchedPrintSetting(PrevalidationError):
    '''
    Error for when a print setting should match across different meshes, but it does not.
    '''
    def __init__(self, mesh1_name, mesh2_name, setting_name):
        self.mesh1_name = mesh1_name
        self.mesh2_name = mesh2_name
        self.setting_name = setting_name

    def error(self):
        return '<i>{}</i> is incompatible between meshes <i>{}</i> and <i>{}</i>.'.format(self.setting_name, self.mesh1_name, self.mesh2_name)

    def resolution(self):
        return '<i>{}</i> must be the same value for each mesh.'.format(self.setting_name)

class PrevalidationCheck:
    pass

class EqualityCheck(PrevalidationCheck):
    '''
    Class used to check if a certain print paramter is equal to the required value.
    '''
    def __init__(self, attr_name, setting_name, setting_value, level_modifier=None):
        self.attr_name = attr_name
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.level_modifier = level_modifier

    def check_error(self, mesh):
        mesh_value = get_config_value(mesh.print_config, self.attr_name, self.level_modifier)

        if mesh_value and mesh_value != self.setting_value:
            return InvalidPrintSetting(mesh.name, self.setting_name, self.setting_value)
        else:
            return None

class BoundsCheck(PrevalidationCheck):
    '''
    Class used to check if a certain print paramter lies within the required bounds.
    '''
    def __init__(self, attr_name, setting_name, min_value, max_value, level_modifier=None):
        self.attr_name = attr_name
        self.setting_name = setting_name
        self.min_value = min_value
        self.max_value = max_value
        self.level_modifier = level_modifier

    def check_error(self, mesh):
        mesh_value = get_config_value(mesh.print_config, self.attr_name, self.level_modifier)

        if mesh_value and not ( self.min_value <= mesh_value <= self.max_value ):
            return OutOfBoundsPrintSetting(mesh.name, self.setting_name, self.min_value, self.max_value)
        else:
            return None

class ListLengthCheck(PrevalidationCheck):
    '''
    Class used to check if a certain print paramter, given as a list, is an acceptable length.
    '''
    def __init__(self, attr_name, setting_name, min_value, max_value, level_modifier=None):
        self.attr_name = attr_name
        self.setting_name = setting_name
        self.min_value = min_value
        self.max_value = max_value
        self.level_modifier = level_modifier

    def check_error(self, mesh):
        mesh_value = get_config_value(mesh.print_config, self.attr_name, self.level_modifier)

        if mesh_value and not ( self.min_value <= len(mesh_value) <= self.max_value ):
            return ListLengthSetting(mesh.name, self.setting_name, self.min_value, self.max_value)
        else:
            return None

class SupportedPrintOptionCheck(PrevalidationCheck):
    '''
    Class used to check if a certain print paramter lies within the set of allowable options.
    '''
    def __init__(self, attr_name, setting_name, allowable_values, level_modifier=None):
        self.attr_name = attr_name
        self.setting_name = setting_name
        self.allowable_values = allowable_values
        self.level_modifier = level_modifier

    def check_error(self, mesh):
        mesh_value = get_config_value(mesh.print_config, self.attr_name, self.level_modifier)

        if mesh_value and mesh_value not in self.allowable_values:
            return UnsupportedPrintOptionSetting(mesh.name, self.setting_name, self.allowable_values)
        else:
            return None

class CompatibilityCheck(PrevalidationCheck):
    '''
    Class used to check if a certain print paramter is equal to another print parameter (as required).
    '''
    def __init__(self, attr_name, setting_name, target_name, target_attr_name, level_modifier=None):
        self.attr_name = attr_name
        self.setting_name = setting_name
        self.target_name = target_name
        self.target_attr_name = target_attr_name
        self.level_modifier = level_modifier

    def check_error(self, mesh):
        mesh_value = get_config_value(mesh.print_config, self.attr_name, self.level_modifier)
        target_value = get_config_value(mesh.print_config, self.target_attr_name, self.level_modifier)

        if mesh_value and mesh_value != target_value:
            return IncompatiblePrintSetting(mesh.name, self.setting_name, self.target_name)
        else:
            return None

class MatchedConfigsCheck(PrevalidationCheck):
    '''
    Class used to check if a certain print paramter is equal across different meshes.
    '''
    def __init__(self, attr_name, setting_name, level_modifier=None):
        self.attr_name = attr_name
        self.setting_name = setting_name
        self.level_modifier = level_modifier

    def check_error(self, mesh1, mesh2):
        mesh1_value = get_config_value(mesh1.print_config, self.attr_name, self.level_modifier)
        mesh2_value = get_config_value(mesh2.print_config, self.attr_name, self.level_modifier)

        if mesh1_value and mesh2_value and mesh1_value != mesh2_value:
            return MismatchedPrintSetting(mesh1.name, mesh2.name, self.setting_name)
        else:
            return None

NECESSARY_PRINT_PARAMETERS = [
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
    'extruders_enabled_count',
    'layer_height_0',
    'infill_line_width',
    'skin_line_width',
    'wall_line_width_0',
    'wall_line_width_x',
    'wall_line_width',
    'initial_layer_line_width_factor',
    'top_bottom_pattern',
    'top_bottom_pattern_0',
    'infill_sparse_thickness',
    'gradual_infill_steps',
    'mold_enabled',
    'magic_mesh_surface_mode',
    'magic_spiralize',
    'spaghetti_infill_enabled',
    'magic_fuzzy_skin_enabled',
    'wireframe_enabled',
    'adaptive_layer_height_enabled'
]

REQUIREMENTS = {
    EqualityCheck('extruders_enabled_count', 'Number of Extruders That Are Enabled', 1),
    EqualityCheck('initial_layer_line_width_factor', 'Initial Layer Line Width', 100),
    EqualityCheck('top_bottom_pattern', 'Top/Bottom Pattern', 'lines'),
    EqualityCheck('top_bottom_pattern_0', 'Bottom Pattern Initial Layer', 'lines'),
    EqualityCheck('gradual_infill_steps', 'Gradual Infill Steps', 0),
    EqualityCheck('mold_enabled', 'Mold', 'false'),
    EqualityCheck('magic_mesh_surface_mode', 'Surface Mode', 'normal'),
    EqualityCheck('magic_spiralize', 'Spiralize Outer Contour', 'false'),
    EqualityCheck('spaghetti_infill_enabled', 'Spaghetti Infill', 'false'),
    EqualityCheck('magic_fuzzy_skin_enabled', 'Fuzzy Skin', 'false'),
    EqualityCheck('wireframe_enabled', 'Wire Printing', 'false'),
    EqualityCheck('adaptive_layer_height_enabled', 'Use Adaptive Layers', 'false'),

    CompatibilityCheck('layer_height_0', 'Initial Layer Height', 'Layer Height', 'layer_height'),
    CompatibilityCheck('infill_line_width',  'Infill Line Width', 'Layer Width', 'layer_width'),
    CompatibilityCheck('skin_line_width', 'Top/Bottom Line Width', 'Layer Width', 'layer_width'),
    CompatibilityCheck('wall_line_width_0', 'Outer Wall Line Width', 'Layer Width', 'layer_width'),
    CompatibilityCheck('wall_line_width_x', 'Inner Wall(s) Line Width', 'Layer Width', 'layer_width'),
    CompatibilityCheck('wall_line_width', 'Wall Line Width', 'Layer Width', 'layer_width'),
    CompatibilityCheck('infill_sparse_thickness', 'Infill Layer Thickness', 'Layer Height', 'layer_height'),

    BoundsCheck('density', 'Infill Density', min_value=20, max_value=100, level_modifier=['infill']),

    ListLengthCheck('infill_angles', 'Number of Infill Line Directions', min_value=0, max_value=1),

    SupportedPrintOptionCheck('pattern', 'Infill Pattern', [am.InfillType.grid, am.InfillType.triangle], level_modifier=['infill'])
}

CONFIG_MATCHING = {
    MatchedConfigsCheck('layer_height', 'Layer Height'),
    MatchedConfigsCheck('layer_width', 'Line Width')
}
