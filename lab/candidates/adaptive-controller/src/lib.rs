//! Isolated candidate policy core for the adaptive-controller bench.
//!
//! This crate chooses between two predeclared actuator channels. It has no
//! coordinate, route, topology-writing, MOOSE-launching, or hardware-control
//! API.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const OBSERVATION_SCHEMA: &str = "adaptive-observation/v1";
pub const ACTION_SCHEMA: &str = "adaptive-action/v1";
pub const AUDIT_SCHEMA: &str = "adaptive-step/v1";

pub const UNIT_DELIVERED_CURRENT: &str = "<SI:delivered-current-pending-calibration>";
pub const UNIT_CURRENT_DENSITY: &str = "<SI:current-density-pending-calibration>";
pub const UNIT_JOULE_DENSITY: &str = "<SI:power-density-pending-calibration>";
pub const UNIT_STRESS: &str = "<SI:stress-pending-calibration>";
pub const UNIT_TEMPERATURE: &str = "<SI:temperature-pending-calibration>";
pub const UNIT_MATERIAL: &str = "<SI:material-pending-calibration>";
pub const UNIT_ENERGY: &str = "<SI:energy-pending-calibration>";
pub const UNIT_VOLTAGE: &str = "<SI:voltage-pending-calibration>";

const FEATURE_COUNT: usize = 8;
const OBJECTIVE_COUNT: usize = 7;
const WARMUP_STEPS: usize = 4;
const NUMERIC_TOLERANCE: f64 = 1.0e-12;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Hash256(pub String);

