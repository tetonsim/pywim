import pywim

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
    # from the triangle surface mesh, slicer configuration, and
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

    # Now we need to 

if __name__ == '__main__':
    main()