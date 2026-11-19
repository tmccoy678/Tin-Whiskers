[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 48
  ny = 32
  xmax = 1.5
  ymax = 1
[]

[Variables]
  [eta]
  []
  [temperature]
    [InitialCondition]
      type = ConstantIC
      value = -0.15
    []
  []
  [voltage]
  []
[]

[ICs]
  [conductive_seed]
    type = SmoothCircleIC
    variable = eta
    int_width = 0.035
    x1 = 0.08
    y1 = 0.5
    radius = 0.045
    outvalue = 0
    invalue = 1
  []
[]

[Kernels]
  [eta_time]
    type = ADTimeDerivative
    variable = eta
  []
  [eta_anisotropy_1]
    type = ADACInterfaceKobayashi1
    variable = eta
    mob_name = mobility
  []
  [eta_anisotropy_2]
    type = ADACInterfaceKobayashi2
    variable = eta
    mob_name = mobility
  []
  [eta_bulk]
    type = ADAllenCahn
    variable = eta
    mob_name = mobility
    f_name = free_energy
  []

  [temperature_time]
    type = ADTimeDerivative
    variable = temperature
  []
  [temperature_diffusion]
    type = ADDiffusion
    variable = temperature
  []
  [latent_heat]
    type = ADCoefCoupledTimeDerivative
    variable = temperature
    v = eta
    coef = -1.2
  []

  [voltage_conduction]
    type = ADMatDiffusion
    variable = voltage
    diffusivity = conductivity
  []
[]

[BCs]
  [source_voltage]
    type = ADDirichletBC
    variable = voltage
    boundary = left
    value = 1
  []
  [sink_voltage]
    type = ADDirichletBC
    variable = voltage
    boundary = right
    value = 0
  []
[]

[Materials]
  [bulk_free_energy]
    type = ADDerivativeParsedMaterial
    property_name = free_energy
    coupled_variables = 'eta temperature'
    constant_names = 'alpha gamma equilibrium pi'
    constant_expressions = '0.9 10 1 4*atan(1)'
    expression = 'm:=alpha/pi*atan(gamma*(equilibrium-temperature)); '
                 '0.25*eta^4-(0.5-m/3)*eta^3+(0.25-m/2)*eta^2'
    derivative_order = 1
  []
  [interface_orientation]
    type = ADInterfaceOrientationMaterial
    op = eta
    anisotropy_strength = 0.035
    mode_number = 6
  []
  [voltage_dependent_mobility]
    type = ADParsedMaterial
    property_name = mobility
    coupled_variables = voltage
    constant_names = 'base voltage_gain'
    constant_expressions = '80 3'
    expression = 'base*(1+voltage_gain*voltage^2)'
  []
  [phase_dependent_conductivity]
    type = ADParsedMaterial
    property_name = conductivity
    coupled_variables = eta
    constant_names = 'medium conductor'
    constant_expressions = '0.01 1'
    expression = 'medium+(conductor-medium)*eta^2*(3-2*eta)'
    outputs = exodus
  []
[]

[Postprocessors]
  [phase_integral]
    type = ElementIntegralVariablePostprocessor
    variable = eta
  []
  [source_flux]
    type = ADSideDiffusiveFluxIntegral
    variable = voltage
    boundary = left
    diffusivity = conductivity
  []
  [sink_flux]
    type = ADSideDiffusiveFluxIntegral
    variable = voltage
    boundary = right
    diffusivity = conductivity
  []
[]

[Preconditioning]
  [coupled]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  scheme = bdf2
  dt = 0.001
  num_steps = 20
  nl_abs_tol = 1e-9
  nl_rel_tol = 1e-7
  nl_max_its = 30
  l_tol = 1e-5
  l_max_its = 100
  petsc_options_iname = '-pc_type'
  petsc_options_value = 'lu'
[]

[Outputs]
  exodus = true
  csv = true
  time_step_interval = 1
[]