impl Hash256 {
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.0.len() == 64
            && self
                .0
                .as_bytes()
                .iter()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(byte))
        {
            Ok(())
        } else {
            Err(ValidationError::InvalidHash)
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct UnitStrings {
    pub delivered_current: String,
    pub current_density: String,
    pub joule_density: String,
    pub mechanical_stress: String,
    pub temperature: String,
    pub material: String,
    pub optical_energy: String,
    pub electrical_energy: String,
    pub voltage: String,
}

impl UnitStrings {
    pub fn pending_si() -> Self {
        Self {
            delivered_current: UNIT_DELIVERED_CURRENT.into(),
            current_density: UNIT_CURRENT_DENSITY.into(),
            joule_density: UNIT_JOULE_DENSITY.into(),
            mechanical_stress: UNIT_STRESS.into(),
            temperature: UNIT_TEMPERATURE.into(),
            material: UNIT_MATERIAL.into(),
            optical_energy: UNIT_ENERGY.into(),
            electrical_energy: UNIT_ENERGY.into(),
            voltage: UNIT_VOLTAGE.into(),
        }
    }

    fn validate(&self) -> Result<(), ValidationError> {
        if self == &Self::pending_si() {
            Ok(())
        } else {
            Err(ValidationError::InvalidUnits)
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChannelAvailability {
    pub material_reservoir: bool,
    pub temperature: bool,
    pub mechanical_stress: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GlobalObservation {
    pub terminal_flux: f64,
    pub metal_fraction: f64,
    pub joule_integral: f64,
    pub peak_current_density: f64,
    pub peak_joule_density: f64,
    pub peak_mechanical_stress: Option<f64>,
    pub material_used: f64,
    pub cumulative_optical_energy: f64,
    pub cumulative_electrical_energy: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FootprintObservation {
    pub mean_current_density: f64,
    pub p95_current_density: f64,
    pub mean_joule_density: f64,
    pub p95_joule_density: f64,
    pub conductive_fraction: f64,
    pub interface_fraction: f64,
    pub mean_available_reservoir: Option<f64>,
    pub mean_temperature: Option<f64>,
    pub p95_temperature: Option<f64>,
    pub mean_mechanical_stress: Option<f64>,
    pub p95_mechanical_stress: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observation {
    pub schema: String,
    pub run_id: String,
    pub epoch: u64,
    pub previous_observation_sha256: Option<Hash256>,
    pub topology_sha256: Hash256,
    pub moose_sha256: Hash256,
    pub units: UnitStrings,
    pub channels: ChannelAvailability,
    /// Fixed order: `[upper, lower]`. These are actuator identities, not coordinates.
    pub footprints: [FootprintObservation; 2],
    pub global: GlobalObservation,
}

impl Observation {
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.schema != OBSERVATION_SCHEMA {
            return Err(ValidationError::SchemaMismatch);
        }
        if self.run_id.is_empty() {
            return Err(ValidationError::RunMismatch);
        }
        self.topology_sha256.validate()?;
        self.moose_sha256.validate()?;
        if let Some(hash) = &self.previous_observation_sha256 {
            hash.validate()?;
        }
        self.units.validate()?;
        self.global.validate()?;
        for footprint in &self.footprints {
            footprint.validate(&self.channels)?;
        }
        let has_stress = self.global.peak_mechanical_stress.is_some();
        if has_stress != self.channels.mechanical_stress {
            return Err(ValidationError::ChannelMaskMismatch);
        }
        Ok(())
    }

    pub fn canonical_json(&self) -> Result<String, SerializationError> {
        canonical_json(self)
    }

    pub fn canonical_hash(&self) -> Result<Hash256, SerializationError> {
        canonical_hash(self)
    }

    fn objective(&self, epsilon: f64) -> Result<ObjectiveVector, ValidationError> {
        let delivery = self.global.terminal_flux.abs();
        if !delivery.is_finite() || delivery <= epsilon {
            return Err(ValidationError::DeliveryTooSmall);
        }
        let objective = ObjectiveVector {
            delivery,
            current_per_delivery: self.global.peak_current_density / delivery,
            heat_per_delivery_squared: self.global.peak_joule_density / delivery.powi(2),
            mechanical_stress: self.global.peak_mechanical_stress,
            material_used: self.global.material_used,
            optical_energy: self.global.cumulative_optical_energy,
            electrical_energy: self.global.cumulative_electrical_energy,
        };
        objective.validate()?;
        Ok(objective)
    }

    fn feature_vector(
        &self,
        action: ActionId,
        epsilon: f64,
        scales: &FeatureScales,
    ) -> [f64; FEATURE_COUNT] {
        let (selected, other) = match action {
            ActionId::UpperHeavy => (&self.footprints[0], &self.footprints[1]),
            ActionId::LowerHeavy => (&self.footprints[1], &self.footprints[0]),
            ActionId::Dark => unreachable!("dark is not a learned action"),
        };
        let delivery = self.global.terminal_flux.abs().max(epsilon);
        [
            1.0,
            delivery / scales.delivery,
            (self.global.peak_current_density / delivery) / scales.current_per_delivery,
            (self.global.peak_joule_density / delivery.powi(2)) / scales.heat_per_delivery_squared,
            selected.mean_current_density / scales.mean_current_density,
            selected.p95_current_density / scales.p95_current_density,
            selected.mean_joule_density / scales.mean_joule_density,
            (selected.interface_fraction - other.interface_fraction) / scales.interface_contrast,
        ]
    }
}

impl GlobalObservation {
    fn validate(&self) -> Result<(), ValidationError> {
        let required = [
            self.terminal_flux,
            self.metal_fraction,
            self.joule_integral,
            self.peak_current_density,
            self.peak_joule_density,
            self.material_used,
            self.cumulative_optical_energy,
            self.cumulative_electrical_energy,
        ];
        if required.iter().any(|value| !value.is_finite())
            || required[1..].iter().any(|value| *value < 0.0)
            || self
                .peak_mechanical_stress
                .is_some_and(|value| !value.is_finite() || value < 0.0)
        {
            return Err(ValidationError::InvalidNumericValue);
        }
        Ok(())
    }
}

impl FootprintObservation {
    fn validate(&self, channels: &ChannelAvailability) -> Result<(), ValidationError> {
        let required = [
            self.mean_current_density,
            self.p95_current_density,
            self.mean_joule_density,
            self.p95_joule_density,
            self.conductive_fraction,
            self.interface_fraction,
        ];
        if required
            .iter()
            .any(|value| !value.is_finite() || *value < 0.0)
            || self.p95_current_density < self.mean_current_density
            || self.p95_joule_density < self.mean_joule_density
            || self.conductive_fraction > 1.0
            || self.interface_fraction > 1.0
        {
            return Err(ValidationError::InvalidNumericValue);
        }
        validate_optional_channel(
            channels.material_reservoir,
            &[self.mean_available_reservoir],
        )?;
        validate_optional_channel(
            channels.temperature,
            &[self.mean_temperature, self.p95_temperature],
        )?;
        validate_optional_channel(
            channels.mechanical_stress,
            &[self.mean_mechanical_stress, self.p95_mechanical_stress],
        )?;
        if self
            .p95_temperature
            .zip(self.mean_temperature)
            .is_some_and(|(p95, mean)| p95 < mean)
            || self
                .p95_mechanical_stress
                .zip(self.mean_mechanical_stress)
                .is_some_and(|(p95, mean)| p95 < mean)
        {
            return Err(ValidationError::InvalidNumericValue);
        }
        Ok(())
    }
}

fn validate_optional_channel(
    available: bool,
    values: &[Option<f64>],
) -> Result<(), ValidationError> {
    if values.iter().any(|value| value.is_some()) != available
        || values.iter().any(|value| value.is_none()) == available
    {
        return Err(ValidationError::ChannelMaskMismatch);
    }
    if values
        .iter()
        .flatten()
        .any(|value| !value.is_finite() || *value < 0.0)
    {
        return Err(ValidationError::InvalidNumericValue);
    }
    Ok(())
}

pub fn parse_observation_strict(input: &str) -> Result<Observation, ParseError> {
    let observation: Observation = serde_json::from_str(input).map_err(ParseError::Json)?;
    observation.validate().map_err(ParseError::Validation)?;
    Ok(observation)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum ActionId {
    UpperHeavy,
    LowerHeavy,
    Dark,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SelectionMode {
    Warmup,
    Renewal,
    Explore,
    Exploit,
    FailClosed,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Action {
    pub schema: String,
    pub id: ActionId,
    pub upper_fraction: f64,
    pub lower_fraction: f64,
    pub optical_pulse_energy: f64,
    pub source_voltage: f64,
    pub electrical_duty: f64,
    pub polarity: i8,
    pub optical_energy_unit: String,
    pub voltage_unit: String,
    pub observation_sha256: Option<Hash256>,
    pub selection_mode: SelectionMode,
    pub propensity: f64,
}

impl Action {
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.schema != ACTION_SCHEMA {
            return Err(ValidationError::SchemaMismatch);
        }
        if self.optical_energy_unit != UNIT_ENERGY || self.voltage_unit != UNIT_VOLTAGE {
            return Err(ValidationError::InvalidUnits);
        }
        if let Some(hash) = &self.observation_sha256 {
            hash.validate()?;
        }
        let numeric = [
            self.upper_fraction,
            self.lower_fraction,
            self.optical_pulse_energy,
            self.source_voltage,
            self.electrical_duty,
            self.propensity,
        ];
        if numeric
            .iter()
            .any(|value| !value.is_finite() || *value < 0.0)
            || self.propensity <= 0.0
            || self.propensity > 1.0
            || self.electrical_duty > 1.0
            || ![-1, 0, 1].contains(&self.polarity)
        {
            return Err(ValidationError::InvalidAction);
        }
        let expected = match self.id {
            ActionId::UpperHeavy => (0.75, 0.25),
            ActionId::LowerHeavy => (0.25, 0.75),
            ActionId::Dark => (0.0, 0.0),
        };
        if !approximately_equal(self.upper_fraction, expected.0)
            || !approximately_equal(self.lower_fraction, expected.1)
        {
            return Err(ValidationError::InvalidAction);
        }
        Ok(())
    }

    pub fn canonical_json(&self) -> Result<String, SerializationError> {
        canonical_json(self)
    }
}

pub fn parse_action_strict(input: &str) -> Result<Action, ParseError> {
    let action: Action = serde_json::from_str(input).map_err(ParseError::Json)?;
    action.validate().map_err(ParseError::Validation)?;
    Ok(action)
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObjectiveVector {
    pub delivery: f64,
    pub current_per_delivery: f64,
    pub heat_per_delivery_squared: f64,
    pub mechanical_stress: Option<f64>,
    pub material_used: f64,
    pub optical_energy: f64,
    pub electrical_energy: f64,
}

impl ObjectiveVector {
    fn validate(&self) -> Result<(), ValidationError> {
        let required = [
            self.delivery,
            self.current_per_delivery,
            self.heat_per_delivery_squared,
            self.material_used,
            self.optical_energy,
            self.electrical_energy,
        ];
        if required
            .iter()
            .any(|value| !value.is_finite() || *value < 0.0)
            || self
                .mechanical_stress
                .is_some_and(|value| !value.is_finite() || value < 0.0)
        {
            return Err(ValidationError::InvalidNumericValue);
        }
        Ok(())
    }

    fn delta_from(&self, prior: &Self) -> [Option<f64>; OBJECTIVE_COUNT] {
        [
            Some(self.delivery - prior.delivery),
            Some(self.current_per_delivery - prior.current_per_delivery),
            Some(self.heat_per_delivery_squared - prior.heat_per_delivery_squared),
            self.mechanical_stress
                .zip(prior.mechanical_stress)
                .map(|(now, before)| now - before),
            Some(self.material_used - prior.material_used),
            Some(self.optical_energy - prior.optical_energy),
            Some(self.electrical_energy - prior.electrical_energy),
        ]
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyLimits {
    pub max_current_per_delivery: f64,
    pub max_heat_per_delivery_squared: f64,
    pub max_mechanical_stress: Option<f64>,
    pub max_material_used: f64,
    pub require_mechanical_stress: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EnergyBudget {
    pub max_optical_energy: f64,
    pub max_electrical_energy: f64,
    pub optical_cost_per_action: f64,
    pub electrical_cost_per_action: f64,
}

/// Frozen positive divisors for the seven measured features.
///
/// The intercept is not represented here and always remains exactly `1.0`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FeatureScales {
    pub delivery: f64,
    pub current_per_delivery: f64,
    pub heat_per_delivery_squared: f64,
    pub mean_current_density: f64,
    pub p95_current_density: f64,
    pub mean_joule_density: f64,
    pub interface_contrast: f64,
}

impl FeatureScales {
    fn validate(&self) -> Result<(), ValidationError> {
        let scales = [
            self.delivery,
            self.current_per_delivery,
            self.heat_per_delivery_squared,
            self.mean_current_density,
            self.p95_current_density,
            self.mean_joule_density,
            self.interface_contrast,
        ];
        if scales
            .iter()
            .any(|scale| !scale.is_finite() || *scale <= 0.0)
        {
            Err(ValidationError::InvalidConfiguration)
        } else {
            Ok(())
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RenewalActionOrder {
    UpperFirst,
    LowerFirst,
    SeededBalanced,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RenewalConfig {
    /// Positive objective-unit divisors used to normalize prediction residuals.
    pub prediction_error_scales: [f64; OBJECTIVE_COUNT],
    /// Positive dimensionless thresholds applied after residual normalization.
    pub prediction_error_thresholds: [f64; OBJECTIVE_COUNT],
    pub consecutive_change_count: usize,
    pub renewal_length: usize,
    pub action_order: RenewalActionOrder,
    /// Frozen marginal upper/lower balance; currently required to be exactly 0.5.
    pub balanced_action_propensity: f64,
    pub seed: u64,
}

impl RenewalConfig {
    fn validate(&self) -> Result<(), ValidationError> {
        if self
            .prediction_error_scales
            .iter()
            .chain(self.prediction_error_thresholds.iter())
            .any(|value| !value.is_finite() || *value <= 0.0)
            || self.consecutive_change_count == 0
            || self.renewal_length < 2
            || self.renewal_length % 2 != 0
            || !self.balanced_action_propensity.is_finite()
            || !approximately_equal(self.balanced_action_propensity, 0.5)
        {
            Err(ValidationError::InvalidConfiguration)
        } else {
            Ok(())
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ControllerConfig {
    pub run_id: String,
    pub seed: u64,
    pub exploration_probability: f64,
    pub ridge_lambda: f64,
    pub confidence_multiplier: f64,
    pub initial_objective_uncertainty: [f64; OBJECTIVE_COUNT],
    pub feature_scales: FeatureScales,
    pub renewal: RenewalConfig,
    pub delivery_tolerance: f64,
    pub delivery_epsilon: f64,
    pub source_voltage: f64,
    pub electrical_duty: f64,
    pub polarity: i8,
    pub safety: SafetyLimits,
    pub budget: EnergyBudget,
}

impl ControllerConfig {
    fn validate(&self) -> Result<(), ValidationError> {
        self.feature_scales.validate()?;
        self.renewal.validate()?;
        let numeric = [
            self.exploration_probability,
            self.ridge_lambda,
            self.confidence_multiplier,
            self.delivery_tolerance,
            self.delivery_epsilon,
            self.source_voltage,
            self.electrical_duty,
            self.safety.max_current_per_delivery,
            self.safety.max_heat_per_delivery_squared,
            self.safety.max_material_used,
            self.budget.max_optical_energy,
            self.budget.max_electrical_energy,
            self.budget.optical_cost_per_action,
            self.budget.electrical_cost_per_action,
        ];
        if self.run_id.is_empty()
            || numeric
                .iter()
                .any(|value| !value.is_finite() || *value < 0.0)
            || self
                .initial_objective_uncertainty
                .iter()
                .any(|value| !value.is_finite() || *value < 0.0)
            || self.exploration_probability <= 0.0
            || self.exploration_probability > 1.0
            || self.ridge_lambda <= 0.0
            || self.delivery_epsilon <= 0.0
            || self.electrical_duty > 1.0
            || ![-1, 1].contains(&self.polarity)
            || self
                .safety
                .max_mechanical_stress
                .is_some_and(|value| !value.is_finite() || value < 0.0)
        {
            return Err(ValidationError::InvalidConfiguration);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BudgetSnapshot {
    pub material_used: f64,
    pub optical_energy_spent: f64,
    pub electrical_energy_spent: f64,
    pub max_material: f64,
    pub max_optical_energy: f64,
    pub max_electrical_energy: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PriorUpdateAudit {
    pub action: ActionId,
    pub delta_objective: [Option<f64>; OBJECTIVE_COUNT],
    pub predicted_delta: [Option<f64>; OBJECTIVE_COUNT],
    pub residual: [Option<f64>; OBJECTIVE_COUNT],
    pub normalized_abs_residual: [Option<f64>; OBJECTIVE_COUNT],
    pub threshold_exceeded: [bool; OBJECTIVE_COUNT],
    pub any_threshold_exceeded: bool,
    pub change_streak_after: usize,
    pub renewal_triggered: bool,
    pub accepted: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RenewalMode {
    Inactive,
    Triggered,
    Active,
    Completed,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RenewalAudit {
    pub mode: RenewalMode,
    pub triggered: bool,
    pub generation: u64,
    pub change_streak: usize,
    pub required_consecutive_changes: usize,
    pub action_order: RenewalActionOrder,
    pub step_index: Option<usize>,
    pub renewal_length: usize,
    pub propensity: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StepAudit {
    pub schema: String,
    pub run_id: String,
    pub epoch: u64,
    pub observation_sha256: Option<Hash256>,
    pub policy_state_before_sha256: Hash256,
    pub prior_update: Option<PriorUpdateAudit>,
    pub renewal: RenewalAudit,
    pub eligible_actions: Vec<ActionId>,
    pub action: Action,
    pub budgets_before: BudgetSnapshot,
    pub budgets_after: BudgetSnapshot,
    pub fail_reason: Option<FailReason>,
    pub policy_state_after_sha256: Hash256,
}

impl StepAudit {
    pub fn canonical_json(&self) -> Result<String, SerializationError> {
        canonical_json(self)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FailReason {
    ControllerHalted,
    SchemaMismatch,
    RunMismatch,
    StaleEpoch,
    MissingPreviousHash,
    PreviousHashMismatch,
    InvalidHash,
    InvalidUnits,
    InvalidObservation,
    ChannelMaskMismatch,
    MissingRequiredStress,
    EnergyCounterMismatch,
    MaterialBudgetExceeded,
    OpticalBudgetExceeded,
    ElectricalBudgetExceeded,
    ObservedSafetyLimit,
    NoSafeAction,
    SerializationFailure,
}

#[derive(Debug)]
pub enum ParseError {
    Json(serde_json::Error),
    Validation(ValidationError),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ValidationError {
    SchemaMismatch,
    RunMismatch,
    InvalidHash,
    InvalidUnits,
    InvalidNumericValue,
    ChannelMaskMismatch,
    DeliveryTooSmall,
    InvalidAction,
    InvalidConfiguration,
}

#[derive(Debug)]
pub struct SerializationError(serde_json::Error);

impl std::fmt::Display for SerializationError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            formatter,
            "deterministic JSON serialization failed: {}",
            self.0
        )
    }
}

impl std::error::Error for SerializationError {}

#[derive(Clone, Debug, Serialize)]
struct PendingUpdate {
    action: ActionId,
    feature: [f64; FEATURE_COUNT],
    objective_before: ObjectiveVector,
    renewal_action: bool,
}

#[derive(Clone, Debug, Serialize)]
struct ArmModel {
    gram: [[f64; FEATURE_COUNT]; FEATURE_COUNT],
    response: [[f64; FEATURE_COUNT]; OBJECTIVE_COUNT],
    response_sum: [f64; OBJECTIVE_COUNT],
    response_sum_sq: [f64; OBJECTIVE_COUNT],
    response_count: [u64; OBJECTIVE_COUNT],
}

impl ArmModel {
    fn new(ridge_lambda: f64) -> Self {
        let mut gram = [[0.0; FEATURE_COUNT]; FEATURE_COUNT];
        for (index, row) in gram.iter_mut().enumerate() {
            row[index] = ridge_lambda;
        }
        Self {
            gram,
            response: [[0.0; FEATURE_COUNT]; OBJECTIVE_COUNT],
            response_sum: [0.0; OBJECTIVE_COUNT],
            response_sum_sq: [0.0; OBJECTIVE_COUNT],
            response_count: [0; OBJECTIVE_COUNT],
        }
    }

    fn update(&mut self, feature: &[f64; FEATURE_COUNT], delta: &[Option<f64>; OBJECTIVE_COUNT]) {
        for row in 0..FEATURE_COUNT {
            for column in 0..FEATURE_COUNT {
                self.gram[row][column] += feature[row] * feature[column];
            }
        }
        for objective in 0..OBJECTIVE_COUNT {
            if let Some(value) = delta[objective] {
                for feature_index in 0..FEATURE_COUNT {
                    self.response[objective][feature_index] += feature[feature_index] * value;
                }
                self.response_sum[objective] += value;
                self.response_sum_sq[objective] += value * value;
                self.response_count[objective] += 1;
            }
        }
    }

    fn predict(
        &self,
        feature: &[f64; FEATURE_COUNT],
        initial_uncertainty: &[f64; OBJECTIVE_COUNT],
    ) -> Option<Prediction> {
        let solved_feature = solve_linear(self.gram, *feature)?;
        let leverage = dot(feature, &solved_feature).max(0.0).sqrt();
        let mut mean = [None; OBJECTIVE_COUNT];
        let mut uncertainty = [None; OBJECTIVE_COUNT];
        for objective in 0..OBJECTIVE_COUNT {
            let coefficients = solve_linear(self.gram, self.response[objective])?;
            mean[objective] = Some(dot(feature, &coefficients));
            let scale = response_scale(
                self.response_count[objective],
                self.response_sum[objective],
                self.response_sum_sq[objective],
                initial_uncertainty[objective],
            );
            uncertainty[objective] = Some(leverage * scale);
        }
        Some(Prediction { mean, uncertainty })
    }
}

#[derive(Clone, Debug)]
struct Prediction {
    mean: [Option<f64>; OBJECTIVE_COUNT],
    uncertainty: [Option<f64>; OBJECTIVE_COUNT],
}

struct PriorUpdateResult {
    audit: Option<PriorUpdateAudit>,
    renewal_triggered: bool,
}

struct SelectedAction {
    id: ActionId,
    mode: SelectionMode,
    propensity: f64,
    renewal_step_index: Option<usize>,
    renewal_completed: bool,
}

#[derive(Clone, Debug, Serialize)]
struct ControllerState {
    feature_scales: FeatureScales,
    renewal_config: RenewalConfig,
    next_epoch: u64,
    last_observation_sha256: Option<Hash256>,
    last_material_used: f64,
    optical_energy_spent: f64,
    electrical_energy_spent: f64,
    warmup_order: [ActionId; WARMUP_STEPS],
    warmup_index: usize,
    rng_state: u64,
    renewal_rng_state: u64,
    change_streak: usize,
    renewal_generation: u64,
    renewal_schedule: Vec<ActionId>,
    renewal_index: usize,
    upper_model: ArmModel,
    lower_model: ArmModel,
    pending: Option<PendingUpdate>,
    halted: bool,
}

pub struct Controller {
    config: ControllerConfig,
    state: ControllerState,
}

impl Controller {
    pub fn new(config: ControllerConfig) -> Result<Self, ValidationError> {
        config.validate()?;
        let mut rng = SplitMix64::new(config.seed);
        let mut warmup_order = [
            ActionId::UpperHeavy,
            ActionId::UpperHeavy,
            ActionId::LowerHeavy,
            ActionId::LowerHeavy,
        ];
        for index in (1..WARMUP_STEPS).rev() {
            let swap = (rng.next_u64() % (index as u64 + 1)) as usize;
            warmup_order.swap(index, swap);
        }
        Ok(Self {
            state: ControllerState {
                feature_scales: config.feature_scales.clone(),
                renewal_config: config.renewal.clone(),
                next_epoch: 0,
                last_observation_sha256: None,
                last_material_used: 0.0,
                optical_energy_spent: 0.0,
                electrical_energy_spent: 0.0,
                warmup_order,
                warmup_index: 0,
                rng_state: rng.state,
                renewal_rng_state: SplitMix64::new(config.renewal.seed).state,
                change_streak: 0,
                renewal_generation: 0,
                renewal_schedule: Vec::new(),
                renewal_index: 0,
                upper_model: ArmModel::new(config.ridge_lambda),
                lower_model: ArmModel::new(config.ridge_lambda),
                pending: None,
                halted: false,
            },
            config,
        })
    }

    pub fn step(&mut self, observation: &Observation) -> StepAudit {
        let state_before_hash = canonical_hash(&self.state)
            .expect("controller state contains only validated serializable values");
        let budgets_before = self.budget_snapshot(self.state.last_material_used);
        if self.state.halted {
            return self.fail_audit(
                observation.epoch,
                None,
                state_before_hash,
                budgets_before,
                FailReason::ControllerHalted,
            );
        }

        let observation_hash = match observation.canonical_hash() {
            Ok(hash) => Some(hash),
            Err(_) => {
                return self.halt_and_audit(
                    observation.epoch,
                    None,
                    state_before_hash,
                    budgets_before,
                    FailReason::SerializationFailure,
                );
            }
        };
        if let Err(reason) = self.validate_step_observation(observation) {
            return self.halt_and_audit(
                observation.epoch,
                observation_hash,
                state_before_hash,
                budgets_before,
                reason,
            );
        }
        let objective = match observation.objective(self.config.delivery_epsilon) {
            Ok(value) => value,
            Err(_) => {
                return self.halt_and_audit(
                    observation.epoch,
                    observation_hash,
                    state_before_hash,
                    budgets_before,
                    FailReason::InvalidObservation,
                );
            }
        };

        let prior = self.update_prior(&objective);
        let eligible_actions = if self.renewal_active() {
            vec![ActionId::UpperHeavy, ActionId::LowerHeavy]
        } else {
            self.safe_actions(observation, &objective)
        };
        let selection = match self.select_action(&eligible_actions, observation, &objective) {
            Some(selection) => selection,
            None => {
                return self.halt_and_audit_with_update(
                    observation.epoch,
                    observation_hash,
                    state_before_hash,
                    budgets_before,
                    prior.audit,
                    FailReason::NoSafeAction,
                );
            }
        };

        let renewal = self.renewal_audit(prior.renewal_triggered, Some(&selection));

        let action = self.active_action(
            selection.id,
            selection.mode,
            selection.propensity,
            observation_hash.clone().expect("validated hash"),
        );
        self.state.optical_energy_spent += self.config.budget.optical_cost_per_action;
        self.state.electrical_energy_spent += self.config.budget.electrical_cost_per_action;
        self.state.last_material_used = objective.material_used;
        self.state.last_observation_sha256 = observation_hash.clone();
        self.state.next_epoch += 1;
        self.state.pending = Some(PendingUpdate {
            action: selection.id,
            feature: observation.feature_vector(
                selection.id,
                self.config.delivery_epsilon,
                &self.config.feature_scales,
            ),
            objective_before: objective,
            renewal_action: selection.mode == SelectionMode::Renewal,
        });
        if selection.mode == SelectionMode::Warmup {
            self.state.warmup_index += 1;
        }
        let budgets_after = self.budget_snapshot(self.state.last_material_used);
        let state_after_hash = canonical_hash(&self.state)
            .expect("controller state contains only validated serializable values");
        StepAudit {
            schema: AUDIT_SCHEMA.into(),
            run_id: self.config.run_id.clone(),
            epoch: observation.epoch,
            observation_sha256: observation_hash,
            policy_state_before_sha256: state_before_hash,
            prior_update: prior.audit,
            renewal,
            eligible_actions,
            action,
            budgets_before,
            budgets_after,
            fail_reason: None,
            policy_state_after_sha256: state_after_hash,
        }
    }

    fn validate_step_observation(&self, observation: &Observation) -> Result<(), FailReason> {
        observation.validate().map_err(map_validation_error)?;
        if observation.run_id != self.config.run_id {
            return Err(FailReason::RunMismatch);
        }
        if observation.epoch != self.state.next_epoch {
            return Err(FailReason::StaleEpoch);
        }
        match (
            self.state.last_observation_sha256.as_ref(),
            observation.previous_observation_sha256.as_ref(),
        ) {
            (None, None) if observation.epoch == 0 => {}
            (Some(expected), Some(actual)) if expected == actual => {}
            (Some(_), None) => return Err(FailReason::MissingPreviousHash),
            _ => return Err(FailReason::PreviousHashMismatch),
        }
        if !approximately_equal(
            observation.global.cumulative_optical_energy,
            self.state.optical_energy_spent,
        ) || !approximately_equal(
            observation.global.cumulative_electrical_energy,
            self.state.electrical_energy_spent,
        ) {
            return Err(FailReason::EnergyCounterMismatch);
        }
        if observation.global.material_used + NUMERIC_TOLERANCE < self.state.last_material_used {
            return Err(FailReason::InvalidObservation);
        }
        if observation.global.material_used > self.config.safety.max_material_used {
            return Err(FailReason::MaterialBudgetExceeded);
        }
        if self.config.safety.require_mechanical_stress && !observation.channels.mechanical_stress {
            return Err(FailReason::MissingRequiredStress);
        }
        let objective = observation
            .objective(self.config.delivery_epsilon)
            .map_err(map_validation_error)?;
        if objective.current_per_delivery > self.config.safety.max_current_per_delivery
            || objective.heat_per_delivery_squared
                > self.config.safety.max_heat_per_delivery_squared
            || objective
                .mechanical_stress
                .zip(self.config.safety.max_mechanical_stress)
                .is_some_and(|(observed, limit)| observed > limit)
        {
            return Err(FailReason::ObservedSafetyLimit);
        }
        if self.state.optical_energy_spent + self.config.budget.optical_cost_per_action
            > self.config.budget.max_optical_energy + NUMERIC_TOLERANCE
        {
            return Err(FailReason::OpticalBudgetExceeded);
        }
        if self.state.electrical_energy_spent + self.config.budget.electrical_cost_per_action
            > self.config.budget.max_electrical_energy + NUMERIC_TOLERANCE
        {
            return Err(FailReason::ElectricalBudgetExceeded);
        }
        Ok(())
    }

    fn update_prior(&mut self, objective: &ObjectiveVector) -> PriorUpdateResult {
        let Some(pending) = self.state.pending.take() else {
            return PriorUpdateResult {
                audit: None,
                renewal_triggered: false,
            };
        };
        let delta = objective.delta_from(&pending.objective_before);
        let prediction = self
            .model(pending.action)
            .predict(&pending.feature, &self.config.initial_objective_uncertainty);
        let predicted_delta = prediction
            .as_ref()
            .map(|value| value.mean)
            .unwrap_or([None; OBJECTIVE_COUNT]);
        let mut residual = [None; OBJECTIVE_COUNT];
        let mut normalized_abs_residual = [None; OBJECTIVE_COUNT];
        let mut threshold_exceeded = [false; OBJECTIVE_COUNT];
        for index in 0..OBJECTIVE_COUNT {
            if let (Some(observed), Some(predicted)) = (delta[index], predicted_delta[index]) {
                let error = observed - predicted;
                let normalized = error.abs() / self.config.renewal.prediction_error_scales[index];
                residual[index] = Some(error);
                normalized_abs_residual[index] = Some(normalized);
                threshold_exceeded[index] =
                    normalized > self.config.renewal.prediction_error_thresholds[index];
            }
        }
        let any_threshold_exceeded = threshold_exceeded.iter().any(|value| *value);
        let detection_enabled = self.state.warmup_index >= WARMUP_STEPS
            && !pending.renewal_action
            && !self.renewal_active();
        let mut renewal_triggered = false;
        if detection_enabled {
            if any_threshold_exceeded {
                self.state.change_streak += 1;
            } else {
                self.state.change_streak = 0;
            }
            if self.state.change_streak >= self.config.renewal.consecutive_change_count {
                self.begin_renewal();
                self.state.change_streak = 0;
                renewal_triggered = true;
            }
        }
        let change_streak_after = self.state.change_streak;

        // Residual evidence above is intentionally computed against the model
        // that existed when the action was chosen. Only then may the outcome
        // update that arm.
        self.model_mut(pending.action)
            .update(&pending.feature, &delta);
        PriorUpdateResult {
            audit: Some(PriorUpdateAudit {
                action: pending.action,
                delta_objective: delta,
                predicted_delta,
                residual,
                normalized_abs_residual,
                threshold_exceeded,
                any_threshold_exceeded,
                change_streak_after,
                renewal_triggered,
                accepted: true,
            }),
            renewal_triggered,
        }
    }

    fn safe_actions(
        &self,
        observation: &Observation,
        objective: &ObjectiveVector,
    ) -> Vec<ActionId> {
        [ActionId::UpperHeavy, ActionId::LowerHeavy]
            .into_iter()
            .filter(|action| self.action_is_safe(observation, objective, *action))
            .collect()
    }

    fn action_is_safe(
        &self,
        observation: &Observation,
        objective: &ObjectiveVector,
        action: ActionId,
    ) -> bool {
        let feature = observation.feature_vector(
            action,
            self.config.delivery_epsilon,
            &self.config.feature_scales,
        );
        let Some(prediction) = self
            .model(action)
            .predict(&feature, &self.config.initial_objective_uncertainty)
        else {
            return false;
        };
        let upper = |index: usize, present: f64| {
            present
                + prediction.mean[index].unwrap_or(0.0)
                + self.config.confidence_multiplier
                    * prediction.uncertainty[index].unwrap_or(f64::INFINITY)
        };
        if upper(1, objective.current_per_delivery) > self.config.safety.max_current_per_delivery
            || upper(2, objective.heat_per_delivery_squared)
                > self.config.safety.max_heat_per_delivery_squared
            || upper(4, objective.material_used) > self.config.safety.max_material_used
        {
            return false;
        }
        if let (Some(stress), Some(limit)) = (
            objective.mechanical_stress,
            self.config.safety.max_mechanical_stress,
        ) && upper(3, stress) > limit
        {
            return false;
        }
        true
    }

    fn select_action(
        &mut self,
        eligible: &[ActionId],
        observation: &Observation,
        objective: &ObjectiveVector,
    ) -> Option<SelectedAction> {
        if self.renewal_active() {
            let step_index = self.state.renewal_index;
            let scheduled = self.state.renewal_schedule[step_index];
            if !eligible.contains(&scheduled) {
                return None;
            }
            let propensity = match self.config.renewal.action_order {
                RenewalActionOrder::UpperFirst | RenewalActionOrder::LowerFirst => 1.0,
                RenewalActionOrder::SeededBalanced => {
                    let remaining = &self.state.renewal_schedule[step_index..];
                    let same = remaining
                        .iter()
                        .filter(|&&action| action == scheduled)
                        .count();
                    same as f64 / remaining.len() as f64
                }
            };
            self.state.renewal_index += 1;
            let renewal_completed = self.state.renewal_index == self.state.renewal_schedule.len();
            if renewal_completed {
                self.state.renewal_schedule.clear();
                self.state.renewal_index = 0;
            }
            return Some(SelectedAction {
                id: scheduled,
                mode: SelectionMode::Renewal,
                propensity,
                renewal_step_index: Some(step_index),
                renewal_completed,
            });
        }
        if self.state.warmup_index < WARMUP_STEPS {
            let scheduled = self.state.warmup_order[self.state.warmup_index];
            if !eligible.contains(&scheduled) {
                return None;
            }
            let remaining = &self.state.warmup_order[self.state.warmup_index..];
            let same = remaining.iter().filter(|&&item| item == scheduled).count();
            return Some(SelectedAction {
                id: scheduled,
                mode: SelectionMode::Warmup,
                propensity: same as f64 / remaining.len() as f64,
                renewal_step_index: None,
                renewal_completed: false,
            });
        }
        if eligible.is_empty() {
            return None;
        }
        if eligible.len() == 1 {
            return Some(SelectedAction {
                id: eligible[0],
                mode: SelectionMode::Exploit,
                propensity: 1.0,
                renewal_step_index: None,
                renewal_completed: false,
            });
        }

        let greedy = self.greedy_action(eligible, observation, objective)?;
        let epsilon = self.config.exploration_probability;
        let mut rng = SplitMix64 {
            state: self.state.rng_state,
        };
        let explore = rng.unit() < epsilon;
        let chosen = if explore {
            eligible[(rng.next_u64() % eligible.len() as u64) as usize]
        } else {
            greedy
        };
        self.state.rng_state = rng.state;
        let random_share = epsilon / eligible.len() as f64;
        let propensity = if chosen == greedy {
            1.0 - epsilon + random_share
        } else {
            random_share
        };
        Some(SelectedAction {
            id: chosen,
            mode: if explore {
                SelectionMode::Explore
            } else {
                SelectionMode::Exploit
            },
            propensity,
            renewal_step_index: None,
            renewal_completed: false,
        })
    }

    fn renewal_active(&self) -> bool {
        self.state.renewal_index < self.state.renewal_schedule.len()
    }

    fn begin_renewal(&mut self) {
        let length = self.config.renewal.renewal_length;
        let mut schedule = Vec::with_capacity(length);
        match self.config.renewal.action_order {
            RenewalActionOrder::UpperFirst => {
                for index in 0..length {
                    schedule.push(if index % 2 == 0 {
                        ActionId::UpperHeavy
                    } else {
                        ActionId::LowerHeavy
                    });
                }
            }
            RenewalActionOrder::LowerFirst => {
                for index in 0..length {
                    schedule.push(if index % 2 == 0 {
                        ActionId::LowerHeavy
                    } else {
                        ActionId::UpperHeavy
                    });
                }
            }
            RenewalActionOrder::SeededBalanced => {
                let upper_count = (length as f64 * self.config.renewal.balanced_action_propensity)
                    .round() as usize;
                schedule.extend(std::iter::repeat_n(ActionId::UpperHeavy, upper_count));
                schedule.extend(std::iter::repeat_n(
                    ActionId::LowerHeavy,
                    length - upper_count,
                ));
                let mut rng = SplitMix64 {
                    state: self.state.renewal_rng_state,
                };
                for index in (1..length).rev() {
                    let swap = (rng.next_u64() % (index as u64 + 1)) as usize;
                    schedule.swap(index, swap);
                }
                self.state.renewal_rng_state = rng.state;
            }
        }
        self.state.renewal_schedule = schedule;
        self.state.renewal_index = 0;
        self.state.renewal_generation += 1;
    }

    fn renewal_audit(&self, triggered: bool, selection: Option<&SelectedAction>) -> RenewalAudit {
        let (mode, step_index, propensity) = match selection {
            Some(selected) if selected.mode == SelectionMode::Renewal => {
                let mode = if triggered {
                    RenewalMode::Triggered
                } else if selected.renewal_completed {
                    RenewalMode::Completed
                } else {
                    RenewalMode::Active
                };
                (mode, selected.renewal_step_index, Some(selected.propensity))
            }
            _ if self.renewal_active() => (RenewalMode::Active, None, None),
            _ => (RenewalMode::Inactive, None, None),
        };
        RenewalAudit {
            mode,
            triggered,
            generation: self.state.renewal_generation,
            change_streak: self.state.change_streak,
            required_consecutive_changes: self.config.renewal.consecutive_change_count,
            action_order: self.config.renewal.action_order,
            step_index,
            renewal_length: self.config.renewal.renewal_length,
            propensity,
        }
    }

    fn greedy_action(
        &self,
        eligible: &[ActionId],
        observation: &Observation,
        objective: &ObjectiveVector,
    ) -> Option<ActionId> {
        let mut best: Option<(ActionId, f64, f64)> = None;
        for action in eligible {
            let feature = observation.feature_vector(
                *action,
                self.config.delivery_epsilon,
                &self.config.feature_scales,
            );
            let prediction = self
                .model(*action)
                .predict(&feature, &self.config.initial_objective_uncertainty)?;
            let delivery_lcb = prediction.mean[0].unwrap_or(0.0)
                - self.config.confidence_multiplier
                    * prediction.uncertainty[0].unwrap_or(f64::INFINITY);
            let stress_score = normalized_stress_score(objective, &prediction, &self.config.safety);
            match best {
                None => best = Some((*action, delivery_lcb, stress_score)),
                Some((best_action, best_delivery, best_stress)) => {
                    let better_delivery =
                        delivery_lcb > best_delivery + self.config.delivery_tolerance;
                    let tied_delivery =
                        (delivery_lcb - best_delivery).abs() <= self.config.delivery_tolerance;
                    if better_delivery
                        || (tied_delivery && stress_score < best_stress)
                        || (tied_delivery
                            && approximately_equal(stress_score, best_stress)
                            && action_rank(*action) < action_rank(best_action))
                    {
                        best = Some((*action, delivery_lcb, stress_score));
                    }
                }
            }
        }
        best.map(|item| item.0)
    }

    fn active_action(
        &self,
        id: ActionId,
        selection_mode: SelectionMode,
        propensity: f64,
        observation_sha256: Hash256,
    ) -> Action {
        let (upper_fraction, lower_fraction) = match id {
            ActionId::UpperHeavy => (0.75, 0.25),
            ActionId::LowerHeavy => (0.25, 0.75),
            ActionId::Dark => unreachable!("dark action is fail-closed only"),
        };
        Action {
            schema: ACTION_SCHEMA.into(),
            id,
            upper_fraction,
            lower_fraction,
            optical_pulse_energy: self.config.budget.optical_cost_per_action,
            source_voltage: self.config.source_voltage,
            electrical_duty: self.config.electrical_duty,
            polarity: self.config.polarity,
            optical_energy_unit: UNIT_ENERGY.into(),
            voltage_unit: UNIT_VOLTAGE.into(),
            observation_sha256: Some(observation_sha256),
            selection_mode,
            propensity,
        }
    }

    fn dark_action(&self, observation_sha256: Option<Hash256>) -> Action {
        Action {
            schema: ACTION_SCHEMA.into(),
            id: ActionId::Dark,
            upper_fraction: 0.0,
            lower_fraction: 0.0,
            optical_pulse_energy: 0.0,
            source_voltage: 0.0,
            electrical_duty: 0.0,
            polarity: 0,
            optical_energy_unit: UNIT_ENERGY.into(),
            voltage_unit: UNIT_VOLTAGE.into(),
            observation_sha256,
            selection_mode: SelectionMode::FailClosed,
            propensity: 1.0,
        }
    }

    fn model(&self, action: ActionId) -> &ArmModel {
        match action {
            ActionId::UpperHeavy => &self.state.upper_model,
            ActionId::LowerHeavy => &self.state.lower_model,
            ActionId::Dark => unreachable!("dark action has no response model"),
        }
    }

    fn model_mut(&mut self, action: ActionId) -> &mut ArmModel {
        match action {
            ActionId::UpperHeavy => &mut self.state.upper_model,
            ActionId::LowerHeavy => &mut self.state.lower_model,
            ActionId::Dark => unreachable!("dark action has no response model"),
        }
    }

    fn budget_snapshot(&self, material_used: f64) -> BudgetSnapshot {
        BudgetSnapshot {
            material_used,
            optical_energy_spent: self.state.optical_energy_spent,
            electrical_energy_spent: self.state.electrical_energy_spent,
            max_material: self.config.safety.max_material_used,
            max_optical_energy: self.config.budget.max_optical_energy,
            max_electrical_energy: self.config.budget.max_electrical_energy,
        }
    }

    fn halt_and_audit(
        &mut self,
        epoch: u64,
        observation_hash: Option<Hash256>,
        state_before_hash: Hash256,
        budgets_before: BudgetSnapshot,
        reason: FailReason,
    ) -> StepAudit {
        self.halt_and_audit_with_update(
            epoch,
            observation_hash,
            state_before_hash,
            budgets_before,
            None,
            reason,
        )
    }

    fn halt_and_audit_with_update(
        &mut self,
        epoch: u64,
        observation_hash: Option<Hash256>,
        state_before_hash: Hash256,
        budgets_before: BudgetSnapshot,
        prior_update: Option<PriorUpdateAudit>,
        reason: FailReason,
    ) -> StepAudit {
        self.state.halted = true;
        let budgets_after = self.budget_snapshot(self.state.last_material_used);
        let state_after_hash = canonical_hash(&self.state)
            .expect("controller state contains only validated serializable values");
        StepAudit {
            schema: AUDIT_SCHEMA.into(),
            run_id: self.config.run_id.clone(),
            epoch,
            observation_sha256: observation_hash.clone(),
            policy_state_before_sha256: state_before_hash,
            prior_update,
            renewal: self.renewal_audit(false, None),
            eligible_actions: Vec::new(),
            action: self.dark_action(observation_hash),
            budgets_before,
            budgets_after,
            fail_reason: Some(reason),
            policy_state_after_sha256: state_after_hash,
        }
    }

    fn fail_audit(
        &self,
        epoch: u64,
        observation_hash: Option<Hash256>,
        state_before_hash: Hash256,
        budgets_before: BudgetSnapshot,
        reason: FailReason,
    ) -> StepAudit {
        StepAudit {
            schema: AUDIT_SCHEMA.into(),
            run_id: self.config.run_id.clone(),
            epoch,
            observation_sha256: observation_hash.clone(),
            policy_state_before_sha256: state_before_hash.clone(),
            prior_update: None,
            renewal: self.renewal_audit(false, None),
            eligible_actions: Vec::new(),
            action: self.dark_action(observation_hash),
            budgets_after: budgets_before.clone(),
            budgets_before,
            fail_reason: Some(reason),
            policy_state_after_sha256: state_before_hash,
        }
    }
}

#[derive(Clone, Copy)]
struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9e3779b97f4a7c15);
        let mut value = self.state;
        value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);
        value ^ (value >> 31)
    }

    fn unit(&mut self) -> f64 {
        let bits = self.next_u64() >> 11;
        bits as f64 / (1_u64 << 53) as f64
    }
}

fn response_scale(count: u64, sum: f64, sum_sq: f64, initial: f64) -> f64 {
    if count < 2 {
        return initial;
    }
    let variance = ((sum_sq - sum * sum / count as f64) / (count - 1) as f64).max(0.0);
    variance.sqrt().max(initial)
}

fn normalized_stress_score(
    present: &ObjectiveVector,
    prediction: &Prediction,
    limits: &SafetyLimits,
) -> f64 {
    let mut score = (present.current_per_delivery + prediction.mean[1].unwrap_or(0.0))
        / limits.max_current_per_delivery.max(NUMERIC_TOLERANCE);
    score = score.max(
        (present.heat_per_delivery_squared + prediction.mean[2].unwrap_or(0.0))
            / limits.max_heat_per_delivery_squared.max(NUMERIC_TOLERANCE),
    );
    if let (Some(stress), Some(limit)) = (present.mechanical_stress, limits.max_mechanical_stress) {
        score =
            score.max((stress + prediction.mean[3].unwrap_or(0.0)) / limit.max(NUMERIC_TOLERANCE));
    }
    score
}

fn action_rank(action: ActionId) -> usize {
    match action {
        ActionId::UpperHeavy => 0,
        ActionId::LowerHeavy => 1,
        ActionId::Dark => 2,
    }
}

fn solve_linear(
    matrix: [[f64; FEATURE_COUNT]; FEATURE_COUNT],
    vector: [f64; FEATURE_COUNT],
) -> Option<[f64; FEATURE_COUNT]> {
    let mut augmented = [[0.0; FEATURE_COUNT + 1]; FEATURE_COUNT];
    for row in 0..FEATURE_COUNT {
        for column in 0..FEATURE_COUNT {
            augmented[row][column] = matrix[row][column];
        }
        augmented[row][FEATURE_COUNT] = vector[row];
    }
    for column in 0..FEATURE_COUNT {
        let pivot = (column..FEATURE_COUNT).max_by(|left, right| {
            augmented[*left][column]
                .abs()
                .total_cmp(&augmented[*right][column].abs())
        })?;
        if augmented[pivot][column].abs() <= 1.0e-15 {
            return None;
        }
        augmented.swap(column, pivot);
        let divisor = augmented[column][column];
        for entry in column..=FEATURE_COUNT {
            augmented[column][entry] /= divisor;
        }
        for row in 0..FEATURE_COUNT {
            if row == column {
                continue;
            }
            let factor = augmented[row][column];
            for entry in column..=FEATURE_COUNT {
                augmented[row][entry] -= factor * augmented[column][entry];
            }
        }
    }
    let mut solution = [0.0; FEATURE_COUNT];
    for index in 0..FEATURE_COUNT {
        solution[index] = augmented[index][FEATURE_COUNT];
    }
    Some(solution)
}

fn dot(left: &[f64; FEATURE_COUNT], right: &[f64; FEATURE_COUNT]) -> f64 {
    left.iter().zip(right).map(|(a, b)| a * b).sum()
}

fn approximately_equal(left: f64, right: f64) -> bool {
    let scale = left.abs().max(right.abs()).max(1.0);
    (left - right).abs() <= NUMERIC_TOLERANCE * scale
}

fn canonical_json<T: Serialize>(value: &T) -> Result<String, SerializationError> {
    serde_json::to_string(value).map_err(SerializationError)
}

fn canonical_hash<T: Serialize>(value: &T) -> Result<Hash256, SerializationError> {
    let serialized = canonical_json(value)?;
    let digest = Sha256::digest(serialized.as_bytes());
    let mut encoded = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write as _;
        write!(&mut encoded, "{byte:02x}").expect("writing to String cannot fail");
    }
    Ok(Hash256(encoded))
}

fn map_validation_error(error: ValidationError) -> FailReason {
    match error {
        ValidationError::SchemaMismatch => FailReason::SchemaMismatch,
        ValidationError::RunMismatch => FailReason::RunMismatch,
        ValidationError::InvalidHash => FailReason::InvalidHash,
        ValidationError::InvalidUnits => FailReason::InvalidUnits,
        ValidationError::ChannelMaskMismatch => FailReason::ChannelMaskMismatch,
        ValidationError::InvalidNumericValue
        | ValidationError::DeliveryTooSmall
        | ValidationError::InvalidAction
        | ValidationError::InvalidConfiguration => FailReason::InvalidObservation,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hash(character: char) -> Hash256 {
        Hash256(std::iter::repeat_n(character, 64).collect())
    }

    fn fixture_config(seed: u64) -> ControllerConfig {
        ControllerConfig {
            run_id: "candidate-test".into(),
            seed,
            exploration_probability: 0.10,
            ridge_lambda: 1.0,
            confidence_multiplier: 0.0,
            initial_objective_uncertainty: [0.01; OBJECTIVE_COUNT],
            feature_scales: FeatureScales {
                delivery: 1.0,
                current_per_delivery: 1.0,
                heat_per_delivery_squared: 1.0,
                mean_current_density: 1.0,
                p95_current_density: 1.0,
                mean_joule_density: 1.0,
                interface_contrast: 1.0,
            },
            renewal: RenewalConfig {
                prediction_error_scales: [1.0; OBJECTIVE_COUNT],
                prediction_error_thresholds: [10.0; OBJECTIVE_COUNT],
                consecutive_change_count: 2,
                renewal_length: 4,
                action_order: RenewalActionOrder::SeededBalanced,
                balanced_action_propensity: 0.5,
                seed: 7_319,
            },
            delivery_tolerance: 1.0e-9,
            delivery_epsilon: 1.0e-12,
            source_voltage: 1.0,
            electrical_duty: 1.0,
            polarity: 1,
            safety: SafetyLimits {
                max_current_per_delivery: 1.0,
                max_heat_per_delivery_squared: 1.0,
                max_mechanical_stress: None,
                max_material_used: 1.0,
                require_mechanical_stress: false,
            },
            budget: EnergyBudget {
                max_optical_energy: 20.0,
                max_electrical_energy: 20.0,
                optical_cost_per_action: 1.0,
                electrical_cost_per_action: 0.5,
            },
        }
    }

    fn fixture_observation(
        epoch: u64,
        previous: Option<Hash256>,
        optical_energy: f64,
        electrical_energy: f64,
    ) -> Observation {
        let footprint = FootprintObservation {
            mean_current_density: 0.10,
            p95_current_density: 0.20,
            mean_joule_density: 0.05,
            p95_joule_density: 0.10,
            conductive_fraction: 0.20,
            interface_fraction: 0.10,
            mean_available_reservoir: None,
            mean_temperature: None,
            p95_temperature: None,
            mean_mechanical_stress: None,
            p95_mechanical_stress: None,
        };
        Observation {
            schema: OBSERVATION_SCHEMA.into(),
            run_id: "candidate-test".into(),
            epoch,
            previous_observation_sha256: previous,
            topology_sha256: hash('a'),
            moose_sha256: hash('b'),
            units: UnitStrings::pending_si(),
            channels: ChannelAvailability {
                material_reservoir: false,
                temperature: false,
                mechanical_stress: false,
            },
            footprints: [footprint.clone(), footprint],
            global: GlobalObservation {
                terminal_flux: 1.0,
                metal_fraction: 0.10,
                joule_integral: 0.10,
                peak_current_density: 0.20,
                peak_joule_density: 0.10,
                peak_mechanical_stress: None,
                material_used: 0.10,
                cumulative_optical_energy: optical_energy,
                cumulative_electrical_energy: electrical_energy,
            },
        }
    }

    #[test]
    fn rejects_coordinate_leakage_as_unknown_input() {
        let observation = fixture_observation(0, None, 0.0, 0.0);
        let mut value = serde_json::to_value(observation).unwrap();
        value
            .as_object_mut()
            .unwrap()
            .insert("route_x".into(), serde_json::json!(0.5));
        let encoded = serde_json::to_string(&value).unwrap();
        assert!(matches!(
            parse_observation_strict(&encoded),
            Err(ParseError::Json(_))
        ));
    }

    #[test]
    fn rejects_unknown_feature_scale_fields() {
        let mut value = serde_json::to_value(fixture_config(319)).unwrap();
        value["feature_scales"]
            .as_object_mut()
            .unwrap()
            .insert("route_coordinate_scale".into(), serde_json::json!(1.0));
        assert!(serde_json::from_value::<ControllerConfig>(value).is_err());
    }

    #[test]
    fn rejects_zero_and_nonfinite_feature_scales() {
        for invalid in [0.0, -1.0, f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
            let mut config = fixture_config(319);
            config.feature_scales.delivery = invalid;
            assert_eq!(
                Controller::new(config).err(),
                Some(ValidationError::InvalidConfiguration)
            );
        }
    }

    #[test]
    fn rejects_invalid_renewal_configuration() {
        let mut invalid_configs = Vec::new();

        let mut zero_scale = fixture_config(319);
        zero_scale.renewal.prediction_error_scales[0] = 0.0;
        invalid_configs.push(zero_scale);

        let mut nonfinite_threshold = fixture_config(319);
        nonfinite_threshold.renewal.prediction_error_thresholds[0] = f64::NAN;
        invalid_configs.push(nonfinite_threshold);

        let mut no_persistence = fixture_config(319);
        no_persistence.renewal.consecutive_change_count = 0;
        invalid_configs.push(no_persistence);

        let mut unbalanced_length = fixture_config(319);
        unbalanced_length.renewal.renewal_length = 3;
        invalid_configs.push(unbalanced_length);

        let mut biased_propensity = fixture_config(319);
        biased_propensity.renewal.balanced_action_propensity = 0.60;
        invalid_configs.push(biased_propensity);

        for config in invalid_configs {
            assert_eq!(
                Controller::new(config).err(),
                Some(ValidationError::InvalidConfiguration)
            );
        }
    }

    #[test]
    fn feature_scales_are_part_of_the_hashed_policy_state() {
        let mut first_config = fixture_config(319);
        first_config.feature_scales.delivery = 1.0;
        let mut second_config = first_config.clone();
        second_config.feature_scales.delivery = 2.0;
        let observation = fixture_observation(0, None, 0.0, 0.0);
        let first = Controller::new(first_config).unwrap().step(&observation);
        let second = Controller::new(second_config).unwrap().step(&observation);
        assert_ne!(
            first.policy_state_before_sha256,
            second.policy_state_before_sha256
        );
    }

    #[test]
    fn scaled_realistic_magnitudes_admit_balanced_finite_limit_warmup() {
        let mut config = fixture_config(319);
        config.confidence_multiplier = 2.0;
        config.initial_objective_uncertainty = [0.001, 5.0, 500.0, 0.0, 0.001, 0.0, 0.0];
        config.feature_scales = FeatureScales {
            delivery: 0.01,
            current_per_delivery: 300.0,
            heat_per_delivery_squared: 100_000.0,
            mean_current_density: 1.0,
            p95_current_density: 2.0,
            mean_joule_density: 1.0,
            interface_contrast: 0.10,
        };
        config.safety.max_current_per_delivery = 350.0;
        config.safety.max_heat_per_delivery_squared = 80_000.0;
        config.safety.max_material_used = 0.20;

        let mut controller = Controller::new(config).unwrap();
        let mut previous = None;
        let mut upper = 0;
        let mut lower = 0;
        for epoch in 0..4 {
            let mut observation =
                fixture_observation(epoch, previous.clone(), epoch as f64, epoch as f64 * 0.5);
            observation.global.terminal_flux = 0.004_335_430_362_330_3;
            observation.global.peak_current_density = 1.177_017_376_987_4;
            observation.global.peak_joule_density = 1.385_369_905_730_3;
            observation.global.metal_fraction = 0.088_568_793_402_773;
            observation.global.material_used = 0.088_568_793_402_773;
            observation.footprints[0].mean_current_density = 0.020;
            observation.footprints[0].p95_current_density = 1.10;
            observation.footprints[0].mean_joule_density = 0.020;
            observation.footprints[0].p95_joule_density = 1.30;
            observation.footprints[0].interface_fraction = 0.040;
            observation.footprints[1].mean_current_density = 0.018;
            observation.footprints[1].p95_current_density = 1.00;
            observation.footprints[1].mean_joule_density = 0.018;
            observation.footprints[1].p95_joule_density = 1.20;
            observation.footprints[1].interface_fraction = 0.020;
            previous = Some(observation.canonical_hash().unwrap());

            let audit = controller.step(&observation);
            assert_eq!(audit.fail_reason, None);
            assert_eq!(audit.action.selection_mode, SelectionMode::Warmup);
            match audit.action.id {
                ActionId::UpperHeavy => upper += 1,
                ActionId::LowerHeavy => lower += 1,
                ActionId::Dark => panic!("warmup failed closed"),
            }
        }
        assert_eq!((upper, lower), (2, 2));
    }

    #[test]
    fn stable_consequences_remain_exploitative_without_renewal() {
        let mut config = fixture_config(319);
        config.exploration_probability = f64::MIN_POSITIVE;
        config.renewal.prediction_error_thresholds = [0.25; OBJECTIVE_COUNT];
        let mut controller = Controller::new(config).unwrap();
        let mut previous = None;

        for epoch in 0..8 {
            let observation =
                fixture_observation(epoch, previous.clone(), epoch as f64, epoch as f64 * 0.5);
            previous = Some(observation.canonical_hash().unwrap());
            let audit = controller.step(&observation);
            assert_eq!(audit.fail_reason, None);
            assert!(!audit.renewal.triggered);
            assert_eq!(audit.renewal.mode, RenewalMode::Inactive);
            if epoch >= WARMUP_STEPS as u64 {
                assert_eq!(audit.action.selection_mode, SelectionMode::Exploit);
            }
        }
    }

    #[test]
    fn persistent_reversed_consequence_triggers_balanced_renewal() {
        let mut config = fixture_config(319);
        config.exploration_probability = f64::MIN_POSITIVE;
        config.renewal.prediction_error_scales = [1.0; OBJECTIVE_COUNT];
        config.renewal.prediction_error_thresholds = [1.0e12; OBJECTIVE_COUNT];
        config.renewal.prediction_error_thresholds[0] = 0.5;
        config.renewal.consecutive_change_count = 2;
        config.renewal.renewal_length = 4;
        config.renewal.action_order = RenewalActionOrder::SeededBalanced;
        let mut controller = Controller::new(config).unwrap();
        let mut previous = None;
        let mut renewal_actions = Vec::new();
        let mut trigger_seen = false;

        for epoch in 0..10 {
            let mut observation =
                fixture_observation(epoch, previous.clone(), epoch as f64, epoch as f64 * 0.5);
            observation.global.terminal_flux = match epoch {
                5 => 3.0,
                _ => 1.0,
            };
            previous = Some(observation.canonical_hash().unwrap());
            let audit = controller.step(&observation);
            assert_eq!(audit.fail_reason, None);

            if audit.renewal.triggered {
                trigger_seen = true;
                assert_eq!(audit.renewal.mode, RenewalMode::Triggered);
                let evidence = audit.prior_update.as_ref().unwrap();
                assert!(evidence.renewal_triggered);
                assert!(evidence.any_threshold_exceeded);
                assert!(evidence.normalized_abs_residual[0].unwrap() > 0.5);
                assert_ne!(
                    audit.policy_state_before_sha256,
                    audit.policy_state_after_sha256
                );
            }
            if audit.action.selection_mode == SelectionMode::Renewal {
                assert_eq!(
                    audit.eligible_actions,
                    vec![ActionId::UpperHeavy, ActionId::LowerHeavy]
                );
                assert!(audit.action.propensity > 0.0);
                assert_eq!(audit.renewal.propensity, Some(audit.action.propensity));
                renewal_actions.push(audit.action.id);
            }
        }

        assert!(trigger_seen);
        assert_eq!(renewal_actions.len(), 4);
        assert_eq!(
            renewal_actions
                .iter()
                .filter(|&&action| action == ActionId::UpperHeavy)
                .count(),
            2
        );
        assert_eq!(
            renewal_actions
                .iter()
                .filter(|&&action| action == ActionId::LowerHeavy)
                .count(),
            2
        );
    }

    #[test]
    fn fails_closed_before_spending_beyond_budget() {
        let mut config = fixture_config(7);
        config.budget.max_optical_energy = 0.5;
        let mut controller = Controller::new(config).unwrap();
        let audit = controller.step(&fixture_observation(0, None, 0.0, 0.0));
        assert_eq!(audit.fail_reason, Some(FailReason::OpticalBudgetExceeded));
        assert_eq!(audit.action.id, ActionId::Dark);
        assert_eq!(audit.budgets_after.optical_energy_spent, 0.0);
    }

    #[test]
    fn same_seed_and_inputs_are_byte_reproducible() {
        let config = fixture_config(319);
        let mut first = Controller::new(config.clone()).unwrap();
        let mut second = Controller::new(config).unwrap();
        let observation = fixture_observation(0, None, 0.0, 0.0);
        let first_audit = first.step(&observation).canonical_json().unwrap();
        let second_audit = second.step(&observation).canonical_json().unwrap();
        assert_eq!(first_audit, second_audit);
    }

    #[test]
    fn warmup_and_adaptive_actions_have_nonzero_propensity() {
        let mut controller = Controller::new(fixture_config(319)).unwrap();
        let mut previous = None;
        for epoch in 0..6 {
            let observation =
                fixture_observation(epoch, previous.clone(), epoch as f64, epoch as f64 * 0.5);
            previous = Some(observation.canonical_hash().unwrap());
            let audit = controller.step(&observation);
            assert_eq!(audit.fail_reason, None);
            assert!(audit.action.propensity > 0.0);
            assert!(audit.action.propensity <= 1.0);
        }
    }

    #[test]
    fn stale_or_mismatched_hash_chain_fails_closed() {
        let mut controller = Controller::new(fixture_config(11)).unwrap();
        let first = fixture_observation(0, None, 0.0, 0.0);
        assert_eq!(controller.step(&first).fail_reason, None);
        let second = fixture_observation(1, Some(hash('c')), 1.0, 0.5);
        let audit = controller.step(&second);
        assert_eq!(audit.fail_reason, Some(FailReason::PreviousHashMismatch));
        assert_eq!(audit.action.id, ActionId::Dark);
    }
}
