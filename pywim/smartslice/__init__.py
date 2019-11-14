import threemf

from . import job, opt, result
from .. import WimException, chop

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

    @classmethod
    def make_asset(cls, name):
        if name == 'job.json':
            return JobThreeMFAsset('job.json')
        return threemf.extension.RawFile(name)

    def process_threemf(self, tmf : threemf.ThreeMF):
        # We want to read the mesh from the 3mf model
        if len(tmf.models) != 1:
            raise WimException('No 3DModel found in 3MF')

        mdl = tmf.models[0]

        if mdl.unit != 'millimeter':
            raise WimException('Unsupported unit type {} in: {}'.format(mdl.unit, mdl.path))

        if len(mdl.objects) == 0:
            raise WimException('No objects found in 3mf model: {}'.format(mdl.path))

        if len(mdl.objects) > 1:
            raise WimException('Multiple objects in 3mf model is not supported: {}'.format(mdl.path))

        obj = mdl.objects[0]

        if not isinstance(obj, threemf.model.ObjectModel):
            raise WimException('Object of type {} in 3mf model is not supported: {}'.format(obj.type, mdl.path))

        # We have the object, now let's look at the build items, verify they're
        # valid for our analysis, and get the transformation matrix for our model

        build = mdl.build

        if len(build.items) == 0:
            raise WimException('No build items found in: {}'.format(mdl.path))

        if len(build.items) > 1:
            raise WimException('Multiple build items in 3mf is not supported: {}'.format(mdl.path))

        item = build.items[0]

        if item.objectid != obj.id:
            raise WimException('Build item objectid does not match model id: {}'.format(mdl.path))

        T = item.transform

        # Now get the job asset
        job_assets = list(filter(lambda a: isinstance(a, JobThreeMFAsset), self.assets))
            
        if len(job_assets) == 1:
            j = job_assets[0]

            mesh = chop.mesh.Mesh.cast_from_base(obj.mesh)
            mesh.transform = T

            mesh.name = 'normal'

            mesh.materials = chop.mesh.MaterialNames(
                '%s-extrusion' % mesh.name,
                '%s-infill' % mesh.name
            )

            j.content.chop.meshes.append(mesh)
