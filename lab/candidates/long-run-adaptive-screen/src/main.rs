use adaptive_controller_candidate::{
    ActionId, ChannelAvailability, Controller, ControllerConfig, EnergyBudget, FeatureScales,
    FootprintObservation, GlobalObservation, Hash256, OBSERVATION_SCHEMA, Observation,
    PriorUpdateAudit, RenewalActionOrder, RenewalAudit, RenewalConfig, SafetyLimits, SelectionMode,
    UnitStrings,
};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufWriter, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

const EVIDENCE_CLASS: &str = "screening-only";
const GRID_W: usize = 16;
const GRID_H: usize = 8;
const CELLS: usize = GRID_W * GRID_H;
const DEFAULT_ACTIONS: usize = 120;
const DEFAULT_SUBSTRATES: usize = 120;
const DEFAULT_ENVIRONMENTS: usize = 120;
const DEFAULT_PULSE_CREDITS_PER_TRAJECTORY: u64 = 60;
const CHECKPOINT_SCHEMA: &str = "long-run-adaptive-screen-checkpoint/v1";
const RECORD_SCHEMA: &str = "long-run-adaptive-screen-choice/v1";
const STATUS_SCHEMA: &str = "long-run-adaptive-screen-status/v1";
const SUMMARY_SCHEMA: &str = "long-run-adaptive-screen-summary/v1";
const DRAW_SCHEMA: &str = "long-run-adaptive-screen-environment/v1";
const RUN_SCHEMA: &str = "long-run-adaptive-screen-run/v1";
const BASE_OPTICAL_COST: f64 = 1.0;
const BASE_ELECTRICAL_COST: f64 = 0.5;

static TERMINATE_REQUESTED: AtomicBool = AtomicBool::new(false);

