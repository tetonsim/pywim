import threemf

from . import job, opt, result
from .. import WimException

class JobThreeMFAsset(threemf.extension.Asset):
    def __init__(self, name):
        super().__init__(name)
        self.content = job.Job()

    def serialize(self):
        return self.content.to_json()

    def deserialize(self, string_content):
        self.content = job.Job.from_json(string_content)

class ThreeMFExtension(threemf.extension.Extension):
    Name = 'SmartSlice'

    def __init__(self):
        super().__init__(ThreeMFExtension.Name)
        self.assets = [
            JobThreeMFAsset('job.json')
        ]

    @classmethod
    def make_asset(cls, name):
        if name == 'job.json':
            return self.assets[0]
        return threemf.extension.RawFile(name)

    def process_threemf(self, tmf : threemf.ThreeMF):
        # We want to read the mesh from the 3mf model
        if len(tmf.models) != 1:
            raise WimException(f'No 3DModel found in 3MF')

        mdl = tmf.models[0]

        if mdl.unit != 'millimeter':
            raise WimException(f'Unsupported unit type {mdl.unit} in: {mdl.path}')

        if len(mdl.objects) == 0:
            raise WimException(f'No objects found in 3mf model: {mdl.path}')

        if len(mdl.objects) > 1:
            raise WimException(f'Multiple objects in 3mf model is not supported: {mdl.path}')

        obj = mdl.objects[0]

        if not isinstance(obj, threemf.model.ObjectModel):
            raise WimException(f'Object of type {obj.type} in 3mf model is not supported: {mdl.path}')

        # We have the object, now let's look at the build items, verify they're
        # valid for our analysis, and get the transformation matrix for our model

        build = mdl.build

        if len(build.items) == 0:
            raise WimException(f'No build items found in: {mdl.path}')

        if len(build.items) > 1:
            raise WimException(f'Multiple build items in 3mf is not supported: {mdl.path}')

        item = build.items[0]

        if item.objectid != obj.id:
            raise WimException(f'Build item objectid does not match model id: {mdl.path}')

        T = item.transform

        # Now get the job asset
        j = self.assets[0]

        j.content.mesh = job.Mesh.cast_from_base(obj.mesh)
        j.content.mesh.transform = T
