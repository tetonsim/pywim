from ... import am, micro
from ...fea.model import Material
from typing import Union

def Hexpack(composite : micro.Composite, name=None):
    hexpack = micro.Hexpack(composite.volume_fraction)
    job = micro.Job(name if name else 'hexpack', hexpack)

    job.materials.extend([
        micro.JobMaterial.FromMaterial('fiber', composite.fiber.name),
        micro.JobMaterial.FromMaterial('matrix', composite.matrix.name)
    ])

    return job

def Particulate(composite : micro.Composite, name=None):
    part = micro.ParticulateBCC(composite.volume_fraction)
    job = micro.Job(name if name else 'particulate', part)

    job.materials.extend([
        micro.JobMaterial.FromMaterial('fiber', composite.fiber.name),
        micro.JobMaterial.FromMaterial('matrix', composite.matrix.name)
    ])

    return job

def ShortFiber(hexpack : micro.Job, particulate : micro.Job, composite : micro.Composite, name=None):
    sf = micro.ShortFiber(composite.volume_fraction, composite.L_over_D)
    job = micro.Job(name if name else 'short_fiber', sf)

    job.materials.extend([
        micro.JobMaterial.FromJob('infinite', hexpack.name),
        micro.JobMaterial.FromJob('end', particulate.name)
    ])

    return job

def ExtrudedLayer(source : Union[Material, micro.Job], config : am.Config, name=None):
    layer = micro.ExtrudedLayer(config)
    job = micro.Job(name if name else 'layer', layer)

    if isinstance(source, Material):
        job.materials.append( micro.JobMaterial.FromMaterial('plastic', source.name) )
    else:
        job.materials.append( micro.JobMaterial.FromJob('plastic', source.name) )

    return job

def Infill(layer : Union[Material, micro.Job], config : am.Config, name=None):
    infill = micro.Infill.FromConfig(config)
    job = micro.Job(name if name else 'infill', infill)

    if isinstance(layer, Material):
        job.materials.append( micro.JobMaterial.FromMaterial('extrusion', layer.name) )
    else:
        job.materials.append( micro.JobMaterial.FromJob('extrusion', layer.name) )

    return job