extern "C" fn handle_sigterm(_: libc::c_int) {
    TERMINATE_REQUESTED.store(true, Ordering::SeqCst);
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ScientificConfig {
    actions: usize,
    substrate_count: usize,
    environment_count: usize,
    master_seed: u64,
    checkpoint_every_trajectories: usize,
    pulse_credits_per_trajectory: u64,
    initial_pulse_reservoir: u64,
    earth_manifest_sha256: String,
    space_manifest_sha256: String,
    sampling_policy_sha256: String,
}

impl ScientificConfig {
    fn choices_total(&self) -> u64 {
        self.actions as u64 * self.substrate_count as u64 * self.environment_count as u64
    }

    fn trajectories_total(&self) -> usize {
        self.substrate_count * self.environment_count
    }
}

#[derive(Clone, Debug)]
struct Cli {
    command: Command,
}

#[derive(Clone, Debug)]
enum Command {
    Run(RunArgs),
    Status { runtime: PathBuf },
}

#[derive(Clone, Debug)]
struct RunArgs {
    output: PathBuf,
    runtime: PathBuf,
    actions: usize,
    substrate_count: usize,
    environment_count: usize,
    master_seed: u64,
    checkpoint_every: usize,
    pulse_credits_per_trajectory: u64,
    nice: i32,
    resume: bool,
    earth_manifest: PathBuf,
    space_manifest: PathBuf,
    sampling_policy: PathBuf,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct SourceDocument {
    path: PathBuf,
    bytes: Vec<u8>,
    sha256: String,
    value: Value,
}

#[derive(Clone, Debug)]
struct Sources {
    earth: SourceDocument,
    space: SourceDocument,
    policy: SourceDocument,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
enum Regime {
    EarthPedotExploratory,
    SpaceCbramScreening,
}

impl Regime {
    fn short(&self) -> &'static str {
        match self {
            Self::EarthPedotExploratory => "earth",
            Self::SpaceCbramScreening => "space",
        }
    }

    fn mode(&self) -> &'static str {
        match self {
            Self::EarthPedotExploratory => "exploratory",
            Self::SpaceCbramScreening => "screening",
        }
    }

    fn candidate_id(&self) -> &'static str {
        match self {
            Self::EarthPedotExploratory => "earth-pedot",
            Self::SpaceCbramScreening => "space-cbram",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
enum ContingencyKind {
    SwapChannelConsequences,
    DegradeUpperConsequence,
    UpperHeatCoupling,
    ShiftReservoirLower,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
struct EnvironmentDraw {
    schema: String,
    evidence_class: String,
    index: usize,
    seed: u64,
    regime: Regime,
    mode: String,
    candidate_id: String,
    source_manifest_sha256: String,
    sampling_policy_sha256: String,
    sampled_parameters: BTreeMap<String, SampledParameter>,
    selected_options: BTreeMap<String, String>,
    required_unset_blockers: Vec<String>,
    static_rejections: Vec<Value>,
    contingency_epoch: usize,
    contingency_kind: ContingencyKind,
    contingency_severity: f64,
    interpretation_boundary: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
struct SampledParameter {
    value: f64,
    unit: String,
    source_status: String,
    allowable_minimum: f64,
    allowable_maximum: f64,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
struct PulseLedger {
    initial: u64,
    remaining: u64,
    earned: u64,
    spent: u64,
    outstanding: u64,
}

impl PulseLedger {
    fn new(initial: u64) -> Self {
        Self {
            initial,
            remaining: initial,
            earned: 0,
            spent: 0,
            outstanding: 0,
        }
    }

    fn earn(&mut self, account: &mut u64) -> u64 {
        if self.remaining == 0 {
            return 0;
        }
        self.remaining -= 1;
        self.earned += 1;
        self.outstanding += 1;
        *account += 1;
        1
    }

    fn spend(&mut self, account: &mut u64) -> u64 {
        if *account == 0 {
            return 0;
        }
        *account -= 1;
        self.spent += 1;
        self.outstanding -= 1;
        1
    }

    fn conserved(&self) -> bool {
        self.initial == self.remaining + self.spent + self.outstanding
            && self.earned == self.spent + self.outstanding
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct Substrate {
    conductance: Vec<f64>,
    field: Vec<f64>,
    concentration: Vec<f64>,
    local_reservoir: Vec<f64>,
    heat: Vec<f64>,
    material_initial: f64,
    material_remaining: f64,
    optical_energy: f64,
    electrical_energy: f64,
    rng_state: u64,
    reservoir_shift_applied: bool,
}

#[derive(Clone, Copy, Debug)]
struct Metrics {
    delivery: f64,
    current_per_delivery: f64,
    heat_per_delivery_squared: f64,
    material_used: f64,
    concentration_proxy: f64,
    heat_proxy: f64,
    mechanical_stress_proxy: f64,
    service: f64,
    safe: bool,
    upper: FootMetrics,
    lower: FootMetrics,
}

#[derive(Clone, Copy, Debug)]
struct FootMetrics {
    mean_current: f64,
    p95_current: f64,
    mean_heat: f64,
    p95_heat: f64,
    conductive_fraction: f64,
    interface_fraction: f64,
    mean_reservoir: f64,
    mean_temperature: f64,
    p95_temperature: f64,
    mean_stress: f64,
    p95_stress: f64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct ChoiceRecord {
    schema: String,
    evidence_class: String,
    choice_index: u64,
    trajectory_index: usize,
    environment_index: usize,
    substrate_index: usize,
    environment_seed: u64,
    substrate_seed: u64,
    regime: Regime,
    epoch: usize,
    observation_sha256: String,
    policy_state_before_sha256: String,
    policy_state_after_sha256: String,
    action: ActionId,
    selection_mode: SelectionMode,
    propensity: f64,
    eligible_actions: Vec<ActionId>,
    controller_prior_update: Option<PriorUpdateAudit>,
    controller_renewal: RenewalAudit,
    renewal_triggered: bool,
    renewal_generation: u64,
    contingency_active: bool,
    contingency_kind: ContingencyKind,
    delivery: f64,
    current_concentration_proxy: f64,
    heat_proxy: f64,
    material_used: f64,
    material_remaining: f64,
    optical_energy_charged: f64,
    electrical_energy_charged: f64,
    service: f64,
    safe_useful_service_delta: f64,
    safe: bool,
    pulse_earned: u64,
    pulse_spent: u64,
    pulse_account_after: u64,
    pulse_trajectory_quota: u64,
    pulse_trajectory_earned: u64,
    pulse_global_initial: u64,
    pulse_global_earned: u64,
    pulse_global_spent: u64,
    pulse_global_outstanding: u64,
    pulse_global_remaining: u64,
    pulse_conserved: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct TrajectoryResult {
    trajectory_index: usize,
    environment_index: usize,
    substrate_index: usize,
    regime: Regime,
    final_delivery: f64,
    final_service: f64,
    final_current_concentration_proxy: f64,
    final_heat_proxy: f64,
    material_used: f64,
    upper_actions: u64,
    lower_actions: u64,
    renewal_actions: u64,
    renewal_triggers: u64,
    pulse_earned: u64,
    pulse_spent: u64,
    pulse_outstanding: u64,
    safe_choices: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct Checkpoint {
    schema: String,
    evidence_class: String,
    config: ScientificConfig,
    next_trajectory: usize,
    choices_completed: u64,
    audit_bytes: u64,
    elapsed_ns: u128,
    pulse: PulseLedger,
    trajectories: Vec<TrajectoryResult>,
}

#[derive(Clone, Debug, Serialize)]
struct Status<'a> {
    schema: &'static str,
    evidence_class: &'static str,
    state: &'a str,
    choices_completed: u64,
    choices_total: u64,
    trajectories_completed: usize,
    trajectories_total: usize,
    fraction_complete: f64,
    elapsed_seconds: f64,
    choices_per_second: f64,
    estimated_seconds_remaining: Option<f64>,
    pulse: PulseLedger,
    checkpoint: String,
    audit_log: String,
    message: &'a str,
}

#[derive(Clone, Debug, Serialize)]
struct Quantiles {
    minimum: f64,
    p05: f64,
    p25: f64,
    p50: f64,
    p75: f64,
    p95: f64,
    maximum: f64,
}

#[derive(Clone, Debug, Serialize)]
struct Summary<'a> {
    schema: &'static str,
    evidence_class: &'static str,
    state: &'a str,
    choices_completed: u64,
    choices_total: u64,
    trajectories_completed: usize,
    trajectories_total: usize,
    elapsed_seconds: f64,
    pulse: PulseLedger,
    pulse_conservation_proven: bool,
    final_delivery: Quantiles,
    final_service: Quantiles,
    final_current_concentration_proxy: Quantiles,
    final_heat_proxy: Quantiles,
    material_used: Quantiles,
    earth_trajectories: usize,
    space_trajectories: usize,
    renewal_triggers: u64,
    interpretation_boundary: &'static str,
}

#[derive(Clone, Copy)]
struct Rng64 {
    state: u64,
}

impl Rng64 {
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

    fn range(&mut self, minimum: f64, maximum: f64) -> f64 {
        minimum + self.unit() * (maximum - minimum)
    }

    fn index(&mut self, length: usize) -> usize {
        (self.next_u64() % length as u64) as usize
    }
}

impl Substrate {
    fn new(seed: u64, environment: &EnvironmentDraw) -> Self {
        let mut rng = Rng64::new(seed);
        let regime_scale = match environment.regime {
            Regime::EarthPedotExploratory => 1.0,
            Regime::SpaceCbramScreening => 0.72,
        };
        let mut conductance = vec![0.012; CELLS];
        let mut local_reservoir = vec![1.0 / CELLS as f64; CELLS];
        let mut concentration = vec![0.82; CELLS];
        for y in GRID_H / 2 - 1..=GRID_H / 2 {
            for x in 0..=1 {
                let i = idx(x, y);
                conductance[i] = 0.42 + 0.04 * rng.unit();
                concentration[i] *= 0.8;
                local_reservoir[i] *= 0.8;
            }
        }
        let initial = regime_scale;
        for value in &mut local_reservoir {
            *value *= initial;
        }
        Self {
            conductance,
            field: vec![0.0; CELLS],
            concentration,
            local_reservoir,
            heat: vec![0.0; CELLS],
            material_initial: initial,
            material_remaining: initial,
            optical_energy: 0.0,
            electrical_energy: 0.0,
            rng_state: rng.state,
            reservoir_shift_applied: false,
        }
    }

    fn update_field(&mut self, environment: &EnvironmentDraw) {
        let drive = drive_scale(environment);
        let previous = self.field.clone();
        for y in 0..GRID_H {
            for x in 0..GRID_W {
                let i = idx(x, y);
                let base = drive / (GRID_W - 1) as f64;
                let neighbor_mean = neighbor_values(&self.conductance, x, y).0;
                let local_focus = 1.0 + 1.8 * (neighbor_mean - self.conductance[i]).max(-0.35);
                let source_sink = 0.82 + 0.36 * (x as f64 / (GRID_W - 1) as f64);
                self.field[i] =
                    (0.55 * previous[i] + 0.45 * base * local_focus * source_sink).max(1.0e-6);
            }
        }
    }

    fn apply_action(
        &mut self,
        action: ActionId,
        pulse_spent: u64,
        epoch: usize,
        environment: &EnvironmentDraw,
    ) {
        self.optical_energy += BASE_OPTICAL_COST;
        self.electrical_energy += BASE_ELECTRICAL_COST;
        self.update_field(environment);
        self.apply_contingency_once(epoch, environment);

        let mut rng = Rng64 {
            state: self.rng_state,
        };
        if self.material_remaining > 1.0e-12 {
            let first = self.choose_growth_site(action, epoch, environment, &mut rng);
            // A spent dimensionless credit permits one more candidate to be
            // considered, not another deposition. Exactly one optical action is
            // charged above and at most one finite-reservoir increment occurs.
            let second = (pulse_spent > 0)
                .then(|| self.choose_growth_site(action, epoch, environment, &mut rng))
                .flatten();
            let chosen = match (first, second) {
                (Some(left), Some(right)) => {
                    if self.opportunity_score(right) > self.opportunity_score(left) {
                        Some(right)
                    } else {
                        Some(left)
                    }
                }
                (Some(value), None) | (None, Some(value)) => Some(value),
                (None, None) => None,
            };
            if let Some(chosen) = chosen {
                let available = self.local_reservoir[chosen].min(self.material_remaining);
                let deposit =
                    0.0015 + 0.0028 * self.field[chosen] + 0.0010 * self.concentration[chosen];
                let deposit = deposit.min(available).max(0.0);
                self.local_reservoir[chosen] -= deposit;
                self.material_remaining -= deposit;
                self.conductance[chosen] = (self.conductance[chosen] + 12.0 * deposit).min(1.0);
                self.concentration[chosen] = (self.concentration[chosen] - 8.0 * deposit).max(0.0);
            }
        }

        let heat_multiplier = contingency_heat_multiplier(action, epoch, environment);
        let old_concentration = self.concentration.clone();
        let old_heat = self.heat.clone();
        for y in 0..GRID_H {
            for x in 0..GRID_W {
                let i = idx(x, y);
                let (c_mean, _) = neighbor_values(&old_concentration, x, y);
                let joule = self.field[i].powi(2) * self.conductance[i] * heat_multiplier;
                self.concentration[i] = (0.94 * old_concentration[i] + 0.06 * c_mean
                    - 0.002 * self.conductance[i])
                    .clamp(0.0, 1.0);
                self.heat[i] = (0.86 * old_heat[i] + 0.14 * joule).max(0.0);
            }
        }
        self.rng_state = rng.state;
    }

    fn opportunity_score(&self, index: usize) -> f64 {
        self.field[index]
            * self.concentration[index].max(0.01)
            * self.local_reservoir[index].max(0.0)
    }

    fn apply_contingency_once(&mut self, epoch: usize, environment: &EnvironmentDraw) {
        if self.reservoir_shift_applied
            || epoch < environment.contingency_epoch
            || environment.contingency_kind != ContingencyKind::ShiftReservoirLower
        {
            return;
        }
        let fraction = (0.15 + 0.25 * environment.contingency_severity).min(0.45);
        let mut moved = 0.0;
        for y in 0..GRID_H / 2 {
            for x in 0..GRID_W {
                let i = idx(x, y);
                let amount = self.local_reservoir[i] * fraction;
                self.local_reservoir[i] -= amount;
                moved += amount;
            }
        }
        let lower_cells = (GRID_H - GRID_H / 2) * GRID_W;
        for y in GRID_H / 2..GRID_H {
            for x in 0..GRID_W {
                self.local_reservoir[idx(x, y)] += moved / lower_cells as f64;
            }
        }
        self.reservoir_shift_applied = true;
    }

    fn choose_growth_site(
        &self,
        action: ActionId,
        epoch: usize,
        environment: &EnvironmentDraw,
        rng: &mut Rng64,
    ) -> Option<usize> {
        let (upper_fraction, lower_fraction) =
            effective_action_fractions(action, epoch, environment);
        let mut weights = [0.0_f64; CELLS];
        let mut total = 0.0;
        for y in 0..GRID_H {
            for x in 1..GRID_W {
                let i = idx(x, y);
                if self.local_reservoir[i] <= 0.0 {
                    continue;
                }
                let (neighbor_mean, neighbor_max) = neighbor_values(&self.conductance, x, y);
                let interface = (neighbor_max - self.conductance[i]).max(0.0) + 0.02;
                let lane = if y < GRID_H / 2 {
                    upper_fraction
                } else {
                    lower_fraction
                };
                let forward = 0.55 + 0.45 * x as f64 / (GRID_W - 1) as f64;
                let weight = lane
                    * forward
                    * self.field[i]
                    * self.concentration[i].max(0.01)
                    * self.local_reservoir[i]
                    * (interface + 0.15 * neighbor_mean);
                if weight.is_finite() && weight > 0.0 {
                    weights[i] = weight;
                    total += weight;
                }
            }
        }
        if total <= 0.0 {
            return None;
        }
        let mut draw = rng.unit() * total;
        for (i, weight) in weights.iter().enumerate() {
            if draw <= *weight {
                return Some(i);
            }
            draw -= *weight;
        }
        weights.iter().rposition(|weight| *weight > 0.0)
    }

    fn metrics(&self, environment: &EnvironmentDraw) -> Metrics {
        let drive = drive_scale(environment);
        let mut row_delivery = [0.0; GRID_H];
        let mut current = vec![0.0; CELLS];
        for y in 0..GRID_H {
            let resistance: f64 = (0..GRID_W)
                .map(|x| 1.0 / self.conductance[idx(x, y)].max(1.0e-5))
                .sum();
            row_delivery[y] = drive / resistance.max(1.0e-9);
            for x in 0..GRID_W {
                current[idx(x, y)] = row_delivery[y] / self.conductance[idx(x, y)].max(1.0e-5);
            }
        }
        let delivery: f64 = row_delivery.iter().sum::<f64>().max(1.0e-12);
        let peak_current = current.iter().copied().fold(0.0_f64, f64::max);
        let peak_heat = self.heat.iter().copied().fold(0.0_f64, f64::max);
        let current_per_delivery = peak_current / delivery;
        let heat_per_delivery_squared = peak_heat / delivery.powi(2).max(1.0e-18);
        let material_used = (self.material_initial - self.material_remaining).max(0.0);
        let mechanical_stress = maximum_gradient(&self.conductance);
        let concentration_proxy = current_per_delivery;
        let heat_proxy = heat_per_delivery_squared;
        let safe = current_per_delivery <= 2.0e5
            && heat_per_delivery_squared <= 2.0e9
            && material_used <= self.material_initial + 1.0e-10;
        let service = delivery
            - 1.0e-7 * current_per_delivery
            - 1.0e-11 * heat_per_delivery_squared
            - 0.02 * material_used;
        let upper = self.foot_metrics(0, GRID_H / 2, &current);
        let lower = self.foot_metrics(GRID_H / 2, GRID_H, &current);
        Metrics {
            delivery,
            current_per_delivery,
            heat_per_delivery_squared,
            material_used,
            concentration_proxy,
            heat_proxy,
            mechanical_stress_proxy: mechanical_stress,
            service,
            safe,
            upper,
            lower,
        }
    }

    fn foot_metrics(&self, y0: usize, y1: usize, current: &[f64]) -> FootMetrics {
        let indices: Vec<usize> = (y0..y1)
            .flat_map(|y| (0..GRID_W).map(move |x| idx(x, y)))
            .collect();
        let currents: Vec<f64> = indices.iter().map(|i| current[*i]).collect();
        let heats: Vec<f64> = indices.iter().map(|i| self.heat[*i]).collect();
        let stresses: Vec<f64> = indices
            .iter()
            .map(|i| {
                let x = i % GRID_W;
                let y = i / GRID_W;
                let (mean, _) = neighbor_values(&self.conductance, x, y);
                (self.conductance[*i] - mean).abs()
            })
            .collect();
        let temperatures: Vec<f64> = heats.iter().map(|value| 293.0 + 4.0 * value).collect();
        let conductive = indices
            .iter()
            .filter(|i| self.conductance[**i] >= 0.08)
            .count() as f64
            / indices.len() as f64;
        let interface = indices
            .iter()
            .filter(|i| {
                let x = *i % GRID_W;
                let y = *i / GRID_W;
                let (_, maximum) = neighbor_values(&self.conductance, x, y);
                maximum >= 0.08 && self.conductance[**i] < 0.08
            })
            .count() as f64
            / indices.len() as f64;
        FootMetrics {
            mean_current: mean(&currents),
            p95_current: percentile(&currents, 0.95),
            mean_heat: mean(&heats),
            p95_heat: percentile(&heats, 0.95),
            conductive_fraction: conductive,
            interface_fraction: interface,
            mean_reservoir: indices
                .iter()
                .map(|i| self.local_reservoir[*i])
                .sum::<f64>()
                / indices.len() as f64,
            mean_temperature: mean(&temperatures),
            p95_temperature: percentile(&temperatures, 0.95),
            mean_stress: mean(&stresses),
            p95_stress: percentile(&stresses, 0.95),
        }
    }
}

fn main() {
    if let Err(error) = real_main() {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}

fn real_main() -> Result<(), String> {
    let cli = parse_cli()?;
    match cli.command {
        Command::Run(args) => run(args),
        Command::Status { runtime } => print_status(&runtime),
    }
}

fn parse_cli() -> Result<Cli, String> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        return Err(usage());
    }
    match args[1].as_str() {
        "run" => {
            let mut run = RunArgs {
                output: PathBuf::from("output/full"),
                runtime: PathBuf::from("runtime/full"),
                actions: DEFAULT_ACTIONS,
                substrate_count: DEFAULT_SUBSTRATES,
                environment_count: DEFAULT_ENVIRONMENTS,
                master_seed: 319,
                checkpoint_every: 120,
                pulse_credits_per_trajectory: DEFAULT_PULSE_CREDITS_PER_TRAJECTORY,
                nice: 15,
                resume: false,
                earth_manifest: PathBuf::from("../material-manifests/earth-pedot.json"),
                space_manifest: PathBuf::from("../material-manifests/space-cbram.json"),
                sampling_policy: PathBuf::from("../material-sampler/policy.json"),
            };
            let mut i = 2;
            while i < args.len() {
                match args[i].as_str() {
                    "--resume" => {
                        run.resume = true;
                        i += 1;
                    }
                    name => {
                        let value = args.get(i + 1).ok_or_else(usage)?;
                        match name {
                            "--output" => run.output = PathBuf::from(value),
                            "--runtime" => run.runtime = PathBuf::from(value),
                            "--actions" => run.actions = parse_positive(value, name)?,
                            "--substrates" => run.substrate_count = parse_positive(value, name)?,
                            "--environments" => {
                                run.environment_count = parse_positive(value, name)?
                            }
                            "--seed" => run.master_seed = value.parse().map_err(|_| usage())?,
                            "--checkpoint-every" => {
                                run.checkpoint_every = parse_positive(value, name)?
                            }
                            "--pulse-credits-per-trajectory" => {
                                run.pulse_credits_per_trajectory =
                                    value.parse().map_err(|_| usage())?
                            }
                            "--nice" => run.nice = value.parse().map_err(|_| usage())?,
                            "--earth-manifest" => run.earth_manifest = PathBuf::from(value),
                            "--space-manifest" => run.space_manifest = PathBuf::from(value),
                            "--sampling-policy" => run.sampling_policy = PathBuf::from(value),
                            _ => return Err(format!("unknown argument {name}\n{}", usage())),
                        }
                        i += 2;
                    }
                }
            }
            if run.nice < 0 || run.nice > 20 {
                return Err("--nice must be between 0 and 20".into());
            }
            if run.pulse_credits_per_trajectory == 0
                || run.pulse_credits_per_trajectory > run.actions as u64
            {
                return Err(
                    "--pulse-credits-per-trajectory must be between 1 and --actions".into(),
                );
            }
            Ok(Cli {
                command: Command::Run(run),
            })
        }
        "status" => {
            let mut runtime = PathBuf::from("runtime/full");
            let mut i = 2;
            while i < args.len() {
                if args[i] != "--runtime" || i + 1 >= args.len() {
                    return Err(usage());
                }
                runtime = PathBuf::from(&args[i + 1]);
                i += 2;
            }
            Ok(Cli {
                command: Command::Status { runtime },
            })
        }
        _ => Err(usage()),
    }
}

fn parse_positive(value: &str, name: &str) -> Result<usize, String> {
    let parsed: usize = value
        .parse()
        .map_err(|_| format!("{name} requires a positive integer"))?;
    if parsed == 0 {
        Err(format!("{name} requires a positive integer"))
    } else {
        Ok(parsed)
    }
}

fn usage() -> String {
    "usage:\n  long-run-adaptive-screen run [--output PATH] [--runtime PATH] [--actions N] [--substrates N] [--environments N] [--seed N] [--checkpoint-every N] [--pulse-credits-per-trajectory N] [--nice 0..20] [--resume]\n  long-run-adaptive-screen status [--runtime PATH]".into()
}

fn run(args: RunArgs) -> Result<(), String> {
    if args.output == args.runtime {
        return Err("--output and --runtime must be different directories".into());
    }
    fs::create_dir_all(&args.output).map_err(io_error)?;
    fs::create_dir_all(&args.runtime).map_err(io_error)?;
    apply_nice(args.nice)?;
    install_signal_handler()?;

    let sources = Sources {
        earth: load_source(&args.earth_manifest)?,
        space: load_source(&args.space_manifest)?,
        policy: load_source(&args.sampling_policy)?,
    };
    validate_sources(&sources)?;
    let trajectories_total = args.substrate_count as u64 * args.environment_count as u64;
    let config = ScientificConfig {
        actions: args.actions,
        substrate_count: args.substrate_count,
        environment_count: args.environment_count,
        master_seed: args.master_seed,
        checkpoint_every_trajectories: args.checkpoint_every,
        pulse_credits_per_trajectory: args.pulse_credits_per_trajectory,
        initial_pulse_reservoir: trajectories_total * args.pulse_credits_per_trajectory,
        earth_manifest_sha256: sources.earth.sha256.clone(),
        space_manifest_sha256: sources.space.sha256.clone(),
        sampling_policy_sha256: sources.policy.sha256.clone(),
    };
    let draws = generate_draws(&sources, args.environment_count, args.master_seed)?;
    let checkpoint_path = args.runtime.join("checkpoint.json");
    let audit_path = args.output.join("choices.jsonl");
    let mut checkpoint = if args.resume {
        load_checkpoint(&checkpoint_path, &config)?
    } else {
        refuse_existing_run(&checkpoint_path, &audit_path)?;
        write_frozen_sources(&args.output, &sources, &config, &draws)?;
        Checkpoint {
            schema: CHECKPOINT_SCHEMA.into(),
            evidence_class: EVIDENCE_CLASS.into(),
            config: config.clone(),
            next_trajectory: 0,
            choices_completed: 0,
            audit_bytes: 0,
            elapsed_ns: 0,
            pulse: PulseLedger::new(config.initial_pulse_reservoir),
            trajectories: Vec::with_capacity(config.trajectories_total()),
        }
    };

    let mut audit_file = OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .open(&audit_path)
        .map_err(io_error)?;
    audit_file
        .set_len(checkpoint.audit_bytes)
        .map_err(io_error)?;
    audit_file.seek(SeekFrom::End(0)).map_err(io_error)?;
    let mut audit = BufWriter::new(audit_file);
    let started = Instant::now();
    let previous_elapsed = Duration::from_nanos(
        checkpoint
            .elapsed_ns
            .min(u64::MAX as u128)
            .try_into()
            .unwrap_or(u64::MAX),
    );

    write_status(
        &args,
        &checkpoint,
        previous_elapsed,
        "running",
        "screening-only run is active",
    )?;

    while checkpoint.next_trajectory < config.trajectories_total() {
        let trajectory_index = checkpoint.next_trajectory;
        let environment_index = trajectory_index / config.substrate_count;
        let substrate_index = trajectory_index % config.substrate_count;
        let substrate_seed = derive_seed(
            config.master_seed,
            environment_index as u64,
            substrate_index as u64,
        );
        let (records, result, next_pulse) = run_trajectory(
            &config,
            &draws[environment_index],
            trajectory_index,
            environment_index,
            substrate_index,
            substrate_seed,
            checkpoint.choices_completed,
            checkpoint.pulse,
        )?;
        for record in &records {
            serde_json::to_writer(&mut audit, record).map_err(json_error)?;
            audit.write_all(b"\n").map_err(io_error)?;
        }
        checkpoint.pulse = next_pulse;
        checkpoint.choices_completed += config.actions as u64;
        checkpoint.next_trajectory += 1;
        checkpoint.trajectories.push(result);

        let periodic = checkpoint.next_trajectory % config.checkpoint_every_trajectories == 0
            || checkpoint.next_trajectory == config.trajectories_total();
        let terminating = TERMINATE_REQUESTED.load(Ordering::SeqCst);
        if periodic || terminating {
            audit.flush().map_err(io_error)?;
            audit.get_ref().sync_all().map_err(io_error)?;
            checkpoint.audit_bytes = audit.get_ref().metadata().map_err(io_error)?.len();
            checkpoint.elapsed_ns = (previous_elapsed + started.elapsed()).as_nanos();
            atomic_json(&checkpoint_path, &checkpoint)?;
            let elapsed = previous_elapsed + started.elapsed();
            write_partial_summary(&args.output, &checkpoint, elapsed, "running")?;
            write_status(
                &args,
                &checkpoint,
                elapsed,
                if terminating { "stopped" } else { "running" },
                if terminating {
                    "SIGTERM observed after a complete trajectory; checkpoint is resumable"
                } else {
                    "atomic checkpoint complete"
                },
            )?;
        }
        if terminating {
            return Ok(());
        }
    }

    audit.flush().map_err(io_error)?;
    audit.get_ref().sync_all().map_err(io_error)?;
    checkpoint.audit_bytes = audit.get_ref().metadata().map_err(io_error)?.len();
    checkpoint.elapsed_ns = (previous_elapsed + started.elapsed()).as_nanos();
    if !checkpoint.pulse.conserved() {
        return Err("pulse conservation failed at completion".into());
    }
    atomic_json(&checkpoint_path, &checkpoint)?;
    let elapsed = previous_elapsed + started.elapsed();
    write_partial_summary(&args.output, &checkpoint, elapsed, "completed")?;
    write_status(
        &args,
        &checkpoint,
        elapsed,
        "completed",
        "all screening-only choices completed and pulse conservation proved",
    )?;
    println!(
        "completed choices={} trajectories={} elapsed_seconds={:.6} audit_bytes={} pulse_conserved={}",
        checkpoint.choices_completed,
        checkpoint.next_trajectory,
        elapsed.as_secs_f64(),
        checkpoint.audit_bytes,
        checkpoint.pulse.conserved()
    );
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn run_trajectory(
    config: &ScientificConfig,
    environment: &EnvironmentDraw,
    trajectory_index: usize,
    environment_index: usize,
    substrate_index: usize,
    substrate_seed: u64,
    choice_start: u64,
    mut pulse: PulseLedger,
) -> Result<(Vec<ChoiceRecord>, TrajectoryResult, PulseLedger), String> {
    let run_id = format!("screen-e{environment_index:03}-s{substrate_index:03}");
    let mut substrate = Substrate::new(substrate_seed, environment);
    substrate.update_field(environment);
    let mut controller =
        Controller::new(controller_config(&run_id, substrate_seed, config.actions))
            .map_err(|error| format!("invalid controller config: {error:?}"))?;
    let mut previous_hash = None;
    let mut previous_service = substrate.metrics(environment).service;
    let mut credit_account = 0_u64;
    let mut records = Vec::with_capacity(config.actions);
    let mut upper_actions = 0;
    let mut lower_actions = 0;
    let mut renewal_actions = 0;
    let mut renewal_triggers = 0;
    let mut earned_local = 0;
    let mut spent_local = 0;
    let mut safe_choices = 0;

    for epoch in 0..config.actions {
        let before = substrate.metrics(environment);
        let observation = make_observation(
            &run_id,
            epoch,
            previous_hash.clone(),
            &substrate,
            before,
            environment,
        )?;
        let observation_hash = observation
            .canonical_hash()
            .map_err(|error| error.to_string())?;
        previous_hash = Some(observation_hash.clone());
        let audit = controller.step(&observation);
        if let Some(reason) = audit.fail_reason {
            return Err(format!(
                "controller failed closed at trajectory {trajectory_index} epoch {epoch}: {reason:?}"
            ));
        }
        let spent = pulse.spend(&mut credit_account);
        spent_local += spent;
        substrate.apply_action(audit.action.id, spent, epoch, environment);
        let after = substrate.metrics(environment);
        let delta_service = after.service - previous_service;
        let earned = if after.safe
            && delta_service > 1.0e-12
            && earned_local < config.pulse_credits_per_trajectory
        {
            pulse.earn(&mut credit_account)
        } else {
            0
        };
        earned_local += earned;
        previous_service = after.service;
        if after.safe {
            safe_choices += 1;
        }
        match audit.action.id {
            ActionId::UpperHeavy => upper_actions += 1,
            ActionId::LowerHeavy => lower_actions += 1,
            ActionId::Dark => unreachable!("failed action handled above"),
        }
        if audit.action.selection_mode == SelectionMode::Renewal {
            renewal_actions += 1;
        }
        if audit.renewal.triggered {
            renewal_triggers += 1;
        }
        if !pulse.conserved() {
            return Err(format!(
                "pulse conservation failed at trajectory {trajectory_index} epoch {epoch}"
            ));
        }
        records.push(ChoiceRecord {
            schema: RECORD_SCHEMA.into(),
            evidence_class: EVIDENCE_CLASS.into(),
            choice_index: choice_start + epoch as u64,
            trajectory_index,
            environment_index,
            substrate_index,
            environment_seed: environment.seed,
            substrate_seed,
            regime: environment.regime.clone(),
            epoch,
            observation_sha256: observation_hash.0,
            policy_state_before_sha256: audit.policy_state_before_sha256.0,
            policy_state_after_sha256: audit.policy_state_after_sha256.0,
            action: audit.action.id,
            selection_mode: audit.action.selection_mode,
            propensity: audit.action.propensity,
            eligible_actions: audit.eligible_actions.clone(),
            controller_prior_update: audit.prior_update.clone(),
            controller_renewal: audit.renewal.clone(),
            renewal_triggered: audit.renewal.triggered,
            renewal_generation: audit.renewal.generation,
            contingency_active: epoch >= environment.contingency_epoch,
            contingency_kind: environment.contingency_kind.clone(),
            delivery: after.delivery,
            current_concentration_proxy: after.concentration_proxy,
            heat_proxy: after.heat_proxy,
            material_used: after.material_used,
            material_remaining: substrate.material_remaining,
            optical_energy_charged: substrate.optical_energy,
            electrical_energy_charged: substrate.electrical_energy,
            service: after.service,
            safe_useful_service_delta: delta_service,
            safe: after.safe,
            pulse_earned: earned,
            pulse_spent: spent,
            pulse_account_after: credit_account,
            pulse_trajectory_quota: config.pulse_credits_per_trajectory,
            pulse_trajectory_earned: earned_local,
            pulse_global_initial: pulse.initial,
            pulse_global_earned: pulse.earned,
            pulse_global_spent: pulse.spent,
            pulse_global_outstanding: pulse.outstanding,
            pulse_global_remaining: pulse.remaining,
            pulse_conserved: pulse.conserved(),
        });
    }
    let final_metrics = substrate.metrics(environment);
    Ok((
        records,
        TrajectoryResult {
            trajectory_index,
            environment_index,
            substrate_index,
            regime: environment.regime.clone(),
            final_delivery: final_metrics.delivery,
            final_service: final_metrics.service,
            final_current_concentration_proxy: final_metrics.concentration_proxy,
            final_heat_proxy: final_metrics.heat_proxy,
            material_used: final_metrics.material_used,
            upper_actions,
            lower_actions,
            renewal_actions,
            renewal_triggers,
            pulse_earned: earned_local,
            pulse_spent: spent_local,
            pulse_outstanding: credit_account,
            safe_choices,
        },
        pulse,
    ))
}

fn controller_config(run_id: &str, seed: u64, actions: usize) -> ControllerConfig {
    ControllerConfig {
        run_id: run_id.into(),
        seed,
        exploration_probability: 0.08,
        ridge_lambda: 1.0,
        confidence_multiplier: 0.0,
        initial_objective_uncertainty: [1.0e-6; 7],
        feature_scales: FeatureScales {
            delivery: 1.0e-3,
            current_per_delivery: 1.0e5,
            heat_per_delivery_squared: 1.0e8,
            mean_current_density: 1.0e3,
            p95_current_density: 1.0e3,
            mean_joule_density: 1.0,
            interface_contrast: 0.1,
        },
        renewal: RenewalConfig {
            prediction_error_scales: [4.0e-5, 250.0, 1.0e5, 0.01, 0.002, 1.0, 0.5],
            prediction_error_thresholds: [2.0; 7],
            consecutive_change_count: 2,
            renewal_length: 4,
            action_order: RenewalActionOrder::SeededBalanced,
            balanced_action_propensity: 0.5,
            seed: seed ^ 0xa319_5710_4e6e_6577,
        },
        delivery_tolerance: 1.0e-12,
        delivery_epsilon: 1.0e-14,
        source_voltage: 1.0,
        electrical_duty: 0.5,
        polarity: 1,
        safety: SafetyLimits {
            max_current_per_delivery: 2.0e5,
            max_heat_per_delivery_squared: 2.0e9,
            max_mechanical_stress: Some(1.5),
            max_material_used: 1.1,
            require_mechanical_stress: true,
        },
        budget: EnergyBudget {
            max_optical_energy: actions as f64 * BASE_OPTICAL_COST,
            max_electrical_energy: actions as f64 * BASE_ELECTRICAL_COST,
            optical_cost_per_action: BASE_OPTICAL_COST,
            electrical_cost_per_action: BASE_ELECTRICAL_COST,
        },
    }
}

fn make_observation(
    run_id: &str,
    epoch: usize,
    previous_hash: Option<Hash256>,
    substrate: &Substrate,
    metrics: Metrics,
    environment: &EnvironmentDraw,
) -> Result<Observation, String> {
    let topology_sha256 = hash_serialized(substrate)?;
    let model_sha256 = sha256_hex(
        format!(
            "reduced-mechanism/v1:{}:{}:{}",
            environment.source_manifest_sha256,
            environment.sampling_policy_sha256,
            environment.seed
        )
        .as_bytes(),
    );
    Ok(Observation {
        schema: OBSERVATION_SCHEMA.into(),
        run_id: run_id.into(),
        epoch: epoch as u64,
        previous_observation_sha256: previous_hash,
        topology_sha256: Hash256(topology_sha256),
        // The tested candidate names this provenance slot after its original MOOSE
        // boundary. Here it hashes the reduced-mechanism version and frozen inputs.
        moose_sha256: Hash256(model_sha256),
        units: UnitStrings::pending_si(),
        channels: ChannelAvailability {
            material_reservoir: true,
            temperature: true,
            mechanical_stress: true,
        },
        footprints: [
            foot_observation(metrics.upper),
            foot_observation(metrics.lower),
        ],
        global: GlobalObservation {
            terminal_flux: metrics.delivery,
            metal_fraction: metrics.material_used / substrate.material_initial,
            joule_integral: substrate.heat.iter().sum(),
            peak_current_density: metrics.current_per_delivery * metrics.delivery,
            peak_joule_density: metrics.heat_per_delivery_squared * metrics.delivery.powi(2),
            peak_mechanical_stress: Some(metrics.mechanical_stress_proxy),
            material_used: metrics.material_used,
            cumulative_optical_energy: substrate.optical_energy,
            cumulative_electrical_energy: substrate.electrical_energy,
        },
    })
}

fn foot_observation(metrics: FootMetrics) -> FootprintObservation {
    FootprintObservation {
        mean_current_density: metrics.mean_current,
        p95_current_density: metrics.p95_current.max(metrics.mean_current),
        mean_joule_density: metrics.mean_heat,
        p95_joule_density: metrics.p95_heat.max(metrics.mean_heat),
        conductive_fraction: metrics.conductive_fraction,
        interface_fraction: metrics.interface_fraction,
        mean_available_reservoir: Some(metrics.mean_reservoir),
        mean_temperature: Some(metrics.mean_temperature),
        p95_temperature: Some(metrics.p95_temperature.max(metrics.mean_temperature)),
        mean_mechanical_stress: Some(metrics.mean_stress),
        p95_mechanical_stress: Some(metrics.p95_stress.max(metrics.mean_stress)),
    }
}

fn generate_draws(
    sources: &Sources,
    count: usize,
    master_seed: u64,
) -> Result<Vec<EnvironmentDraw>, String> {
    let mut draws = Vec::with_capacity(count);
    for index in 0..count {
        let regime = if index % 2 == 0 {
            Regime::EarthPedotExploratory
        } else {
            Regime::SpaceCbramScreening
        };
        let seed = derive_seed(master_seed ^ 0x656e_7669_726f_6e6d, index as u64, 0);
        draws.push(generate_draw(sources, index, seed, regime)?);
    }
    Ok(draws)
}

fn generate_draw(
    sources: &Sources,
    index: usize,
    seed: u64,
    regime: Regime,
) -> Result<EnvironmentDraw, String> {
    let manifest = match regime {
        Regime::EarthPedotExploratory => &sources.earth,
        Regime::SpaceCbramScreening => &sources.space,
    };
    let policy_regime = sources
        .policy
        .value
        .pointer(&format!("/regimes/{}", regime.short()))
        .ok_or_else(|| format!("policy missing {} regime", regime.short()))?;
    let mut rng = Rng64::new(seed);
    let mut parameters = BTreeMap::new();
    let axes = policy_regime
        .get("sample_axes")
        .and_then(Value::as_array)
        .ok_or("policy sample_axes must be an array")?;
    for axis in axes {
        let path = axis
            .get("path")
            .and_then(Value::as_str)
            .ok_or("sample axis path missing")?;
        let quantity = value_at_dot_path(&manifest.value, path)
            .ok_or_else(|| format!("manifest missing sample axis {path}"))?;
        let status = quantity
            .get("status")
            .and_then(Value::as_str)
            .ok_or_else(|| format!("{path} status missing"))?;
        if status != "proposed" {
            return Err(format!("sample axis {path} is not proposed"));
        }
        let minimum = quantity
            .pointer("/allowable_range/minimum")
            .and_then(Value::as_f64)
            .ok_or_else(|| format!("{path} minimum missing"))?;
        let maximum = quantity
            .pointer("/allowable_range/maximum")
            .and_then(Value::as_f64)
            .ok_or_else(|| format!("{path} maximum missing"))?;
        if !minimum.is_finite() || !maximum.is_finite() || minimum > maximum {
            return Err(format!("{path} range invalid"));
        }
        let unit = quantity
            .get("unit")
            .and_then(Value::as_str)
            .ok_or_else(|| format!("{path} unit missing"))?;
        parameters.insert(
            path.into(),
            SampledParameter {
                value: normalized_float(rng.range(minimum, maximum)),
                unit: unit.into(),
                source_status: status.into(),
                allowable_minimum: minimum,
                allowable_maximum: maximum,
            },
        );
    }
    let options_value = policy_regime
        .get("admitted_options")
        .and_then(Value::as_object)
        .ok_or("policy admitted_options missing")?;
    let constraints = policy_regime
        .get("constraints")
        .and_then(Value::as_array)
        .ok_or("policy constraints missing")?;
    let options = sample_options(&mut rng, options_value, constraints)?;
    let blockers = manifest
        .value
        .get("required_unset_gates")
        .and_then(Value::as_object)
        .ok_or("manifest required_unset_gates missing")?
        .iter()
        .filter_map(|(name, quantity)| {
            (quantity.get("status").and_then(Value::as_str) == Some("required-unset")
                && quantity.get("value").is_some_and(Value::is_null))
            .then_some(format!("required_unset_gates.{name}"))
        })
        .collect::<Vec<_>>();
    let static_rejections = policy_regime
        .get("static_rejections")
        .and_then(Value::as_array)
        .cloned()
        .ok_or("policy static_rejections missing")?;
    let contingency_kind = match rng.index(4) {
        0 => ContingencyKind::SwapChannelConsequences,
        1 => ContingencyKind::DegradeUpperConsequence,
        2 => ContingencyKind::UpperHeatCoupling,
        _ => ContingencyKind::ShiftReservoirLower,
    };
    Ok(EnvironmentDraw {
        schema: DRAW_SCHEMA.into(),
        evidence_class: EVIDENCE_CLASS.into(),
        index,
        seed,
        regime: regime.clone(),
        mode: regime.mode().into(),
        candidate_id: regime.candidate_id().into(),
        source_manifest_sha256: manifest.sha256.clone(),
        sampling_policy_sha256: sources.policy.sha256.clone(),
        sampled_parameters: parameters,
        selected_options: options,
        required_unset_blockers: blockers,
        static_rejections,
        contingency_epoch: 48 + rng.index(25),
        contingency_kind,
        contingency_severity: normalized_float(rng.range(0.55, 0.90)),
        interpretation_boundary: "Deterministic reduced-mechanism draw only; no wet-lab, hardware, chemical, radiation, reliability, or qualification claim.".into(),
    })
}

fn sample_options(
    rng: &mut Rng64,
    admitted: &Map<String, Value>,
    constraints: &[Value],
) -> Result<BTreeMap<String, String>, String> {
    for _ in 0..128 {
        let mut selected = BTreeMap::new();
        let mut names: Vec<&String> = admitted.keys().collect();
        names.sort();
        for name in names {
            let values = admitted[name]
                .as_array()
                .ok_or_else(|| format!("option {name} must be an array"))?;
            if values.is_empty() {
                return Err(format!("option {name} has no values"));
            }
            let value = values[rng.index(values.len())]
                .as_str()
                .ok_or_else(|| format!("option {name} contains a non-string"))?;
            selected.insert(name.clone(), value.into());
        }
        if constraints_satisfied(&selected, constraints)? {
            return Ok(selected);
        }
    }
    Err("no admitted option combination within 128 attempts".into())
}

fn constraints_satisfied(
    selected: &BTreeMap<String, String>,
    constraints: &[Value],
) -> Result<bool, String> {
    for constraint in constraints {
        let condition = constraint
            .get("if")
            .and_then(Value::as_object)
            .ok_or("constraint if object missing")?;
        let matches = condition.iter().all(|(key, value)| {
            value
                .as_str()
                .is_some_and(|expected| selected.get(key).is_some_and(|actual| actual == expected))
        });
        if !matches {
            continue;
        }
        if let Some(required) = constraint.get("requires").and_then(Value::as_object)
            && required.iter().any(|(key, value)| {
                value.as_str().is_some_and(|expected| {
                    selected.get(key).is_none_or(|actual| actual != expected)
                })
            })
        {
            return Ok(false);
        }
        if let Some(forbidden) = constraint.get("forbids").and_then(Value::as_object)
            && forbidden.iter().any(|(key, value)| {
                value.as_str().is_some_and(|expected| {
                    selected.get(key).is_some_and(|actual| actual == expected)
                })
            })
        {
            return Ok(false);
        }
    }
    Ok(true)
}

fn validate_sources(sources: &Sources) -> Result<(), String> {
    validate_manifest(&sources.earth, "earth", "earth-pedot", "space")?;
    validate_manifest(&sources.space, "space", "space-cbram", "earth")?;
    if sources
        .policy
        .value
        .get("policy_version")
        .and_then(Value::as_str)
        != Some("1.0.0")
    {
        return Err("sampling policy version must be 1.0.0".into());
    }
    for (regime, manifest) in [("earth", &sources.earth), ("space", &sources.space)] {
        let policy = sources
            .policy
            .value
            .pointer(&format!("/regimes/{regime}"))
            .ok_or_else(|| format!("policy missing {regime}"))?;
        if policy.get("candidate_id") != manifest.value.get("candidate_id") {
            return Err(format!("{regime} policy candidate does not match manifest"));
        }
        let axes = policy
            .get("sample_axes")
            .and_then(Value::as_array)
            .ok_or_else(|| format!("{regime} policy has no sample axes"))?;
        for axis in axes {
            let path = axis
                .get("path")
                .and_then(Value::as_str)
                .ok_or("sample axis path missing")?;
            let quantity = value_at_dot_path(&manifest.value, path)
                .ok_or_else(|| format!("{regime} manifest lacks {path}"))?;
            if quantity.get("status").and_then(Value::as_str) != Some("proposed") {
                return Err(format!("{path} is not proposed"));
            }
        }
    }
    Ok(())
}

fn validate_manifest(
    source: &SourceDocument,
    regime: &str,
    candidate_id: &str,
    forbidden_regime: &str,
) -> Result<(), String> {
    if source.value.get("schema_version").and_then(Value::as_str) != Some("1.0.0")
        || source.value.get("regime").and_then(Value::as_str) != Some(regime)
        || source.value.get("candidate_id").and_then(Value::as_str) != Some(candidate_id)
        || source
            .value
            .pointer("/separation_contract/regime_id")
            .and_then(Value::as_str)
            != Some(regime)
        || source
            .value
            .pointer("/separation_contract/forbidden_regime_id")
            .and_then(Value::as_str)
            != Some(forbidden_regime)
        || source
            .value
            .pointer("/separation_contract/prohibits_cross_regime_parameter_import")
            .and_then(Value::as_bool)
            != Some(true)
    {
        return Err(format!(
            "{} fails manifest identity or separation validation",
            source.path.display()
        ));
    }
    Ok(())
}

fn load_source(path: &Path) -> Result<SourceDocument, String> {
    let bytes = fs::read(path).map_err(io_error)?;
    let value = serde_json::from_slice(&bytes).map_err(json_error)?;
    Ok(SourceDocument {
        path: path.to_path_buf(),
        sha256: sha256_hex(&bytes),
        bytes,
        value,
    })
}

fn write_frozen_sources(
    output: &Path,
    sources: &Sources,
    config: &ScientificConfig,
    draws: &[EnvironmentDraw],
) -> Result<(), String> {
    let frozen = output.join("frozen-manifests");
    fs::create_dir_all(&frozen).map_err(io_error)?;
    atomic_bytes(&frozen.join("earth-pedot.json"), &sources.earth.bytes)?;
    atomic_bytes(&frozen.join("space-cbram.json"), &sources.space.bytes)?;
    atomic_bytes(&frozen.join("sampling-policy.json"), &sources.policy.bytes)?;
    let mut draw_bytes = Vec::new();
    for draw in draws {
        serde_json::to_writer(&mut draw_bytes, draw).map_err(json_error)?;
        draw_bytes.push(b'\n');
    }
    atomic_bytes(&output.join("environment-draws.jsonl"), &draw_bytes)?;
    let blockers: Vec<Value> = draws
        .iter()
        .map(|draw| {
            json!({
                "environment_index": draw.index,
                "regime": draw.regime,
                "required_unset_blockers": draw.required_unset_blockers,
            })
        })
        .collect();
    let manifest = json!({
        "schema": RUN_SCHEMA,
        "evidence_class": EVIDENCE_CLASS,
        "config": config,
        "source_hashes": {
            "earth_manifest_sha256": sources.earth.sha256,
            "space_manifest_sha256": sources.space.sha256,
            "sampling_policy_sha256": sources.policy.sha256,
        },
        "required_unset_blockers_by_environment": blockers,
        "interpretation_boundary": "All results are reduced-mechanism screening only. Pulse credits are finite dimensionless scheduling credits, not sugar, chemistry, energy, or matter.",
    });
    atomic_json(&output.join("run-manifest.json"), &manifest)
}

fn load_checkpoint(path: &Path, expected: &ScientificConfig) -> Result<Checkpoint, String> {
    let checkpoint: Checkpoint =
        serde_json::from_slice(&fs::read(path).map_err(io_error)?).map_err(json_error)?;
    if checkpoint.schema != CHECKPOINT_SCHEMA
        || checkpoint.evidence_class != EVIDENCE_CLASS
        || &checkpoint.config != expected
        || !checkpoint.pulse.conserved()
        || checkpoint.choices_completed
            != checkpoint.next_trajectory as u64 * expected.actions as u64
        || checkpoint.trajectories.len() != checkpoint.next_trajectory
    {
        return Err("checkpoint is inconsistent with requested run".into());
    }
    Ok(checkpoint)
}

fn refuse_existing_run(checkpoint: &Path, audit: &Path) -> Result<(), String> {
    if checkpoint.exists() || audit.exists() {
        Err("existing checkpoint or audit log found; use --resume or choose new directories".into())
    } else {
        Ok(())
    }
}

fn write_status(
    args: &RunArgs,
    checkpoint: &Checkpoint,
    elapsed: Duration,
    state: &str,
    message: &str,
) -> Result<(), String> {
    let choices_total = checkpoint.config.choices_total();
    let seconds = elapsed.as_secs_f64();
    let rate = if seconds > 0.0 {
        checkpoint.choices_completed as f64 / seconds
    } else {
        0.0
    };
    let remaining = if rate > 0.0 {
        Some((choices_total - checkpoint.choices_completed) as f64 / rate)
    } else {
        None
    };
    let status = Status {
        schema: STATUS_SCHEMA,
        evidence_class: EVIDENCE_CLASS,
        state,
        choices_completed: checkpoint.choices_completed,
        choices_total,
        trajectories_completed: checkpoint.next_trajectory,
        trajectories_total: checkpoint.config.trajectories_total(),
        fraction_complete: checkpoint.choices_completed as f64 / choices_total as f64,
        elapsed_seconds: seconds,
        choices_per_second: rate,
        estimated_seconds_remaining: remaining,
        pulse: checkpoint.pulse,
        checkpoint: args.runtime.join("checkpoint.json").display().to_string(),
        audit_log: args.output.join("choices.jsonl").display().to_string(),
        message,
    };
    atomic_json(&args.runtime.join("status.json"), &status)?;
    atomic_json(&args.output.join("status.json"), &status)?;
    let intel = format!(
        "LONG-RUN ADAPTIVE SCREEN — SCREENING ONLY\nSTATE: {state}\nCHOICES: {} / {} ({:.3}%)\nTRAJECTORIES: {} / {}\nRATE: {:.1} choices/s\nETA: {}\nPULSE: initial={} earned={} spent={} outstanding={} remaining={} conserved={}\n{}\n",
        checkpoint.choices_completed,
        choices_total,
        100.0 * checkpoint.choices_completed as f64 / choices_total as f64,
        checkpoint.next_trajectory,
        checkpoint.config.trajectories_total(),
        rate,
        remaining
            .map(format_duration)
            .unwrap_or_else(|| "unknown".into()),
        checkpoint.pulse.initial,
        checkpoint.pulse.earned,
        checkpoint.pulse.spent,
        checkpoint.pulse.outstanding,
        checkpoint.pulse.remaining,
        checkpoint.pulse.conserved(),
        message,
    );
    atomic_bytes(&args.output.join("intel-status.txt"), intel.as_bytes())
}

fn write_partial_summary(
    output: &Path,
    checkpoint: &Checkpoint,
    elapsed: Duration,
    state: &str,
) -> Result<(), String> {
    if checkpoint.trajectories.is_empty() {
        return Ok(());
    }
    let values = |extract: fn(&TrajectoryResult) -> f64| {
        checkpoint
            .trajectories
            .iter()
            .map(extract)
            .collect::<Vec<_>>()
    };
    let summary = Summary {
        schema: SUMMARY_SCHEMA,
        evidence_class: EVIDENCE_CLASS,
        state,
        choices_completed: checkpoint.choices_completed,
        choices_total: checkpoint.config.choices_total(),
        trajectories_completed: checkpoint.trajectories.len(),
        trajectories_total: checkpoint.config.trajectories_total(),
        elapsed_seconds: elapsed.as_secs_f64(),
        pulse: checkpoint.pulse,
        pulse_conservation_proven: checkpoint.pulse.conserved(),
        final_delivery: quantiles(&values(|item| item.final_delivery)),
        final_service: quantiles(&values(|item| item.final_service)),
        final_current_concentration_proxy: quantiles(&values(|item| {
            item.final_current_concentration_proxy
        })),
        final_heat_proxy: quantiles(&values(|item| item.final_heat_proxy)),
        material_used: quantiles(&values(|item| item.material_used)),
        earth_trajectories: checkpoint
            .trajectories
            .iter()
            .filter(|item| item.regime == Regime::EarthPedotExploratory)
            .count(),
        space_trajectories: checkpoint
            .trajectories
            .iter()
            .filter(|item| item.regime == Regime::SpaceCbramScreening)
            .count(),
        renewal_triggers: checkpoint
            .trajectories
            .iter()
            .map(|item| item.renewal_triggers)
            .sum(),
        interpretation_boundary: "Reduced-mechanism screening only; no material performance, chemical, hardware, reliability, mission, intelligence, or qualification claim.",
    };
    atomic_json(&output.join("summary.json"), &summary)
}

fn quantiles(values: &[f64]) -> Quantiles {
    Quantiles {
        minimum: percentile(values, 0.0),
        p05: percentile(values, 0.05),
        p25: percentile(values, 0.25),
        p50: percentile(values, 0.50),
        p75: percentile(values, 0.75),
        p95: percentile(values, 0.95),
        maximum: percentile(values, 1.0),
    }
}

fn print_status(runtime: &Path) -> Result<(), String> {
    let path = runtime.join("status.json");
    let bytes = fs::read(&path).map_err(io_error)?;
    let value: Value = serde_json::from_slice(&bytes).map_err(json_error)?;
    println!(
        "{}",
        serde_json::to_string_pretty(&value).map_err(json_error)?
    );
    Ok(())
}

fn apply_nice(value: i32) -> Result<(), String> {
    let result = unsafe { libc::setpriority(libc::PRIO_PROCESS, 0, value) };
    if result != 0 {
        return Err(format!(
            "could not set process nice level to {value}: {}",
            std::io::Error::last_os_error()
        ));
    }
    Ok(())
}

fn install_signal_handler() -> Result<(), String> {
    let previous = unsafe {
        libc::signal(
            libc::SIGTERM,
            handle_sigterm as *const () as libc::sighandler_t,
        )
    };
    if previous == libc::SIG_ERR {
        Err(format!(
            "could not install SIGTERM handler: {}",
            std::io::Error::last_os_error()
        ))
    } else {
        Ok(())
    }
}

fn atomic_json<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
    let bytes = serde_json::to_vec_pretty(value).map_err(json_error)?;
    atomic_bytes(path, &bytes)
}

fn atomic_bytes(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let parent = path.parent().ok_or("atomic path has no parent")?;
    fs::create_dir_all(parent).map_err(io_error)?;
    let temp = parent.join(format!(
        ".{}.{}.tmp",
        path.file_name()
            .and_then(|value| value.to_str())
            .unwrap_or("write"),
        std::process::id()
    ));
    {
        let mut file = File::create(&temp).map_err(io_error)?;
        file.write_all(bytes).map_err(io_error)?;
        file.sync_all().map_err(io_error)?;
    }
    fs::rename(&temp, path).map_err(io_error)?;
    File::open(parent)
        .and_then(|file| file.sync_all())
        .map_err(io_error)?;
    Ok(())
}

fn hash_serialized<T: Serialize>(value: &T) -> Result<String, String> {
    Ok(sha256_hex(&serde_json::to_vec(value).map_err(json_error)?))
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut text = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write as _;
        write!(&mut text, "{byte:02x}").expect("write to String");
    }
    text
}

fn drive_scale(environment: &EnvironmentDraw) -> f64 {
    match environment.regime {
        Regime::EarthPedotExploratory => {
            let voltage = parameter(
                environment,
                "numeric_parameters.growth_drive.growth_voltage_peak_to_peak",
                8.5,
            );
            let duty = parameter(
                environment,
                "numeric_parameters.growth_drive.growth_duty_fraction",
                0.5,
            );
            let irradiance = parameter(
                environment,
                "numeric_parameters.optical_interface.projected_irradiance",
                50.0,
            );
            (0.55 + 0.045 * voltage + 0.20 * duty + 0.001 * irradiance).clamp(0.4, 1.2)
        }
        Regime::SpaceCbramScreening => {
            let temperature = parameter(
                environment,
                "numeric_parameters.vacuum_environment.comparison_temperature",
                293.0,
            );
            let electrolyte = parameter(
                environment,
                "numeric_parameters.geometry.solid_electrolyte_thickness",
                80.0,
            );
            (0.82 + 0.002 * (temperature - 291.0) - 0.002 * (electrolyte - 72.0)).clamp(0.55, 1.0)
        }
    }
}

fn parameter(environment: &EnvironmentDraw, name: &str, fallback: f64) -> f64 {
    environment
        .sampled_parameters
        .get(name)
        .map(|value| value.value)
        .unwrap_or(fallback)
}

fn effective_action_fractions(
    action: ActionId,
    epoch: usize,
    environment: &EnvironmentDraw,
) -> (f64, f64) {
    let base = match action {
        ActionId::UpperHeavy => (0.75, 0.25),
        ActionId::LowerHeavy => (0.25, 0.75),
        ActionId::Dark => (0.0, 0.0),
    };
    if epoch < environment.contingency_epoch {
        return base;
    }
    match environment.contingency_kind {
        ContingencyKind::SwapChannelConsequences => (base.1, base.0),
        ContingencyKind::DegradeUpperConsequence => {
            let upper = base.0 * (1.0 - environment.contingency_severity);
            let total = upper + base.1;
            (upper / total, base.1 / total)
        }
        _ => base,
    }
}

fn contingency_heat_multiplier(
    action: ActionId,
    epoch: usize,
    environment: &EnvironmentDraw,
) -> f64 {
    if epoch >= environment.contingency_epoch
        && environment.contingency_kind == ContingencyKind::UpperHeatCoupling
        && action == ActionId::UpperHeavy
    {
        1.0 + 2.0 * environment.contingency_severity
    } else {
        1.0
    }
}

fn idx(x: usize, y: usize) -> usize {
    y * GRID_W + x
}

fn neighbor_values(values: &[f64], x: usize, y: usize) -> (f64, f64) {
    let mut sum = 0.0;
    let mut maximum = 0.0_f64;
    let mut count = 0;
    if x > 0 {
        let value = values[idx(x - 1, y)];
        sum += value;
        maximum = maximum.max(value);
        count += 1;
    }
    if x + 1 < GRID_W {
        let value = values[idx(x + 1, y)];
        sum += value;
        maximum = maximum.max(value);
        count += 1;
    }
    if y > 0 {
        let value = values[idx(x, y - 1)];
        sum += value;
        maximum = maximum.max(value);
        count += 1;
    }
    if y + 1 < GRID_H {
        let value = values[idx(x, y + 1)];
        sum += value;
        maximum = maximum.max(value);
        count += 1;
    }
    (sum / count as f64, maximum)
}

fn maximum_gradient(values: &[f64]) -> f64 {
    let mut maximum = 0.0_f64;
    for y in 0..GRID_H {
        for x in 0..GRID_W {
            let i = idx(x, y);
            let (mean, _) = neighbor_values(values, x, y);
            maximum = maximum.max((values[i] - mean).abs());
        }
    }
    maximum
}

fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len().max(1) as f64
}

fn percentile(values: &[f64], quantile: f64) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f64::total_cmp);
    let position = quantile.clamp(0.0, 1.0) * (sorted.len() - 1) as f64;
    let lower = position.floor() as usize;
    let upper = position.ceil() as usize;
    if lower == upper {
        sorted[lower]
    } else {
        let fraction = position - lower as f64;
        sorted[lower] * (1.0 - fraction) + sorted[upper] * fraction
    }
}

fn derive_seed(master: u64, first: u64, second: u64) -> u64 {
    let mut rng = Rng64::new(master ^ first.rotate_left(17) ^ second.rotate_left(41));
    rng.next_u64()
}

fn normalized_float(value: f64) -> f64 {
    format!("{value:.12}").parse().unwrap_or(value)
}

fn value_at_dot_path<'a>(value: &'a Value, path: &str) -> Option<&'a Value> {
    path.split('.')
        .try_fold(value, |current, part| current.get(part))
}

fn format_duration(seconds: f64) -> String {
    if !seconds.is_finite() {
        return "unknown".into();
    }
    let seconds = seconds.max(0.0) as u64;
    format!(
        "{:02}:{:02}:{:02}",
        seconds / 3600,
        (seconds % 3600) / 60,
        seconds % 60
    )
}

fn io_error(error: std::io::Error) -> String {
    error.to_string()
}

fn json_error(error: serde_json::Error) -> String {
    error.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn source_paths() -> (PathBuf, PathBuf, PathBuf) {
        let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        (
            base.join("../material-manifests/earth-pedot.json"),
            base.join("../material-manifests/space-cbram.json"),
            base.join("../material-sampler/policy.json"),
        )
    }

    fn sources() -> Sources {
        let (earth, space, policy) = source_paths();
        let sources = Sources {
            earth: load_source(&earth).unwrap(),
            space: load_source(&space).unwrap(),
            policy: load_source(&policy).unwrap(),
        };
        validate_sources(&sources).unwrap();
        sources
    }

    #[test]
    fn exact_full_choice_count_is_1_728_000() {
        assert_eq!(
            (DEFAULT_ACTIONS * DEFAULT_SUBSTRATES * DEFAULT_ENVIRONMENTS) as u64,
            1_728_000
        );
    }

    #[test]
    fn pulse_ledger_proves_both_conservation_equalities() {
        let mut ledger = PulseLedger::new(4);
        let mut account = 0;
        assert_eq!(ledger.earn(&mut account), 1);
        assert_eq!(ledger.earn(&mut account), 1);
        assert_eq!(ledger.spend(&mut account), 1);
        assert!(ledger.conserved());
        assert_eq!(
            ledger.initial,
            ledger.remaining + ledger.spent + ledger.outstanding
        );
        assert_eq!(ledger.earned, ledger.spent + ledger.outstanding);
    }

    #[test]
    fn environment_draws_are_deterministic_and_preserve_space_blockers() {
        let sources = sources();
        let first = generate_draws(&sources, 4, 319).unwrap();
        let second = generate_draws(&sources, 4, 319).unwrap();
        assert_eq!(first, second);
        assert_eq!(first[1].required_unset_blockers.len(), 8);
        assert!(first[0].required_unset_blockers.is_empty());
        assert_eq!(first[0].source_manifest_sha256, sources.earth.sha256);
        assert_eq!(first[1].source_manifest_sha256, sources.space.sha256);
    }

    #[test]
    fn reduced_substrate_is_deterministic_for_seed_and_draw() {
        let sources = sources();
        let draw = generate_draws(&sources, 1, 319).unwrap().remove(0);
        let mut first = Substrate::new(571, &draw);
        let mut second = Substrate::new(571, &draw);
        for epoch in 0..12 {
            first.apply_action(ActionId::UpperHeavy, (epoch % 2) as u64, epoch, &draw);
            second.apply_action(ActionId::UpperHeavy, (epoch % 2) as u64, epoch, &draw);
        }
        assert_eq!(
            hash_serialized(&first).unwrap(),
            hash_serialized(&second).unwrap()
        );
        assert!(first.material_remaining <= first.material_initial);
    }

    #[test]
    fn controller_integration_retains_hash_action_and_pulse_audit() {
        let sources = sources();
        let draw = generate_draws(&sources, 1, 319).unwrap().remove(0);
        let config = ScientificConfig {
            actions: 8,
            substrate_count: 1,
            environment_count: 1,
            master_seed: 319,
            checkpoint_every_trajectories: 1,
            pulse_credits_per_trajectory: 4,
            initial_pulse_reservoir: 4,
            earth_manifest_sha256: sources.earth.sha256.clone(),
            space_manifest_sha256: sources.space.sha256.clone(),
            sampling_policy_sha256: sources.policy.sha256.clone(),
        };
        let (records, result, pulse) =
            run_trajectory(&config, &draw, 0, 0, 0, 571, 0, PulseLedger::new(4)).unwrap();
        assert_eq!(records.len(), 8);
        assert_eq!(result.upper_actions + result.lower_actions, 8);
        assert!(records.iter().all(|record| record.pulse_conserved));
        assert!(
            records
                .iter()
                .all(|record| record.observation_sha256.len() == 64)
        );
        assert!(pulse.conserved());
    }
}
