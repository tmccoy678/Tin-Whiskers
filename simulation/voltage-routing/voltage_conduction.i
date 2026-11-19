[Mesh]
  type = ImageMesh
  dim = 2
  file = topologies/grown-cherenkov.png
  scale_to_one = true
[]

[Variables]
  [voltage]
  []
[]

[AuxVariables]
  [metal]
    order = CONSTANT
    family = MONOMIAL
  []
  [conductivity]
    order = CONSTANT
    family = MONOMIAL
  []
  [grad_voltage_x]
    order = CONSTANT
    family = MONOMIAL
  []
  [grad_voltage_y]
    order = CONSTANT
    family = MONOMIAL
  []
  [current_density]
    order = CONSTANT
    family = MONOMIAL
  []
  [joule_density]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[Functions]
  [metal_image]
    type = ImageFunction
    component = 0
    threshold = 128
    lower_value = 0
    upper_value = 1
  []
[]

[AuxKernels]
  [metal_from_image]
    type = FunctionAux
    variable = metal
    function = metal_image
    execute_on = initial
  []
  [conductivity_from_material]
    type = MaterialRealAux
    variable = conductivity
    property = D
    execute_on = 'initial timestep_end'
  []
  [voltage_gradient_x]
    type = VariableGradientComponent
    variable = grad_voltage_x
    gradient_variable = voltage
    component = x
    execute_on = timestep_end
  []
  [voltage_gradient_y]
    type = VariableGradientComponent
    variable = grad_voltage_y
    gradient_variable = voltage
    component = y
    execute_on = timestep_end
  []
  [current_density_from_field]
    type = ParsedAux
    variable = current_density
    coupled_variables = 'conductivity grad_voltage_x grad_voltage_y'
    expression = 'conductivity * sqrt(grad_voltage_x^2 + grad_voltage_y^2)'
    execute_on = timestep_end
  []
  [joule_density_from_field]
    type = ParsedAux
    variable = joule_density
    coupled_variables = 'conductivity grad_voltage_x grad_voltage_y'
    expression = 'conductivity * (grad_voltage_x^2 + grad_voltage_y^2)'
    execute_on = timestep_end
  []
[]

[Materials]
  [conductivity]
    type = ParsedMaterial
    property_name = D
    coupled_variables = metal
    constant_names = 'sigma_medium sigma_metal'
    constant_expressions = '1e-6 1'
    expression = 'sigma_medium + (sigma_metal - sigma_medium) * metal'
    outputs = exodus
  []
[]

[Kernels]
  [voltage_conduction]
    type = MatDiffusion
    variable = voltage
  []
[]

[BCs]
  [source]
    type = DirichletBC
    variable = voltage
    boundary = left
    value = 1
  []
  [sink]
    type = DirichletBC
    variable = voltage
    boundary = right
    value = 0
  []
[]

[Postprocessors]
  [terminal_flux]
    type = SideDiffusiveFluxIntegral
    variable = voltage
    boundary = right
    diffusivity = D
  []
  [metal_fraction]
    type = ElementIntegralVariablePostprocessor
    variable = metal
  []
  [joule_integral]
    type = ElementIntegralVariablePostprocessor
    variable = joule_density
  []
  [peak_current_density]
    type = ElementExtremeValue
    variable = current_density
    value_type = max
  []
  [peak_joule_density]
    type = ElementExtremeValue
    variable = joule_density
    value_type = max
  []
[]

[Executioner]
  type = Steady
  solve_type = LINEAR
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_package'
  petsc_options_value = 'lu       superlu_dist'
[]

[Outputs]
  exodus = true
  csv = true
[]
