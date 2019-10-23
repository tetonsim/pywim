import pywim
import zipfile

def main():
    job = pywim.smartslice.job.Job()

    job.type = pywim.smartslice.job.JobType.optimization

    # Create the bulk material definition. This likely will be pre-defined
    # in a materials database or file somewhere
    job.bulk = pywim.fea.model.Material(name='abs')
    job.bulk.density = 1.0
    job.bulk.elastic = pywim.fea.model.Elastic(properties={'E': 2000.0, 'nu': 0.3})

    # Setup optimization configuration
    job.optimization.min_safety_factor = 2.5
    job.optimization.max_displacement = 3.0 # millimeters

    # Setup the chop model - chop is responsible for creating an FEA model
    # from the triangulated surface mesh, slicer configuration, and
    # the prescribed boundary conditions
    
    # The chop.model.Model class has an attribute for defining
    # the mesh, however, it's not necessary that we do so.
    # When the back-end reads the 3MF it will obtain the mesh
    # from the 3MF object model, therefore, defining it in the 
    # chop object would be redundant.
    #job.chop.meshes.append( ... ) <-- Not necessary

    # Define the load step for the FE analysis
    step = pywim.chop.model.Step(name='default')

    # Create the fixed boundary conditions (anchor points)
    anchor1 = pywim.chop.model.FixedBoundaryCondition(name='anchor1')

    # Add the face Ids from the STL mesh that the user selected for
    # this anchor
    anchor1.face.extend(
        (97, 98, 111, 112)
    )

    step.boundary_conditions.append(anchor1)

    # Add any other boundary conditions in a similar manner...

    # Create an applied force
    force1 = pywim.chop.model.Force(name='force1')

    # Set the components on the force vector. In this example
    # we have 100 N, 200 N, and 50 N in the x, y, and z
    # directions respectfully.
    force1.force.set((100., 200., 50.))

    # Add the face Ids from the STL mesh that the user selected for
    # this force
    force1.face.extend(
        (156, 157, 158)
    )

    step.loads.append(force1)

    # Add any other loads in a similar manner...

    # Append the step definition to the chop model. Smart Slice only
    # supports one step right now. In the future we may allow multiple
    # loading steps.
    job.chop.steps.append(step)

    # Now we need to setup the print/slicer configuration
    # This is split between two attributes in the chop model:
    # print_config: contains the print parameters that smart slice uses
    # slicer: contains all of the configuration that is necessary
    #   for the chosen slicer to execute
    
    print_config = job.chop.print_config
    print_config.layer_width = 0.45
    # ... and so on, check pywim.am.Config for full definition

    # Setup the slicer configuration. See each class for more
    # information. The Extruder, Printer, and Config classes each
    # contain a "settings" dictionary which should be used to define
    # the slicer specific settings. These will be passed on directly
    # to the slicer (CuraEngine).
    extruder0 = pywim.chop.machine.Extruder(diameter=0.4)
    printer = pywim.chop.machine.Printer(name='Ultimaker S5', extruders=(extruder0, ))
    cura_config = pywim.chop.slicer.Config(printer)

    # And finally set the slicer to the Cura Engine with the
    # config defined above
    job.chop.slicer = pywim.chop.slicer.CuraEngine(config=cura_config)

    with zipfile.ZipFile('test.3mf', 'a') as tmf:
        tmf.writestr('SmartSlice/job.json', job.to_json())

if __name__ == '__main__':
    main()